# Add Your Smallest.ai API Key

## Step 1: Get Your API Key
1. Go to https://app.smallest.ai/
2. Sign in to your account
3. Navigate to "API Keys" or "Settings"
4. Copy your API key

## Step 2: Add to Environment
Open `web\.env.local` and replace this line:
```
SMALLEST_API_KEY=your_smallest_ai_api_key_here
```

With your actual API key:
```
SMALLEST_API_KEY=sk_your_actual_api_key_here
```

## Step 3: Restart Server
After adding the key:
1. Stop the current server (Ctrl+C)
2. Restart: `python smallest_tts_server.py`

## Step 4: Test Voice Cloning
Once the server is running with your API key:
1. Your web app will automatically use smallest.ai
2. First time using each character, it will create a voice clone
3. Subsequent requests will use the cached voice clone

## What Happens:
1. **First Request**: Creates voice clone using reference audio + text
2. **Voice Clone**: Stored in smallest.ai with character name
3. **Speech Generation**: Uses the cloned voice for perfect accuracy
4. **Caching**: Results cached locally for speed

## Characters Ready:
- ✅ Osho (has osho_ref.mp3)
- ✅ Tesla (has tesla_ref.mp3) 
- ✅ Hitler (has hitler_ref.mp3)
- ❌ Bhagat Singh (missing bhagat_singh_ref.wav)
- ❌ SSR (missing ssr_ref.wav)

The system will work perfectly for the 3 characters that have reference audio!