"""
Core data models and interfaces for the enhanced F5-TTS system.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
from enum import Enum
import time


class BackendType(Enum):
    """Available TTS backend types."""
    LOCAL_F5TTS = "local_f5tts"
    HUGGINGFACE_F5TTS = "huggingface_f5tts"
    FALLBACK_TTS = "fallback_tts"


class AudioFormat(Enum):
    """Supported audio formats."""
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"


@dataclass
class TTSParameters:
    """F5-TTS generation parameters for character-specific optimization."""
    temperature: float = 0.7
    top_p: float = 0.9
    speed: float = 1.0
    pitch_adjustment: float = 0.0
    noise_scale: float = 0.667
    length_scale: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "speed": self.speed,
            "pitch_adjustment": self.pitch_adjustment,
            "noise_scale": self.noise_scale,
            "length_scale": self.length_scale
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TTSParameters':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class AudioQualityMetrics:
    """Comprehensive audio quality metrics for voice generation."""
    similarity_score: float
    clarity_score: float
    naturalness_score: float
    artifacts_detected: List[str]
    generation_time: float
    backend_used: str
    timestamp: float = field(default_factory=time.time)
    
    def is_acceptable(self, threshold: float = 0.75) -> bool:
        """Check if quality meets acceptance threshold."""
        return self.similarity_score >= threshold and len(self.artifacts_detected) == 0


@dataclass
class ValidationResult:
    """Result of audio validation process."""
    is_valid: bool
    quality_score: float
    issues: List[str]
    recommendations: List[str]
    
    def __bool__(self) -> bool:
        """Allow boolean evaluation."""
        return self.is_valid


@dataclass
class AudioArtifact:
    """Detected audio artifact with details."""
    artifact_type: str  # "clipping", "distortion", "unnatural_pause", etc.
    severity: float  # 0.0 to 1.0
    timestamp: float  # Position in audio (seconds)
    description: str


@dataclass
class ParameterResult:
    """Result of parameter optimization attempt."""
    parameters: TTSParameters
    quality_metrics: AudioQualityMetrics
    success: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class CharacterConfig:
    """Configuration for a specific character's voice cloning."""
    character_id: str
    reference_audio_path: Path
    reference_text: str
    tts_parameters: TTSParameters
    quality_threshold: float = 0.75
    optimization_history: List[ParameterResult] = field(default_factory=list)
    
    def get_best_parameters(self) -> TTSParameters:
        """Get the best performing parameters from history."""
        if not self.optimization_history:
            return self.tts_parameters
        
        successful_results = [r for r in self.optimization_history if r.success]
        if not successful_results:
            return self.tts_parameters
        
        # Return parameters with highest similarity score
        best_result = max(successful_results, 
                         key=lambda r: r.quality_metrics.similarity_score)
        return best_result.parameters


@dataclass
class AudioResult:
    """Result of audio generation process."""
    audio_path: Optional[Path]
    quality_metrics: Optional[AudioQualityMetrics]
    success: bool
    error_message: Optional[str] = None
    cached: bool = False
    
    def __bool__(self) -> bool:
        """Allow boolean evaluation."""
        return self.success and self.audio_path is not None


@dataclass
class HealthStatus:
    """System health status information."""
    overall_status: str  # "healthy", "degraded", "unhealthy"
    backend_status: Dict[str, bool]
    reference_audio_status: Dict[str, bool]
    cache_status: Dict[str, Any]
    error_rate: float
    avg_generation_time: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class TTSMetrics:
    """Comprehensive TTS system metrics."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    cache_hits: int
    cache_misses: int
    avg_generation_time: float
    avg_similarity_score: float
    backend_usage: Dict[str, int]
    character_usage: Dict[str, int]
    error_breakdown: Dict[str, int]
    timestamp: float = field(default_factory=time.time)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total_cache_requests = self.cache_hits + self.cache_misses
        if total_cache_requests == 0:
            return 0.0
        return (self.cache_hits / total_cache_requests) * 100


@dataclass
class QuotaStatus:
    """Backend quota status information."""
    backend_type: BackendType
    requests_remaining: Optional[int]
    reset_time: Optional[float]
    is_available: bool
    last_error: Optional[str] = None


@dataclass
class TTSOptions:
    """Options for TTS generation request."""
    use_cache: bool = True
    max_retries: int = 3
    quality_threshold: float = 0.75
    preferred_backend: Optional[BackendType] = None
    streaming: bool = False
    enhance_audio: bool = True