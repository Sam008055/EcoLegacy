@echo off
echo ========================================
echo EchoLegacy Local TTS Setup for RTX 3050
echo ========================================
echo.

echo [1/4] Creating Python virtual environment...
python -m venv tts_env
call tts_env\Scripts\activate.bat

echo.
echo [2/4] Installing PyTorch with CUDA support...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

echo.
echo [3/4] Installing TTS requirements...
pip install -r requirements_tts.txt

echo.
echo [4/4] Testing GPU availability...
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To start the TTS server:
echo 1. call tts_env\Scripts\activate.bat
echo 2. python local_tts_server.py
echo.
echo Expected performance on RTX 3050:
echo - Latency: 2-4 seconds per response
echo - VRAM usage: ~3GB
echo - Quality: High (better than HuggingFace)
echo ========================================

pause