"""
Quality validation component for the enhanced F5-TTS system.

Handles voice similarity scoring, artifact detection, and quality validation.
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
import librosa
import soundfile as sf
from scipy import signal
import torch

from .interfaces import QualityValidatorInterface
from .models import ValidationResult, AudioArtifact, AudioQualityMetrics

logger = logging.getLogger(__name__)


class QualityValidator(QualityValidatorInterface):
    """
    Quality validation component that measures voice similarity and detects
    audio artifacts to ensure high-quality voice clones.
    """
    
    def __init__(self, 
                 similarity_threshold: float = 0.75,
                 artifact_threshold: float = 0.1,
                 device: str = "auto"):
        """
        Initialize the quality validator.
        
        Args:
            similarity_threshold: Minimum acceptable similarity score
            artifact_threshold: Maximum acceptable artifact level
            device: Device for model inference ("cpu", "cuda", or "auto")
        """
        self.similarity_threshold = similarity_threshold
        self.artifact_threshold = artifact_threshold
        
        # Set device
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        # Initialize speaker verification model (lazy loading)
        self._speaker_model = None
        self._speaker_classifier = None
    
    def _load_speaker_verification_model(self):
        """Lazy load the speaker verification model."""
        if self._speaker_model is None:
            try:
                import speechbrain as sb
                from speechbrain.pretrained import SpeakerRecognition
                
                # Load pre-trained speaker verification model
                self._speaker_model = SpeakerRecognition.from_hparams(
                    source="speechbrain/spkrec-ecapa-voxceleb",
                    savedir="pretrained_models/spkrec-ecapa-voxceleb",
                    run_opts={"device": self.device}
                )
                logger.info(f"Loaded speaker verification model on {self.device}")
                
            except ImportError:
                logger.warning("SpeechBrain not available, using fallback similarity calculation")
                self._speaker_model = "fallback"
            except Exception as e:
                logger.error(f"Error loading speaker verification model: {e}")
                self._speaker_model = "fallback"
    
    def calculate_similarity_score(self, generated_audio: Path, reference_audio: Path) -> float:
        """
        Calculate voice similarity score using speaker verification.
        
        Args:
            generated_audio: Path to generated audio file
            reference_audio: Path to reference audio file
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            self._load_speaker_verification_model()
            
            if self._speaker_model == "fallback":
                return self._calculate_fallback_similarity(generated_audio, reference_audio)
            
            # Use SpeechBrain speaker verification
            score = self._speaker_model.verify_files(str(generated_audio), str(reference_audio))
            
            # Convert score to 0-1 range (SpeechBrain returns cosine similarity)
            # Cosine similarity ranges from -1 to 1, we map to 0-1
            normalized_score = (score + 1.0) / 2.0
            
            return float(np.clip(normalized_score, 0.0, 1.0))
            
        except Exception as e:
            logger.error(f"Error calculating similarity score: {e}")
            return self._calculate_fallback_similarity(generated_audio, reference_audio)
    
    def _calculate_fallback_similarity(self, generated_audio: Path, reference_audio: Path) -> float:
        """
        Fallback similarity calculation using spectral features.
        
        This is used when SpeechBrain is not available.
        """
        try:
            # Load both audio files
            gen_audio, gen_sr = librosa.load(str(generated_audio), sr=22050)
            ref_audio, ref_sr = librosa.load(str(reference_audio), sr=22050)
            
            # Extract MFCC features
            gen_mfcc = librosa.feature.mfcc(y=gen_audio, sr=gen_sr, n_mfcc=13)
            ref_mfcc = librosa.feature.mfcc(y=ref_audio, sr=ref_sr, n_mfcc=13)
            
            # Calculate mean MFCC vectors
            gen_mean = np.mean(gen_mfcc, axis=1)
            ref_mean = np.mean(ref_mfcc, axis=1)
            
            # Calculate cosine similarity
            dot_product = np.dot(gen_mean, ref_mean)
            gen_norm = np.linalg.norm(gen_mean)
            ref_norm = np.linalg.norm(ref_mean)
            
            if gen_norm == 0 or ref_norm == 0:
                return 0.0
            
            cosine_sim = dot_product / (gen_norm * ref_norm)
            
            # Convert to 0-1 range
            similarity = (cosine_sim + 1.0) / 2.0
            
            return float(np.clip(similarity, 0.0, 1.0))
            
        except Exception as e:
            logger.error(f"Error in fallback similarity calculation: {e}")
            return 0.0
    
    def detect_artifacts(self, audio_path: Path) -> List[AudioArtifact]:
        """
        Detect audio artifacts like clipping, distortion, unnatural pauses.
        
        Args:
            audio_path: Path to audio file to analyze
            
        Returns:
            List of detected artifacts
        """
        artifacts = []
        
        try:
            # Load audio
            audio_data, sample_rate = librosa.load(str(audio_path), sr=22050)
            
            # 1. Detect clipping
            clipping_artifacts = self._detect_clipping(audio_data, sample_rate)
            artifacts.extend(clipping_artifacts)
            
            # 2. Detect distortion
            distortion_artifacts = self._detect_distortion(audio_data, sample_rate)
            artifacts.extend(distortion_artifacts)
            
            # 3. Detect unnatural pauses
            pause_artifacts = self._detect_unnatural_pauses(audio_data, sample_rate)
            artifacts.extend(pause_artifacts)
            
            # 4. Detect volume inconsistencies
            volume_artifacts = self._detect_volume_inconsistencies(audio_data, sample_rate)
            artifacts.extend(volume_artifacts)
            
            # 5. Detect spectral anomalies
            spectral_artifacts = self._detect_spectral_anomalies(audio_data, sample_rate)
            artifacts.extend(spectral_artifacts)
            
        except Exception as e:
            logger.error(f"Error detecting artifacts in {audio_path}: {e}")
            artifacts.append(AudioArtifact(
                artifact_type="analysis_error",
                severity=1.0,
                timestamp=0.0,
                description=f"Error during artifact detection: {str(e)}"
            ))
        
        return artifacts
    
    def validate_quality(self, audio_path: Path, reference_audio: Path, threshold: float = 0.75) -> ValidationResult:
        """
        Comprehensive quality validation.
        
        Args:
            audio_path: Path to generated audio file
            reference_audio: Path to reference audio file
            threshold: Quality threshold for acceptance
            
        Returns:
            ValidationResult with quality assessment
        """
        try:
            # Calculate similarity score
            similarity_score = self.calculate_similarity_score(audio_path, reference_audio)
            
            # Detect artifacts
            artifacts = self.detect_artifacts(audio_path)
            
            # Calculate overall quality score
            quality_score = similarity_score
            
            # Penalize for artifacts
            artifact_penalty = sum(artifact.severity for artifact in artifacts) * 0.1
            quality_score = max(0.0, quality_score - artifact_penalty)
            
            # Determine if valid
            is_valid = (quality_score >= threshold and 
                       len([a for a in artifacts if a.severity > 0.5]) == 0)
            
            # Generate issues and recommendations
            issues = []
            recommendations = []
            
            if similarity_score < threshold:
                issues.append(f"Low voice similarity: {similarity_score:.3f} (threshold: {threshold})")
                recommendations.append("Try different TTS parameters or better reference audio")
            
            for artifact in artifacts:
                if artifact.severity > 0.3:
                    issues.append(f"{artifact.artifact_type}: {artifact.description}")
                    
                    if artifact.artifact_type == "clipping":
                        recommendations.append("Reduce audio levels to prevent clipping")
                    elif artifact.artifact_type == "distortion":
                        recommendations.append("Check TTS parameters and audio processing chain")
                    elif artifact.artifact_type == "unnatural_pause":
                        recommendations.append("Review text preprocessing and TTS timing")
            
            return ValidationResult(
                is_valid=is_valid,
                quality_score=quality_score,
                issues=issues,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error validating quality: {e}")
            return ValidationResult(
                is_valid=False,
                quality_score=0.0,
                issues=[f"Quality validation error: {str(e)}"],
                recommendations=["Check audio files and try again"]
            )
    
    def _detect_clipping(self, audio_data: np.ndarray, sample_rate: int) -> List[AudioArtifact]:
        """Detect audio clipping artifacts."""
        artifacts = []
        
        # Find samples near maximum amplitude
        clipping_threshold = 0.95
        clipped_samples = np.where(np.abs(audio_data) > clipping_threshold)[0]
        
        if len(clipped_samples) > 0:
            # Group consecutive clipped samples
            clipping_regions = []
            current_region = [clipped_samples[0]]
            
            for i in range(1, len(clipped_samples)):
                if clipped_samples[i] - clipped_samples[i-1] <= 10:  # Within 10 samples
                    current_region.append(clipped_samples[i])
                else:
                    clipping_regions.append(current_region)
                    current_region = [clipped_samples[i]]
            
            clipping_regions.append(current_region)
            
            # Create artifacts for significant clipping regions
            for region in clipping_regions:
                if len(region) > 5:  # At least 5 consecutive samples
                    timestamp = region[0] / sample_rate
                    severity = min(1.0, len(region) / 100.0)  # Severity based on length
                    
                    artifacts.append(AudioArtifact(
                        artifact_type="clipping",
                        severity=severity,
                        timestamp=timestamp,
                        description=f"Audio clipping detected for {len(region)} samples"
                    ))
        
        return artifacts
    
    def _detect_distortion(self, audio_data: np.ndarray, sample_rate: int) -> List[AudioArtifact]:
        """Detect audio distortion using harmonic analysis."""
        artifacts = []
        
        try:
            # Calculate THD (Total Harmonic Distortion) in overlapping windows
            window_size = int(0.1 * sample_rate)  # 100ms windows
            hop_size = window_size // 2
            
            for i in range(0, len(audio_data) - window_size, hop_size):
                window = audio_data[i:i + window_size]
                
                # Calculate FFT
                fft = np.fft.fft(window)
                freqs = np.fft.fftfreq(len(window), 1/sample_rate)
                magnitude = np.abs(fft)
                
                # Find fundamental frequency (peak in low frequencies)
                low_freq_mask = (freqs > 80) & (freqs < 800)
                if np.any(low_freq_mask):
                    fundamental_idx = np.argmax(magnitude[low_freq_mask])
                    fundamental_freq = freqs[low_freq_mask][fundamental_idx]
                    
                    # Calculate harmonic distortion
                    thd = self._calculate_thd(magnitude, freqs, fundamental_freq)
                    
                    if thd > 0.1:  # 10% THD threshold
                        timestamp = i / sample_rate
                        severity = min(1.0, thd)
                        
                        artifacts.append(AudioArtifact(
                            artifact_type="distortion",
                            severity=severity,
                            timestamp=timestamp,
                            description=f"High harmonic distortion: {thd*100:.1f}% THD"
                        ))
        
        except Exception as e:
            logger.warning(f"Error in distortion detection: {e}")
        
        return artifacts
    
    def _detect_unnatural_pauses(self, audio_data: np.ndarray, sample_rate: int) -> List[AudioArtifact]:
        """Detect unnatural pauses in speech."""
        artifacts = []
        
        try:
            # Calculate RMS energy in short windows
            window_size = int(0.02 * sample_rate)  # 20ms windows
            hop_size = window_size // 2
            
            rms_values = []
            timestamps = []
            
            for i in range(0, len(audio_data) - window_size, hop_size):
                window = audio_data[i:i + window_size]
                rms = np.sqrt(np.mean(window**2))
                rms_values.append(rms)
                timestamps.append(i / sample_rate)
            
            rms_values = np.array(rms_values)
            
            # Find silence regions (low RMS)
            silence_threshold = np.percentile(rms_values, 10)  # Bottom 10%
            silence_mask = rms_values < silence_threshold
            
            # Find consecutive silence regions
            silence_regions = []
            in_silence = False
            silence_start = 0
            
            for i, is_silent in enumerate(silence_mask):
                if is_silent and not in_silence:
                    silence_start = i
                    in_silence = True
                elif not is_silent and in_silence:
                    silence_regions.append((silence_start, i))
                    in_silence = False
            
            # Check for unnaturally long pauses
            for start_idx, end_idx in silence_regions:
                duration = (end_idx - start_idx) * hop_size / sample_rate
                
                if duration > 1.0:  # Pauses longer than 1 second
                    timestamp = timestamps[start_idx]
                    severity = min(1.0, duration / 3.0)  # Severity increases with duration
                    
                    artifacts.append(AudioArtifact(
                        artifact_type="unnatural_pause",
                        severity=severity,
                        timestamp=timestamp,
                        description=f"Unnaturally long pause: {duration:.1f}s"
                    ))
        
        except Exception as e:
            logger.warning(f"Error in pause detection: {e}")
        
        return artifacts
    
    def _detect_volume_inconsistencies(self, audio_data: np.ndarray, sample_rate: int) -> List[AudioArtifact]:
        """Detect sudden volume changes."""
        artifacts = []
        
        try:
            # Calculate RMS in overlapping windows
            window_size = int(0.1 * sample_rate)  # 100ms windows
            hop_size = window_size // 4
            
            rms_values = []
            for i in range(0, len(audio_data) - window_size, hop_size):
                window = audio_data[i:i + window_size]
                rms = np.sqrt(np.mean(window**2))
                rms_values.append(rms)
            
            rms_values = np.array(rms_values)
            
            # Find sudden changes in RMS
            if len(rms_values) > 1:
                rms_diff = np.abs(np.diff(rms_values))
                change_threshold = np.std(rms_values) * 3  # 3 standard deviations
                
                sudden_changes = np.where(rms_diff > change_threshold)[0]
                
                for change_idx in sudden_changes:
                    timestamp = change_idx * hop_size / sample_rate
                    severity = min(1.0, rms_diff[change_idx] / (np.mean(rms_values) + 1e-8))
                    
                    artifacts.append(AudioArtifact(
                        artifact_type="volume_inconsistency",
                        severity=severity,
                        timestamp=timestamp,
                        description=f"Sudden volume change detected"
                    ))
        
        except Exception as e:
            logger.warning(f"Error in volume consistency detection: {e}")
        
        return artifacts
    
    def _detect_spectral_anomalies(self, audio_data: np.ndarray, sample_rate: int) -> List[AudioArtifact]:
        """Detect spectral anomalies that might indicate processing artifacts."""
        artifacts = []
        
        try:
            # Calculate spectrogram
            stft = librosa.stft(audio_data, hop_length=512)
            magnitude = np.abs(stft)
            
            # Look for unusual spectral patterns
            # 1. Check for spectral holes (missing frequency bands)
            freq_energy = np.mean(magnitude, axis=1)
            
            # Find frequency bins with unusually low energy
            energy_threshold = np.percentile(freq_energy, 5)
            low_energy_bins = np.where(freq_energy < energy_threshold)[0]
            
            if len(low_energy_bins) > len(freq_energy) * 0.1:  # More than 10% of bins
                artifacts.append(AudioArtifact(
                    artifact_type="spectral_hole",
                    severity=0.5,
                    timestamp=0.0,
                    description="Spectral holes detected - missing frequency content"
                ))
            
            # 2. Check for spectral peaks (aliasing or processing artifacts)
            peak_threshold = np.percentile(freq_energy, 95)
            peak_bins = np.where(freq_energy > peak_threshold)[0]
            
            # Look for isolated peaks that might be artifacts
            for peak_bin in peak_bins:
                if peak_bin > 0 and peak_bin < len(freq_energy) - 1:
                    neighbors = freq_energy[peak_bin-1:peak_bin+2]
                    if freq_energy[peak_bin] > 3 * np.mean(neighbors):
                        artifacts.append(AudioArtifact(
                            artifact_type="spectral_peak",
                            severity=0.3,
                            timestamp=0.0,
                            description=f"Isolated spectral peak at {peak_bin * sample_rate / (2 * len(freq_energy)):.0f}Hz"
                        ))
        
        except Exception as e:
            logger.warning(f"Error in spectral anomaly detection: {e}")
        
        return artifacts
    
    def _calculate_thd(self, magnitude: np.ndarray, freqs: np.ndarray, fundamental_freq: float) -> float:
        """Calculate Total Harmonic Distortion."""
        try:
            # Find fundamental and harmonics
            freq_resolution = freqs[1] - freqs[0]
            tolerance = freq_resolution * 2
            
            # Find fundamental peak
            fundamental_idx = np.argmin(np.abs(freqs - fundamental_freq))
            fundamental_power = magnitude[fundamental_idx]**2
            
            # Find harmonic peaks (2f, 3f, 4f, 5f)
            harmonic_power = 0
            for harmonic in range(2, 6):
                harmonic_freq = fundamental_freq * harmonic
                if harmonic_freq < freqs[-1]:
                    harmonic_idx = np.argmin(np.abs(freqs - harmonic_freq))
                    harmonic_power += magnitude[harmonic_idx]**2
            
            # Calculate THD
            if fundamental_power > 0:
                thd = np.sqrt(harmonic_power / fundamental_power)
            else:
                thd = 0
            
            return float(thd)
            
        except Exception:
            return 0.0