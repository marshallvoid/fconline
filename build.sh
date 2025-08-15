#!/bin/bash

# Local build script for testing
echo "🚀 Building FC Online Tool..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Sync dependencies
echo "📦 Installing dependencies..."
if ! uv sync; then
    echo "❌ Failed to sync dependencies"
    exit 1
fi

# Add PyInstaller
echo "🔧 Installing PyInstaller..."
if ! uv add pyinstaller; then
    echo "❌ Failed to install PyInstaller"
    exit 1
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ __pycache__/ src/__pycache__/ src/*/__pycache__/ src/*/*/__pycache__/

# Build the executable
echo "🏗️ Building executable..."
if ! uv run pyinstaller build.spec; then
    echo "❌ Build failed! Check the output above for errors."
    exit 1
fi

# Check if build was successful
if [ -f "dist/FC_Online_Tool.exe" ]; then
    echo "✅ Build successful! File created: dist/FC_Online_Tool.exe"
    echo "📊 File size: $(du -h dist/FC_Online_Tool.exe | cut -f1)"
    echo "📍 Location: $(pwd)/dist/FC_Online_Tool.exe"
else
    echo "❌ Build failed! Executable not found."
    exit 1
fi

echo "🎉 Done! You can now run dist/FC_Online_Tool.exe"
