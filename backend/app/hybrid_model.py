"""
hybrid_model.py — wrapper around TURL-MV LeafFuse (the main model).

All model logic lives in models/turl_mv/predict.py, which is used exactly
as exported from training. Do not copy or rewrite its feature code here:
the same file defines canonicalize() and the 36 lexical features, so
training and serving stay identical.

load_hybrid_model() is called once at API startup (see main.py).
If loading fails, the reason is stored and shown by /health; the API
stays up but /api/check answers 503 (there is no fallback model).
"""

import os
import sys

MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "turl_mv"))
MODEL_NAME = "turl-mv-leaffuse"

_pm = None
_loaded = False
_load_error = None


def is_available():
    return _loaded


def load_error():
    return _load_error


def threshold():
    return _pm.M["threshold"] if _loaded else None


def load_hybrid_model():
    global _pm, _loaded, _load_error
    needed = ["predict.py", "config.json", "sklearn_parts.joblib", "m1.json", "m5.json", "m7.json"]
    missing = [f for f in needed if not os.path.exists(os.path.join(MODEL_DIR, f))]
    if missing or not os.path.isdir(os.path.join(MODEL_DIR, "bert")):
        _load_error = f"Missing in models/turl_mv/: {missing or ''} {'bert/' if not os.path.isdir(os.path.join(MODEL_DIR, 'bert')) else ''}".strip()
        print(f"[turl_mv] {_load_error}")
        return
    try:
        if MODEL_DIR not in sys.path:
            sys.path.insert(0, MODEL_DIR)
        import predict as pm  # models/turl_mv/predict.py
        print("[turl_mv] Loading TURL-MV LeafFuse (BERT + XGBoost + TF-IDF + meta)...")
        pm.load_model(MODEL_DIR, device="cpu")
        _pm = pm
        _loaded = True
        print(f"[turl_mv] Ready. threshold={pm.M['threshold']:.4f}")
    except Exception as e:  # keep the API alive, report the reason
        _load_error = f"{type(e).__name__}: {e}"
        print(f"[turl_mv] FAILED to load: {_load_error}")


def predict(url):
    """Returns (verdict, confidence) with verdict 'safe' | 'unsafe'.
    Raises ValueError for input with no usable host."""
    if not _loaded:
        raise RuntimeError("TURL-MV LeafFuse is not loaded.")
    r = _pm.predict(url)
    if r["verdict"] == "Invalid":
        raise ValueError("That doesn't look like a valid URL.")
    return r["verdict"].lower(), float(r["confidence"])