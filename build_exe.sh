#!/bin/bash
# Build standalone executables for WhatsApp Chat Viewer

set -e

echo "🔨 Building WhatsApp Chat Viewer executable..."

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "❌ PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Build the executable
echo "🚀 Building executable with PyInstaller..."
pyinstaller whatsapp_chat_viewer.spec --clean

echo "✅ Build complete!"
echo "📁 Executable location: dist/whatsapp-chat-viewer"
echo ""
echo "To run:"
echo "  ./dist/whatsapp-chat-viewer --help"
