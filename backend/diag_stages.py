"""Run from backend (venv-turl active):  python diag_stages.py
Prints every stage of TURL-MV LeafFuse for 3 URLs so we can see which stage misbehaves."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from scipy.sparse import hstack, csr_matrix
from app import hybrid_model

hybrid_model.load_hybrid_model()
if not hybrid_model.is_available():
    sys.exit("Model not loaded: " + str(hybrid_model.load_error()))
pm = hybrid_model._pm
M = pm.M
torch = M["torch"]

URLS = ["https://en.wikipedia.org/wiki/Phishing", "https://www.abc.net.au",
        "http://amaz0n-account-verify.top/login.php?id=88123"]
names = ["M1 xgb-lex", "M2 tfidf-char", "M3 tfidf-word", "M4 bert", "M5 xgb-cls", "M6 rf-cls", "M7 xgb-hyb", "M8 rf-hyb"]

for raw in URLS:
    u = pm.canonicalize(raw)
    print("\n=====", raw, "->", u)
    toks = M["tok"].convert_ids_to_tokens(M["tok"](u, truncation=True, max_length=64)["input_ids"])
    print("tokens:", toks[:20])
    lex_df = pd.DataFrame([pm.extract_features(u)], columns=pm.FEATURE_NAMES)
    with torch.no_grad():
        enc = M["tok"]([u], truncation=True, max_length=64, padding="max_length", return_tensors="pt")
        out = M["bert"](**{k: v.to(M["device"]) for k, v in enc.items()}, output_hidden_states=True)
        p4 = torch.softmax(out.logits.float(), 1)[:, 1].cpu().numpy()
        emb = out.hidden_states[-1][:, 0, :].float().cpu().numpy()
    hyb = np.concatenate([emb, lex_df.values], axis=1)
    probs = np.column_stack([
        M["m1"].predict_proba(lex_df)[:, 1], M["m2"].predict_proba(M["char_vec"].transform([u]))[:, 1],
        M["m3"].predict_proba(M["tok_vec"].transform([u]))[:, 1], p4,
        M["m5"].predict_proba(emb)[:, 1], M["m6"].predict_proba(emb)[:, 1],
        M["m7"].predict_proba(hyb)[:, 1], M["m8"].predict_proba(hyb)[:, 1]])
    for n, v in zip(names, probs[0]):
        print(f"  {n:15s} p_malicious = {v:.4f}")
    print(f"  CLS vector: norm={np.linalg.norm(emb):.1f}  mean={emb.mean():.3f}  std={emb.std():.3f}")
    raw_dense = np.concatenate([probs, emb, lex_df.values], axis=1)
    dense = M["scaler"].transform(raw_dense)
    print(f"  scaled dense: max|z|={np.abs(dense).max():.1f}  mean|z|={np.abs(dense).mean():.2f}  count|z|>6: {(np.abs(dense)>6).sum()}")
    leaves = M["m7"].apply(hyb)
    ohe = M["leaf_ohe"].transform(leaves)
    print(f"  leaf one-hot: nonzero={ohe.nnz} of 100 trees (unknown leaves are dropped)")
    X = hstack([csr_matrix(dense), ohe]).tocsr()
    print(f"  meta decision value={M['meta'].decision_function(X)[0]:.2f}  p={M['meta'].predict_proba(X)[0,1]:.6f}")