"""
predict.py
==========
Core prediction helpers using MediaPipe Tasks API (v0.10+).
  - predict_image(file_bytes)  → dict with shot, confidence, annotated_image (base64 PNG)
  - predict_video(file_bytes)  → dict with shot, confidence, frame_count, annotated_gif
"""

import os
import io
import base64
import pickle
import numpy as np
import cv2
from PIL import Image

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions
    from mediapipe.tasks.python.core.base_options import BaseOptions
    MEDIAPIPE_OK = True
except Exception as e:
    print(f"[WARN] MediaPipe import failed: {e}. Predictions disabled.")
    MEDIAPIPE_OK = False

# ─── Paths ────────────────────────────────────────────────────────────────────
MODEL_DIR       = os.path.join(os.path.dirname(__file__), "model")
TASK_MODEL_PATH = os.path.join(MODEL_DIR, "pose_landmarker.task")

# ─── MediaPipe skeleton drawing connections ───────────────────────────────────
# Standard MediaPipe POSE_CONNECTIONS (33-point skeleton)
POSE_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,7),(0,4),(4,5),(5,6),(6,8),
    (9,10),(11,12),(11,13),(13,15),(15,17),(15,19),(15,21),
    (17,19),(12,14),(14,16),(16,18),(16,20),(16,22),(18,20),
    (11,23),(12,24),(23,24),(23,25),(24,26),(25,27),(26,28),
    (27,29),(28,30),(29,31),(30,32),(27,31),(28,32)
]

# ─── Lazy-loaded singletons ────────────────────────────────────────────────────
_clf, _le               = None, None
_landmarker_image       = None
_landmarker_video       = None


def _load_model():
    global _clf, _le
    if _clf is None:
        clf_path = os.path.join(MODEL_DIR, "shot_classifier.pkl")
        le_path  = os.path.join(MODEL_DIR, "label_encoder.pkl")
        if not os.path.exists(clf_path) or not os.path.exists(le_path):
            raise FileNotFoundError(
                "Model files not found. Please run train_model.py first."
            )
        with open(clf_path, "rb") as f:
            _clf = pickle.load(f)
        with open(le_path, "rb") as f:
            _le = pickle.load(f)
    return _clf, _le


def _get_image_landmarker():
    global _landmarker_image
    if _landmarker_image is None:
        opts = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=TASK_MODEL_PATH),
            running_mode=mp_vision.RunningMode.IMAGE,
            min_pose_detection_confidence=0.3,
            min_pose_presence_confidence=0.3,
            num_poses=1
        )
        _landmarker_image = PoseLandmarker.create_from_options(opts)
    return _landmarker_image


def _get_video_landmarker():
    global _landmarker_video
    if _landmarker_video is None:
        opts = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=TASK_MODEL_PATH),
            running_mode=mp_vision.RunningMode.VIDEO,
            min_pose_detection_confidence=0.3,
            min_pose_presence_confidence=0.3,
            min_tracking_confidence=0.3,
            num_poses=1
        )
        _landmarker_video = PoseLandmarker.create_from_options(opts)
    return _landmarker_video


# ─── Drawing Helpers ──────────────────────────────────────────────────────────
def _draw_skeleton(img_bgr: np.ndarray, landmarks, img_w: int, img_h: int):
    """Draw pose skeleton on a copy of img_bgr using pixel coordinates."""
    out = img_bgr.copy()
    pts = []
    for lm in landmarks:
        x = int(lm.x * img_w)
        y = int(lm.y * img_h)
        pts.append((x, y))

    for a, b in POSE_CONNECTIONS:
        if a < len(pts) and b < len(pts):
            cv2.line(out, pts[a], pts[b], (0, 200, 255), 2)

    for (x, y) in pts:
        cv2.circle(out, (x, y), 4, (0, 255, 100), -1)
        cv2.circle(out, (x, y), 4, (0, 180, 80), 1)

    return out


def _landmarks_to_features(landmarks):
    return np.array([v for p in landmarks for v in (p.x, p.y, p.z)], dtype=np.float32)


def _bgr_to_base64(img_bgr: np.ndarray) -> str:
    _, buf = cv2.imencode(".png", img_bgr)
    return "data:image/png;base64," + base64.b64encode(buf).decode("utf-8")


def _gif_to_base64(frames_rgb: list) -> str:
    if not frames_rgb:
        return ""
    pil_frames = [Image.fromarray(f) for f in frames_rgb]
    buf = io.BytesIO()
    pil_frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=pil_frames[1:],
        loop=0,
        duration=80,
        optimize=True
    )
    return "data:image/gif;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")


# ─── Public API ───────────────────────────────────────────────────────────────

