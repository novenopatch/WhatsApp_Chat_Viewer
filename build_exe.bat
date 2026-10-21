@echo off
REM Build standalone executables for WhatsApp Chat Viewer (Windows)

echo 🔨 Building WhatsApp Chat Viewer executable...

REM Check if PyInstaller is installed
pyinstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ PyInstaller not found. Installing...
    pip install pyinstaller
)

REM Install dependencies
echo 📦 Installing dependencies...
pip install -r requirements.txt

REM Build the executable
echo 🚀 Building executable with PyInstaller...
pyinstaller whatsapp_chat_viewer.spec --clean

echo ✅ Build complete!
echo 📁 Executable location: dist\whatsapp-chat-viewer.exe
echo.
echo To run:
echo   dist\whatsapp-chat-viewer.exe --help

pause
