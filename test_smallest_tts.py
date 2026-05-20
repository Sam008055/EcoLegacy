#!/usr/bin/env python3
"""
Test script for smallest.ai TTS server.
Tests voice cloning and speech generation.
"""

import requests
import time
from pathlib import Path

SERVER_URL = "http://127.0.0.1:5000"

def test_health():
    """Test server health."""
    print("🔍 Testing server health...")
    try:
        response = requests.get(f"{SERVER_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server status: {data['status']}")
            print(f"🔧 Backend: {data['backend']}")
            print(f"🔑 API configured: {data['api_configured']}")
            print(f"🎭 Voice clones ready: {data['voice_clones']}")
            
            if not data['api_configured']:
                print("❌ API key not configured! Add SMALLEST_API_KEY to web/.env.local")
                return False
            
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_characters():
    """Test characters endpoint."""
    print("\n🎭 Testing characters endpoint...")
    try:
        response = requests.get(f"{SERVER_URL}/characters")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total_count']} characters")
            print(f"🎯 Clones ready: {data['clones_ready']}")
            
            for char_id, info in data['characters'].items():
                status = "✅" if info['audio_exists'] else "❌"
                clone_status = "🎯" if info['clone_ready'] else "⏳"
                print(f"  {status} {clone_status} {char_id}: {info['reference_audio']}")
            
            missing = data.get('missing_audio', [])
            if missing:
                print(f"⚠️  Missing audio: {', '.join(missing)}")
            
            return True
        else:
            print(f"❌ Characters endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Characters endpoint error: {e}")
        return False

def test_voice_generation(character_id="osho", text="Hello, this is a test of smallest.ai voice cloning."):
    """Test voice generation."""
    print(f"\n🎤 Testing voice generation for {character_id}...")
    try:
        payload = {
            "text": text,
            "character_id": character_id
        }
        
        start_time = time.time()
        response = requests.post(f"{SERVER_URL}/tts", json=payload)
        generation_time = time.time() - start_time
        
        if response.status_code == 200:
            # Save audio file
            audio_path = Path(f"test_{character_id}_smallest.wav")
            with open(audio_path, 'wb') as f:
                f.write(response.content)
            
            file_size = len(response.content)
            print(f"✅ Generation successful!")
            print(f"📊 File size: {file_size} bytes")
            print(f"⏱️  Generation time: {generation_time:.2f}s")
            print(f"💾 Saved to: {audio_path}")
            
            return True
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            print(f"❌ Generation failed: {response.status_code}")
            print(f"   Error: {error_data.get('error', 'Unknown error')}")
            print(f"   Detail: {error_data.get('detail', 'No details')}")
            
            return False
            
    except Exception as e:
        print(f"❌ Voice generation error: {e}")
        return False

def test_clone_creation(character_id="osho"):
    """Test manual clone creation."""
    print(f"\n🎯 Testing clone creation for {character_id}...")
    try:
        response = requests.post(f"{SERVER_URL}/create_clone/{character_id}")
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"✅ Clone created successfully!")
                print(f"🎯 Voice ID: {data['voice_id']}")
                print(f"📝 Message: {data['message']}")
                return True
            else:
                print(f"❌ Clone creation failed: {data.get('error', 'Unknown error')}")
                return False
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            print(f"❌ Clone creation failed: {response.status_code}")
            print(f"   Error: {error_data.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Clone creation error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Smallest.ai TTS Server Test Suite")
    print("=" * 50)
    
    # Test server health
    if not test_health():
        print("\n❌ Server not ready. Make sure:")
        print("1. Server is running: python smallest_tts_server.py")
        print("2. API key is configured in web/.env.local")
        return
    
    # Test characters endpoint
    test_characters()
    
    # Test available characters (those with reference audio)
    available_characters = ["osho"]
    
    for char_id in available_characters:
        print(f"\n{'='*20} Testing {char_id.upper()} {'='*20}")
        
        # Test clone creation
        clone_success = test_clone_creation(char_id)
        
        if clone_success:
            # Test voice generation
            test_voice_generation(char_id, f"Hello, I am {char_id}. This is a test of smallest.ai voice cloning technology.")
    
    print(f"\n🎉 Test suite completed!")
    print("\n💡 Next steps:")
    print("1. Check generated audio files for quality")
    print("2. Test with your web application")
    print("3. Add missing reference audio files for other characters")
    print("4. Monitor smallest.ai API usage and credits")

if __name__ == "__main__":
    main()