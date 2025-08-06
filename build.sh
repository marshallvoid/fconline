#!/bin/bash

# Local build script for testing
echo "🚀 Building FC Online Tool..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Sync dependencies
echo "📦 Installing dependencies..."
uv sync

# Add PyInstaller
echo "🔧 Installing PyInstaller..."
uv add pyinstaller

# Build the executable
echo "🏗️ Building executable..."
uv run pyinstaller build.spec

# Check if build was successful
if [ -f "dist/FC_Online_Tool.exe" ]; then
    echo "✅ Build successful! File created: dist/FC_Online_Tool.exe"
    echo "📊 File size: $(du -h dist/FC_Online_Tool.exe | cut -f1)"
else
    echo "❌ Build failed! Check the output above for errors."
    exit 1
fi

echo "🎉 Done! You can now run dist/FC_Online_Tool.exe"
