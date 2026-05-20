"""
Simple Local TTS Server for RTX 3050 4GB
Optimized for reliability and speed
"""

import os
import torch
import torchaudio
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import tempfile
import hashlib
import time
from pathlib import Path
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
CACHE_DIR = Path("./tts_cache")
CACHE_DIR.mkdir(exist_ok=True)

# Global model storage
tts_model = None
device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"🚀 Starting Simple TTS Server on {device}")
if torch.cuda.is_available():
    print(f"💾 GPU: {torch.cuda.get_device_name(0)}")
    print(f"💾 VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")

def load_tts_model():
    """Load the best TTS model for RTX 3050"""
    global tts_model
    
    try:
        # Try Edge-TTS first (fastest, no VRAM needed)
        import edge_tts
        tts_model = "edge"
        logger.info("✅ Edge-TTS loaded (CPU-based, very fast)")
        return True
        
    except ImportError:
        logger.info("Edge-TTS not available, trying other options...")
    
    try:
        # Try pyttsx3 as backup
        import pyttsx3
        engine = pyttsx3.init()
        tts_model = engine
        logger.info("✅ pyttsx3 loaded (CPU-based)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load any TTS model: {e}")
        return False

def get_cache_path(text, character_id):
    """Generate cache file path"""
    cache_key = hashlib.md5(f"{text}_{character_id}".encode()).hexdigest()
    return CACHE_DIR / f"{cache_key}.wav"

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "device": device,
        "model": str(type(tts_model).__name__) if tts_model else "none",
        "vram_gb": torch.cuda.get_device_properties(0).total_memory / 1024**3 if torch.cuda.is_available() else 0
    })

@app.route('/tts', methods=['POST'])
def generate_tts():
    """Generate TTS audio"""
    try:
        data = request.json
        text = data.get('text', '')
        character_id = data.get('character_id', 'default')
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        logger.info(f"🎤 Generating TTS for: {text[:50]}...")
        
        # Check cache first
        cache_path = get_cache_path(text, character_id)
        if cache_path.exists():
            logger.info(f"🎯 Cache hit!")
            return send_file(cache_path, mimetype='audio/wav')
        
        start_time = time.time()
        
        # Generate audio
        if tts_model == "edge":
            audio_path = generate_edge_tts(text, character_id, cache_path)
        elif hasattr(tts_model, 'say'):  # pyttsx3
            audio_path = generate_pyttsx3(text, cache_path)
        else:
            return jsonify({"error": "No TTS model available"}), 500
        
        generation_time = time.time() - start_time
        logger.info(f"🎵 Generated in {generation_time:.2f}s")
        
        return send_file(audio_path, mimetype='audio/wav')
        
    except Exception as e:
        logger.error(f"❌ TTS generation failed: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

def generate_edge_tts(text, character_id, output_path):
    """Generate using Edge-TTS (fastest option)"""
    import asyncio
    import edge_tts
    
    # Character voices
    voices = {
        'osho': 'en-US-AriaNeural',
        'tesla': 'en-US-GuyNeural', 
        'ssr': 'en-US-DavisNeural',
        'bhagat_singh': 'en-IN-NeerjaNeural',
        'hitler': 'en-US-TonyNeural'
    }
    
    voice = voices.get(character_id, 'en-US-AriaNeural')
    
    async def generate():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(output_path))
    
    # Run async in sync context
    asyncio.run(generate())
    return output_path

def generate_pyttsx3(text, output_path):
    """Generate using pyttsx3"""
    # Set properties
    tts_model.setProperty('rate', 150)    # Speed
    tts_model.setProperty('volume', 0.9)  # Volume
    
    # Save to file
    tts_model.save_to_file(text, str(output_path))
    tts_model.runAndWait()
    
    return output_path

if __name__ == '__main__':
    # Load TTS model
    if not load_tts_model():
        print("❌ Failed to load any TTS model!")
        print("Installing Edge-TTS...")
        os.system("pip install edge-tts")
        if not load_tts_model():
            print("❌ Still failed. Exiting.")
            exit(1)
    
    print("\n" + "="*50)
    print("🎤 EchoLegacy Simple TTS Server")
    print("="*50)
    print(f"🖥️  Device: {device}")
    print(f"🧠 Model: {tts_model}")
    print(f"🌐 Server: http://localhost:5000")
    print(f"📁 Cache: {CACHE_DIR}")
    print("="*50)
    print("✅ Ready! Expected latency: 1-3 seconds")
    print("="*50)
    
    app.run(host='0.0.0.0', port=5000, debug=False)