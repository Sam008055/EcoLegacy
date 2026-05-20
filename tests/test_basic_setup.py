"""
Basic setup tests to verify project structure and core functionality.
"""

import pytest
from pathlib import Path

from enhanced_tts.models import TTSParameters, CharacterConfig, AudioQualityMetrics
from enhanced_tts.interfaces import AudioPreprocessorInterface, QualityValidatorInterface
from enhanced_tts.audio_preprocessor import AudioPreprocessor
from enhanced_tts.quality_validator import QualityValidator
from enhanced_tts.character_config_manager import CharacterConfigManager


class TestBasicSetup:
    """Test basic project setup and imports."""
    
    def test_core_models_import(self):
        """Test that core models can be imported and instantiated."""
        # Test TTSParameters
        params = TTSParameters()
        assert params.temperature == 0.7
        assert params.top_p == 0.9
        
        # Test parameter conversion
        params_dict = params.to_dict()
        assert isinstance(params_dict, dict)
        assert params_dict["temperature"] == 0.7
        
        # Test parameter creation from dict
        new_params = TTSParameters.from_dict(params_dict)
        assert new_params.temperature == params.temperature
    
    def test_audio_quality_metrics(self):
        """Test AudioQualityMetrics model."""
        metrics = AudioQualityMetrics(
            similarity_score=0.8,
            clarity_score=0.7,
            naturalness_score=0.9,
            artifacts_detected=[],
            generation_time=5.0,
            backend_used="test_backend"
        )
        
        assert metrics.similarity_score == 0.8
        assert metrics.is_acceptable(threshold=0.75)
        assert not metrics.is_acceptable(threshold=0.85)
    
    def test_character_config_creation(self, sample_character_config):
        """Test CharacterConfig model."""
        config = sample_character_config
        
        assert config.character_id == "test_character"
        assert config.quality_threshold == 0.75
        assert isinstance(config.tts_parameters, TTSParameters)
        
        # Test getting best parameters (should return default when no history)
        best_params = config.get_best_parameters()
        assert isinstance(best_params, TTSParameters)
    
    def test_audio_preprocessor_instantiation(self):
        """Test that AudioPreprocessor can be instantiated."""
        preprocessor = AudioPreprocessor()
        
        assert isinstance(preprocessor, AudioPreprocessorInterface)
        assert preprocessor.min_sample_rate == 16000
        assert preprocessor.target_sample_rate == 22050
    
    def test_quality_validator_instantiation(self):
        """Test that QualityValidator can be instantiated."""
        validator = QualityValidator()
        
        assert isinstance(validator, QualityValidatorInterface)
        assert validator.similarity_threshold == 0.75
    
    def test_character_config_manager_instantiation(self, temp_dir):
        """Test that CharacterConfigManager can be instantiated."""
        manager = CharacterConfigManager(config_dir=temp_dir)
        
        assert manager.config_dir == temp_dir
        assert isinstance(manager.default_parameters, TTSParameters)
    
    def test_backend_imports(self):
        """Test that backend classes can be imported."""
        from enhanced_tts.backends import HuggingFaceF5TTSBackend, LocalF5TTSBackend, FallbackTTSBackend
        
        # Test instantiation
        hf_backend = HuggingFaceF5TTSBackend()
        local_backend = LocalF5TTSBackend()
        fallback_backend = FallbackTTSBackend()
        
        # Test backend type identification
        from enhanced_tts.models import BackendType
        assert hf_backend.get_backend_type() == BackendType.HUGGINGFACE_F5TTS
        assert local_backend.get_backend_type() == BackendType.LOCAL_F5TTS
        assert fallback_backend.get_backend_type() == BackendType.FALLBACK_TTS
    
    def test_project_structure(self):
        """Test that required project directories exist."""
        project_root = Path(".")
        
        # Check main directories
        assert (project_root / "enhanced_tts").exists()
        assert (project_root / "enhanced_tts" / "backends").exists()
        assert (project_root / "tests").exists()
        
        # Check key files
        assert (project_root / "enhanced_tts" / "__init__.py").exists()
        assert (project_root / "enhanced_tts" / "models.py").exists()
        assert (project_root / "enhanced_tts" / "interfaces.py").exists()
        assert (project_root / "requirements_enhanced_tts.txt").exists()
        assert (project_root / "pytest.ini").exists()
    
    def test_dependency_availability(self):
        """Test that key dependencies are available."""
        import librosa
        import soundfile
        import numpy
        import scipy
        import torch
        import hypothesis
        import pytest
        
        # Test basic functionality
        assert hasattr(librosa, 'load')
        assert hasattr(soundfile, 'write')
        assert hasattr(numpy, 'array')
        assert hasattr(torch, 'tensor')
        assert hasattr(hypothesis, 'given')