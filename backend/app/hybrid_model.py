"""
hybrid_model.py — the Default model. Implements the exact 6-step
pipeline as specified (do not alter the logic — it must match how the
model was trained):

  1. BERT embedding (768-dim) via bert_binary_best_model/
  2. Handcrafted features (20-dim) via extract_url_features()
  3. Concatenate -> hybrid vector (788-dim)
  4. XGBoost .apply() -> leaf indices (150-dim)   [NOT .predict()/.predict_proba()]
  5. Concatenate -> final vector (938-dim)
  6. Random Forest .predict() + .predict_proba() -> final verdict + confidence

This module loads nothing at import time — load_hybrid_model() is called
once at API startup (see main.py), and is a no-op (with a clear log
message) if the three model artifacts aren't present yet.
"""

import os
import math
from collections import Counter
from urllib.parse import urlparse

import numpy as np
from joblib import load as joblib_load

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "hybrid")
BERT_DIR = os.path.join(MODELS_DIR, "bert_binary_best_model")
XGB_PATH = os.path.join(MODELS_DIR, "xgb_final_optimized_model.joblib")
RF_PATH = os.path.join(MODELS_DIR, "rf_final_optimized_model.joblib")

_bert_tokenizer = None
_bert_model = None
_xgb_model = None
_rf_model = None
_torch = None
_is_loaded = False


# ---- Step 2: handcrafted features — EXACT function as specified, unchanged ----

def calculate_entropy(text):
    counter = Counter(text)
    length = len(text)
    entropy = 0
    for count in counter.values():
        probability = count / length
        entropy -= probability * math.log2(probability)
    return entropy


def extract_url_features(url):
    url = str(url)
    parsed = urlparse(url)
    domain = parsed.netloc
    path = parsed.path

    features = [
        len(url),
        len(domain),
        len(path),
        url.count("."),
        url.count("-"),
        url.count("_"),
        url.count("/"),
        url.count("?"),
        url.count("="),
        sum(c.isdigit() for c in url),
        sum(c.isalpha() for c in url),
        url.count("@"),
        url.count("%"),
        url.count("&"),
        calculate_entropy(url),
        int("https" in url),
        int("login" in url.lower()),
        int("verify" in url.lower()),
        int("secure" in url.lower()),
        int("account" in url.lower()),
    ]
    return features


def is_available():
    return _is_loaded


def load_hybrid_model():
    """Attempts to load the 3 hybrid model artifacts. If they aren't
    present yet, logs a clear message and leaves is_available() == False
    rather than crashing the whole API — the rest of the app (statistical
    models) should keep working while the hybrid model is pending."""
    global _bert_tokenizer, _bert_model, _xgb_model, _rf_model, _torch, _is_loaded

    if not (os.path.isdir(BERT_DIR) and os.path.exists(XGB_PATH) and os.path.exists(RF_PATH)):
        print("[hybrid_model] Model artifacts not found in models/hybrid/. "
              "'Default' will be unavailable until bert_binary_best_model/, "
              "xgb_final_optimized_model.joblib, and rf_final_optimized_model.joblib are added.")
        return

    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except ImportError:
        print("[hybrid_model] torch/transformers not installed — run "
              "`pip install torch transformers` to enable the Default model.")
        return

    _torch = torch
    print("[hybrid_model] Loading BERT tokenizer + encoder...")
    _bert_tokenizer = AutoTokenizer.from_pretrained(BERT_DIR)
    _bert_model = AutoModel.from_pretrained(BERT_DIR)
    _bert_model.eval()

    print("[hybrid_model] Loading XGBoost leaf-generator...")
    _xgb_model = joblib_load(XGB_PATH)

    print("[hybrid_model] Loading final Random Forest classifier...")
    _rf_model = joblib_load(RF_PATH)

    _is_loaded = True
    print("[hybrid_model] Ready.")


def predict(url):
    if not _is_loaded:
        raise RuntimeError(
            "Hybrid model is not loaded. Add the model files to models/hybrid/ and restart the API."
        )

    # ---- Step 1: BERT embedding (768-dim) ----
    inputs = _bert_tokenizer(
        url, padding="max_length", truncation=True, max_length=128, return_tensors="pt"
    )
    with _torch.no_grad():
        outputs = _bert_model(**inputs)
    bert_embedding = outputs.last_hidden_state[:, 0, :].squeeze(0).numpy()  # (768,)
    assert bert_embedding.shape == (768,), f"Expected (768,), got {bert_embedding.shape}"

    # ---- Step 2: handcrafted features (20-dim) ----
    handcrafted = np.array(extract_url_features(url), dtype=np.float64)  # (20,)
    assert handcrafted.shape == (20,), f"Expected (20,), got {handcrafted.shape}"

    # ---- Step 3: hybrid vector (788-dim) ----
    hybrid_vector = np.concatenate([bert_embedding, handcrafted]).reshape(1, -1)  # (1, 788)
    assert hybrid_vector.shape == (1, 788), f"Expected (1, 788), got {hybrid_vector.shape}"

    # ---- Step 4: XGBoost leaf indices (150-dim) — .apply(), NOT .predict() ----
    leaf_indices = _xgb_model.apply(hybrid_vector)  # (1, 150)
    assert leaf_indices.shape == (1, 150), f"Expected (1, 150), got {leaf_indices.shape}"

    # ---- Step 5: final vector (938-dim) ----
    final_vector = np.concatenate([hybrid_vector, leaf_indices], axis=1)  # (1, 938)
    assert final_vector.shape == (1, 938), f"Expected (1, 938), got {final_vector.shape}"

    # ---- Step 6: final prediction ----
    pred = _rf_model.predict(final_vector)[0]          # 0 = Safe, 1 = Unsafe
    proba = _rf_model.predict_proba(final_vector)[0]
    confidence = float(proba[int(pred)])

    verdict = "unsafe" if pred == 1 else "safe"
    return verdict, confidence
