"""Quick test: clone voice from web/public/audio reference only."""
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO))

from dotenv import load_dotenv

load_dotenv(_REPO / "web" / ".env.local")

from character_tts_config import get_character_tts
from minimal_tts_server import generate_reference_clone, get_cache_path, get_hf_tokens

def main():
    character_id = sys.argv[1] if len(sys.argv) > 1 else "osho"
    text = sys.argv[2] if len(sys.argv) > 2 else "This is a test of the reference voice clone."

    cfg = get_character_tts(character_id)
    if not cfg:
        print(f"Unknown character: {character_id}")
        sys.exit(1)

    ref = cfg["reference_audio"]
    print(f"Character: {character_id}")
    print(f"Reference: {ref} ({'OK' if ref.is_file() else 'MISSING'})")
    print(f"HF tokens: {len(get_hf_tokens())}")

    out = get_cache_path(text, character_id)
    if generate_reference_clone(text, character_id, out):
        print(f"SUCCESS -> {out} ({out.stat().st_size} bytes)")
    else:
        err = getattr(generate_reference_clone, "_last_error", "unknown")
        print(f"FAILED: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
