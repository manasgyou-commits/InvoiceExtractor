#!/bin/bash
# Build script for Invoice Extractor Android App

echo "Building Invoice Extractor Pro APK..."

# Check buildozer
if ! command -v buildozer &> /dev/null; then
    echo "Installing buildozer..."
    pip install buildozer cython
fi

# Clean previous builds
rm -rf bin/ .buildozer/

# Build debug APK
echo "Starting build..."
buildozer android debug

# Move APK to output
mkdir -p output
mv bin/*.apk output/ 2>/dev/null || true

echo "Build complete! Check output/ folder"
