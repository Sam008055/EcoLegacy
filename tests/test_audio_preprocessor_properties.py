"""
Property-based tests for AudioPreprocessor component.

Tests universal properties that should hold across all valid audio inputs.
"""

import pytest
import numpy as np
import soundfile as sf
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume
from hypothesis.extra.numpy import arrays

from enhanced_tts.audio_preprocessor import AudioPreprocessor
from enhanced_tts.models import ValidationResult


class TestAudioPreprocessorProperties:
    """Property-based tests for AudioPreprocessor."""
    
    @pytest.fixture
    def preprocessor(self):
        """Create AudioPreprocessor instance for testing."""
        return AudioPreprocessor()
    
    @given(
        sample_rate=st.integers(min_value=16000, max_value=48000),
        duration=st.floats(min_value=1.0, max_value=10.0),
        amplitude=st.floats(min_value=0.1, max_value=0.8)
    )
    @settings(max_examples=50, deadline=5000)
    @pytest.mark.property
    def test_property_1_audio_quality_validation_consistency(
        self, preprocessor, temp_dir, sample_rate, duration, amplitude
    ):
        """
        Property 1: Audio Quality Validation Consistency
        
        For any reference audio file with measurable quality parameters,
        the Audio_Preprocessor validation SHALL consistently accept files
        meeting minimum standards and reject files below these thresholds.
        
        Feature: f5-tts-voice-cloning-accuracy, Property 1: Audio Quality Validation Consistency
        Validates: Requirements 1.1
        """
        # Generate test audio with known characteristics
        num_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, num_samples)
        
        # Create clean audio that should pass validation
        clean_audio = amplitude * np.sin(2 * np.pi * 440 * t)  # 440Hz sine wave
        
        clean_file = temp_dir / "clean_audio.wav"
        sf.write(clean_file, clean_audio, sample_rate)
        
        # Test that clean audio with good parameters passes validation
        result = preprocessor.validate_audio(clean_file)
        
        # Audio meeting minimum standards should be valid
        if sample_rate >= preprocessor.min_sample_rate and duration >= preprocessor.min_duration:
            assert result.is_valid, f"Clean audio should pass validation: {result.issues}"
            assert result.quality_score > 0.5, f"Quality score too low: {result.quality_score}"
        
        # Create problematic audio that should fail validation
        if sample_rate >= 8000:  # Only test if we can create low sample rate version
            # Low sample rate version
            low_sr_file = temp_dir / "low_sr_audio.wav"
            low_sample_rate = 8000  # Below minimum
            low_sr_samples = int(low_sample_rate * duration)
            low_sr_t = np.linspace(0, duration, low_sr_samples)
            low_sr_audio = amplitude * np.sin(2 * np.pi * 440 * low_sr_t)
            sf.write(low_sr_file, low_sr_audio, low_sample_rate)
            
            low_sr_result = preprocessor.validate_audio(low_sr_file)
            
            # Low sample rate should be flagged
            assert any("sample rate" in issue.lower() for issue in low_sr_result.issues), \
                "Low sample rate should be detected"
    
    @given(
        sample_rate=st.integers(min_value=16000, max_value=48000),
        duration=st.floats(min_value=2.0, max_value=5.0),
        amplitude=st.floats(min_value=0.1, max_value=0.8)
    )
    @settings(max_examples=30, deadline=10000)
    @pytest.mark.property
    def test_property_2_audio_normalization_preservation(
        self, preprocessor, temp_dir, sample_rate, duration, amplitude
    ):
        """
        Property 2: Audio Normalization Preservation
        
        For any valid audio file, applying Audio_Preprocessor normalization
        SHALL preserve the original speech content while producing consistent
        output levels and removing silence.
        
        Feature: f5-tts-voice-cloning-accuracy, Property 2: Audio Normalization Preservation
        Validates: Requirements 1.3
        """
        # Create test audio with silence padding and varying levels
        num_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, num_samples)
        
        # Add silence at beginning and end
        silence_duration = 0.5  # 0.5 seconds of silence
        silence_samples = int(sample_rate * silence_duration)
        
        # Create audio with speech in the middle
        speech_audio = amplitude * np.sin(2 * np.pi * 440 * t)
        
        # Add silence padding
        padded_audio = np.concatenate([
            np.zeros(silence_samples),  # Leading silence
            speech_audio,
            np.zeros(silence_samples)   # Trailing silence
        ])
        
        original_file = temp_dir / "original_with_silence.wav"
        sf.write(original_file, padded_audio, sample_rate)
        
        # Normalize the audio
        normalized_file = preprocessor.normalize_audio(original_file)
        
        # Load normalized audio
        normalized_audio, normalized_sr = sf.read(normalized_file)
        
        # Verify preservation properties
        assert normalized_sr == preprocessor.target_sample_rate, \
            "Sample rate should be normalized to target"
        
        # Normalized audio should be shorter (silence removed)
        original_speech_duration = duration
        normalized_duration = len(normalized_audio) / normalized_sr
        
        # Should remove most silence but preserve speech content
        assert normalized_duration <= original_speech_duration + 1.0, \
            "Normalized audio should not be longer than original speech"
        assert normalized_duration >= original_speech_duration * 0.8, \
            "Should preserve most of the speech content"
        
        # Check that output levels are consistent (peak around -3dB = 0.707)
        peak_level = np.max(np.abs(normalized_audio))
        assert 0.5 <= peak_level <= 0.8, \
            f"Peak level should be normalized to ~0.707, got {peak_level}"
    
    @given(
        total_duration=st.floats(min_value=35.0, max_value=60.0),
        target_duration=st.integers(min_value=10, max_value=30)
    )
    @settings(max_examples=20, deadline=15000)
    @pytest.mark.property
    def test_property_3_optimal_segment_extraction_bounds(
        self, preprocessor, temp_dir, total_duration, target_duration
    ):
        """
        Property 3: Optimal Segment Extraction Bounds
        
        For any audio file exceeding 30 seconds, the Audio_Preprocessor
        SHALL extract a segment between 10-30 seconds that represents
        the clearest portion of the original audio.
        
        Feature: f5-tts-voice-cloning-accuracy, Property 3: Optimal Segment Extraction Bounds
        Validates: Requirements 1.4
        """
        assume(total_duration > 30.0)  # Only test with long audio
        
        sample_rate = 22050
        num_samples = int(sample_rate * total_duration)
        
        # Create audio with varying quality segments
        t = np.linspace(0, total_duration, num_samples)
        
        # Create a base signal
        base_audio = 0.3 * np.sin(2 * np.pi * 440 * t)
        
        # Add a high-quality segment in the middle
        mid_start = int(len(base_audio) * 0.4)
        mid_end = int(len(base_audio) * 0.6)
        
        # Make middle segment cleaner (higher amplitude, less noise)
        base_audio[mid_start:mid_end] *= 1.5  # Higher amplitude
        
        # Add noise to other parts
        noise_level = 0.1
        noise = noise_level * np.random.normal(0, 1, len(base_audio))
        noisy_audio = base_audio + noise
        
        # Keep middle segment clean
        noisy_audio[mid_start:mid_end] = base_audio[mid_start:mid_end]
        
        long_file = temp_dir / "long_audio.wav"
        sf.write(long_file, noisy_audio, sample_rate)
        
        # Extract optimal segment
        segment_file = preprocessor.extract_optimal_segment(long_file, target_duration)
        
        # Load extracted segment
        segment_audio, segment_sr = sf.read(segment_file)
        segment_duration = len(segment_audio) / segment_sr
        
        # Verify bounds
        assert 10 <= segment_duration <= 30, \
            f"Extracted segment duration {segment_duration}s not in bounds [10, 30]"
        
        # Verify it's close to target duration
        assert abs(segment_duration - target_duration) <= 1.0, \
            f"Segment duration {segment_duration}s should be close to target {target_duration}s"
        
        # Verify the segment has reasonable quality
        segment_rms = np.sqrt(np.mean(segment_audio**2))
        assert segment_rms > 0.1, "Extracted segment should have reasonable energy level"
    
    @given(
        input_format=st.sampled_from(["wav", "flac"]),  # MP3 not fully supported yet
        sample_rate=st.integers(min_value=16000, max_value=48000),
        duration=st.floats(min_value=1.0, max_value=3.0)
    )
    @settings(max_examples=20, deadline=10000)
    @pytest.mark.property
    def test_property_4_format_conversion_consistency(
        self, preprocessor, temp_dir, input_format, sample_rate, duration
    ):
        """
        Property 4: Format Conversion Consistency
        
        For any supported audio format, the F5_TTS_System SHALL convert
        the input to the optimal format while preserving audio quality.
        
        Feature: f5-tts-voice-cloning-accuracy, Property 4: Format Conversion Consistency
        Validates: Requirements 1.5
        """
        # Create test audio
        num_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, num_samples)
        test_audio = 0.3 * np.sin(2 * np.pi * 440 * t)
        
        # Save in input format
        input_file = temp_dir / f"test_audio.{input_format}"
        
        if input_format == "wav":
            sf.write(input_file, test_audio, sample_rate, format='WAV')
        elif input_format == "flac":
            sf.write(input_file, test_audio, sample_rate, format='FLAC')
        
        # Convert to target format (WAV)
        converted_file = preprocessor.convert_format(input_file, "wav")
        
        # Load converted audio
        converted_audio, converted_sr = sf.read(converted_file)
        
        # Verify format conversion preserved audio characteristics
        assert converted_sr == preprocessor.target_sample_rate, \
            "Sample rate should be normalized to target"
        
        # Duration should be preserved (within small tolerance for resampling)
        converted_duration = len(converted_audio) / converted_sr
        assert abs(converted_duration - duration) <= 0.1, \
            f"Duration should be preserved: original {duration}s, converted {converted_duration}s"
        
        # Audio content should be similar (correlation test)
        if sample_rate != preprocessor.target_sample_rate:
            # Resample original for comparison
            import librosa
            original_resampled = librosa.resample(test_audio, orig_sr=sample_rate, 
                                                target_sr=preprocessor.target_sample_rate)
        else:
            original_resampled = test_audio
        
        # Trim to same length for comparison
        min_length = min(len(original_resampled), len(converted_audio))
        correlation = np.corrcoef(
            original_resampled[:min_length], 
            converted_audio[:min_length]
        )[0, 1]
        
        assert correlation > 0.95, \
            f"Converted audio should be highly correlated with original: {correlation}"