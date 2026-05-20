"""
Pytest configuration and fixtures for enhanced TTS testing.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator
import numpy as np
import soundfile as sf

from enhanced_tts.models import CharacterConfig, TTSParameters


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_audio_file(temp_dir: Path) -> Path:
    """Create a sample audio file for testing."""
    # Generate 3 seconds of sample audio (sine wave)
    sample_rate = 22050
    duration = 3.0
    frequency = 440.0  # A4 note
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = 0.3 * np.sin(2 * np.pi * frequency * t)
    
    audio_file = temp_dir / "sample_audio.wav"
    sf.write(audio_file, audio_data, sample_rate)
    
    return audio_file


@pytest.fixture
def sample_character_config(sample_audio_file: Path) -> CharacterConfig:
    """Create a sample character configuration."""
    return CharacterConfig(
        character_id="test_character",
        reference_audio_path=sample_audio_file,
        reference_text="This is a test reference text for voice cloning.",
        tts_parameters=TTSParameters(),
        quality_threshold=0.75
    )


@pytest.fixture
def multiple_audio_files(temp_dir: Path) -> list[Path]:
    """Create multiple audio files with different characteristics."""
    files = []
    sample_rate = 22050
    
    # High quality audio
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    clean_audio = 0.3 * np.sin(2 * np.pi * 440 * t)
    
    high_quality_file = temp_dir / "high_quality.wav"
    sf.write(high_quality_file, clean_audio, sample_rate)
    files.append(high_quality_file)
    
    # Low quality audio (with noise)
    noisy_audio = clean_audio + 0.1 * np.random.normal(0, 1, len(clean_audio))
    low_quality_file = temp_dir / "low_quality.wav"
    sf.write(low_quality_file, noisy_audio, sample_rate)
    files.append(low_quality_file)
    
    # Long audio (30+ seconds)
    long_duration = 35.0
    t_long = np.linspace(0, long_duration, int(sample_rate * long_duration))
    long_audio = 0.3 * np.sin(2 * np.pi * 440 * t_long)
    
    long_file = temp_dir / "long_audio.wav"
    sf.write(long_file, long_audio, sample_rate)
    files.append(long_file)
    
    return files


@pytest.fixture
def mock_hf_tokens(monkeypatch):
    """Mock HuggingFace tokens for testing."""
    def mock_get_hf_tokens():
        return ["test_token_1", "test_token_2"]
    
    monkeypatch.setattr("enhanced_tts.backends.huggingface.get_hf_tokens", mock_get_hf_tokens)
    return mock_get_hf_tokens