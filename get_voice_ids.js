// Script to get voice IDs from smallest.ai for all characters
const fs = require('fs');
const path = require('path');

const SMALLEST_API_BASE = 'https://api.smallest.ai/waves/v1';
const API_KEY = 'sk_807304f995e368e0e86ff84dd9f48691'; // Your API key

const characters = {
  osho: '/web/public/audio/osho_ref.mp3',
  bhagat_singh: '/web/public/audio/bhagat_ref.mpeg', 
  ssr: '/web/public/audio/ssr_ref.mpeg',
  tesla: '/web/public/audio/tesla_ref.mp3',
  hitler: '/web/public/audio/hitler_ref.mp3'
};

async function createVoiceClone(characterId, audioPath) {
  try {
    console.log(`Creating voice clone for ${characterId}...`);
    
    const fullPath = path.join(__dirname, audioPath);
    if (!fs.existsSync(fullPath)) {
      console.error(`Audio file not found: ${fullPath}`);
      return null;
    }

    const audioBuffer = fs.readFileSync(fullPath);
    const formData = new FormData();
    
    const audioBlob = new Blob([audioBuffer], { type: 'audio/mpeg' });
    formData.append('file', audioBlob, `${characterId}_ref.mp3`);
    formData.append('displayName', `${characterId.charAt(0).toUpperCase() + characterId.slice(1)} Voice Clone`);
    formData.append('description', `Voice clone for ${characterId} character`);
    formData.append('model', 'lightning-v3.1');
    formData.append('language', 'en');

    const response = await fetch(`${SMALLEST_API_BASE}/voice-cloning`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
      },
      body: formData,
    });

    if (response.ok) {
      const result = await response.json();
      const voiceId = result.data?.voiceId;
      if (voiceId) {
        console.log(`✅ ${characterId}: ${voiceId}`);
        return voiceId;
      } else {
        console.error(`❌ ${characterId}: No voiceId in response`);
        return null;
      }
    } else {
      const errorText = await response.text();
      console.error(`❌ ${characterId}: ${response.status} - ${errorText}`);
      return null;
    }
  } catch (error) {
    console.error(`❌ ${characterId}: ${error.message}`);
    return null;
  }
}

async function getAllVoiceIds() {
  console.log('🎤 Creating voice clones for all characters...\n');
  
  const voiceIds = {};
  
  for (const [characterId, audioPath] of Object.entries(characters)) {
    const voiceId = await createVoiceClone(characterId, audioPath);
    if (voiceId) {
      voiceIds[characterId] = voiceId;
    }
    // Wait 2 seconds between requests to avoid rate limiting
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  
  console.log('\n📋 Copy this to your TTS API:');
  console.log('const CHARACTER_VOICE_IDS: Record<string, string> = {');
  for (const [characterId, voiceId] of Object.entries(voiceIds)) {
    console.log(`  ${characterId}: '${voiceId}',`);
  }
  console.log('};');
}

getAllVoiceIds().catch(console.error);