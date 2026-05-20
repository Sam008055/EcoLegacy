"""
Fallback TTS backend implementation.

Provides a fallback TTS service when F5-TTS backends are unavailable.
"""

import logging
import time
import tempfile
from pathlib import Path
from typing import Optional

from ..interfaces import VoiceGenerationBackendInterface
from ..models import AudioResult, TTSParameters, QuotaStatus, BackendType, AudioQualityMetrics

logger = logging.getLogger(__name__)


class FallbackTTSBackend(VoiceGenerationBackendInterface):
    """
    Fallback TTS backend using alternative TTS services.
    
    This backend provides basic TTS functionality when F5-TTS is unavailable.
    Uses edge-tts or other available TTS services.
    """
    
    def __init__(self, 
                 preferred_service: str = "edge-tts",
                 voice_mapping: dict = None):
        """
        Initialize the fallback TTS backend.
        
        Args:
            preferred_service: Preferred TTS service ("edge-tts", "espeak", etc.)
            voice_mapping: Mapping of character IDs to fallback voices
        """
        self.preferred_service = preferred_service
        self.voice_mapping = voice_mapping or {
            "osho": "en-US-AriaNeural",
            "bhagat_singh": "en-IN-NeerjaNeural", 
            "ssr": "en-IN-PrabhatNeural",
            "tesla": "en-US-GuyNeural",
            "hitler": "de-DE-ConradNeural"
        }
        
        self._service_available = None
        self._last_error = None
    
    def generate(self, text: str, reference_audio: Path, params: TTSParameters) -> AudioResult:
        """
        Generate speech using fallback TTS service.
        
        Note: Fallback TTS doesn't use reference audio for voice cloning,
        but uses predefined voices based on character mapping.
        
        Args:
            text: Text to synthesize
            reference_audio: Path to reference audio (not used in fallback)
            params: TTS parameters (limited support)
            
        Returns:
            AudioResult with generated audio or error information
        """
        start_time = time.time()
        
        # Check if service is available
        if not self.is_available():
            return AudioResult(
                audio_path=None,
                quality_metrics=None,
                success=False,
                error_message=f"Fallback TTS service '{self.preferred_service}' not available: {self._last_error}"
            )
        
        # Prepare text
        gen_text = text.replace("\n", " ").strip()
        if len(gen_text) > 1000:  # Fallback services often have longer limits
            gen_text = gen_text[:1000] + "..."
        
        logger.info(f"Fallback TTS generation | service={self.preferred_service} | text_length={len(gen_text)}")
        
        try:
            # Generate audio using the fallback service
            output_path = self._generate_with_service(gen_text, params)
            
            if output_path and output_path.exists() and output_path.stat().st_size > 100:
                generation_time = time.time() - start_time
                
                # Create quality metrics (fallback has lower quality expectations)
                quality_metrics = AudioQualityMetrics(
                    similarity_score=0.3,  # Lower similarity since no voice cloning
                    clarity_score=0.7,     # Usually good clarity
                    naturalness_score=0.6, # Decent naturalness
                    artifacts_detected=[], # Will be detected by quality validator
                    generation_time=generation_time,
                    backend_used="fallback_tts"
                )
                
                logger.info(f"Fallback TTS success | size={output_path.stat().st_size} bytes | time={generation_time:.1f}s")
                
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
                    error_message="Fallback TTS generated empty or invalid audio"
                )
        
        except Exception as e:
            logger.error(f"Fallback TTS generation failed: {e}")
            return AudioResult(
                audio_path=None,
                quality_metrics=None,
                success=False,
                error_message=f"Fallback TTS error: {str(e)}"
            )
    
    def is_available(self) -> bool:
        """Check if the fallback TTS service is available."""
        if self._service_available is not None:
            return self._service_available
        
        return self._check_service_availability()
    
    def get_quota_status(self) -> QuotaStatus:
        """Get current quota status for fallback backend."""
        # Most fallback services have generous or no quotas
        return QuotaStatus(
            backend_type=BackendType.FALLBACK_TTS,
            requests_remaining=1000,  # Generous estimate
            reset_time=None,
            is_available=self.is_available(),
            last_error=self._last_error
        )
    
    def get_backend_type(self) -> BackendType:
        """Get the backend type identifier."""
        return BackendType.FALLBACK_TTS
    
    def _check_service_availability(self) -> bool:
        """Check if the preferred TTS service is available."""
        try:
            if self.preferred_service == "edge-tts":
                return self._check_edge_tts()
            elif self.preferred_service == "espeak":
                return self._check_espeak()
            else:
                self._last_error = f"Unknown fallback service: {self.preferred_service}"
                return False
                
        except Exception as e:
            self._last_error = f"Error checking service availability: {e}"
            logger.error(self._last_error)
            return False
    
    def _check_edge_tts(self) -> bool:
        """Check if edge-tts is available."""
        try:
            import edge_tts
            self._service_available = True
            return True
        except ImportError:
            self._last_error = "edge-tts not installed. Run: pip install edge-tts"
            self._service_available = False
            return False
    
    def _check_espeak(self) -> bool:
        """Check if espeak is available."""
        try:
            import subprocess
            result = subprocess.run(["espeak", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self._service_available = True
                return True
            else:
                self._last_error = "espeak not found in system PATH"
                self._service_available = False
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self._last_error = "espeak not available"
            self._service_available = False
            return False
    
    def _generate_with_service(self, text: str, params: TTSParameters) -> Optional[Path]:
        """Generate audio using the configured fallback service."""
        if self.preferred_service == "edge-tts":
            return self._generate_with_edge_tts(text, params)
        elif self.preferred_service == "espeak":
            return self._generate_with_espeak(text, params)
        else:
            raise ValueError(f"Unsupported service: {self.preferred_service}")
    
    def _generate_with_edge_tts(self, text: str, params: TTSParameters) -> Optional[Path]:
        """Generate audio using edge-tts."""
        try:
            import edge_tts
            import asyncio
            
            # Create output file
            output_dir = Path("temp_audio_output")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"fallback_edge_{int(time.time())}.wav"
            
            # Select voice (use default if no mapping)
            voice = "en-US-AriaNeural"  # Default voice
            
            # Apply speed parameter
            rate = f"{int((params.speed - 1.0) * 50):+d}%"  # Convert to percentage
            
            async def generate():
                communicate = edge_tts.Communicate(text, voice, rate=rate)
                await communicate.save(str(output_path))
            
            # Run the async function
            asyncio.run(generate())
            
            logger.info(f"Edge-TTS generation complete: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Edge-TTS generation error: {e}")
            return None
    
    def _generate_with_espeak(self, text: str, params: TTSParameters) -> Optional[Path]:
        """Generate audio using espeak."""
        try:
            import subprocess
            
            # Create output file
            output_dir = Path("temp_audio_output")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"fallback_espeak_{int(time.time())}.wav"
            
            # Build espeak command
            speed_wpm = int(175 * params.speed)  # Default 175 WPM, adjust by speed
            
            cmd = [
                "espeak",
                "-s", str(speed_wpm),  # Speed in words per minute
                "-w", str(output_path),  # Output file
                text
            ]
            
            # Run espeak
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and output_path.exists():
                logger.info(f"Espeak generation complete: {output_path}")
                return output_path
            else:
                logger.error(f"Espeak failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Espeak generation error: {e}")
            return None
    
    def get_character_voice(self, character_id: str) -> str:
        """Get the fallback voice for a character."""
        return self.voice_mapping.get(character_id, "en-US-AriaNeural")