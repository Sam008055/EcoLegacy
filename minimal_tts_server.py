"""
Local TTS server — voice cloning using each character's reference clip in
web/public/audio (same paths as web/utils/characters.ts).

Uses the HuggingFace F5-TTS Gradio space (no local f5-tts install — keeps disk small).
Set HUGGINGFACE_TOKEN in web/.env.local or repo .env.
"""

import os
import hashlib
import time
import shutil
import logging
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

from character_tts_config import get_character_tts, AUDIO_DIR, CHARACTER_TTS

# Load tokens from web/.env.local first, then repo root
_REPO = Path(__file__).resolve().parent
load_dotenv(_REPO / "web" / ".env.local")
load_dotenv(_REPO / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

CACHE_DIR = Path("./tts_cache")
CACHE_DIR.mkdir(exist_ok=True)

HF_SPACE = "chenxie95/Cross-Lingual_F5-TTS_Space"


def get_hf_tokens() -> list[str]:
    keys = [
        "HUGGINGFACE_TOKEN",
        "HUGGINGFACE_TOKEN_1",
        "HUGGINGFACE_TOKEN_2",
        "HUGGINGFACE_TOKEN_3",
        "HUGGINGFACE_TOKEN_4",
        "HUGGINGFACE_TOKEN_5",
    ]
    return [os.environ[k] for k in keys if os.environ.get(k)]


def get_cache_path(text: str, character_id: str) -> Path:
    cache_key = hashlib.md5(f"{text}_{character_id}_ref".encode()).hexdigest()
    return CACHE_DIR / f"{cache_key}.wav"


def _copy_gradio_output_to_path(src, dest: Path) -> bool:
    if src is None:
        return False
    src_path = Path(src) if not isinstance(src, str) else Path(src)
    if not src_path.is_file():
        return False
    shutil.copy2(src_path, dest)
    return dest.is_file() and dest.stat().st_size > 100


def _copy_gradio_output_to_path(src, dest: Path) -> bool:
    if src is None:
        return False
    src_path = Path(src) if not isinstance(src, str) else Path(src)
    if not src_path.is_file():
        return False
    shutil.copy2(src_path, dest)
    return dest.is_file() and dest.stat().st_size > 100


def generate_reference_clone(text: str, character_id: str, output_path: Path) -> bool:
    """Clone voice via HF F5-TTS space + character reference wav/mp3."""
    generate_reference_clone._last_error = None  # type: ignore[attr-defined]

    cfg = get_character_tts(character_id)
    if not cfg:
        generate_reference_clone._last_error = f"Unknown character_id: {character_id}"  # type: ignore[attr-defined]
        return False

    ref_path: Path = cfg["reference_audio"]
    if not ref_path.is_file():
        generate_reference_clone._last_error = (  # type: ignore[attr-defined]
            f"Reference audio missing: {ref_path.name}. Add it under web/public/audio/"
        )
        return False

    tokens = get_hf_tokens()
    if not tokens:
        generate_reference_clone._last_error = (  # type: ignore[attr-defined]
            "No HUGGINGFACE_TOKEN in web/.env.local"
        )
        return False

    gen_text = text.replace("\n", " ").strip()
    if len(gen_text) > 500:
        gen_text = gen_text[:500] + "..."

    # Get reference text for better voice matching
    ref_text = cfg.get("reference_text", "")

    logger.info("HF F5 clone | character=%s | ref=%s | ref_text=%s", 
                character_id, ref_path.name, bool(ref_text))

    try:
        from gradio_client import Client, handle_file
    except ImportError:
        generate_reference_clone._last_error = "pip install gradio-client python-dotenv"  # type: ignore[attr-defined]
        return False

    last_err = ""
    for i, token in enumerate(tokens):
        try:
            logger.info("HF token %s/%s...", i + 1, len(tokens))
            client = Client(HF_SPACE, token=token, verbose=False)
            
            # Try with reference text first (better accuracy)
            if ref_text:
                try:
                    result = client.predict(
                        ref_wav_input=handle_file(str(ref_path)),
                        ref_txt_input=ref_text,  # Use reference text for better matching
                        gen_txt_input=gen_text,
                        randomize_seed=True,
                        seed_input=0,
                        api_name="/basic_tts",
                    )
                except Exception as ref_err:
                    logger.warning("Reference text method failed, trying basic: %s", ref_err)
                    # Fallback to basic method
                    result = client.predict(
                        ref_wav_input=handle_file(str(ref_path)),
                        gen_txt_input=gen_text,
                        randomize_seed=True,
                        seed_input=0,
                        api_name="/basic_tts",
                    )
            else:
                # Basic method without reference text
                result = client.predict(
                    ref_wav_input=handle_file(str(ref_path)),
                    gen_txt_input=gen_text,
                    randomize_seed=True,
                    seed_input=0,
                    api_name="/basic_tts",
                )

            audio_src = None
            if isinstance(result, (list, tuple)) and len(result) > 0:
                audio_src = result[0]
                if hasattr(audio_src, "path"):
                    audio_src = audio_src.path
                elif isinstance(audio_src, dict):
                    audio_src = audio_src.get("path") or audio_src.get("url")
            elif isinstance(result, dict):
                audio_src = result.get("path") or result.get("url")

            if _copy_gradio_output_to_path(audio_src, output_path):
                logger.info("HF clone OK (%s bytes)", output_path.stat().st_size)
                return True

            last_err = "HF returned no audio file"
            logger.warning("Token %s: empty output", i + 1)

        except Exception as e:
            last_err = repr(e)
            logger.warning("HF token %s failed: %s", i + 1, e)

    generate_reference_clone._last_error = last_err or "All HF tokens failed"  # type: ignore[attr-defined]
    if "quota" in last_err.lower() or "zerogpu" in last_err.lower():
        generate_reference_clone._last_error += (  # type: ignore[attr-defined]
            " — ZeroGPU quota exhausted; wait for reset or use a fresh HF token."
        )
    return False


@app.route("/health", methods=["GET"])
def health_check():
    refs = {}
    for cid, cfg in CHARACTER_TTS.items():
        p = cfg["reference_audio"]
        refs[cid] = {"file": p.name, "exists": p.is_file()}
    return jsonify({
        "status": "healthy",
        "backend": "huggingface-f5-space",
        "space": HF_SPACE,
        "audio_dir": str(AUDIO_DIR),
        "references": refs,
        "hf_tokens_configured": len(get_hf_tokens()),
    })


@app.route("/tts", methods=["POST"])
def generate_tts():
    try:
        data = request.json or {}
        text = data.get("text", "")
        character_id = data.get("character_id", "osho")

        if not text:
            return jsonify({"error": "No text provided"}), 400

        cache_path = get_cache_path(text, character_id)
        if cache_path.exists() and cache_path.stat().st_size > 100:
            logger.info("Cache hit for %s", character_id)
            return send_file(cache_path, mimetype="audio/wav")

        if cache_path.exists():
            cache_path.unlink(missing_ok=True)

        start = time.time()
        if not generate_reference_clone(text, character_id, cache_path):
            detail = getattr(generate_reference_clone, "_last_error", "TTS failed")
            return jsonify({
                "error": "TTS generation failed",
                "detail": detail,
            }), 500

        logger.info("Generated in %.2fs", time.time() - start)
        return send_file(cache_path, mimetype="audio/wav")

    except Exception as e:
        logger.exception("TTS route error")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("EchoLegacy Reference-Audio TTS Server")
    print("Backend: HuggingFace F5-TTS space + web/public/audio clips")
    print("Audio dir:", AUDIO_DIR)
    print("HF tokens:", len(get_hf_tokens()))
    for cid, cfg in CHARACTER_TTS.items():
        p = cfg["reference_audio"]
        print(f"  [{cid}] {p.name}: {'OK' if p.is_file() else 'MISSING'}")
    print("Server: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
