"""
train_model.py
==============
Improved training pipeline for CRICSHOT:
  - Merges duplicate/alias shot classes
  - Skips classes with too few samples
  - Balances class distribution via oversampling
  - Uses a stronger MLP + StandardScaler pipeline
  - Saves shot_classifier.pkl, label_encoder.pkl
"""

import os
import io
import pickle
import sys
import urllib.request
import numpy as np
import cv2

import mediapipe as mp
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions
from mediapipe.tasks.python.core.base_options import BaseOptions

from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import Pipeline

# ─── Config ───────────────────────────────────────────────────────────────────
DATASET_DIR = os.path.join(os.path.dirname(__file__), "data", "Dataset")
MODEL_DIR   = os.path.join(os.path.dirname(__file__), "model")
os.makedirs(MODEL_DIR, exist_ok=True)

TASK_MODEL_PATH = os.path.join(MODEL_DIR, "pose_landmarker.task")
TASK_MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)

# ─── Class aliases: folder name → canonical class name ────────────────────────
# Merges duplicate/alias classes into one canonical label
CLASS_ALIASES = {
    "drive":          "Straight Drive",   # small duplicate folder → merge
    "pullshot":       "Pull",             # duplicate of Pull
    "legglance-flick": "Flick",           # duplicate of Flick
}

# Canonical class list (what the model will actually predict)
CANONICAL_CLASSES = [
    "Cover Drive", "Defensive", "Down The Wicket", "Flick", "Hook",
    "Late Cut", "Lofted Legside", "Lofted Offside", "Pull",
    "Reverse Sweep", "Scoop", "Square Cut", "Straight Drive", "Sweep",
    "Upper Cut",
]

# Minimum samples required to include a class
MIN_SAMPLES = 10

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXTS = {".avi", ".mp4", ".mov", ".mkv", ".wmv"}

# How many frames to sample per video
FRAMES_PER_VIDEO = 8


# ─── Download pose model if needed ────────────────────────────────────────────
def ensure_task_model():
    if not os.path.exists(TASK_MODEL_PATH):
        print("  Downloading MediaPipe pose model ...")
        urllib.request.urlretrieve(TASK_MODEL_URL, TASK_MODEL_PATH)
        print(f"  [OK] Saved to {TASK_MODEL_PATH}")
    else:
        print(f"  [OK] Using cached: {TASK_MODEL_PATH}")


# ─── Build landmarkers ────────────────────────────────────────────────────────
def build_image_landmarker():
    opts = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=TASK_MODEL_PATH),
        running_mode=mp_vision.RunningMode.IMAGE,
        min_pose_detection_confidence=0.3,
        min_pose_presence_confidence=0.3,
        num_poses=1
    )
    return PoseLandmarker.create_from_options(opts)


def build_video_landmarker():
    opts = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=TASK_MODEL_PATH),
        running_mode=mp_vision.RunningMode.VIDEO,
        min_pose_detection_confidence=0.3,
        min_pose_presence_confidence=0.3,
        min_tracking_confidence=0.3,
        num_poses=1
    )
    return PoseLandmarker.create_from_options(opts)


def bgr_to_mp(img_bgr: np.ndarray) -> mp.Image:
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)


def landmarks_to_features(lm_list) -> np.ndarray:
    return np.array([v for p in lm_list for v in (p.x, p.y, p.z)], dtype=np.float32)


# ─── Extraction functions ─────────────────────────────────────────────────────
def extract_from_image(landmarker, path: str):
    img = cv2.imread(path)
    if img is None:
        return None
    # Resize for consistency
    h, w = img.shape[:2]
    scale = min(512 / w, 512 / h, 1.0)
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)))
    result = landmarker.detect(bgr_to_mp(img))
    if not result.pose_landmarks:
        return None
    return landmarks_to_features(result.pose_landmarks[0])


