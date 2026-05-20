"""
Core interfaces for the enhanced F5-TTS system components.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import (
    AudioResult, ValidationResult, TTSParameters, AudioQualityMetrics,
    CharacterConfig, HealthStatus, TTSMetrics, QuotaStatus, BackendType,
    TTSOptions, AudioArtifact
)


class AudioPreprocessorInterface(ABC):
    """Interface for audio preprocessing operations."""
    
    @abstractmethod
    def validate_audio(self, audio_path: Path) -> ValidationResult:
        """Validate audio file quality and format."""
        pass
    
    @abstractmethod
    def normalize_audio(self, audio_path: Path, output_path: Optional[Path] = None) -> Path:
        """Normalize audio levels and remove silence."""
        pass
    
    @abstractmethod
    def extract_optimal_segment(self, audio_path: Path, target_duration: int = 20) -> Path:
        """Extract the clearest segment from longer audio."""
        pass
    
    @abstractmethod
    def convert_format(self, audio_path: Path, target_format: str = "wav") -> Path:
        """Convert audio to target format."""
        pass


class QualityValidatorInterface(ABC):
    """Interface for audio quality validation."""
    
    @abstractmethod
    def calculate_similarity_score(self, generated_audio: Path, reference_audio: Path) -> float:
        """Calculate voice similarity score using speaker verification."""
        pass
    
    @abstractmethod
    def detect_artifacts(self, audio_path: Path) -> List[AudioArtifact]:
        """Detect audio artifacts like clipping, distortion."""
        pass
    
    @abstractmethod
    def validate_quality(self, audio_path: Path, reference_audio: Path, threshold: float = 0.75) -> ValidationResult:
        """Comprehensive quality validation."""
        pass


class CharacterConfigManagerInterface(ABC):
    """Interface for character configuration management."""
    
    @abstractmethod
    def get_character_config(self, character_id: str) -> Optional[CharacterConfig]:
        """Get configuration for a character."""
        pass
    
    @abstractmethod
    def update_parameters(self, character_id: str, params: TTSParameters) -> bool:
        """Update TTS parameters for a character."""
        pass
    
    @abstractmethod
    def optimize_parameters(self, character_id: str, performance_data: List[AudioQualityMetrics]) -> TTSParameters:
        """Optimize parameters based on performance history."""
        pass
    
    @abstractmethod
    def save_config(self, config: CharacterConfig) -> bool:
        """Save character configuration."""
        pass


class VoiceGenerationBackendInterface(ABC):
    """Interface for voice generation backends."""
    
    @abstractmethod
    def generate(self, text: str, reference_audio: Path, params: TTSParameters) -> AudioResult:
        """Generate voice clone audio."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if backend is available."""
        pass
    
    @abstractmethod
    def get_quota_status(self) -> QuotaStatus:
        """Get current quota status."""
        pass
    
    @abstractmethod
    def get_backend_type(self) -> BackendType:
        """Get the backend type identifier."""
        pass


class CacheManagerInterface(ABC):
    """Interface for intelligent caching system."""
    
    @abstractmethod
    def get_cached_audio(self, text: str, character_id: str) -> Optional[Path]:
        """Get cached audio if available."""
        pass
    
    @abstractmethod
    def cache_audio(self, text: str, character_id: str, audio_path: Path, quality_metrics: AudioQualityMetrics) -> bool:
        """Cache generated audio with metadata."""
        pass
    
    @abstractmethod
    def invalidate_cache(self, character_id: Optional[str] = None) -> bool:
        """Invalidate cache entries."""
        pass
    
    @abstractmethod
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class AudioEnhancerInterface(ABC):
    """Interface for audio enhancement and post-processing."""
    
    @abstractmethod
    def enhance_audio(self, audio_path: Path, reference_audio: Path) -> Path:
        """Enhance audio quality and match reference characteristics."""
        pass
    
    @abstractmethod
    def normalize_volume(self, audio_path: Path) -> Path:
        """Normalize audio volume levels."""
        pass
    
    @abstractmethod
    def reduce_noise(self, audio_path: Path) -> Path:
        """Apply noise reduction."""
        pass


class HealthMonitorInterface(ABC):
    """Interface for system health monitoring."""
    
    @abstractmethod
    def get_health_status(self) -> HealthStatus:
        """Get current system health status."""
        pass
    
    @abstractmethod
    def check_backend_health(self, backend_type: BackendType) -> bool:
        """Check specific backend health."""
        pass
    
    @abstractmethod
    def get_metrics(self) -> TTSMetrics:
        """Get comprehensive system metrics."""
        pass
    
    @abstractmethod
    def record_generation_attempt(self, character_id: str, success: bool, 
                                generation_time: float, backend_used: str) -> None:
        """Record a generation attempt for metrics."""
        pass


class EnhancedTTSServerInterface(ABC):
    """Interface for the main TTS server orchestration."""
    
    @abstractmethod
    def generate_voice(self, text: str, character_id: str, options: TTSOptions) -> AudioResult:
        """Generate voice clone with full pipeline."""
        pass
    
    @abstractmethod
    def health_check(self) -> HealthStatus:
        """Perform health check."""
        pass
    
    @abstractmethod
    def get_metrics(self) -> TTSMetrics:
        """Get system metrics."""
        pass
    
    @abstractmethod
    def clear_cache(self, character_id: Optional[str] = None) -> bool:
        """Clear system cache."""
        pass