"""
Local TTS Server for EchoLegacy
Optimized for RTX 3050 4GB VRAM

This runs a Flask server that provides TTS via multiple models:
1. XTTS (Coqui) - Fast, good quality
2. Bark - Natural sounding
3. Edge-TTS - Fallback (no GPU needed)
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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
CACHE_DIR = Path("./tts_cache")
CACHE_DIR.mkdir(exist_ok=True)

# Global model storage
models = {}
device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"🚀 Starting TTS Server on {device}")
print(f"💾 VRAM Available: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB" if torch.cuda.is_available() else "CPU Mode")

def load_xtts_model():
    """Load XTTS model (optimized for 4GB VRAM)"""
    try:
        from TTS.api import TTS
        
        # Use smaller XTTS model for 4GB VRAM
        model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        
        tts = TTS(model_name).to(device)
        
        # Enable mixed precision for memory efficiency
        if device == "cuda":
            tts.synthesizer.tts_model.half()  # Use fp16
        
        models['xtts'] = tts
        logger.info("✅ XTTS model loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load XTTS: {e}")
        return False

def load_bark_model():
    """Load Bark model (backup option)"""
    try:
        from bark import SAMPLE_RATE, generate_audio, preload_models
        
        # Preload models
        preload_models()
        models['bark'] = True
        logger.info("✅ Bark model loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load Bark: {e}")
        return False

def load_edge_tts():
    """Load Edge-TTS (CPU fallback)"""
    try:
        import edge_tts
        models['edge'] = True
        logger.info("✅ Edge-TTS loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load Edge-TTS: {e}")
        return False

def get_cache_path(text, character_id, model_type):
    """Generate cache file path"""
    cache_key = hashlib.md5(f"{text}_{character_id}_{model_type}".encode()).hexdigest()
    return CACHE_DIR / f"{cache_key}.wav"

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "device": device,
        "models_loaded": list(models.keys()),
        "vram_gb": torch.cuda.get_device_properties(0).total_memory / 1024**3 if torch.cuda.is_available() else 0
    })

@app.route('/tts', methods=['POST'])
def generate_tts():
    """Generate TTS audio"""
    try:
        data = request.json
        text = data.get('text', '')
        character_id = data.get('character_id', 'default')
        model_type = data.get('model', 'auto')  # auto, xtts, bark, edge
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Check cache first
        cache_path = get_cache_path(text, character_id, model_type)
        if cache_path.exists():
            logger.info(f"🎯 Cache hit for: {text[:30]}...")
            return send_file(cache_path, mimetype='audio/wav')
        
        start_time = time.time()
        
        # Auto-select best available model
        if model_type == 'auto':
            if 'xtts' in models:
                model_type = 'xtts'
            elif 'bark' in models:
                model_type = 'bark'
            elif 'edge' in models:
                model_type = 'edge'
            else:
                return jsonify({"error": "No TTS models available"}), 500
        
        # Generate audio based on model type
        if model_type == 'xtts' and 'xtts' in models:
            audio_path = generate_xtts(text, character_id, cache_path)
        elif model_type == 'bark' and 'bark' in models:
            audio_path = generate_bark(text, cache_path)
        elif model_type == 'edge' and 'edge' in models:
            audio_path = generate_edge_tts_sync(text, character_id, cache_path)
        else:
            return jsonify({"error": f"Model {model_type} not available"}), 400
        
        generation_time = time.time() - start_time
        logger.info(f"🎵 Generated audio in {generation_time:.2f}s using {model_type}")
        
        return send_file(audio_path, mimetype='audio/wav')
        
    except Exception as e:
        logger.error(f"❌ TTS generation failed: {e}")
        return jsonify({"error": str(e)}), 500

def generate_xtts(text, character_id, output_path):
    """Generate audio using XTTS"""
    # Character-specific voice mapping
    voice_map = {
        'osho': 'male_calm',
        'tesla': 'male_scientist', 
        'ssr': 'male_young',
        'bhagat_singh': 'male_passionate',
        'hitler': 'male_authoritative'
    }
    
    voice = voice_map.get(character_id, 'male_calm')
    
    # Generate with XTTS
    tts = models['xtts']
    
    # Reference clips live in web/public/audio (see character_tts_config.py)
    try:
        from character_tts_config import get_character_tts
        cfg = get_character_tts(character_id)
        ref_audio_path = str(cfg["reference_audio"]) if cfg else None
    except ImportError:
        ref_audio_path = f"./web/public/audio/{character_id}_ref.wav"
    if ref_audio_path and os.path.exists(ref_audio_path):
        tts.tts_to_file(
            text=text,
            speaker_wav=ref_audio_path,
            language="en",
            file_path=str(output_path)
        )
    else:
        # Use built-in voice
        tts.tts_to_file(
            text=text,
            speaker=voice,
            language="en", 
            file_path=str(output_path)
        )
    
    return output_path

def generate_bark(text, output_path):
    """Generate audio using Bark"""
    from bark import generate_audio, SAMPLE_RATE
    
    # Generate audio
    audio_array = generate_audio(text, history_prompt="v2/en_speaker_6")
    
    # Save to file
    torchaudio.save(str(output_path), torch.tensor(audio_array).unsqueeze(0), SAMPLE_RATE)
    
    return output_path

def generate_edge_tts_sync(text, character_id, output_path):
    """Generate audio using Edge-TTS (synchronous wrapper)"""
    import asyncio
    import edge_tts
    
    # Character-specific voice mapping for Edge-TTS
    voice_map = {
        'osho': 'en-US-AriaNeural',
        'tesla': 'en-US-GuyNeural',
        'ssr': 'en-US-DavisNeural', 
        'bhagat_singh': 'en-IN-NeerjaNeural',
        'hitler': 'en-US-TonyNeural'
    }
    
    voice = voice_map.get(character_id, 'en-US-AriaNeural')
    
    async def generate_async():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(output_path))
    
    # Run async function in sync context
    asyncio.run(generate_async())
    
    return output_path

async def generate_edge_tts(text, character_id, output_path):
    """Generate audio using Edge-TTS (async version - kept for compatibility)"""
    import edge_tts
    
    # Character-specific voice mapping for Edge-TTS
    voice_map = {
        'osho': 'en-US-AriaNeural',
        'tesla': 'en-US-GuyNeural',
        'ssr': 'en-US-DavisNeural', 
        'bhagat_singh': 'en-IN-NeerjaNeural',
        'hitler': 'en-US-TonyNeural'
    }
    
    voice = voice_map.get(character_id, 'en-US-AriaNeural')
    
    # Generate TTS
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))
    
    return output_path

# Initialize models on startup
def initialize_models():
    """Load available TTS models"""
    logger.info("🔄 Initializing TTS models...")
    
    # Try to load models in order of preference
    success = False
    
    if load_xtts_model():
        success = True
    
    if load_bark_model():
        success = True
        
    if load_edge_tts():
        success = True
    
    if not success:
        logger.error("❌ No TTS models could be loaded!")
        exit(1)
    
    logger.info(f"✅ TTS Server ready with models: {list(models.keys())}")

if __name__ == '__main__':
    # Initialize models
    initialize_models()
    
    # Start server
    print("\n" + "="*50)
    print("🎤 EchoLegacy Local TTS Server")
    print("="*50)
    print(f"🖥️  Device: {device}")
    print(f"🧠 Models: {list(models.keys())}")
    print(f"🌐 Server: http://localhost:5000")
    print(f"📁 Cache: {CACHE_DIR}")
    print("="*50)
    
    app.run(host='0.0.0.0', port=5000, debug=False)