def extract_from_video(path: str):
    """Sample FRAMES_PER_VIDEO evenly and return list of feature arrays."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return []

    lm = build_video_landmarker()
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps   = cap.get(cv2.CAP_PROP_FPS) or 25
    indices_to_sample = set(
        np.linspace(0, max(total - 1, 0), FRAMES_PER_VIDEO, dtype=int).tolist()
    )

    features_list = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx in indices_to_sample:
            ts_ms  = int((frame_idx / fps) * 1000)
            mp_img = bgr_to_mp(frame)
            result = lm.detect_for_video(mp_img, ts_ms)
            if result.pose_landmarks:
                features_list.append(landmarks_to_features(result.pose_landmarks[0]))
        frame_idx += 1

    cap.release()
    lm.close()
    return features_list


# ─── Oversample minority classes to balance dataset ───────────────────────────
def oversample_to_balance(X, y, min_count=None):
    """Duplicate samples from minority classes so all classes have >= min_count."""
    unique, counts = np.unique(y, return_counts=True)
    if min_count is None:
        # Target: median count (avoid inflating too much)
        min_count = max(int(np.median(counts)), 30)

    X_bal, y_bal = list(X), list(y)
    for cls, cnt in zip(unique, counts):
        if cnt < min_count:
            needed = min_count - cnt
            cls_X = X[y == cls]
            # Repeat with noise augmentation
            for _ in range(needed):
                sample = cls_X[np.random.randint(len(cls_X))].copy()
                # Add tiny Gaussian noise for augmentation
                sample += np.random.normal(0, 0.005, sample.shape).astype(np.float32)
                X_bal.append(sample)
                y_bal.append(cls)

    return np.array(X_bal), np.array(y_bal)


# ─── Main ─────────────────────────────────────────────────────────────────────
print("=" * 62)
print("  CRICSHOT - Improved Model Training")
print("=" * 62)

ensure_task_model()
img_landmarker = build_image_landmarker()

X, y = [], []

# All folders to process = canonical classes + alias folders
all_folders = os.listdir(DATASET_DIR) if os.path.isdir(DATASET_DIR) else []

for folder_name in all_folders:
    class_dir = os.path.join(DATASET_DIR, folder_name)
    if not os.path.isdir(class_dir):
        continue

    # Resolve canonical label (handle aliases)
    canonical = CLASS_ALIASES.get(folder_name, folder_name)

    # Skip folders whose canonical class is not in our target list
    if canonical not in CANONICAL_CLASSES:
        print(f"  [SKIP] {folder_name} (not in canonical list)")
        continue

    count = 0
    for fname in os.listdir(class_dir):
        ext  = os.path.splitext(fname)[1].lower()
        path = os.path.join(class_dir, fname)

        if ext in IMAGE_EXTS:
            feats = extract_from_image(img_landmarker, path)
            if feats is not None:
                X.append(feats)
                y.append(canonical)
                count += 1

        elif ext in VIDEO_EXTS:
            for feats in extract_from_video(path):
                X.append(feats)
                y.append(canonical)
                count += 1

    print(f"  [{folder_name:25s} -> {canonical:20s}]  {count:5d} samples")

img_landmarker.close()

print(f"\n  Total samples (raw): {len(X)}")

X = np.array(X)
y = np.array(y)

# ─── Remove classes with too few samples ──────────────────────────────────────
unique_classes, class_counts = np.unique(y, return_counts=True)
valid_classes = unique_classes[class_counts >= MIN_SAMPLES]
removed = unique_classes[class_counts < MIN_SAMPLES]
if len(removed) > 0:
    print(f"\n  [DROPPING] Classes with < {MIN_SAMPLES} samples: {list(removed)}")

mask = np.isin(y, valid_classes)
X, y = X[mask], y[mask]
print(f"  Total after dropping: {len(X)} samples, {len(valid_classes)} classes")

if len(X) < len(valid_classes) * 2:
    print("\n[ERROR] Too few samples. Check your dataset.")
    sys.exit(1)

# ─── Balance classes ──────────────────────────────────────────────────────────
print("\nBalancing classes via oversampling ...")
X, y = oversample_to_balance(X, y)
unique2, counts2 = np.unique(y, return_counts=True)
for cls, cnt in zip(unique2, counts2):
    print(f"  {cls:30s}: {cnt} samples")
print(f"\n  Total samples (balanced): {len(X)}")

# ─── Encode labels ────────────────────────────────────────────────────────────
le    = LabelEncoder()
le.fit(valid_classes)   # Fix encoder to valid_classes only
y_enc = le.transform(y)

X_train, X_test, y_train, y_test = train_test_split(
    X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
)

# ─── Build a pipeline: Scaler + MLP ──────────────────────────────────────────
print("\nTraining MLP Classifier (with StandardScaler) ...")
clf_pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("mlp", MLPClassifier(
        hidden_layer_sizes=(512, 256, 128, 64),
        activation="relu",
        solver="adam",
        alpha=0.001,           # L2 regularization
        batch_size=64,
        learning_rate="adaptive",
        max_iter=1000,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=30,
        verbose=True
    ))
])

clf_pipeline.fit(X_train, y_train)

y_pred = clf_pipeline.predict(X_test)
acc    = accuracy_score(y_test, y_pred)
print(f"\nTest Accuracy: {acc * 100:.2f}%")
print("\nClassification Report:")
report = classification_report(y_test, y_pred, target_names=le.classes_)
print(report)

# ─── Save Classification Report as JSON ──────────────────────────────────────
import json
from sklearn.metrics import classification_report as cr_dict, confusion_matrix

report_dict = cr_dict(y_test, y_pred, target_names=le.classes_, output_dict=True)
with open(os.path.join(MODEL_DIR, "classification_report.json"), "w") as f:
    json.dump(report_dict, f, indent=2)
print(f"[OK] Classification report -> {MODEL_DIR}/classification_report.json")

# ─── Generate Confusion Matrix ───────────────────────────────────────────────
cm = confusion_matrix(y_test, y_pred)
cm_data = {
    "labels": le.classes_.tolist(),
    "matrix": cm.tolist(),
    "accuracy": float(acc),
    "total_test_samples": int(len(y_test)),
}
with open(os.path.join(MODEL_DIR, "confusion_matrix.json"), "w") as f:
    json.dump(cm_data, f, indent=2)
print(f"[OK] Confusion matrix data -> {MODEL_DIR}/confusion_matrix.json")

# ─── Generate Confusion Matrix Heatmap ────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    fig, ax = plt.subplots(figsize=(16, 13))
    fig.patch.set_facecolor("#0a1628")
    ax.set_facecolor("#0a1628")

    cm_pct = cm.astype(float) / cm.sum(axis=1, keepdims=True) * 100
    cm_pct = np.nan_to_num(cm_pct, 0)

    sns.heatmap(
        cm_pct, annot=True, fmt=".0f", cmap="YlGn",
        xticklabels=le.classes_, yticklabels=le.classes_,
        linewidths=0.5, linecolor="#1a2a4a",
        cbar_kws={"label": "Prediction %", "shrink": 0.8},
        ax=ax
    )
    ax.set_xlabel("Predicted Shot", fontsize=12, color="white", labelpad=14)
    ax.set_ylabel("Actual Shot", fontsize=12, color="white", labelpad=14)
    ax.set_title(f"Confusion Matrix — {acc*100:.1f}% Accuracy", fontsize=16,
                 color="#00e88a", fontweight="bold", pad=20)
    ax.tick_params(colors="white", labelsize=8)
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)

    cbar = ax.collections[0].colorbar
    cbar.ax.yaxis.label.set_color("white")
    cbar.ax.tick_params(colors="white")

    plt.tight_layout()
    heatmap_path = os.path.join(MODEL_DIR, "confusion_matrix.png")
    fig.savefig(heatmap_path, dpi=150, facecolor="#0a1628", bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Confusion matrix heatmap -> {heatmap_path}")
except ImportError as e:
    print(f"[WARN] Could not generate heatmap (install matplotlib + seaborn): {e}")

# ─── Save Model (pipeline includes scaler) ───────────────────────────────────
with open(os.path.join(MODEL_DIR, "shot_classifier.pkl"), "wb") as f:
    pickle.dump(clf_pipeline, f)
with open(os.path.join(MODEL_DIR, "label_encoder.pkl"), "wb") as f:
    pickle.dump(le, f)

print(f"\n[OK] Model saved  -> {MODEL_DIR}/shot_classifier.pkl")
print(f"[OK] Encoder saved -> {MODEL_DIR}/label_encoder.pkl")
print("\nTraining complete!")
