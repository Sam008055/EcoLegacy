// Test script for web app TTS with smallest.ai integration
// Run this after adding your SMALLEST_API_KEY to web/.env.local

const testTTS = async () => {
  const baseUrl = 'http://localhost:3000';
  
  console.log('🚀 Testing Web App TTS with Smallest.ai');
  console.log('=' .repeat(50));
  
  const testCases = [
    { character: 'osho', text: 'Meditation is the key to understanding existence.' },
    { character: 'tesla', text: 'The future belongs to wireless power transmission.' },
    { character: 'hitler', text: 'The strength of a nation lies in its people.' }
  ];
  
  for (const { character, text } of testCases) {
    console.log(`\n🎤 Testing ${character}...`);
    
    try {
      const response = await fetch(`${baseUrl}/api/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, characterId: character })
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log(`✅ Success! Source: ${result.source}`);
        console.log(`📊 Cached: ${result.cached}`);
        console.log(`🎯 Audio URL length: ${result.audioUrl?.length || 0} chars`);
      } else {
        const error = await response.json();
        console.log(`❌ Failed: ${error.error}`);
        console.log(`📝 Detail: ${error.detail || 'No details'}`);
      }
    } catch (error) {
      console.log(`❌ Error: ${error.message}`);
    }
  }
  
  console.log('\n🎉 Test completed!');
  console.log('\n💡 If you see "source: smallest-ai", it\'s working!');
  console.log('💡 If you see errors, check your SMALLEST_API_KEY in web/.env.local');
};

// Run the test
testTTS();