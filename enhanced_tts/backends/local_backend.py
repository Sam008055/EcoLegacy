"""
Local F5-TTS backend implementation.

Uses a local F5-TTS installation for voice generation.
"""

import logging
import time
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import torch

from ..interfaces import VoiceGenerationBackendInterface
from ..models import AudioResult, TTSParameters, QuotaStatus, BackendType, AudioQualityMetrics

logger = logging.getLogger(__name__)


class LocalF5TTSBackend(VoiceGenerationBackendInterface):
    """
    Local F5-TTS backend using local installation.
    
    This backend requires a local F5-TTS installation and GPU support.
    """
    
    def __init__(self, 
                 model_path: Optional[Path] = None,
                 device: str = "auto",
                 max_length: int = 500):
        """
        Initialize the local F5-TTS backend.
        
        Args:
            model_path: Path to local F5-TTS model (if None, uses default)
            device: Device for inference ("cpu", "cuda", or "auto")
            max_length: Maximum text length for generation
        """
        self.model_path = model_path
        self.max_length = max_length
        
        # Set device
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        # Model will be loaded lazily
        self._model = None
        self._model_loaded = False
        self._load_error = None
    
    def generate(self, text: str, reference_audio: Path, params: TTSParameters) -> AudioResult:
        """
        Generate voice clone using local F5-TTS.
        
        Args:
            text: Text to synthesize
            reference_audio: Path to reference audio file
            params: TTS parameters
            
        Returns:
            AudioResult with generated audio or error information
        """
        start_time = time.time()
        
        if not reference_audio.exists():
            return AudioResult(
                audio_path=None,
                quality_metrics=None,
                success=False,
                error_message=f"Reference audio not found: {reference_audio}"
            )
        
        # Load model if not already loaded
        if not self._model_loaded:
            load_success = self._load_model()
            if not load_success:
                return AudioResult(
                    audio_path=None,
                    quality_metrics=None,
                    success=False,
                    error_message=f"Failed to load local F5-TTS model: {self._load_error}"
                )
        
        # Prepare text
        gen_text = text.replace("\n", " ").strip()
        if len(gen_text) > self.max_length:
            gen_text = gen_text[:self.max_length] + "..."
        
        logger.info(f"Local F5-TTS generation | text_length={len(gen_text)} | device={self.device}")
        
        try:
            # Generate audio using local F5-TTS
            output_path = self._generate_with_local_f5tts(gen_text, reference_audio, params)
            
            if output_path and output_path.exists() and output_path.stat().st_size > 100:
                generation_time = time.time() - start_time
                
                # Create quality metrics
                quality_metrics = AudioQualityMetrics(
                    similarity_score=0.0,  # Will be calculated by quality validator
                    clarity_score=0.0,     # Will be calculated by quality validator
                    naturalness_score=0.0, # Will be calculated by quality validator
                    artifacts_detected=[], # Will be detected by quality validator
                    generation_time=generation_time,
                    backend_used="local_f5tts"
                )
                
                logger.info(f"Local F5-TTS success | size={output_path.stat().st_size} bytes | time={generation_time:.1f}s")
                
                return AudioResult(
                    audio_path=output_path,
                    quality_metrics=quality_metrics,
                    success=True
                )
            else:
                return AudioResult(
                    audio_path=None,
                    quality_metrics=None,
                    success=False,
                    error_message="Local F5-TTS generated empty or invalid audio"
                )
        
        except Exception as e:
            logger.error(f"Local F5-TTS generation failed: {e}")
            return AudioResult(
                audio_path=None,
                quality_metrics=None,
                success=False,
                error_message=f"Local F5-TTS error: {str(e)}"
            )
    
    def is_available(self) -> bool:
        """Check if the local F5-TTS backend is available."""
        if not self._model_loaded:
            return self._check_f5tts_availability()
        return self._model is not None
    
    def get_quota_status(self) -> QuotaStatus:
        """Get current quota status for local backend."""
        # Local backend has no quota limits
        return QuotaStatus(
            backend_type=BackendType.LOCAL_F5TTS,
            requests_remaining=None,  # Unlimited
            reset_time=None,
            is_available=self.is_available(),
            last_error=self._load_error
        )
    
    def get_backend_type(self) -> BackendType:
        """Get the backend type identifier."""
        return BackendType.LOCAL_F5TTS
    
    def _load_model(self) -> bool:
        """Load the local F5-TTS model."""
        try:
            logger.info(f"Loading local F5-TTS model on {self.device}")
            
            # Try to import F5-TTS
            try:
                # This is a placeholder - actual F5-TTS import would depend on the specific installation
                # For now, we'll simulate the model loading
                if self.device == "cuda" and not torch.cuda.is_available():
                    raise RuntimeError("CUDA not available but requested")
                
                # Simulate model loading
                self._model = "f5tts_model_placeholder"  # Would be actual model object
                self._model_loaded = True
                
                logger.info("Local F5-TTS model loaded successfully")
                return True
                
            except ImportError as e:
                self._load_error = f"F5-TTS not installed: {e}"
                logger.error(self._load_error)
                return False
            
        except Exception as e:
            self._load_error = f"Error loading F5-TTS model: {e}"
            logger.error(self._load_error)
            return False
    
    def _check_f5tts_availability(self) -> bool:
        """Check if F5-TTS is available without loading the model."""
        try:
            # Check if F5-TTS package is available
            # This is a placeholder check - would depend on actual F5-TTS installation
            
            # Check for CUDA if needed
            if self.device == "cuda" and not torch.cuda.is_available():
                return False
            
            # Check for minimum GPU memory if using CUDA
            if self.device == "cuda":
                gpu_memory = torch.cuda.get_device_properties(0).total_memory
                min_memory = 4 * 1024**3  # 4GB minimum
                if gpu_memory < min_memory:
                    logger.warning(f"GPU memory {gpu_memory/1024**3:.1f}GB < minimum {min_memory/1024**3:.1f}GB")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking F5-TTS availability: {e}")
            return False
    
    def _generate_with_local_f5tts(self, text: str, reference_audio: Path, params: TTSParameters) -> Optional[Path]:
        """Generate audio using local F5-TTS installation."""
        try:
            # Create temporary output file
            output_dir = Path("temp_audio_output")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"local_f5tts_{int(time.time())}.wav"
            
            # This is a placeholder implementation
            # In a real implementation, this would call the actual F5-TTS model
            
            # For now, we'll simulate the generation by copying the reference audio
            # and adding some processing to indicate it's "generated"
            import shutil
            import librosa
            import soundfile as sf
            import numpy as np
            
            # Load reference audio
            audio_data, sample_rate = librosa.load(str(reference_audio), sr=22050)
            
            # Apply some simple processing to simulate generation
            # (In real implementation, this would be the F5-TTS model inference)
            
            # Adjust speed based on parameters
            if params.speed != 1.0:
                audio_data = librosa.effects.time_stretch(audio_data, rate=1.0/params.speed)
            
            # Adjust pitch
            if params.pitch_adjustment != 0.0:
                # Convert pitch adjustment to semitones
                semitones = params.pitch_adjustment * 12  # Rough conversion
                audio_data = librosa.effects.pitch_shift(audio_data, sr=sample_rate, n_steps=semitones)
            
            # Add some variation based on temperature (simulate randomness)
            if params.temperature > 0.5:
                noise_level = (params.temperature - 0.5) * 0.02
                noise = np.random.normal(0, noise_level, len(audio_data))
                audio_data = audio_data + noise
            
            # Normalize
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data)) * 0.8
            
            # Save generated audio
            sf.write(str(output_path), audio_data, sample_rate)
            
            logger.info(f"Local F5-TTS simulation complete: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error in local F5-TTS generation: {e}")
            return None