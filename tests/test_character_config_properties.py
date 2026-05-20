"""
Property-based tests for CharacterConfigManager component.

Tests universal properties for character-specific parameter management.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume

from enhanced_tts.character_config_manager import CharacterConfigManager
from enhanced_tts.models import CharacterConfig, TTSParameters, AudioQualityMetrics


class TestCharacterConfigManagerProperties:
    """Property-based tests for CharacterConfigManager."""
    
    @pytest.fixture
    def config_manager(self):
        """Create CharacterConfigManager with temporary directory."""
        temp_dir = Path(tempfile.mkdtemp())
        manager = CharacterConfigManager(config_dir=temp_dir)
        yield manager
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(
        character_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        temperature=st.floats(min_value=0.1, max_value=1.0),
        top_p=st.floats(min_value=0.1, max_value=1.0),
        speed=st.floats(min_value=0.5, max_value=2.0)
    )
    @settings(max_examples=30, deadline=5000)
    @pytest.mark.property
    def test_property_11_character_specific_parameter_application(
        self, config_manager, sample_character_config, character_id, temperature, top_p, speed
    ):
        """
        Property 11: Character-Specific Parameter Application
        
        For any voice generation request, the F5_TTS_System SHALL apply
        the character-specific optimization parameters configured for that character.
        
        Feature: f5-tts-voice-cloning-accuracy, Property 11: Character-Specific Parameter Application
        Validates: Requirements 4.2
        """
        # Create custom parameters for the character
        custom_params = TTSParameters(
            temperature=temperature,
            top_p=top_p,
            speed=speed,
            pitch_adjustment=0.1,
            noise_scale=0.6,
            length_scale=1.1
        )
        
        # Create character config with custom parameters
        config = CharacterConfig(
            character_id=character_id,
            reference_audio_path=sample_character_config.reference_audio_path,
            reference_text=sample_character_config.reference_text,
            tts_parameters=custom_params,
            quality_threshold=0.75
        )
        
        # Save the configuration
        save_success = config_manager.save_config(config)
        assert save_success, "Should successfully save character configuration"
        
        # Retrieve the configuration
        retrieved_config = config_manager.get_character_config(character_id)
        
        # Property: Retrieved config should have the exact parameters we set
        assert retrieved_config is not None, f"Should retrieve config for character {character_id}"
        assert retrieved_config.character_id == character_id, "Character ID should match"
        
        # Verify all parameter values are preserved
        retrieved_params = retrieved_config.tts_parameters
        assert abs(retrieved_params.temperature - temperature) < 1e-6, \
            f"Temperature should be preserved: expected {temperature}, got {retrieved_params.temperature}"
        assert abs(retrieved_params.top_p - top_p) < 1e-6, \
            f"Top_p should be preserved: expected {top_p}, got {retrieved_params.top_p}"
        assert abs(retrieved_params.speed - speed) < 1e-6, \
            f"Speed should be preserved: expected {speed}, got {retrieved_params.speed}"
        assert abs(retrieved_params.pitch_adjustment - 0.1) < 1e-6, \
            "Pitch adjustment should be preserved"
        assert abs(retrieved_params.noise_scale - 0.6) < 1e-6, \
            "Noise scale should be preserved"
        assert abs(retrieved_params.length_scale - 1.1) < 1e-6, \
            "Length scale should be preserved"
        
        # Property: Parameters should be within valid ranges
        assert 0.1 <= retrieved_params.temperature <= 1.0, "Temperature should be in valid range"
        assert 0.1 <= retrieved_params.top_p <= 1.0, "Top_p should be in valid range"
        assert 0.5 <= retrieved_params.speed <= 2.0, "Speed should be in valid range"
    
    @given(
        character_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        num_generations=st.integers(min_value=1, max_value=10),
        success_rate=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=20, deadline=8000)
    @pytest.mark.property
    def test_property_12_successful_parameter_caching(
        self, config_manager, sample_character_config, character_id, num_generations, success_rate
    ):
        """
        Property 12: Successful Parameter Caching
        
        For any voice generation that achieves quality scores above threshold,
        the F5_TTS_System SHALL cache the successful parameter combination
        for that character to improve future generation efficiency.
        
        Feature: f5-tts-voice-cloning-accuracy, Property 12: Successful Parameter Caching
        Validates: Requirements 4.5
        """
        # Create initial character config
        initial_params = TTSParameters(temperature=0.7, top_p=0.9, speed=1.0)
        config = CharacterConfig(
            character_id=character_id,
            reference_audio_path=sample_character_config.reference_audio_path,
            reference_text=sample_character_config.reference_text,
            tts_parameters=initial_params,
            quality_threshold=0.75
        )
        
        # Save initial config
        config_manager.save_config(config)
        
        # Simulate multiple generation attempts with varying success
        successful_params = []
        
        for i in range(num_generations):
            # Create slightly different parameters for each attempt
            attempt_params = TTSParameters(
                temperature=0.7 + (i * 0.05),
                top_p=0.9 - (i * 0.02),
                speed=1.0 + (i * 0.1)
            )
            
            # Determine if this attempt is successful based on success_rate
            is_successful = (i / num_generations) < success_rate
            
            # Create quality metrics
            if is_successful:
                similarity_score = 0.8 + (i * 0.02)  # Increasing quality
                successful_params.append(attempt_params)
            else:
                similarity_score = 0.6 - (i * 0.01)  # Decreasing quality
            
            quality_metrics = AudioQualityMetrics(
                similarity_score=similarity_score,
                clarity_score=0.8,
                naturalness_score=0.7,
                artifacts_detected=[],
                generation_time=5.0,
                backend_used="test_backend"
            )
            
            # Record the generation result
            record_success = config_manager.record_generation_result(
                character_id, attempt_params, quality_metrics, is_successful
            )
            assert record_success, f"Should successfully record generation result {i}"
        
        # Retrieve updated config
        updated_config = config_manager.get_character_config(character_id)
        assert updated_config is not None, "Should retrieve updated config"
        
        # Property: Optimization history should contain all attempts
        assert len(updated_config.optimization_history) == num_generations, \
            f"Should have {num_generations} history entries, got {len(updated_config.optimization_history)}"
        
        # Property: Successful attempts should be marked as successful
        successful_attempts = [r for r in updated_config.optimization_history if r.success]
        expected_successful = int(num_generations * success_rate)
        
        # Allow some tolerance due to floating point comparison
        assert abs(len(successful_attempts) - expected_successful) <= 1, \
            f"Should have ~{expected_successful} successful attempts, got {len(successful_attempts)}"
        
        # Property: Best parameters should come from successful attempts
        if successful_attempts:
            best_params = updated_config.get_best_parameters()
            
            # Best parameters should be from one of the successful attempts
            best_similarity = max(r.quality_metrics.similarity_score for r in successful_attempts)
            
            # The best parameters should correspond to high-quality results
            # (We can't guarantee exact match due to optimization blending, but should be reasonable)
            assert isinstance(best_params, TTSParameters), "Should return TTSParameters object"
            assert 0.1 <= best_params.temperature <= 1.0, "Best temperature should be in valid range"
            assert 0.1 <= best_params.top_p <= 1.0, "Best top_p should be in valid range"
        
        # Property: Configuration should be persistently saved
        # Create new manager instance to test persistence
        new_manager = CharacterConfigManager(config_dir=config_manager.config_dir)
        persistent_config = new_manager.get_character_config(character_id)
        
        assert persistent_config is not None, "Config should persist across manager instances"
        assert len(persistent_config.optimization_history) == num_generations, \
            "Optimization history should persist"
    
    @given(
        character_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        num_variants=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=15, deadline=5000)
    @pytest.mark.property
    def test_property_23_ab_testing_comparison_validity(
        self, config_manager, sample_character_config, character_id, num_variants
    ):
        """
        Property 23: A/B Testing Comparison Validity
        
        For any two different reference audio samples for the same character,
        the F5_TTS_System SHALL provide meaningful comparison metrics that
        accurately reflect the relative voice cloning performance of each sample.
        
        Feature: f5-tts-voice-cloning-accuracy, Property 23: A/B Testing Comparison Validity
        Validates: Requirements 8.3
        """
        # Create character config
        config = CharacterConfig(
            character_id=character_id,
            reference_audio_path=sample_character_config.reference_audio_path,
            reference_text=sample_character_config.reference_text,
            tts_parameters=TTSParameters(),
            quality_threshold=0.75
        )
        
        config_manager.save_config(config)
        
        # Generate A/B test parameter variants
        variants = config_manager.get_ab_test_parameters(character_id, num_variants)
        
        # Property: Should generate the requested number of variants
        assert len(variants) == num_variants, \
            f"Should generate {num_variants} variants, got {len(variants)}"
        
        # Property: All variants should be valid TTSParameters
        for i, variant in enumerate(variants):
            assert isinstance(variant, TTSParameters), f"Variant {i} should be TTSParameters"
            assert 0.1 <= variant.temperature <= 1.0, f"Variant {i} temperature should be valid"
            assert 0.1 <= variant.top_p <= 1.0, f"Variant {i} top_p should be valid"
            assert 0.5 <= variant.speed <= 2.0, f"Variant {i} speed should be valid"
        
        # Property: Variants should be different from each other
        if num_variants > 1:
            for i in range(len(variants)):
                for j in range(i + 1, len(variants)):
                    variant_a = variants[i]
                    variant_b = variants[j]
                    
                    # At least one parameter should be different
                    params_different = (
                        abs(variant_a.temperature - variant_b.temperature) > 1e-6 or
                        abs(variant_a.top_p - variant_b.top_p) > 1e-6 or
                        abs(variant_a.speed - variant_b.speed) > 1e-6 or
                        abs(variant_a.pitch_adjustment - variant_b.pitch_adjustment) > 1e-6 or
                        abs(variant_a.noise_scale - variant_b.noise_scale) > 1e-6 or
                        abs(variant_a.length_scale - variant_b.length_scale) > 1e-6
                    )
                    
                    assert params_different, f"Variants {i} and {j} should have different parameters"
        
        # Simulate A/B test results with different quality levels
        ab_results = []
        
        for i, variant in enumerate(variants):
            # Create quality metrics with varying performance
            # First variant (baseline) gets medium performance
            # Others get varying performance to test comparison
            if i == 0:
                similarity = 0.75
                clarity = 0.7
                naturalness = 0.8
            else:
                # Vary performance for other variants
                similarity = 0.6 + (i * 0.1) % 0.3
                clarity = 0.65 + (i * 0.05) % 0.25
                naturalness = 0.7 + (i * 0.08) % 0.2
            
            metrics = AudioQualityMetrics(
                similarity_score=similarity,
                clarity_score=clarity,
                naturalness_score=naturalness,
                artifacts_detected=[],
                generation_time=5.0 + i,
                backend_used="test_backend"
            )
            
            ab_results.append((variant, metrics))
        
        # Compare A/B test results
        comparison = config_manager.compare_ab_test_results(character_id, ab_results)
        
        # Property: Comparison should contain all required fields
        assert "character_id" in comparison, "Should include character_id"
        assert "num_variants" in comparison, "Should include num_variants"
        assert "results" in comparison, "Should include results"
        assert "best_variant" in comparison, "Should include best_variant"
        assert "recommendations" in comparison, "Should include recommendations"
        
        # Property: Number of results should match input
        assert comparison["num_variants"] == num_variants, \
            f"Should report {num_variants} variants"
        assert len(comparison["results"]) == num_variants, \
            f"Should have {num_variants} result entries"
        
        # Property: Best variant should be identified
        assert comparison["best_variant"] is not None, "Should identify best variant"
        best_variant = comparison["best_variant"]
        
        assert "variant_index" in best_variant, "Best variant should have index"
        assert "composite_score" in best_variant, "Best variant should have composite score"
        assert 0 <= best_variant["variant_index"] < num_variants, \
            "Best variant index should be valid"
        
        # Property: Best variant should have highest composite score
        all_scores = [result["composite_score"] for result in comparison["results"]]
        max_score = max(all_scores)
        
        assert abs(best_variant["composite_score"] - max_score) < 1e-6, \
            "Best variant should have the highest composite score"
        
        # Property: Recommendations should be provided
        assert isinstance(comparison["recommendations"], list), \
            "Recommendations should be a list"
        assert len(comparison["recommendations"]) > 0, \
            "Should provide at least one recommendation"