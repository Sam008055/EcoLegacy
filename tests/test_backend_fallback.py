"""
Unit tests for backend fallback mechanisms.

Tests automatic switching between backends on failures and quota exhaustion handling.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import time

from enhanced_tts.backends.huggingface_backend import HuggingFaceF5TTSBackend
from enhanced_tts.backends.local_backend import LocalF5TTSBackend
from enhanced_tts.backends.fallback_backend import FallbackTTSBackend
from enhanced_tts.models import TTSParameters, AudioResult, BackendType


class TestBackendFallback:
    """Unit tests for backend fallback mechanisms."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def sample_params(self):
        """Create sample TTS parameters."""
        return TTSParameters(temperature=0.7, top_p=0.9, speed=1.0)
    
    def test_huggingface_backend_quota_exhaustion_handling(self, temp_dir, sample_params):
        """
        Test quota exhaustion handling and request queuing for HuggingFace backend.
        
        Validates: Requirements 4.4, 5.2
        """
        # Create test reference audio
        ref_audio = temp_dir / "reference.wav"
        ref_audio.write_text("dummy audio content")  # Placeholder
        
        backend = HuggingFaceF5TTSBackend()
        
        # Mock the token functions
        with patch('enhanced_tts.backends.huggingface_backend.get_hf_tokens') as mock_tokens:
            mock_tokens.return_value = ["token1", "token2"]
            
            # Mock gradio client to simulate quota exhaustion
            with patch('enhanced_tts.backends.huggingface_backend.Client') as mock_client:
                # First token fails with quota error
                mock_client.side_effect = [
                    Exception("ZeroGPU quota exhausted"),
                    Exception("Rate limit exceeded")
                ]
                
                # Test generation with quota exhaustion
                result = backend.generate("Test text", ref_audio, sample_params)
                
                # Should fail when all tokens are exhausted
                assert not result.success
                assert "quota" in result.error_message.lower()
                
                # Check that tokens are marked as exhausted
                assert backend._is_token_exhausted("token1")
                assert backend._is_token_exhausted("token2")
                
                # Backend should report as unavailable
                assert not backend.is_available()
                
                # Quota status should reflect exhaustion
                quota_status = backend.get_quota_status()
                assert not quota_status.is_available
                assert quota_status.requests_remaining == 0
    
    def test_huggingface_backend_token_recovery(self, temp_dir, sample_params):
        """
        Test that tokens recover after quota reset time.
        
        Validates: Requirements 4.4
        """
        backend = HuggingFaceF5TTSBackend()
        
        # Mark a token as exhausted
        backend._mark_token_exhausted("test_token")
        assert backend._is_token_exhausted("test_token")
        
        # Simulate time passing (mock time to avoid waiting)
        with patch('time.time') as mock_time:
            # Set initial time
            mock_time.return_value = 1000
            backend._mark_token_exhausted("test_token")
            
            # Token should still be exhausted
            assert backend._is_token_exhausted("test_token")
            
            # Advance time by more than 1 hour (3600 seconds)
            mock_time.return_value = 1000 + 3700
            
            # Token should now be recovered
            assert not backend._is_token_exhausted("test_token")
    
    def test_local_backend_availability_check(self):
        """
        Test local backend availability checking with GPU requirements.
        
        Validates: Requirements 4.3
        """
        # Test with CUDA available
        with patch('torch.cuda.is_available') as mock_cuda:
            mock_cuda.return_value = True
            
            with patch('torch.cuda.get_device_properties') as mock_props:
                # Mock GPU with sufficient memory (8GB)
                mock_props.return_value = Mock(total_memory=8 * 1024**3)
                
                backend = LocalF5TTSBackend(device="cuda")
                assert backend.device == "cuda"
                
                # Should be available with sufficient GPU memory
                with patch.object(backend, '_check_f5tts_availability', return_value=True):
                    assert backend.is_available()
        
        # Test with insufficient GPU memory
        with patch('torch.cuda.is_available') as mock_cuda:
            mock_cuda.return_value = True
            
            with patch('torch.cuda.get_device_properties') as mock_props:
                # Mock GPU with insufficient memory (2GB)
                mock_props.return_value = Mock(total_memory=2 * 1024**3)
                
                backend = LocalF5TTSBackend(device="cuda")
                
                # Should not be available with insufficient memory
                assert not backend._check_f5tts_availability()
        
        # Test CPU fallback
        backend = LocalF5TTSBackend(device="cpu")
        assert backend.device == "cpu"
        
        # CPU backend should be available if F5-TTS is installed
        with patch.object(backend, '_check_f5tts_availability', return_value=True):
            assert backend.is_available()
    
    def test_fallback_backend_service_detection(self):
        """
        Test fallback backend service detection and availability.
        
        Validates: Requirements 4.4
        """
        # Test edge-tts availability
        backend = FallbackTTSBackend(preferred_service="edge-tts")
        
        # Mock edge-tts as available
        with patch('enhanced_tts.backends.fallback_backend.edge_tts'):
            assert backend._check_edge_tts()
            assert backend.is_available()
        
        # Mock edge-tts as unavailable
        with patch('enhanced_tts.backends.fallback_backend.edge_tts', side_effect=ImportError):
            assert not backend._check_edge_tts()
            assert not backend.is_available()
        
        # Test espeak availability
        backend = FallbackTTSBackend(preferred_service="espeak")
        
        # Mock espeak as available
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            assert backend._check_espeak()
            assert backend.is_available()
        
        # Mock espeak as unavailable
        with patch('subprocess.run', side_effect=FileNotFoundError):
            assert not backend._check_espeak()
            assert not backend.is_available()
    
    def test_backend_type_identification(self):
        """
        Test that each backend correctly identifies its type.
        
        Validates: Requirements 4.3
        """
        hf_backend = HuggingFaceF5TTSBackend()
        local_backend = LocalF5TTSBackend()
        fallback_backend = FallbackTTSBackend()
        
        assert hf_backend.get_backend_type() == BackendType.HUGGINGFACE_F5TTS
        assert local_backend.get_backend_type() == BackendType.LOCAL_F5TTS
        assert fallback_backend.get_backend_type() == BackendType.FALLBACK_TTS
    
    def test_quota_status_reporting(self):
        """
        Test quota status reporting for different backends.
        
        Validates: Requirements 4.4
        """
        # HuggingFace backend quota status
        hf_backend = HuggingFaceF5TTSBackend()
        
        with patch('enhanced_tts.backends.huggingface_backend.get_hf_tokens') as mock_tokens:
            mock_tokens.return_value = ["token1", "token2", "token3"]
            
            quota_status = hf_backend.get_quota_status()
            assert quota_status.backend_type == BackendType.HUGGINGFACE_F5TTS
            assert quota_status.requests_remaining > 0  # Should have some quota
            assert quota_status.is_available
        
        # Local backend quota status (unlimited)
        local_backend = LocalF5TTSBackend()
        quota_status = local_backend.get_quota_status()
        
        assert quota_status.backend_type == BackendType.LOCAL_F5TTS
        assert quota_status.requests_remaining is None  # Unlimited
        
        # Fallback backend quota status
        fallback_backend = FallbackTTSBackend()
        quota_status = fallback_backend.get_quota_status()
        
        assert quota_status.backend_type == BackendType.FALLBACK_TTS
        assert quota_status.requests_remaining > 0  # Should have generous quota
    
    def test_backend_error_handling(self, temp_dir, sample_params):
        """
        Test error handling and recovery for backend failures.
        
        Validates: Requirements 5.2
        """
        ref_audio = temp_dir / "reference.wav"
        ref_audio.write_text("dummy audio content")
        
        # Test HuggingFace backend error handling
        hf_backend = HuggingFaceF5TTSBackend()
        
        with patch('enhanced_tts.backends.huggingface_backend.get_hf_tokens') as mock_tokens:
            # No tokens configured
            mock_tokens.return_value = []
            
            result = hf_backend.generate("Test text", ref_audio, sample_params)
            assert not result.success
            assert "token" in result.error_message.lower()
        
        # Test with missing reference audio
        missing_audio = temp_dir / "missing.wav"
        result = hf_backend.generate("Test text", missing_audio, sample_params)
        
        assert not result.success
        assert "not found" in result.error_message.lower()
    
    def test_generation_timeout_handling(self, temp_dir, sample_params):
        """
        Test handling of generation timeouts and long-running requests.
        
        Validates: Requirements 5.2
        """
        ref_audio = temp_dir / "reference.wav"
        ref_audio.write_text("dummy audio content")
        
        backend = HuggingFaceF5TTSBackend(timeout=1)  # Very short timeout
        
        with patch('enhanced_tts.backends.huggingface_backend.get_hf_tokens') as mock_tokens:
            mock_tokens.return_value = ["token1"]
            
            with patch('enhanced_tts.backends.huggingface_backend.Client') as mock_client:
                # Mock a slow response that would timeout
                def slow_predict(*args, **kwargs):
                    time.sleep(2)  # Longer than timeout
                    return None
                
                mock_client.return_value.predict = slow_predict
                
                # Generation should handle timeout gracefully
                start_time = time.time()
                result = backend.generate("Test text", ref_audio, sample_params)
                end_time = time.time()
                
                # Should fail due to timeout/error
                assert not result.success
                # Should not take much longer than timeout (allowing some overhead)
                assert end_time - start_time < 5