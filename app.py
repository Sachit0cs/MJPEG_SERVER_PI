import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
from flask import Flask, Response, jsonify, render_template, request


@dataclass
class StreamConfig:
    blur_strength: int = 7
    running: bool = True


class MotionBlurProcessor:
    def __init__(self, strength: int) -> None:
        self._strength = max(1, int(strength))
        self._lock = threading.Lock()

    def set_strength(self, strength: int) -> None:
        with self._lock:
            self._strength = max(1, int(strength))

    def get_strength(self) -> int:
        with self._lock:
            return self._strength

    def apply(self, frame):
        k = self.get_strength()
        if k <= 1:
            return frame
        # Motion blur kernel: diagonal line normalized.
        kernel = self._create_kernel(k)
        return cv2.filter2D(frame, -1, kernel)

    @staticmethod
    def _create_kernel(size: int):
        size = max(1, int(size))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (size, size)).astype("float32")
        kernel[:] = 0.0
        for i in range(size):
            kernel[i, i] = 1.0
        kernel /= kernel.sum()
        return kernel


class WebcamSource:
    def __init__(self, index: int = 0, resolution: Tuple[int, int] = (1280, 720)) -> None:
        self._index = index
        self._resolution = resolution
        self._cap: Optional[cv2.VideoCapture] = None

    def open(self) -> None:
        self._cap = cv2.VideoCapture(self._index)
        if not self._cap.isOpened():
            raise RuntimeError("Failed to open webcam. Check permissions or device index.")
        width, height = self._resolution
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def read(self):
        if self._cap is None:
            return False, None
        return self._cap.read()

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class FrameStreamer:
    def __init__(self, source: WebcamSource, processor: MotionBlurProcessor) -> None:
        self._source = source
        self._processor = processor
        self._config = StreamConfig()
        self._frame_lock = threading.Lock()
        self._latest_frame = None
        self._fps = 0.0
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)

    def start(self) -> None:
        self._source.open()
        self._thread.start()

    def set_running(self, running: bool) -> None:
        self._config.running = bool(running)

    def set_blur_strength(self, strength: int) -> None:
        self._processor.set_strength(strength)

    def get_status(self) -> dict:
        return {
            "running": self._config.running,
            "blur_strength": self._processor.get_strength(),
            "fps": round(self._fps, 1),
        }

    def get_latest_frame(self):
        with self._frame_lock:
            return self._latest_frame

    def _capture_loop(self) -> None:
        last_time = time.time()
        frames = 0
        while True:
            ok, frame = self._source.read()
            if not ok:
                time.sleep(0.05)
                continue

            if self._config.running:
                frame = self._processor.apply(frame)

            frames += 1
            now = time.time()
            if now - last_time >= 1.0:
                self._fps = frames / (now - last_time)
                frames = 0
                last_time = now

            with self._frame_lock:
                self._latest_frame = frame


app = Flask(__name__)

processor = MotionBlurProcessor(strength=7)
source = WebcamSource(index=0)
streamer = FrameStreamer(source, processor)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    return Response(_frame_generator(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/control", methods=["POST"])
def control():
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if action == "start":
        streamer.set_running(True)
    elif action == "stop":
        streamer.set_running(False)
    return jsonify(streamer.get_status())


@app.route("/blur", methods=["POST"])
def blur():
    data = request.get_json(silent=True) or {}
    strength = int(data.get("strength", 1))
    streamer.set_blur_strength(strength)
    return jsonify(streamer.get_status())


@app.route("/status")
def status():
    return jsonify(streamer.get_status())


def _frame_generator():
    while True:
        frame = streamer.get_latest_frame()
        if frame is None:
            time.sleep(0.02)
            continue
        # Encode current frame as JPEG for MJPEG streaming.
        ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ok:
            continue
        frame_bytes = buffer.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )


if __name__ == "__main__":
    streamer.start()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
