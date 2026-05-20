"""
HuggingFace F5-TTS backend implementation.

Uses the HuggingFace Gradio space for F5-TTS voice generation.
"""

import os
import logging
import time
import shutil
from pathlib import Path
from typing import Optional

from ..interfaces import VoiceGenerationBackendInterface
from ..models import AudioResult, TTSParameters, QuotaStatus, BackendType, AudioQualityMetrics

logger = logging.getLogger(__name__)


def get_hf_tokens() -> list[str]:
    """Get available HuggingFace tokens from environment."""
    keys = [
        "HUGGINGFACE_TOKEN",
        "HUGGINGFACE_TOKEN_1", 
        "HUGGINGFACE_TOKEN_2",
        "HUGGINGFACE_TOKEN_3",
        "HUGGINGFACE_TOKEN_4",
        "HUGGINGFACE_TOKEN_5",
    ]
    return [os.environ[k] for k in keys if os.environ.get(k)]


class HuggingFaceF5TTSBackend(VoiceGenerationBackendInterface):
    """
    HuggingFace F5-TTS backend using Gradio space.
    
    This backend uses the HuggingFace F5-TTS Gradio space for voice generation,
    with support for multiple tokens and quota management.
    """
    
    def __init__(self, 
                 space_name: str = "chenxie95/Cross-Lingual_F5-TTS_Space",
                 max_retries: int = 3,
                 timeout: int = 60):
        """
        Initialize the HuggingFace F5-TTS backend.
        
        Args:
            space_name: HuggingFace space identifier
            max_retries: Maximum retry attempts per token
            timeout: Request timeout in seconds
        """
        self.space_name = space_name
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Track quota status for each token
        self._token_status = {}
        self._last_error = None
    
    def generate(self, text: str, reference_audio: Path, params: TTSParameters) -> AudioResult:
        """
        Generate voice clone using HuggingFace F5-TTS.
        
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
        
        tokens = get_hf_tokens()
        if not tokens:
            return AudioResult(
                audio_path=None,
                quality_metrics=None,
                success=False,
                error_message="No HuggingFace tokens configured"
            )
        
        # Prepare text (limit length and clean)
        gen_text = text.replace("\n", " ").strip()
        if len(gen_text) > 500:
            gen_text = gen_text[:500] + "..."
        
        logger.info(f"HF F5-TTS generation | text_length={len(gen_text)} | ref={reference_audio.name}")
        
        try:
            from gradio_client import Client, handle_file
        except ImportError:
            return AudioResult(
                audio_path=None,
                quality_metrics=None,
                success=False,
                error_message="gradio-client not installed. Run: pip install gradio-client"
            )
        
        # Try each token until one succeeds
        last_error = ""
        
        for i, token in enumerate(tokens):
            try:
                logger.info(f"Trying HF token {i + 1}/{len(tokens)}")
                
                # Check if this token is known to be exhausted
                if self._is_token_exhausted(token):
                    logger.info(f"Skipping token {i + 1} (quota exhausted)")
                    continue
                
                client = Client(self.space_name, token=token, verbose=False)
                
                # Make the API call with parameters
                result = client.predict(
                    ref_wav_input=handle_file(str(reference_audio)),
                    gen_txt_input=gen_text,
                    randomize_seed=True,
                    seed_input=0,
                    api_name="/basic_tts",
                )
                
                # Extract audio file from result
                audio_path = self._extract_audio_from_result(result)
                
                if audio_path and audio_path.exists() and audio_path.stat().st_size > 100:
                    generation_time = time.time() - start_time
                    
                    # Create quality metrics (basic info, detailed analysis done elsewhere)
                    quality_metrics = AudioQualityMetrics(
                        similarity_score=0.0,  # Will be calculated by quality validator
                        clarity_score=0.0,     # Will be calculated by quality validator
                        naturalness_score=0.0, # Will be calculated by quality validator
                        artifacts_detected=[], # Will be detected by quality validator
                        generation_time=generation_time,
                        backend_used="huggingface_f5tts"
                    )
                    
                    logger.info(f"HF F5-TTS success | size={audio_path.stat().st_size} bytes | time={generation_time:.1f}s")
                    
                    # Mark token as working
                    self._mark_token_working(token)
                    
                    return AudioResult(
                        audio_path=audio_path,
                        quality_metrics=quality_metrics,
                        success=True
                    )
                else:
                    last_error = "HuggingFace returned empty or invalid audio"
                    logger.warning(f"Token {i + 1}: {last_error}")
            
            except Exception as e:
                last_error = str(e)
                logger.warning(f"HF token {i + 1} failed: {e}")
                
                # Check if this is a quota/ZeroGPU error
                if any(keyword in last_error.lower() for keyword in ["quota", "zerogpu", "rate limit"]):
                    self._mark_token_exhausted(token)
                    logger.info(f"Marked token {i + 1} as quota exhausted")
        
        # All tokens failed
        self._last_error = last_error
        
        if "quota" in last_error.lower() or "zerogpu" in last_error.lower():
            error_msg = f"{last_error} - All HuggingFace tokens quota exhausted. Wait for reset or add more tokens."
        else:
            error_msg = f"All HuggingFace tokens failed: {last_error}"
        
        return AudioResult(
            audio_path=None,
            quality_metrics=None,
            success=False,
            error_message=error_msg
        )
    
    def is_available(self) -> bool:
        """Check if the HuggingFace backend is available."""
        tokens = get_hf_tokens()
        if not tokens:
            return False
        
        # Check if at least one token is not exhausted
        available_tokens = [token for token in tokens if not self._is_token_exhausted(token)]
        return len(available_tokens) > 0
    
    def get_quota_status(self) -> QuotaStatus:
        """Get current quota status for HuggingFace backend."""
        tokens = get_hf_tokens()
        
        if not tokens:
            return QuotaStatus(
                backend_type=BackendType.HUGGINGFACE_F5TTS,
                requests_remaining=0,
                reset_time=None,
                is_available=False,
                last_error="No HuggingFace tokens configured"
            )
        
        # Count available tokens (not exhausted)
        available_tokens = [token for token in tokens if not self._is_token_exhausted(token)]
        
        return QuotaStatus(
            backend_type=BackendType.HUGGINGFACE_F5TTS,
            requests_remaining=len(available_tokens) * 10,  # Rough estimate
            reset_time=None,  # HuggingFace doesn't provide reset time
            is_available=len(available_tokens) > 0,
            last_error=self._last_error
        )
    
    def get_backend_type(self) -> BackendType:
        """Get the backend type identifier."""
        return BackendType.HUGGINGFACE_F5TTS
    
    def _extract_audio_from_result(self, result) -> Optional[Path]:
        """Extract audio file path from Gradio client result."""
        try:
            audio_src = None
            
            if isinstance(result, (list, tuple)) and len(result) > 0:
                audio_src = result[0]
                if hasattr(audio_src, "path"):
                    audio_src = audio_src.path
                elif isinstance(audio_src, dict):
                    audio_src = audio_src.get("path") or audio_src.get("url")
            elif isinstance(result, dict):
                audio_src = result.get("path") or result.get("url")
            elif isinstance(result, str):
                audio_src = result
            
            if audio_src:
                src_path = Path(audio_src)
                if src_path.exists():
                    # Copy to a permanent location
                    output_dir = Path("temp_audio_output")
                    output_dir.mkdir(exist_ok=True)
                    
                    output_path = output_dir / f"hf_output_{int(time.time())}.wav"
                    shutil.copy2(src_path, output_path)
                    
                    return output_path
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting audio from result: {e}")
            return None
    
    def _is_token_exhausted(self, token: str) -> bool:
        """Check if a token is marked as quota exhausted."""
        status = self._token_status.get(token, {})
        
        # If marked as exhausted, check if enough time has passed (reset after 1 hour)
        if status.get("exhausted", False):
            exhausted_time = status.get("exhausted_at", 0)
            if time.time() - exhausted_time > 3600:  # 1 hour
                # Reset the token status
                self._token_status[token] = {"exhausted": False}
                return False
            return True
        
        return False
    
    def _mark_token_exhausted(self, token: str):
        """Mark a token as quota exhausted."""
        self._token_status[token] = {
            "exhausted": True,
            "exhausted_at": time.time()
        }
    
    def _mark_token_working(self, token: str):
        """Mark a token as working (not exhausted)."""
        self._token_status[token] = {"exhausted": False}