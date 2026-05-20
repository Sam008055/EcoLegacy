"""
Character configuration management for the enhanced F5-TTS system.

Handles character-specific TTS parameters, optimization, and A/B testing.
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import time
import statistics

from .interfaces import CharacterConfigManagerInterface
from .models import CharacterConfig, TTSParameters, AudioQualityMetrics, ParameterResult

logger = logging.getLogger(__name__)


class CharacterConfigManager(CharacterConfigManagerInterface):
    """
    Character configuration manager that handles character-specific TTS parameters,
    optimization based on performance history, and A/B testing support.
    """
    
    def __init__(self, config_dir: Path = None):
        """
        Initialize the character configuration manager.
        
        Args:
            config_dir: Directory to store character configurations
        """
        if config_dir is None:
            config_dir = Path("enhanced_tts_configs")
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Cache for loaded configurations
        self._config_cache: Dict[str, CharacterConfig] = {}
        
        # Default parameters for new characters
        self.default_parameters = TTSParameters()
    
    def get_character_config(self, character_id: str) -> Optional[CharacterConfig]:
        """
        Get configuration for a character.
        
        Args:
            character_id: Character identifier
            
        Returns:
            CharacterConfig if found, None otherwise
        """
        # Check cache first
        if character_id in self._config_cache:
            return self._config_cache[character_id]
        
        # Try to load from file
        config_file = self.config_dir / f"{character_id}.json"
        
        if config_file.exists():
            try:
                config = self._load_config_from_file(config_file)
                self._config_cache[character_id] = config
                return config
            except Exception as e:
                logger.error(f"Error loading config for {character_id}: {e}")
                return None
        
        # Try to create from legacy character_tts_config.py
        legacy_config = self._load_legacy_config(character_id)
        if legacy_config:
            # Save as new format and cache
            self.save_config(legacy_config)
            self._config_cache[character_id] = legacy_config
            return legacy_config
        
        return None
    
    def update_parameters(self, character_id: str, params: TTSParameters) -> bool:
        """
        Update TTS parameters for a character.
        
        Args:
            character_id: Character identifier
            params: New TTS parameters
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config = self.get_character_config(character_id)
            
            if config is None:
                logger.warning(f"Character {character_id} not found, cannot update parameters")
                return False
            
            # Update parameters
            config.tts_parameters = params
            
            # Save updated configuration
            return self.save_config(config)
            
        except Exception as e:
            logger.error(f"Error updating parameters for {character_id}: {e}")
            return False
    
    def optimize_parameters(self, character_id: str, performance_data: List[AudioQualityMetrics]) -> TTSParameters:
        """
        Optimize parameters based on performance history.
        
        Args:
            character_id: Character identifier
            performance_data: List of quality metrics from recent generations
            
        Returns:
            Optimized TTS parameters
        """
        config = self.get_character_config(character_id)
        
        if config is None:
            logger.warning(f"Character {character_id} not found, returning default parameters")
            return self.default_parameters
        
        if not performance_data:
            logger.info(f"No performance data for {character_id}, returning current parameters")
            return config.tts_parameters
        
        try:
            # Analyze performance trends
            avg_similarity = statistics.mean(m.similarity_score for m in performance_data)
            avg_clarity = statistics.mean(m.clarity_score for m in performance_data)
            avg_naturalness = statistics.mean(m.naturalness_score for m in performance_data)
            
            # Get current parameters as starting point
            optimized_params = TTSParameters(
                temperature=config.tts_parameters.temperature,
                top_p=config.tts_parameters.top_p,
                speed=config.tts_parameters.speed,
                pitch_adjustment=config.tts_parameters.pitch_adjustment,
                noise_scale=config.tts_parameters.noise_scale,
                length_scale=config.tts_parameters.length_scale
            )
            
            # Optimization heuristics based on performance
            if avg_similarity < 0.7:
                # Low similarity - try adjusting temperature and top_p
                if optimized_params.temperature > 0.5:
                    optimized_params.temperature *= 0.9  # Reduce randomness
                if optimized_params.top_p > 0.8:
                    optimized_params.top_p *= 0.95  # More focused sampling
            
            if avg_clarity < 0.7:
                # Low clarity - adjust noise scale and speed
                if optimized_params.noise_scale > 0.5:
                    optimized_params.noise_scale *= 0.9  # Reduce noise
                if optimized_params.speed > 1.1:
                    optimized_params.speed *= 0.95  # Slightly slower for clarity
            
            if avg_naturalness < 0.7:
                # Low naturalness - adjust length scale and pitch
                if abs(optimized_params.pitch_adjustment) > 0.1:
                    optimized_params.pitch_adjustment *= 0.8  # Reduce pitch adjustment
                if optimized_params.length_scale != 1.0:
                    # Move length scale closer to 1.0
                    optimized_params.length_scale = (optimized_params.length_scale + 1.0) / 2
            
            # Look at optimization history for additional insights
            if config.optimization_history:
                best_results = [r for r in config.optimization_history if r.success and 
                              r.quality_metrics.similarity_score > avg_similarity]
                
                if best_results:
                    # Find the best performing parameters
                    best_result = max(best_results, 
                                    key=lambda r: r.quality_metrics.similarity_score)
                    
                    # Blend with best historical parameters
                    blend_factor = 0.3
                    optimized_params.temperature = (
                        (1 - blend_factor) * optimized_params.temperature +
                        blend_factor * best_result.parameters.temperature
                    )
                    optimized_params.top_p = (
                        (1 - blend_factor) * optimized_params.top_p +
                        blend_factor * best_result.parameters.top_p
                    )
            
            # Ensure parameters stay within valid ranges
            optimized_params.temperature = max(0.1, min(1.0, optimized_params.temperature))
            optimized_params.top_p = max(0.1, min(1.0, optimized_params.top_p))
            optimized_params.speed = max(0.5, min(2.0, optimized_params.speed))
            optimized_params.pitch_adjustment = max(-0.5, min(0.5, optimized_params.pitch_adjustment))
            optimized_params.noise_scale = max(0.1, min(1.0, optimized_params.noise_scale))
            optimized_params.length_scale = max(0.5, min(2.0, optimized_params.length_scale))
            
            logger.info(f"Optimized parameters for {character_id} based on {len(performance_data)} samples")
            return optimized_params
            
        except Exception as e:
            logger.error(f"Error optimizing parameters for {character_id}: {e}")
            return config.tts_parameters
    
    def save_config(self, config: CharacterConfig) -> bool:
        """
        Save character configuration to file.
        
        Args:
            config: Character configuration to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config_file = self.config_dir / f"{config.character_id}.json"
            
            # Convert to dictionary for JSON serialization
            config_dict = {
                "character_id": config.character_id,
                "reference_audio_path": str(config.reference_audio_path),
                "reference_text": config.reference_text,
                "tts_parameters": config.tts_parameters.to_dict(),
                "quality_threshold": config.quality_threshold,
                "optimization_history": [
                    {
                        "parameters": result.parameters.to_dict(),
                        "quality_metrics": {
                            "similarity_score": result.quality_metrics.similarity_score,
                            "clarity_score": result.quality_metrics.clarity_score,
                            "naturalness_score": result.quality_metrics.naturalness_score,
                            "artifacts_detected": result.quality_metrics.artifacts_detected,
                            "generation_time": result.quality_metrics.generation_time,
                            "backend_used": result.quality_metrics.backend_used,
                            "timestamp": result.quality_metrics.timestamp
                        },
                        "success": result.success,
                        "timestamp": result.timestamp
                    }
                    for result in config.optimization_history
                ]
            }
            
            # Write to file with pretty formatting
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            # Update cache
            self._config_cache[config.character_id] = config
            
            logger.info(f"Saved configuration for {config.character_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving config for {config.character_id}: {e}")
            return False
    
    def record_generation_result(self, character_id: str, parameters: TTSParameters, 
                               quality_metrics: AudioQualityMetrics, success: bool) -> bool:
        """
        Record the result of a generation attempt for optimization history.
        
        Args:
            character_id: Character identifier
            parameters: Parameters used for generation
            quality_metrics: Quality metrics from the generation
            success: Whether the generation was successful
            
        Returns:
            True if recorded successfully, False otherwise
        """
        try:
            config = self.get_character_config(character_id)
            
            if config is None:
                logger.warning(f"Character {character_id} not found, cannot record result")
                return False
            
            # Create parameter result
            result = ParameterResult(
                parameters=parameters,
                quality_metrics=quality_metrics,
                success=success,
                timestamp=time.time()
            )
            
            # Add to optimization history
            config.optimization_history.append(result)
            
            # Keep only recent history (last 100 results)
            if len(config.optimization_history) > 100:
                config.optimization_history = config.optimization_history[-100:]
            
            # Save updated configuration
            return self.save_config(config)
            
        except Exception as e:
            logger.error(f"Error recording generation result for {character_id}: {e}")
            return False
    
    def get_ab_test_parameters(self, character_id: str, num_variants: int = 2) -> List[TTSParameters]:
        """
        Generate parameter variants for A/B testing.
        
        Args:
            character_id: Character identifier
            num_variants: Number of parameter variants to generate
            
        Returns:
            List of parameter variants for testing
        """
        config = self.get_character_config(character_id)
        
        if config is None:
            logger.warning(f"Character {character_id} not found, returning default variants")
            base_params = self.default_parameters
        else:
            base_params = config.get_best_parameters()
        
        variants = [base_params]  # Include current best as baseline
        
        # Generate variants by adjusting different parameters
        for i in range(num_variants - 1):
            variant = TTSParameters(
                temperature=base_params.temperature,
                top_p=base_params.top_p,
                speed=base_params.speed,
                pitch_adjustment=base_params.pitch_adjustment,
                noise_scale=base_params.noise_scale,
                length_scale=base_params.length_scale
            )
            
            # Apply different variations for each variant
            if i == 0:
                # Variant 1: Adjust temperature and top_p
                variant.temperature = max(0.1, min(1.0, base_params.temperature * 1.1))
                variant.top_p = max(0.1, min(1.0, base_params.top_p * 0.95))
            elif i == 1:
                # Variant 2: Adjust speed and noise
                variant.speed = max(0.5, min(2.0, base_params.speed * 0.95))
                variant.noise_scale = max(0.1, min(1.0, base_params.noise_scale * 0.9))
            elif i == 2:
                # Variant 3: Adjust pitch and length
                variant.pitch_adjustment = max(-0.5, min(0.5, base_params.pitch_adjustment + 0.05))
                variant.length_scale = max(0.5, min(2.0, base_params.length_scale * 1.05))
            
            variants.append(variant)
        
        return variants
    
    def compare_ab_test_results(self, character_id: str, 
                              results: List[tuple[TTSParameters, AudioQualityMetrics]]) -> Dict[str, Any]:
        """
        Compare A/B test results and provide recommendations.
        
        Args:
            character_id: Character identifier
            results: List of (parameters, quality_metrics) tuples
            
        Returns:
            Dictionary with comparison results and recommendations
        """
        if not results:
            return {"error": "No results to compare"}
        
        try:
            # Analyze results
            comparison = {
                "character_id": character_id,
                "num_variants": len(results),
                "results": [],
                "best_variant": None,
                "recommendations": []
            }
            
            best_score = 0
            best_idx = 0
            
            for i, (params, metrics) in enumerate(results):
                # Calculate composite score
                composite_score = (
                    0.4 * metrics.similarity_score +
                    0.3 * metrics.clarity_score +
                    0.3 * metrics.naturalness_score
                )
                
                result_info = {
                    "variant_index": i,
                    "parameters": params.to_dict(),
                    "similarity_score": metrics.similarity_score,
                    "clarity_score": metrics.clarity_score,
                    "naturalness_score": metrics.naturalness_score,
                    "composite_score": composite_score,
                    "artifacts_count": len(metrics.artifacts_detected),
                    "generation_time": metrics.generation_time
                }
                
                comparison["results"].append(result_info)
                
                if composite_score > best_score:
                    best_score = composite_score
                    best_idx = i
            
            # Identify best variant
            comparison["best_variant"] = comparison["results"][best_idx]
            
            # Generate recommendations
            best_params, best_metrics = results[best_idx]
            
            if best_score > 0.8:
                comparison["recommendations"].append(
                    f"Variant {best_idx} shows excellent performance (score: {best_score:.3f}). "
                    "Consider adopting these parameters."
                )
            elif best_score > 0.7:
                comparison["recommendations"].append(
                    f"Variant {best_idx} shows good performance (score: {best_score:.3f}). "
                    "Consider further optimization based on these parameters."
                )
            else:
                comparison["recommendations"].append(
                    "All variants show room for improvement. "
                    "Consider trying more diverse parameter ranges."
                )
            
            # Specific parameter recommendations
            if best_metrics.similarity_score < 0.7:
                comparison["recommendations"].append(
                    "Low similarity scores across variants suggest reviewing reference audio quality."
                )
            
            if best_metrics.generation_time > 20:
                comparison["recommendations"].append(
                    "High generation times suggest optimizing for performance."
                )
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing A/B test results: {e}")
            return {"error": str(e)}
    
    def _load_config_from_file(self, config_file: Path) -> CharacterConfig:
        """Load character configuration from JSON file."""
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert back to objects
        tts_params = TTSParameters.from_dict(data["tts_parameters"])
        
        optimization_history = []
        for result_data in data.get("optimization_history", []):
            params = TTSParameters.from_dict(result_data["parameters"])
            
            from .models import AudioQualityMetrics
            metrics = AudioQualityMetrics(
                similarity_score=result_data["quality_metrics"]["similarity_score"],
                clarity_score=result_data["quality_metrics"]["clarity_score"],
                naturalness_score=result_data["quality_metrics"]["naturalness_score"],
                artifacts_detected=result_data["quality_metrics"]["artifacts_detected"],
                generation_time=result_data["quality_metrics"]["generation_time"],
                backend_used=result_data["quality_metrics"]["backend_used"],
                timestamp=result_data["quality_metrics"]["timestamp"]
            )
            
            result = ParameterResult(
                parameters=params,
                quality_metrics=metrics,
                success=result_data["success"],
                timestamp=result_data["timestamp"]
            )
            optimization_history.append(result)
        
        return CharacterConfig(
            character_id=data["character_id"],
            reference_audio_path=Path(data["reference_audio_path"]),
            reference_text=data["reference_text"],
            tts_parameters=tts_params,
            quality_threshold=data.get("quality_threshold", 0.75),
            optimization_history=optimization_history
        )
    
    def _load_legacy_config(self, character_id: str) -> Optional[CharacterConfig]:
        """Load configuration from legacy character_tts_config.py format."""
        try:
            from character_tts_config import get_character_tts
            
            legacy_config = get_character_tts(character_id)
            if legacy_config:
                return CharacterConfig(
                    character_id=character_id,
                    reference_audio_path=legacy_config["reference_audio"],
                    reference_text=legacy_config["reference_text"],
                    tts_parameters=self.default_parameters,
                    quality_threshold=0.75
                )
        except ImportError:
            logger.warning("Legacy character_tts_config.py not found")
        except Exception as e:
            logger.error(f"Error loading legacy config for {character_id}: {e}")
        
        return None