# MJPEG Webcam Streamer

Flask app that serves a live MJPEG webcam stream with adjustable motion blur.

## Requirements

- Python 3.9+ (recommended)
- A working webcam (or a virtual camera)

## Setup

1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then open:

- http://localhost:5000

## Controls

- Use the slider to set motion blur strength (1-31)
- Start/Stop toggles whether blur is applied (stream continues)

## API Endpoints

- GET /: UI
- GET /video_feed: MJPEG stream
- GET /status: JSON status
- POST /control: {"action": "start" | "stop"}
- POST /blur: {"strength": number}

## Notes

- Webcam device index defaults to 0.
- If the camera fails to open, check permissions or update the device index in app.py.
