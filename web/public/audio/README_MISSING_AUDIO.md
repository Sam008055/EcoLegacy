# Missing Reference Audio Files

The following reference audio files are missing and need to be added for accurate voice cloning:

## Required Files:

1. **bhagat_singh_ref.wav** - Reference audio for Bhagat Singh character
   - Should contain clear speech sample (10-30 seconds)
   - Recommended text: "They may kill me, but they cannot kill my ideas. They can crush my body, but they will not be able to crush my spirit."
   - Format: WAV, MP3, or FLAC
   - Quality: 16kHz+ sample rate, minimal background noise

2. **ssr_ref.wav** - Reference audio for SSR character  
   - Should contain clear speech sample (10-30 seconds)
   - Recommended text: "I think we are all interconnected, just like the quantum entanglement we see in physics."
   - Format: WAV, MP3, or FLAC
   - Quality: 16kHz+ sample rate, minimal background noise

## How to Add Reference Audio:

1. Find or create high-quality audio samples of the target voices
2. Ensure the audio is clear with minimal background noise
3. Trim to 10-30 seconds of the clearest speech
4. Save with the exact filenames above in this directory
5. Restart the TTS server to detect the new files

## Audio Quality Tips:

- Use noise reduction if needed
- Normalize audio levels
- Remove long silences at start/end
- Ensure the spoken text matches the reference text in character_tts_config.py
- Test different segments to find the clearest voice sample

## Temporary Workaround:

The enhanced TTS server will continue to work without these files, but voice cloning accuracy will be significantly reduced for these characters. The system will show warnings and lower quality scores until proper reference audio is added.