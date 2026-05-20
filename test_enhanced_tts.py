#!/usr/bin/env python3
"""
Test script for enhanced F5-TTS voice cloning server.
Tests the new quality validation and character-specific features.
"""

import requests
import json
import time
from pathlib import Path

SERVER_URL = "http://127.0.0.1:5000"

def test_health_endpoint():
    """Test the enhanced health endpoint."""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{SERVER_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server status: {data['status']}")
            print(f"📊 Features: {', '.join(data['features'])}")
            print(f"🎭 Characters: {len(data['references'])}")
            
            missing = data.get('missing_references', [])
            if missing:
                print(f"⚠️  Missing audio: {', '.join(missing)}")
            else:
                print("✅ All reference audio files present")
            
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_characters_endpoint():
    """Test the new characters endpoint."""
    print("\n🎭 Testing characters endpoint...")
    try:
        response = requests.get(f"{SERVER_URL}/characters")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total_count']} characters")
            
            for char_id, info in data['characters'].items():
                status = "✅" if info['audio_exists'] else "❌"
                threshold = info['quality_threshold']
                print(f"  {status} {char_id}: threshold={threshold}")
            
            return True
        else:
            print(f"❌ Characters endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Characters endpoint error: {e}")
        return False

def test_tts_generation(character_id="osho", text="Hello, this is a test of the enhanced voice cloning system."):
    """Test TTS generation with quality validation."""
    print(f"\n🎤 Testing TTS generation for {character_id}...")
    try:
        payload = {
            "text": text,
            "character_id": character_id
        }
        
        start_time = time.time()
        response = requests.post(f"{SERVER_URL}/tts", json=payload)
        generation_time = time.time() - start_time
        
        if response.status_code == 200:
            # Check for quality metadata in headers
            metadata_header = response.headers.get('X-TTS-Metadata')
            if metadata_header:
                metadata = json.loads(metadata_header)
                quality_score = metadata.get('quality_score', 0)
                backend_used = metadata.get('backend_used', 'unknown')
                retry_count = metadata.get('retry_count', 0)
                
                print(f"✅ Generation successful!")
                print(f"📊 Quality score: {quality_score:.2f}")
                print(f"🔄 Retries: {retry_count}")
                print(f"⚡ Backend: {backend_used}")
                print(f"⏱️  Total time: {generation_time:.2f}s")
                
                # Save audio file for inspection
                audio_path = Path(f"test_output_{character_id}.wav")
                with open(audio_path, 'wb') as f:
                    f.write(response.content)
                print(f"💾 Audio saved to: {audio_path}")
                
                return True, quality_score
            else:
                print("✅ Generation successful (no quality metadata)")
                return True, None
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            print(f"❌ Generation failed: {response.status_code}")
            print(f"   Error: {error_data.get('error', 'Unknown error')}")
            print(f"   Detail: {error_data.get('detail', 'No details')}")
            
            suggestions = error_data.get('suggestions', [])
            if suggestions:
                print("💡 Suggestions:")
                for suggestion in suggestions:
                    print(f"   • {suggestion}")
            
            return False, None
            
    except Exception as e:
        print(f"❌ TTS generation error: {e}")
        return False, None

def test_quality_validation():
    """Test the quality validation endpoint."""
    print("\n🔍 Testing quality validation...")
    
    # First generate an audio file
    success, quality_score = test_tts_generation("osho", "Short test for validation.")
    if not success:
        print("❌ Cannot test validation without generated audio")
        return False
    
    try:
        audio_path = "test_output_osho.wav"
        payload = {
            "character_id": "osho",
            "audio_file": audio_path
        }
        
        response = requests.post(f"{SERVER_URL}/tts/validate", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Validation successful!")
            print(f"📊 Quality score: {data['quality_score']:.2f}")
            print(f"✅ Valid: {data['is_valid']}")
            print(f"🎯 Threshold: {data['threshold']}")
            
            if data['issues']:
                print("⚠️  Issues found:")
                for issue in data['issues']:
                    print(f"   • {issue}")
            
            return True
        else:
            print(f"❌ Validation failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Enhanced F5-TTS Voice Cloning Test Suite")
    print("=" * 50)
    
    # Test if server is running
    if not test_health_endpoint():
        print("\n❌ Server not running. Start with: python minimal_tts_server.py")
        return
    
    # Test all endpoints
    test_characters_endpoint()
    
    # Test TTS generation for available characters
    characters_to_test = ["osho", "tesla", "hitler"]  # Characters with existing audio
    
    for char_id in characters_to_test:
        success, quality_score = test_tts_generation(char_id, f"Hello from {char_id}, testing enhanced voice cloning.")
        if success and quality_score:
            print(f"📈 {char_id} quality: {quality_score:.2f}")
    
    # Test quality validation
    test_quality_validation()
    
    print("\n🎉 Test suite completed!")
    print("\n💡 Next steps:")
    print("1. Add missing reference audio files (bhagat_singh_ref.wav, ssr_ref.wav)")
    print("2. Test with longer texts to verify quality consistency")
    print("3. Adjust character-specific parameters based on quality scores")
    print("4. Monitor generation times and optimize as needed")

if __name__ == "__main__":
    main()