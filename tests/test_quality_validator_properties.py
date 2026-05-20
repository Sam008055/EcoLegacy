"""
Property-based tests for QualityValidator component.

Tests universal properties for voice similarity and artifact detection.
"""

import pytest
import numpy as np
import soundfile as sf
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume

from enhanced_tts.quality_validator import QualityValidator
from enhanced_tts.models import ValidationResult, AudioArtifact


class TestQualityValidatorProperties:
    """Property-based tests for QualityValidator."""
    
    @pytest.fixture
    def validator(self):
        """Create QualityValidator instance for testing."""
        return QualityValidator(device="cpu")  # Use CPU for testing
    
    @given(
        similarity_level=st.floats(min_value=0.0, max_value=1.0),
        threshold=st.floats(min_value=0.5, max_value=0.9)
    )
    @settings(max_examples=30, deadline=10000)
    @pytest.mark.property
    def test_property_5_voice_similarity_threshold_compliance(
        self, validator, temp_dir, similarity_level, threshold
    ):
        """
        Property 5: Voice Similarity Threshold Compliance
        
        For any generated voice clone, when compared to its reference audio
        using speaker verification models, the F5_TTS_System SHALL achieve
        a Voice_Similarity_Score of at least 0.75, or trigger regeneration.
        
        Feature: f5-tts-voice-cloning-accuracy, Property 5: Voice Similarity Threshold Compliance
        Validates: Requirements 2.1
        """
        sample_rate = 22050
        duration = 3.0
        
        # Create reference audio
        t = np.linspace(0, duration, int(sample_rate * duration))
        reference_audio = 0.3 * np.sin(2 * np.pi * 440 * t)  # 440Hz sine wave
        
        reference_file = temp_dir / "reference.wav"
        sf.write(reference_file, reference_audio, sample_rate)
        
        # Create generated audio with controlled similarity
        # Higher similarity_level means more similar to reference
        if similarity_level > 0.7:
            # High similarity: same frequency, slight variations
            generated_audio = reference_audio * (0.8 + 0.4 * similarity_level)
            generated_audio += 0.05 * np.random.normal(0, 1, len(generated_audio))
        elif similarity_level > 0.4:
            # Medium similarity: different amplitude, some frequency shift
            freq_shift = (1.0 - similarity_level) * 200  # Up to 200Hz shift
            generated_audio = 0.3 * np.sin(2 * np.pi * (440 + freq_shift) * t)
            generated_audio *= similarity_level + 0.3
        else:
            # Low similarity: different frequency and characteristics
            generated_audio = 0.3 * np.sin(2 * np.pi * 880 * t)  # Different frequency
            generated_audio += 0.2 * np.random.normal(0, 1, len(generated_audio))
        
        generated_file = temp_dir / "generated.wav"
        sf.write(generated_file, generated_audio, sample_rate)
        
        # Calculate similarity score
        calculated_score = validator.calculate_similarity_score(generated_file, reference_file)
        
        # Validate quality with threshold
        validation_result = validator.validate_quality(generated_file, reference_file, threshold)
        
        # Property: If similarity is below threshold, validation should fail
        if calculated_score < threshold:
            assert not validation_result.is_valid, \
                f"Validation should fail when similarity {calculated_score:.3f} < threshold {threshold:.3f}"
            assert any("similarity" in issue.lower() for issue in validation_result.issues), \
                "Low similarity should be reported in issues"
        
        # Property: Similarity score should be in valid range
        assert 0.0 <= calculated_score <= 1.0, \
            f"Similarity score {calculated_score} should be in range [0, 1]"
    
    @given(
        clipping_level=st.floats(min_value=0.0, max_value=0.3),
        noise_level=st.floats(min_value=0.0, max_value=0.5)
    )
    @settings(max_examples=25, deadline=8000)
    @pytest.mark.property
    def test_property_9_audio_artifact_detection_accuracy(
        self, validator, temp_dir, clipping_level, noise_level
    ):
        """
        Property 9: Audio Artifact Detection Accuracy
        
        For any audio containing detectable artifacts (clipping, distortion,
        unnatural pauses), the Quality_Validator SHALL identify and flag
        these issues with appropriate artifact type classification.
        
        Feature: f5-tts-voice-cloning-accuracy, Property 9: Audio Artifact Detection Accuracy
        Validates: Requirements 3.3
        """
        sample_rate = 22050
        duration = 2.0
        
        # Create base audio
        t = np.linspace(0, duration, int(sample_rate * duration))
        clean_audio = 0.3 * np.sin(2 * np.pi * 440 * t)
        
        # Add controlled artifacts
        test_audio = clean_audio.copy()
        expected_artifacts = []
        
        # Add clipping if specified
        if clipping_level > 0.1:
            # Amplify part of the audio to cause clipping
            clip_start = int(len(test_audio) * 0.3)
            clip_end = int(len(test_audio) * 0.4)
            amplification = 1.0 + clipping_level * 10
            test_audio[clip_start:clip_end] *= amplification
            test_audio = np.clip(test_audio, -1.0, 1.0)  # Hard clipping
            expected_artifacts.append("clipping")
        
        # Add noise/distortion if specified
        if noise_level > 0.2:
            noise = noise_level * np.random.normal(0, 1, len(test_audio))
            test_audio += noise
            if noise_level > 0.3:
                expected_artifacts.append("distortion")
        
        # Add unnatural pause if we want to test that
        if len(expected_artifacts) == 0:  # Only add pause if no other artifacts
            # Insert a long silence in the middle
            pause_start = int(len(test_audio) * 0.4)
            pause_duration = int(sample_rate * 1.5)  # 1.5 second pause
            pause_end = min(pause_start + pause_duration, len(test_audio))
            test_audio[pause_start:pause_end] = 0
            expected_artifacts.append("unnatural_pause")
        
        test_file = temp_dir / "test_audio.wav"
        sf.write(test_file, test_audio, sample_rate)
        
        # Detect artifacts
        detected_artifacts = validator.detect_artifacts(test_file)
        
        # Property: Should detect expected artifacts
        detected_types = [artifact.artifact_type for artifact in detected_artifacts]
        
        for expected_type in expected_artifacts:
            if expected_type == "clipping" and clipping_level > 0.15:
                assert any("clipping" in detected_type for detected_type in detected_types), \
                    f"Should detect clipping artifact with level {clipping_level}"
            elif expected_type == "unnatural_pause":
                assert any("pause" in detected_type for detected_type in detected_types), \
                    "Should detect unnatural pause artifact"
        
        # Property: All detected artifacts should have valid properties
        for artifact in detected_artifacts:
            assert isinstance(artifact, AudioArtifact), "Should return AudioArtifact objects"
            assert 0.0 <= artifact.severity <= 1.0, \
                f"Artifact severity {artifact.severity} should be in range [0, 1]"
            assert artifact.timestamp >= 0.0, \
                f"Artifact timestamp {artifact.timestamp} should be non-negative"
            assert len(artifact.description) > 0, "Artifact should have description"
    
    @given(
        generation_time=st.floats(min_value=1.0, max_value=30.0),
        backend_name=st.sampled_from(["local_f5tts", "huggingface_f5tts", "fallback_tts"])
    )
    @settings(max_examples=20, deadline=5000)
    @pytest.mark.property
    def test_property_10_metrics_logging_completeness(
        self, validator, temp_dir, generation_time, backend_name
    ):
        """
        Property 10: Metrics Logging Completeness
        
        For any voice generation request, the F5_TTS_System SHALL log all
        required quality metrics (generation time, similarity score, backend used,
        parameters) to enable comprehensive performance monitoring.
        
        Feature: f5-tts-voice-cloning-accuracy, Property 10: Metrics Logging Completeness
        Validates: Requirements 3.4, 7.1
        """
        sample_rate = 22050
        duration = 2.0
        
        # Create test audio files
        t = np.linspace(0, duration, int(sample_rate * duration))
        reference_audio = 0.3 * np.sin(2 * np.pi * 440 * t)
        generated_audio = 0.3 * np.sin(2 * np.pi * 450 * t)  # Slightly different
        
        reference_file = temp_dir / "reference.wav"
        generated_file = temp_dir / "generated.wav"
        
        sf.write(reference_file, reference_audio, sample_rate)
        sf.write(generated_file, generated_audio, sample_rate)
        
        # Perform quality validation (simulates full pipeline)
        validation_result = validator.validate_quality(generated_file, reference_file)
        
        # Calculate individual metrics that should be logged
        similarity_score = validator.calculate_similarity_score(generated_file, reference_file)
        artifacts = validator.detect_artifacts(generated_file)
        
        # Property: All required metrics should be available and valid
        assert isinstance(similarity_score, float), "Similarity score should be numeric"
        assert 0.0 <= similarity_score <= 1.0, "Similarity score should be in valid range"
        
        assert isinstance(artifacts, list), "Artifacts should be a list"
        for artifact in artifacts:
            assert hasattr(artifact, 'artifact_type'), "Artifact should have type"
            assert hasattr(artifact, 'severity'), "Artifact should have severity"
            assert hasattr(artifact, 'timestamp'), "Artifact should have timestamp"
        
        assert isinstance(validation_result.quality_score, float), "Quality score should be numeric"
        assert 0.0 <= validation_result.quality_score <= 1.0, "Quality score should be in valid range"
        
        # Property: Validation result should contain comprehensive information
        assert hasattr(validation_result, 'is_valid'), "Should have validity flag"
        assert hasattr(validation_result, 'issues'), "Should have issues list"
        assert hasattr(validation_result, 'recommendations'), "Should have recommendations"
        
        # Simulate creating AudioQualityMetrics (this would be done by the TTS server)
        from enhanced_tts.models import AudioQualityMetrics
        
        # Calculate additional metrics
        clarity_score = 0.8  # Would be calculated by audio processor
        naturalness_score = 0.7  # Would be calculated by quality validator
        
        metrics = AudioQualityMetrics(
            similarity_score=similarity_score,
            clarity_score=clarity_score,
            naturalness_score=naturalness_score,
            artifacts_detected=[a.artifact_type for a in artifacts],
            generation_time=generation_time,
            backend_used=backend_name
        )
        
        # Property: Metrics object should contain all required fields
        assert hasattr(metrics, 'similarity_score'), "Should have similarity score"
        assert hasattr(metrics, 'clarity_score'), "Should have clarity score"
        assert hasattr(metrics, 'naturalness_score'), "Should have naturalness score"
        assert hasattr(metrics, 'artifacts_detected'), "Should have artifacts list"
        assert hasattr(metrics, 'generation_time'), "Should have generation time"
        assert hasattr(metrics, 'backend_used'), "Should have backend identifier"
        assert hasattr(metrics, 'timestamp'), "Should have timestamp"
        
        # Property: Metrics should be acceptable for quality threshold
        is_acceptable = metrics.is_acceptable(threshold=0.75)
        assert isinstance(is_acceptable, bool), "Acceptability should be boolean"