def predict_image(file_bytes: bytes) -> dict:
    clf, le = _load_model()
    landmarker = _get_image_landmarker()

    np_arr = np.frombuffer(file_bytes, np.uint8)
    img    = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        return {"error": "Cannot decode image."}

    # Resize for display
    h, w  = img.shape[:2]
    scale = min(640 / w, 640 / h, 1.0)
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    h, w  = img.shape[:2]
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_img  = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
    result  = landmarker.detect(mp_img)

    if not result.pose_landmarks:
        return {
            "error": "No person detected. Try a clearer cricket image.",
            "annotated_image": _bgr_to_base64(img)
        }

    lm       = result.pose_landmarks[0]
    features = _landmarks_to_features(lm)
    annotated = _draw_skeleton(img, lm, w, h)

    proba    = clf.predict_proba([features])[0]
    top_idx  = int(np.argmax(proba))
    shot     = le.classes_[top_idx]
    conf     = float(proba[top_idx])

    top5_idx = np.argsort(proba)[::-1][:5]
    all_scores = [{"shot": le.classes_[i], "confidence": float(proba[i])} for i in top5_idx]

    return {
        "shot": shot,
        "confidence": conf,
        "all_scores": all_scores,
        "annotated_image": _bgr_to_base64(annotated)
    }


def predict_video(file_bytes: bytes) -> dict:
    clf, le = _load_model()
    landmarker = _get_video_landmarker()

    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    cap = None
    try:
        cap = cv2.VideoCapture(tmp_path)
        if not cap or not cap.isOpened():
            return {"error": "Cannot open video file. It may be corrupt or an unsupported codec."}

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps          = cap.get(cv2.CAP_PROP_FPS) or 25
        MAX_FRAMES   = 60
        step         = max(1, total_frames // MAX_FRAMES)

        all_proba, gif_frames = [], []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % step == 0:
                h, w  = frame.shape[:2]
                frame_sm = cv2.resize(frame, (min(w, 480), min(h, 270)))
                h, w     = frame_sm.shape[:2]

                img_rgb = cv2.cvtColor(frame_sm, cv2.COLOR_BGR2RGB)
                mp_img  = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
                ts_ms   = int((frame_idx / fps) * 1000)
                
                try:
                    result = landmarker.detect_for_video(mp_img, ts_ms)
                    if result.pose_landmarks:
                        lm    = result.pose_landmarks[0]
                        feats = _landmarks_to_features(lm)
                        proba = clf.predict_proba([feats])[0]
                        all_proba.append(proba)
                        annotated = _draw_skeleton(frame_sm, lm, w, h)
                    else:
                        annotated = frame_sm
                except Exception:
                    annotated = frame_sm

                gif_frames.append(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB))

            frame_idx += 1

        if not all_proba:
            return {"error": "No pose detected in any video frame.", "frame_count": frame_idx}

        avg_proba = np.mean(all_proba, axis=0)
        top_idx   = int(np.argmax(avg_proba))
        shot      = le.classes_[top_idx]
        conf      = float(avg_proba[top_idx])

        top5_idx  = np.argsort(avg_proba)[::-1][:5]
        all_scores = [{"shot": le.classes_[i], "confidence": float(avg_proba[i])} for i in top5_idx]

        return {
            "shot": shot,
            "confidence": conf,
            "all_scores": all_scores,
            "frame_count": frame_idx,
            "frames_processed": len(all_proba),
            "annotated_gif": _gif_to_base64(gif_frames[:30])
        }

    except Exception as e:
        return {"error": f"Video processing failed: {str(e)}"}
    finally:
        if cap:
            cap.release()
        
        # Give Windows a moment to release the handle if needed, though cap.release() should be enough
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception as e:
            print(f"Warning: Could not delete temp file {tmp_path}: {e}")


def predict_frame(base64_str: str) -> dict:
    """Lightweight prediction from a base64 frame — no annotation, for real-time webcam."""
    clf, le = _load_model()
    landmarker = _get_image_landmarker()

    # Decode base64
    if "," in base64_str:
        base64_str = base64_str.split(",", 1)[1]
    img_bytes = base64.b64decode(base64_str)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        return {"error": "Cannot decode frame."}

    h, w = img.shape[:2]
    scale = min(320 / w, 320 / h, 1.0)
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    h, w = img.shape[:2]
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
    result = landmarker.detect(mp_img)

    if not result.pose_landmarks:
        return {"error": "no_pose", "shot": None, "confidence": 0}

    lm = result.pose_landmarks[0]
    features = _landmarks_to_features(lm)
    proba = clf.predict_proba([features])[0]
    top_idx = int(np.argmax(proba))
    shot = le.classes_[top_idx]
    conf = float(proba[top_idx])

    top5_idx = np.argsort(proba)[::-1][:5]
    all_scores = [{"shot": le.classes_[i], "confidence": float(proba[i])} for i in top5_idx]

    return {"shot": shot, "confidence": conf, "all_scores": all_scores}

