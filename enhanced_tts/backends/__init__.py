"""
Voice generation backends for the enhanced F5-TTS system.
"""

from .huggingface_backend import HuggingFaceF5TTSBackend
from .local_backend import LocalF5TTSBackend
from .fallback_backend import FallbackTTSBackend

__all__ = [
    'HuggingFaceF5TTSBackend',
    'LocalF5TTSBackend', 
    'FallbackTTSBackend'
]