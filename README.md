# 🏏 CRICSHOT — AI Cricket Shot Prediction

An AI-powered cricket shot prediction system built with Flask, MediaPipe, and scikit-learn.

## Features
- 15 cricket shot types detected from images and videos
- Real-time pose skeleton overlay
- OTP-based authentication (Email via SMTP2GO, SMS via Twilio)
- Prediction history and analytics dashboard

## Tech Stack
- **Backend**: Python, Flask, SQLAlchemy, Flask-Login
- **ML**: MediaPipe Pose Landmarker, scikit-learn MLPClassifier
- **Auth**: OTP via SMTP2GO (email) and Twilio (SMS)
- **Frontend**: Vanilla HTML/CSS/JS

## Local Setup
```bash
pip install -r requirements.txt
cp .env.template .env   # fill in credentials
python app.py
```

## Environment Variables
See `.env.template` for required variables.
