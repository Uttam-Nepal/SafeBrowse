"""
diagnose_hybrid.py — reuses the ACTUAL app/hybrid_model.py code (not a
reimplementation) and adds the per-tree vote breakdown + intermediate
vector stats your research assistant recommended, so we can see exactly
where a flat 1.0 confidence is coming from.

Run from the backend folder, with (venv) active:
    python diagnose_hybrid.py
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from app import hybrid_model

print("Loading model artifacts...")
hybrid_model.load_hybrid_model()

if not hybrid_model.is_available():
    print("Hybrid model failed to load — fix that before running this diagnostic.")
    sys.exit(1)

test_urls = [
    "paypa1-login-secure-account.com/verify",
    "amaz0n-account-verify.tk/secure/login.php",
    "https://www.wikipedia.org",
    "github.com/anthropics",
    "asdkjaslkdj12312",
]


def diagnose(url):
    print(f"\nURL: {url}")

    # ---- Step 1: BERT embedding ----
    inputs = hybrid_model._bert_tokenizer(
        url, padding="max_length", truncation=True, max_length=128, return_tensors="pt"
    )
    with hybrid_model._torch.no_grad():
        outputs = hybrid_model._bert_model(**inputs)
    bert_embedding = outputs.last_hidden_state[:, 0, :].squeeze(0).numpy()
    print(f"  BERT embedding -> mean={bert_embedding.mean():.4f}, std={bert_embedding.std():.4f}, "
          f"first 5 values={bert_embedding[:5]}")

    # ---- Step 2: handcrafted features ----
    handcrafted = np.array(hybrid_model.extract_url_features(url), dtype=np.float64)
    print(f"  Handcrafted features: {handcrafted}")

    # ---- Step 3: hybrid vector ----
    hybrid_vector = np.concatenate([bert_embedding, handcrafted]).reshape(1, -1)
    print(f"  Hybrid vector (788-dim) -> mean={hybrid_vector.mean():.4f}, std={hybrid_vector.std():.4f}")

    # ---- Step 4: XGBoost leaf indices ----
    leaf_indices = hybrid_model._xgb_model.apply(hybrid_vector)
    print(f"  Leaf indices (first 10 of 150): {leaf_indices[0][:10]}")

    # ---- Step 5: final vector ----
    final_vector = np.concatenate([hybrid_vector, leaf_indices], axis=1)
    print(f"  Final vector shape: {final_vector.shape}")

    # ---- Step 6: prediction + per-tree vote breakdown ----
    pred = hybrid_model._rf_model.predict(final_vector)[0]
    proba = hybrid_model._rf_model.predict_proba(final_vector)[0]

    tree_votes = np.array([tree.predict(final_vector)[0] for tree in hybrid_model._rf_model.estimators_])
    vote_counts = np.bincount(tree_votes.astype(int), minlength=2)
    print(f"  Per-tree vote split: {vote_counts[0]} voted Safe, {vote_counts[1]} voted Unsafe "
          f"(out of {len(tree_votes)} trees)")
    print(f"  -> Prediction: {'Unsafe' if pred == 1 else 'Safe'}, Confidence: {proba}")


for u in test_urls:
    diagnose(u)
