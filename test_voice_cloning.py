#!/usr/bin/env python3
"""
Simple test for improved F5-TTS voice cloning.
Tests the reference text improvement.
"""

import requests
import time
from pathlib import Path

SERVER_URL = "http://127.0.0.1:5000"

def test_voice_generation(character_id, text):
    """Test voice generation for a character."""
    print(f"\n🎤 Testing {character_id}...")
    
    payload = {
        "text": text,
        "character_id": character_id
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{SERVER_URL}/tts", json=payload)
        generation_time = time.time() - start_time
        
        if response.status_code == 200:
            # Save the audio file
            output_file = f"test_{character_id}_{int(time.time())}.wav"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            file_size = len(response.content)
            print(f"✅ Success! Generated {file_size} bytes in {generation_time:.2f}s")
            print(f"💾 Saved to: {output_file}")
            return True
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            print(f"❌ Failed: {response.status_code}")
            print(f"   Error: {error_data.get('error', 'Unknown')}")
            print(f"   Detail: {error_data.get('detail', 'No details')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Test voice generation for available characters."""
    print("🚀 Testing Improved F5-TTS Voice Cloning")
    print("=" * 45)
    
    # Test characters that have reference audio
    test_cases = [
        ("osho", "Meditation is the key to understanding the mysteries of existence."),
        ("tesla", "The future belongs to those who understand the power of electricity and wireless transmission."),
        ("hitler", "The strength of a nation lies in the unity and determination of its people."),
    ]
    
    success_count = 0
    total_tests = len(test_cases)
    
    for character_id, text in test_cases:
        if test_voice_generation(character_id, text):
            success_count += 1
    
    print(f"\n📊 Results: {success_count}/{total_tests} successful")
    
    if success_count == total_tests:
        print("🎉 All tests passed! Voice cloning is working.")
        print("\n💡 The improvement: Now using reference text with audio for better voice matching!")
    else:
        print("⚠️  Some tests failed. Check server logs for details.")
    
    print(f"\n📝 Next steps:")
    print("1. Add missing reference audio files (see GET_MISSING_AUDIO.md)")
    print("2. Test with longer texts to verify consistency")
    print("3. Compare voice quality with previous generations")

if __name__ == "__main__":
    main()