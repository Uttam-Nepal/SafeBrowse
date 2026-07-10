"""
feature_extraction.py — lexical/structural feature extraction for the
Statistical model family (Random Forest, XGBoost, Logistic Regression,
Decision Tree, SVM, Naive Bayes).

NOTE: this is intentionally separate from the hybrid model's own
extract_url_features() function. The hybrid model's feature function
must stay exactly as specified (it was used at training time and
cannot change). This module is ours, for the experiment-tier
statistical models we're training from scratch.

These 20 features are also reused by app/explain.py to generate the
"reasons" shown in the UI, so the same signals a model used to decide
are the same signals a plain-language explanation is built from.
"""

import math
import re
from collections import Counter
from urllib.parse import urlparse

FEATURE_NAMES = [
    "url_length",
    "hostname_length",
    "path_length",
    "num_dots",
    "num_hyphens",
    "num_underscore",
    "num_slash",
    "num_question",
    "num_equal",
    "num_digits",
    "num_letters",
    "num_at",
    "num_percent",
    "num_ampersand",
    "entropy",
    "has_ip_hostname",
    "num_subdomains",
    "suspicious_keyword_count",
    "digit_ratio",
    "brand_typosquat_flag",
]

# A small set of frequently-impersonated brand names for typosquat
# detection (e.g. "paypa1" vs "paypal", "amaz0n" vs "amazon"). Real
# deployments would use a much larger, maintained list; this is
# illustrative but catches the common cases.
WELL_KNOWN_BRANDS = [
    "paypal", "amazon", "google", "apple", "microsoft", "facebook",
    "netflix", "instagram", "ebay", "bankofamerica", "wellsfargo",
    "chase", "linkedin", "twitter", "whatsapp", "dropbox", "adobe",
]


def _levenshtein(a, b):
    """Simple edit-distance implementation (no external dependency)."""
    if a == b:
        return 0
    if len(a) == 0:
        return len(b)
    if len(b) == 0:
        return len(a)
    prev_row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr_row = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr_row[j] = min(
                prev_row[j] + 1,        # deletion
                curr_row[j - 1] + 1,    # insertion
                prev_row[j - 1] + cost, # substitution
            )
        prev_row = curr_row
    return prev_row[-1]


def brand_typosquat_flag(hostname):
    """Returns 1 if any token in the hostname looks like a near-miss
    typosquat of a known brand (edit distance exactly 1 — a single
    character swap/insert/delete, e.g. 'paypa1' vs 'paypal'), else 0.

    NOTE: an earlier version allowed distance up to 2, but on the real
    dataset that caught too many unrelated short words that happened to
    be edit-distance-2 from a brand name (e.g. random 4-5 letter tokens
    near "ebay"/"chase"), which diluted the signal rather than helping.
    Distance-1 only is stricter but meaningfully more precise."""
    if not hostname:
        return 0
    label = hostname.lower().split(".")[0]
    tokens = re.split(r"[-_]", label)
    for token in tokens:
        if not token or token in WELL_KNOWN_BRANDS:
            continue  # exact match to a brand name is legitimate, not a typosquat
        for brand in WELL_KNOWN_BRANDS:
            if abs(len(token) - len(brand)) > 1:
                continue
            if _levenshtein(token, brand) == 1:
                return 1
    return 0

SUSPICIOUS_KEYWORDS = [
    "login", "verify", "secure", "account", "update",
    "confirm", "bank", "signin", "password", "free",
]

IP_PATTERN = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")


def calculate_entropy(text):
    if not text:
        return 0.0
    counter = Counter(text)
    length = len(text)
    entropy = 0.0
    for count in counter.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


SCHEME_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
WWW_PATTERN = re.compile(r"^www\.", re.IGNORECASE)


def normalize_url(raw_url):
    """Strips scheme (http://, https://) and a leading 'www.' so that
    formatting differences between data sources (some URLs recorded with
    a scheme, some without; some with www., some without) can't leak into
    character-count features. This was found to be a real artifact in
    the training data — see training/train_statistical.py notes."""
    url = str(raw_url).strip()
    url = SCHEME_PATTERN.sub("", url)
    url = WWW_PATTERN.sub("", url)
    return url


def _ensure_scheme(url):
    # urlparse needs a scheme to correctly split host vs path. We add a
    # consistent http:// here purely so urlparse can do its job — this
    # does NOT mean we treat the URL as insecure; protocol isn't a
    # feature we use at all (see normalize_url note above on why).
    return "http://" + url


def extract_features(raw_url):
    url = normalize_url(raw_url)
    try:
        parsed = urlparse(_ensure_scheme(url))
        hostname = (parsed.netloc or "").split(":")[0]
        path = parsed.path or ""
    except ValueError:
        # A handful of real-world URLs are malformed (e.g. bad IPv6 brackets)
        # and urlparse rejects them outright. Fall back to treating the
        # whole string as an opaque blob rather than dropping the row.
        hostname = ""
        path = ""

    lower_url = url.lower()

    num_digits = sum(c.isdigit() for c in url)

    features = [
        len(url),                                              # url_length
        len(hostname),                                          # hostname_length
        len(path),                                               # path_length
        url.count("."),                                          # num_dots
        url.count("-"),                                          # num_hyphens
        url.count("_"),                                          # num_underscore
        url.count("/"),                                          # num_slash
        url.count("?"),                                          # num_question
        url.count("="),                                          # num_equal
        num_digits,                                              # num_digits
        sum(c.isalpha() for c in url),                           # num_letters
        url.count("@"),                                          # num_at
        url.count("%"),                                          # num_percent
        url.count("&"),                                          # num_ampersand
        calculate_entropy(url),                                  # entropy
        int(bool(IP_PATTERN.match(hostname))),                  # has_ip_hostname
        max(hostname.count(".") - 1, 0),                        # num_subdomains (rough)
        sum(kw in lower_url for kw in SUSPICIOUS_KEYWORDS),      # suspicious_keyword_count
        (num_digits / len(url)) if len(url) > 0 else 0.0,       # digit_ratio
        brand_typosquat_flag(hostname),                          # brand_typosquat_flag
    ]
    return features


def extract_features_batch(urls):
    """Returns a list of feature vectors for a list/Series of URLs."""
    return [extract_features(u) for u in urls]
