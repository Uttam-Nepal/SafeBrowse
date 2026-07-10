"""
train_statistical.py — trains all 6 "Statistical" family models on the
malicious_phish.csv dataset and saves them to models/statistical/.

Run from the backend project root:
    python training/train_statistical.py --data data/malicious_phish.csv
"""

import argparse
import time
import sys
import os
import json

import numpy as np
import pandas as pd
from joblib import dump

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.feature_extraction import extract_features_batch, FEATURE_NAMES

# XGBoost is optional here — only available where the package is installed.
try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False


def load_and_label(csv_path):
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["url", "type"])
    # benign -> 0 (safe), everything else (phishing/defacement/malware) -> 1 (unsafe)
    df["label"] = (df["type"].str.lower() != "benign").astype(int)
    return df


def build_features(df):
    print(f"Extracting features for {len(df):,} URLs...")
    t0 = time.time()
    X = extract_features_batch(df["url"].tolist())
    X = np.array(X, dtype=np.float64)
    print(f"  done in {time.time() - t0:.1f}s")
    y = df["label"].values
    return X, y


def evaluate(name, model, X_test, y_test):
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds)
    rec = recall_score(y_test, preds)
    f1 = f1_score(y_test, preds)
    print(f"  {name:22s} acc={acc:.4f}  precision={prec:.4f}  recall={rec:.4f}  f1={f1:.4f}")
    return {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/malicious_phish.csv")
    parser.add_argument("--out", default="models/statistical")
    parser.add_argument("--sample", type=int, default=None, help="optional: subsample N rows for a quick test run")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    df = load_and_label(args.data)
    if args.sample:
        df = df.sample(n=min(args.sample, len(df)), random_state=42)
    print(f"Loaded {len(df):,} rows. Label balance:\n{df['label'].value_counts()}\n")

    X, y = build_features(df)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42, stratify=y)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    dump(scaler, os.path.join(args.out, "scaler.joblib"), compress=3)

    results = {}

    # ---- Random Forest ----
    # NOTE: unconstrained RF on 650k rows produced a 336MB file — far too
    # large for shared hosting and slow to load per-request. Capping tree
    # count/depth and requiring a minimum leaf size keeps the file small
    # with only a marginal accuracy trade-off.
    print("Training Random Forest...")
    t0 = time.time()
    rf = RandomForestClassifier(
        n_estimators=100, max_depth=14, min_samples_leaf=5, n_jobs=-1, random_state=42
    )
    rf.fit(X_train, y_train)  # tree models don't need scaling
    print(f"  trained in {time.time()-t0:.1f}s")
    results["rf"] = evaluate("Random Forest", rf, X_test, y_test)
    dump(rf, os.path.join(args.out, "rf.joblib"), compress=3)

    # ---- Decision Tree ----
    print("Training Decision Tree...")
    t0 = time.time()
    dt = DecisionTreeClassifier(max_depth=16, min_samples_leaf=5, random_state=42)
    dt.fit(X_train, y_train)
    print(f"  trained in {time.time()-t0:.1f}s")
    results["dt"] = evaluate("Decision Tree", dt, X_test, y_test)
    dump(dt, os.path.join(args.out, "dt.joblib"), compress=3)

    # ---- Logistic Regression ----
    print("Training Logistic Regression...")
    t0 = time.time()
    lr = LogisticRegression(max_iter=1000)
    lr.fit(X_train_scaled, y_train)
    print(f"  trained in {time.time()-t0:.1f}s")
    results["lr"] = evaluate("Logistic Regression", lr, X_test_scaled, y_test)
    dump(lr, os.path.join(args.out, "lr.joblib"), compress=3)

    # ---- Naive Bayes ----
    print("Training Naive Bayes...")
    t0 = time.time()
    nb = GaussianNB()
    nb.fit(X_train_scaled, y_train)
    print(f"  trained in {time.time()-t0:.1f}s")
    results["nb"] = evaluate("Naive Bayes", nb, X_test_scaled, y_test)
    dump(nb, os.path.join(args.out, "nb.joblib"), compress=3)

    # ---- SVM (LinearSVC, calibrated for probability output) ----
    print("Training SVM (LinearSVC, calibrated)...")
    t0 = time.time()
    base_svm = LinearSVC(max_iter=5000, dual="auto")
    svm = CalibratedClassifierCV(base_svm, cv=3)
    svm.fit(X_train_scaled, y_train)
    print(f"  trained in {time.time()-t0:.1f}s")
    results["svm"] = evaluate("SVM", svm, X_test_scaled, y_test)
    dump(svm, os.path.join(args.out, "svm.joblib"), compress=3)

    # ---- XGBoost (only if installed) ----
    if HAS_XGB:
        print("Training XGBoost...")
        t0 = time.time()
        xgb = XGBClassifier(n_estimators=200, max_depth=8, use_label_encoder=False, eval_metric="logloss", n_jobs=-1)
        xgb.fit(X_train, y_train)
        print(f"  trained in {time.time()-t0:.1f}s")
        results["xgb"] = evaluate("XGBoost", xgb, X_test, y_test)
        dump(xgb, os.path.join(args.out, "xgb.joblib"), compress=3)
    else:
        print("xgboost not installed — skipping. Run `pip install xgboost` and re-run this script to include it.")

    with open(os.path.join(args.out, "metrics.json"), "w") as f:
        json.dump(results, f, indent=2)

    print("\nAll done. Models saved to:", args.out)
    print("Feature order (must match at inference time):", FEATURE_NAMES)


if __name__ == "__main__":
    main()
