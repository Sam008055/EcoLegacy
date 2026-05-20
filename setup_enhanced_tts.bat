@echo off
echo Installing Enhanced F5-TTS Voice Cloning Server Dependencies
echo ============================================================

REM Activate virtual environment if it exists
if exist "tts_env\Scripts\activate.bat" (
    echo Activating virtual environment...
    call tts_env\Scripts\activate.bat
) else (
    echo No virtual environment found. Creating one...
    python -m venv tts_env
    call tts_env\Scripts\activate.bat
)

echo.
echo Installing minimal requirements for enhanced TTS server...
pip install flask>=2.3.0
pip install flask-cors>=4.0.0
pip install python-dotenv>=1.0.0
pip install gradio-client>=0.8.0
pip install requests>=2.31.0
pip install numpy>=1.24.0

echo.
echo Optional: Installing audio processing libraries (recommended)...
pip install librosa>=0.10.0
pip install soundfile>=0.12.0
pip install scipy>=1.10.0

echo.
echo ============================================================
echo Enhanced F5-TTS Server Setup Complete!
echo.
echo Next steps:
echo 1. Add missing reference audio files to web/public/audio/:
echo    - bhagat_singh_ref.wav
echo    - ssr_ref.wav
echo.
echo 2. Set your HUGGINGFACE_TOKEN in web/.env.local
echo.
echo 3. Start the server:
echo    python minimal_tts_server.py
echo.
echo 4. Test the enhancements:
echo    python test_enhanced_tts.py
echo ============================================================
pause