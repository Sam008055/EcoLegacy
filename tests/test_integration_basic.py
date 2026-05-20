"""
Basic integration tests to verify components work together.
"""

import pytest
import numpy as np
import soundfile as sf
from pathlib import Path

from enhanced_tts.audio_preprocessor import AudioPreprocessor
from enhanced_tts.quality_validator import QualityValidator
from enhanced_tts.character_config_manager import CharacterConfigManager
from enhanced_tts.models import TTSParameters, CharacterConfig


class TestBasicIntegration:
    """Test basic integration between components."""
    
    def test_audio_preprocessor_validation_workflow(self, temp_dir):
        """Test complete audio preprocessing workflow."""
        preprocessor = AudioPreprocessor()
        
        # Create test audio files with different characteristics
        sample_rate = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Good quality audio
        good_audio = 0.3 * np.sin(2 * np.pi * 440 * t)
        good_file = temp_dir / "good_audio.wav"
        sf.write(good_file, good_audio, sample_rate)
        
        # Poor quality audio (very quiet)
        poor_audio = 0.01 * np.sin(2 * np.pi * 440 * t)
        poor_file = temp_dir / "poor_audio.wav"
        sf.write(poor_file, poor_audio, sample_rate)
        
        # Test validation
        good_result = preprocessor.validate_audio(good_file)
        poor_result = preprocessor.validate_audio(poor_file)
        
        assert good_result.is_valid
        assert good_result.quality_score > poor_result.quality_score
        assert len(good_result.issues) <= len(poor_result.issues)
        
        # Test normalization
        normalized_file = preprocessor.normalize_audio(good_file)
        assert normalized_file.exists()
        
        # Verify normalized audio
        normalized_audio, _ = sf.read(normalized_file)
        assert len(normalized_audio) > 0
        assert np.max(np.abs(normalized_audio)) <= 1.0
    
    def test_character_config_workflow(self, temp_dir, sample_audio_file):
        """Test character configuration management workflow."""
        manager = CharacterConfigManager(config_dir=temp_dir)
        
        # Create a character config
        config = CharacterConfig(
            character_id="test_char",
            reference_audio_path=sample_audio_file,
            reference_text="Test reference text",
            tts_parameters=TTSParameters(temperature=0.8),
            quality_threshold=0.7
        )
        
        # Save config
        assert manager.save_config(config)
        
        # Retrieve config
        retrieved_config = manager.get_character_config("test_char")
        assert retrieved_config is not None
        assert retrieved_config.character_id == "test_char"
        assert retrieved_config.tts_parameters.temperature == 0.8
        
        # Test parameter update
        new_params = TTSParameters(temperature=0.9, top_p=0.8)
        assert manager.update_parameters("test_char", new_params)
        
        # Verify update
        updated_config = manager.get_character_config("test_char")
        assert updated_config.tts_parameters.temperature == 0.9
        assert updated_config.tts_parameters.top_p == 0.8
    
    def test_quality_validator_workflow(self, temp_dir):
        """Test quality validation workflow."""
        validator = QualityValidator()
        
        # Create two similar audio files
        sample_rate = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Reference audio
        ref_audio = 0.3 * np.sin(2 * np.pi * 440 * t)
        ref_file = temp_dir / "reference.wav"
        sf.write(ref_file, ref_audio, sample_rate)
        
        # Generated audio (similar but with slight variation)
        gen_audio = 0.3 * np.sin(2 * np.pi * 442 * t)  # Slightly different frequency
        gen_file = temp_dir / "generated.wav"
        sf.write(gen_file, gen_audio, sample_rate)
        
        # Test similarity calculation
        similarity = validator.calculate_similarity_score(gen_file, ref_file)
        assert 0.0 <= similarity <= 1.0
        
        # Test artifact detection
        artifacts = validator.detect_artifacts(gen_file)
        assert isinstance(artifacts, list)
        
        # Test quality validation
        validation_result = validator.validate_quality(gen_file, ref_file, threshold=0.5)
        assert hasattr(validation_result, 'is_valid')
        assert hasattr(validation_result, 'quality_score')
        assert isinstance(validation_result.issues, list)
        assert isinstance(validation_result.recommendations, list)
    
    def test_component_integration(self, temp_dir, sample_audio_file):
        """Test integration between preprocessor, validator, and config manager."""
        # Initialize components
        preprocessor = AudioPreprocessor()
        validator = QualityValidator()
        config_manager = CharacterConfigManager(config_dir=temp_dir)
        
        # Create character config
        config = CharacterConfig(
            character_id="integration_test",
            reference_audio_path=sample_audio_file,
            reference_text="Integration test reference",
            tts_parameters=TTSParameters(),
            quality_threshold=0.6
        )
        
        # Save config
        assert config_manager.save_config(config)
        
        # Validate reference audio
        validation_result = preprocessor.validate_audio(sample_audio_file)
        assert validation_result is not None
        
        if validation_result.is_valid:
            # Normalize audio
            normalized_file = preprocessor.normalize_audio(sample_audio_file)
            assert normalized_file.exists()
            
            # Test quality validation
            quality_result = validator.validate_quality(
                normalized_file, 
                sample_audio_file, 
                threshold=config.quality_threshold
            )
            assert quality_result is not None
        
        # Retrieve and verify config
        retrieved_config = config_manager.get_character_config("integration_test")
        assert retrieved_config is not None
        assert retrieved_config.character_id == "integration_test"
    
    def test_error_handling(self, temp_dir):
        """Test error handling across components."""
        preprocessor = AudioPreprocessor()
        validator = QualityValidator()
        config_manager = CharacterConfigManager(config_dir=temp_dir)
        
        # Test with non-existent file
        non_existent = temp_dir / "does_not_exist.wav"
        
        # Preprocessor should handle missing files gracefully
        validation_result = preprocessor.validate_audio(non_existent)
        assert not validation_result.is_valid
        assert "not found" in " ".join(validation_result.issues).lower()
        
        # Config manager should handle missing characters gracefully
        missing_config = config_manager.get_character_config("non_existent_character")
        assert missing_config is None
        
        # Validator should handle missing files gracefully
        try:
            similarity = validator.calculate_similarity_score(non_existent, non_existent)
            # Should return 0.0 or handle gracefully
            assert 0.0 <= similarity <= 1.0
        except Exception:
            # Exception is acceptable for missing files
            pass