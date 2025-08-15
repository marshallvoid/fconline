@echo off
echo 🚀 Building FC Online Tool...

REM Check if uv is installed
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ uv is not installed. Please install it first:
    echo    https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "pyproject.toml" (
    echo ❌ Please run this script from the project root directory
    pause
    exit /b 1
)

REM Sync dependencies
echo 📦 Installing dependencies...
uv sync
if %errorlevel% neq 0 (
    echo ❌ Failed to sync dependencies
    pause
    exit /b 1
)

REM Add PyInstaller
echo 🔧 Installing PyInstaller...
uv add pyinstaller
if %errorlevel% neq 0 (
    echo ❌ Failed to install PyInstaller
    pause
    exit /b 1
)

REM Clean previous builds
echo 🧹 Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"
if exist "src\__pycache__" rmdir /s /q "src\__pycache__"
for /d %%d in (src\*\__pycache__) do rmdir /s /q "%%d" 2>nul

REM Build the executable
echo 🏗️ Building executable...
uv run pyinstaller build.spec
if %errorlevel% neq 0 (
    echo ❌ Build failed! Check the output above for errors.
    pause
    exit /b 1
)

REM Check if build was successful
if exist "dist\FC_Online_Tool.exe" (
    echo ✅ Build successful! File created: dist\FC_Online_Tool.exe
    for %%A in (dist\FC_Online_Tool.exe) do echo 📊 File size: %%~zA bytes
    echo 📍 Location: %CD%\dist\FC_Online_Tool.exe
) else (
    echo ❌ Build failed! Executable not found.
    pause
    exit /b 1
)

echo 🎉 Done! You can now run dist\FC_Online_Tool.exe
pause
