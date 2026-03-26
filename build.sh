#!/usr/bin/env bash
# build.sh — Install system deps needed by mediapipe + opencv on Render Linux
set -o errexit

# Install system-level libraries required by mediapipe and opencv-headless
apt-get update -y
apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Pre-build Matplotlib font cache so it doesn't block Gunicorn startup
# (without this, the cache build can take 10-30s and trigger Render's port-scan timeout)
echo "Pre-building Matplotlib font cache..."
MPLCONFIGDIR=/tmp/matplotlib python -c "import matplotlib; matplotlib.font_manager._load_fontmanager(try_read_cache=False)"
echo "Font cache build complete."
