"""Run from the backend folder (venv-turl active):  python test_urls.py
Scores a list of URLs with TURL-MV LeafFuse and prints the malicious probability."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import hybrid_model

hybrid_model.load_hybrid_model()
if not hybrid_model.is_available():
    sys.exit("Model not loaded: " + str(hybrid_model.load_error()))
pm = hybrid_model._pm
thr = pm.M["threshold"]

GROUPS = {
  "Your site, written different ways": [
    "reflexitsolution.com", "http://reflexitsolution.com", "https://reflexitsolution.com/",
    "https://reflexitsolution.com/about", "https://www.reflexitsolution.com",
  ],
  "Genuine sites (expected Safe)": [
    "https://www.bom.gov.au", "https://www.abc.net.au", "https://www.sbs.com.au",
    "https://www.rba.gov.au", "https://www.kathmandupost.com", "https://www.mihe.com.au",
    "https://www.nytimes.com/section/world", "https://en.wikipedia.org/wiki/Phishing",
    "https://github.com/Uttam-Nepal/SafeBrowse", "https://www.bunnings.com.au/products",
  ],
  "Suspicious (expected Unsafe)": [
    "paypa1-login-secure-account.com", "192.168.1.1/admin/login.php",
    "http://secure-login.verify-account-update.xyz/signin",
    "http://amaz0n-account-verify.top/login.php?id=88123",
  ],
}

for title, urls in GROUPS.items():
    print("\n==", title)
    for u in urls:
        c = pm.canonicalize(u)
        p = float(pm.predict_proba([c])[0])
        print(f"  {'UNSAFE' if p >= thr else 'safe  '}  p={p:.4f}  {u}")