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
