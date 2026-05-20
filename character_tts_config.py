"""
Character reference audio — keep in sync with web/utils/characters.ts
Files live under web/public/audio/
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
AUDIO_DIR = REPO_ROOT / "web" / "public" / "audio"

CHARACTER_TTS = {
    "osho": {
        "reference_audio": AUDIO_DIR / "osho_ref.mp3",
        "reference_text": (
            "Meditation is not a concentration, it is a relaxation."
        ),
    },
    "bhagat_singh": {
        "reference_audio": AUDIO_DIR / "bhagat_singh_ref.wav",
        "reference_text": (
            "They may kill me, but they cannot kill my ideas. They can crush my body, "
            "but they will not be able to crush my spirit."
        ),
    },
    "ssr": {
        "reference_audio": AUDIO_DIR / "ssr_ref.wav",
        "reference_text": (
            "I think we are all interconnected, just like the quantum entanglement we see in physics."
        ),
    },
    "tesla": {
        "reference_audio": AUDIO_DIR / "tesla_ref.mp3",
        "reference_text": (
            "The present is theirs; the future, for which I really worked, is mine. "
            "My brain is only a receiver, in the Universe there is a core from which we obtain knowledge, "
            "strength, and inspiration."
        ),
    },
    "hitler": {
        "reference_audio": AUDIO_DIR / "hitler_ref.mp3",
        "reference_text": (
            "The strength of a nation lies not in its material wealth, but in the unbreakable will of its people."
        ),
    },
}


def get_character_tts(character_id: str) -> dict | None:
    return CHARACTER_TTS.get(character_id)
