"""
statistical_models.py — loads all trained statistical models once at
startup and exposes a single predict() function used by the API layer.
"""

import os
import numpy as np
from joblib import load

from app.feature_extraction import extract_features

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "statistical")

# Models that need the StandardScaler applied before prediction
# (tree-based models — RF, DT, XGB — split on raw feature values and
# don't need or benefit from scaling; linear/distance-based models do).
NEEDS_SCALING = {"lr", "nb", "svm"}

_models = {}
_scaler = None


def load_all():
    """Call once at API startup. Loads whatever model files are present.
    Each model is loaded independently, wrapped in its own try/except, so
    one bad or incompatible file (e.g. xgb.joblib present but the xgboost
    package missing in this environment) can't take the whole service
    down or block the other models from loading."""
    global _scaler
    scaler_path = os.path.join(MODELS_DIR, "scaler.joblib")
    if os.path.exists(scaler_path):
        try:
            _scaler = load(scaler_path)
        except Exception as e:
            print(f"[statistical_models] failed to load scaler: {e}")

    for key in ["rf", "dt", "lr", "nb", "svm", "xgb"]:
        path = os.path.join(MODELS_DIR, f"{key}.joblib")
        if not os.path.exists(path):
            print(f"[statistical_models] {key}.joblib not found — '{key}' will be unavailable until trained")
            continue
        try:
            _models[key] = load(path)
            print(f"[statistical_models] loaded {key}")
        except Exception as e:
            print(f"[statistical_models] failed to load {key} ({e}) — skipping, other models unaffected")

    return _models


def available_models():
    return list(_models.keys())


def predict(model_key, url):
    if model_key not in _models:
        raise ValueError(
            f"Model '{model_key}' is not available. Trained models: {available_models()}"
        )

    features = np.array([extract_features(url)], dtype=np.float64)

    if model_key in NEEDS_SCALING:
        if _scaler is None:
            raise RuntimeError("Scaler not loaded — required for this model.")
        features = _scaler.transform(features)

    model = _models[model_key]
    pred = model.predict(features)[0]  # 0 = safe, 1 = unsafe
    proba = model.predict_proba(features)[0]
    confidence = float(proba[int(pred)])

    verdict = "unsafe" if pred == 1 else "safe"
    return verdict, confidence