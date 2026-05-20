# Missing Reference Audio Files - Quick Fix

## What You Need:

1. **bhagat_singh_ref.wav** - Bhagat Singh voice sample
2. **ssr_ref.wav** - SSR voice sample

## Where to Get Them:

### Option 1: Find Real Audio Samples
- Search YouTube for Bhagat Singh speeches/interviews
- Search for SSR (Sushant Singh Rajput) interviews/movies
- Use audio from documentaries or historical recordings
- Download and convert to WAV format

### Option 2: Use AI Voice Generation
- Use ElevenLabs, Murf, or similar services to create samples
- Generate the reference text for each character
- Save as high-quality WAV files

### Option 3: Record Yourself (Temporary)
- Record yourself saying the reference text in the character's style
- Use as placeholder until you find better audio

## Reference Texts to Use:

**Bhagat Singh:**
"They may kill me, but they cannot kill my ideas. They can crush my body, but they will not be able to crush my spirit."

**SSR:**
"I think we are all interconnected, just like the quantum entanglement we see in physics."

## Audio Requirements:

- **Format:** WAV, MP3, or FLAC
- **Duration:** 10-30 seconds of clear speech
- **Quality:** 16kHz+ sample rate, minimal background noise
- **Content:** Should match the reference text above

## Quick Steps:

1. Find/create the audio files
2. Name them exactly: `bhagat_singh_ref.wav` and `ssr_ref.wav`
3. Put them in `web/public/audio/` folder
4. Restart the TTS server
5. Test voice generation

## Temporary Workaround:

Your server will work for Osho, Tesla, and Hitler (which have reference audio). For Bhagat Singh and SSR, it will show "MISSING" but won't crash.

The **key improvement** I made is using reference text with the audio, which should significantly improve voice cloning accuracy for the characters that do have reference audio files.