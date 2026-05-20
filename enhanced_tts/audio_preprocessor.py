"""
Audio preprocessing component for the enhanced F5-TTS system.

Handles audio validation, normalization, format conversion, and optimal segment extraction.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import librosa
import soundfile as sf
from scipy import signal

from .interfaces import AudioPreprocessorInterface
from .models import ValidationResult, AudioFormat

logger = logging.getLogger(__name__)


class AudioPreprocessor(AudioPreprocessorInterface):
    """
    Audio preprocessing component that validates, normalizes, and optimizes
    reference audio files for optimal voice cloning performance.
    """
    
    def __init__(self, 
                 min_sample_rate: int = 16000,
                 target_sample_rate: int = 22050,
                 min_duration: float = 1.0,
                 max_duration: float = 60.0,
                 noise_threshold: float = 0.1):
        """
        Initialize the audio preprocessor.
        
        Args:
            min_sample_rate: Minimum acceptable sample rate (Hz)
            target_sample_rate: Target sample rate for processing (Hz)
            min_duration: Minimum audio duration (seconds)
            max_duration: Maximum audio duration (seconds)
            noise_threshold: Maximum acceptable noise level (0.0-1.0)
        """
        self.min_sample_rate = min_sample_rate
        self.target_sample_rate = target_sample_rate
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.noise_threshold = noise_threshold
    
    def validate_audio(self, audio_path: Path) -> ValidationResult:
        """
        Validate audio file quality and format.
        
        Checks sample rate, duration, noise levels, and speech clarity.
        """
        if not audio_path.exists():
            return ValidationResult(
                is_valid=False,
                quality_score=0.0,
                issues=[f"Audio file not found: {audio_path}"],
                recommendations=["Ensure the audio file exists and is accessible"]
            )
        
        try:
            # Load audio file
            audio_data, sample_rate = librosa.load(str(audio_path), sr=None)
            duration = len(audio_data) / sample_rate
            
            issues = []
            recommendations = []
            quality_score = 1.0
            
            # Check sample rate
            if sample_rate < self.min_sample_rate:
                issues.append(f"Sample rate too low: {sample_rate}Hz (minimum: {self.min_sample_rate}Hz)")
                recommendations.append(f"Resample audio to at least {self.min_sample_rate}Hz")
                quality_score *= 0.7
            
            # Check duration
            if duration < self.min_duration:
                issues.append(f"Audio too short: {duration:.1f}s (minimum: {self.min_duration}s)")
                recommendations.append(f"Use audio at least {self.min_duration} seconds long")
                quality_score *= 0.5
            elif duration > self.max_duration:
                issues.append(f"Audio too long: {duration:.1f}s (maximum: {self.max_duration}s)")
                recommendations.append("Consider extracting a shorter segment")
                quality_score *= 0.9
            
            # Check for clipping
            clipping_ratio = np.sum(np.abs(audio_data) > 0.95) / len(audio_data)
            if clipping_ratio > 0.01:  # More than 1% clipped samples
                issues.append(f"Audio clipping detected: {clipping_ratio*100:.1f}% of samples")
                recommendations.append("Use audio with lower input levels to avoid clipping")
                quality_score *= 0.8
            
            # Estimate noise level
            noise_level = self._estimate_noise_level(audio_data)
            if noise_level > self.noise_threshold:
                issues.append(f"High noise level detected: {noise_level:.2f}")
                recommendations.append("Use cleaner audio with less background noise")
                quality_score *= 0.6
            
            # Check for silence
            silence_ratio = self._calculate_silence_ratio(audio_data)
            if silence_ratio > 0.5:  # More than 50% silence
                issues.append(f"Too much silence: {silence_ratio*100:.1f}% of audio")
                recommendations.append("Trim silence or use audio with more speech content")
                quality_score *= 0.7
            
            # Speech clarity estimation
            clarity_score = self._estimate_speech_clarity(audio_data, sample_rate)
            if clarity_score < 0.5:
                issues.append(f"Low speech clarity: {clarity_score:.2f}")
                recommendations.append("Use clearer speech audio with better articulation")
                quality_score *= clarity_score
            
            is_valid = len(issues) == 0 or quality_score >= 0.6
            
            return ValidationResult(
                is_valid=is_valid,
                quality_score=quality_score,
                issues=issues,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error validating audio {audio_path}: {e}")
            return ValidationResult(
                is_valid=False,
                quality_score=0.0,
                issues=[f"Error reading audio file: {str(e)}"],
                recommendations=["Check audio file format and integrity"]
            )
    
    def normalize_audio(self, audio_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Normalize audio levels and remove silence.
        
        Args:
            audio_path: Input audio file path
            output_path: Output path (if None, creates normalized version)
            
        Returns:
            Path to normalized audio file
        """
        if output_path is None:
            output_path = audio_path.parent / f"{audio_path.stem}_normalized{audio_path.suffix}"
        
        try:
            # Load audio
            audio_data, sample_rate = librosa.load(str(audio_path), sr=self.target_sample_rate)
            
            # Remove silence from beginning and end
            audio_data = self._trim_silence(audio_data)
            
            # Normalize volume to -3dB peak
            peak_level = np.max(np.abs(audio_data))
            if peak_level > 0:
                target_peak = 0.707  # -3dB
                audio_data = audio_data * (target_peak / peak_level)
            
            # Apply gentle high-pass filter to remove low-frequency noise
            audio_data = self._apply_highpass_filter(audio_data, sample_rate, cutoff=80)
            
            # Save normalized audio
            sf.write(str(output_path), audio_data, sample_rate)
            
            logger.info(f"Normalized audio saved to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error normalizing audio {audio_path}: {e}")
            raise
    
    def extract_optimal_segment(self, audio_path: Path, target_duration: int = 20) -> Path:
        """
        Extract the clearest segment from longer audio.
        
        Args:
            audio_path: Input audio file path
            target_duration: Target segment duration in seconds
            
        Returns:
            Path to extracted segment
        """
        try:
            # Load audio
            audio_data, sample_rate = librosa.load(str(audio_path), sr=self.target_sample_rate)
            total_duration = len(audio_data) / sample_rate
            
            if total_duration <= target_duration:
                # Audio is already short enough, just normalize and return
                return self.normalize_audio(audio_path)
            
            # Find the best segment
            segment_samples = int(target_duration * sample_rate)
            best_start = 0
            best_score = 0
            
            # Analyze overlapping windows to find the clearest segment
            hop_size = int(2 * sample_rate)  # 2-second hops
            
            for start_sample in range(0, len(audio_data) - segment_samples, hop_size):
                segment = audio_data[start_sample:start_sample + segment_samples]
                
                # Score this segment based on clarity metrics
                score = self._score_audio_segment(segment, sample_rate)
                
                if score > best_score:
                    best_score = score
                    best_start = start_sample
            
            # Extract the best segment
            best_segment = audio_data[best_start:best_start + segment_samples]
            
            # Save extracted segment
            output_path = audio_path.parent / f"{audio_path.stem}_segment{audio_path.suffix}"
            sf.write(str(output_path), best_segment, sample_rate)
            
            logger.info(f"Extracted optimal segment ({target_duration}s) from {audio_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error extracting segment from {audio_path}: {e}")
            raise
    
    def convert_format(self, audio_path: Path, target_format: str = "wav") -> Path:
        """
        Convert audio to target format.
        
        Args:
            audio_path: Input audio file path
            target_format: Target format ("wav", "mp3", "flac")
            
        Returns:
            Path to converted audio file
        """
        target_format = target_format.lower()
        if target_format not in ["wav", "mp3", "flac"]:
            raise ValueError(f"Unsupported target format: {target_format}")
        
        output_path = audio_path.parent / f"{audio_path.stem}.{target_format}"
        
        # If already in target format, just return the path
        if audio_path.suffix.lower() == f".{target_format}":
            return audio_path
        
        try:
            # Load and resave in target format
            audio_data, sample_rate = librosa.load(str(audio_path), sr=self.target_sample_rate)
            
            if target_format == "wav":
                sf.write(str(output_path), audio_data, sample_rate, format='WAV')
            elif target_format == "flac":
                sf.write(str(output_path), audio_data, sample_rate, format='FLAC')
            elif target_format == "mp3":
                # For MP3, we need to use a different approach since soundfile doesn't support MP3 writing
                # Convert to WAV first, then use external tool or library
                wav_path = audio_path.parent / f"{audio_path.stem}_temp.wav"
                sf.write(str(wav_path), audio_data, sample_rate, format='WAV')
                
                # For now, return WAV format as MP3 encoding requires additional dependencies
                logger.warning("MP3 encoding not implemented, returning WAV format")
                return wav_path
            
            logger.info(f"Converted {audio_path} to {target_format} format")
            return output_path
            
        except Exception as e:
            logger.error(f"Error converting audio format: {e}")
            raise
    
    def _estimate_noise_level(self, audio_data: np.ndarray) -> float:
        """Estimate the noise level in audio data."""
        # Use the bottom 10% of energy frames as noise estimate
        frame_length = 2048
        hop_length = 512
        
        # Calculate RMS energy for each frame
        frames = librosa.util.frame(audio_data, frame_length=frame_length, 
                                  hop_length=hop_length, axis=0)
        rms_energy = np.sqrt(np.mean(frames**2, axis=0))
        
        # Noise level is estimated as the 10th percentile of RMS energy
        noise_level = np.percentile(rms_energy, 10)
        return float(noise_level)
    
    def _calculate_silence_ratio(self, audio_data: np.ndarray, threshold: float = 0.01) -> float:
        """Calculate the ratio of silence in audio data."""
        # Consider samples below threshold as silence
        silence_samples = np.sum(np.abs(audio_data) < threshold)
        return silence_samples / len(audio_data)
    
    def _estimate_speech_clarity(self, audio_data: np.ndarray, sample_rate: int) -> float:
        """Estimate speech clarity using spectral features."""
        # Calculate spectral centroid and bandwidth
        spectral_centroids = librosa.feature.spectral_centroid(y=audio_data, sr=sample_rate)[0]
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=audio_data, sr=sample_rate)[0]
        
        # Higher spectral centroid and lower bandwidth generally indicate clearer speech
        avg_centroid = np.mean(spectral_centroids)
        avg_bandwidth = np.mean(spectral_bandwidth)
        
        # Normalize to 0-1 range (these are rough heuristics)
        centroid_score = min(avg_centroid / 3000, 1.0)  # Normalize around 3kHz
        bandwidth_score = max(0, 1.0 - avg_bandwidth / 4000)  # Lower bandwidth is better
        
        clarity_score = (centroid_score + bandwidth_score) / 2
        return float(clarity_score)
    
    def _trim_silence(self, audio_data: np.ndarray, threshold: float = 0.01) -> np.ndarray:
        """Trim silence from the beginning and end of audio."""
        # Find first and last non-silent samples
        non_silent = np.where(np.abs(audio_data) > threshold)[0]
        
        if len(non_silent) == 0:
            return audio_data  # All silence, return as-is
        
        start_idx = non_silent[0]
        end_idx = non_silent[-1] + 1
        
        return audio_data[start_idx:end_idx]
    
    def _apply_highpass_filter(self, audio_data: np.ndarray, sample_rate: int, cutoff: float = 80) -> np.ndarray:
        """Apply a gentle high-pass filter to remove low-frequency noise."""
        nyquist = sample_rate / 2
        normalized_cutoff = cutoff / nyquist
        
        # Design a 2nd order Butterworth high-pass filter
        b, a = signal.butter(2, normalized_cutoff, btype='high')
        
        # Apply the filter
        filtered_audio = signal.filtfilt(b, a, audio_data)
        return filtered_audio
    
    def _score_audio_segment(self, segment: np.ndarray, sample_rate: int) -> float:
        """Score an audio segment based on clarity and quality metrics."""
        # Multiple factors contribute to the score
        
        # 1. RMS energy (higher is generally better for speech)
        rms_energy = np.sqrt(np.mean(segment**2))
        energy_score = min(rms_energy * 10, 1.0)  # Normalize
        
        # 2. Spectral clarity
        clarity_score = self._estimate_speech_clarity(segment, sample_rate)
        
        # 3. Low noise level
        noise_level = self._estimate_noise_level(segment)
        noise_score = max(0, 1.0 - noise_level * 5)  # Lower noise is better
        
        # 4. Low silence ratio
        silence_ratio = self._calculate_silence_ratio(segment)
        speech_score = max(0, 1.0 - silence_ratio)
        
        # Combine scores with weights
        total_score = (
            0.3 * energy_score +
            0.3 * clarity_score +
            0.2 * noise_score +
            0.2 * speech_score
        )
        
        return float(total_score)