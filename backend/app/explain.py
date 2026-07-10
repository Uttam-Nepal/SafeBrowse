"""
explain.py — ONE shared, model-agnostic explanation layer.

Every model (statistical, deep learning, transformer, hybrid) only needs
to produce a verdict + confidence. This module looks at the URL itself
and produces the plain-language "reasons" shown in the UI, independent
of which model actually classified it. This matches the product
decision: normal users see one clear explanation, not a different one
per model.
"""

from app.feature_extraction import extract_features, FEATURE_NAMES, SUSPICIOUS_KEYWORDS

# Common, high-trust domains — a tiny illustrative allowlist, not exhaustive.
# In a real deployment this would be a much larger curated/maintained list
# or a call to a reputation service; kept small here so it's easy to read.
TRUSTED_DOMAINS = {
    "google.com", "wikipedia.org", "github.com", "microsoft.com",
    "apple.com", "amazon.com", "youtube.com", "mozilla.org",
}


def _feature_dict(url):
    values = extract_features(url)
    return dict(zip(FEATURE_NAMES, values))


def generate_reasons(url, verdict):
    f = _feature_dict(url)
    reasons = []
    lower_url = url.lower()
    hostname = lower_url.split("/")[0].replace("http://", "").replace("https://", "")
    root_domain = ".".join(hostname.split(".")[-2:]) if "." in hostname else hostname

    if verdict == "unsafe":
        if f["has_ip_hostname"]:
            reasons.append("The address uses a raw IP instead of a domain name, a common phishing evasion technique")
        if f["suspicious_keyword_count"] >= 2:
            reasons.append("Multiple suspicious keywords found (e.g. login, verify, secure, account)")
        elif f["suspicious_keyword_count"] == 1:
            reasons.append("URL pattern resembles a login or account-verification page")
        if f["num_hyphens"] >= 3:
            reasons.append("Unusually high number of hyphens in the domain — often used to mimic real brand names")
        if f["entropy"] > 4.5:
            reasons.append("URL has unusually high randomness, consistent with generated/obfuscated phishing links")
        if f["num_subdomains"] >= 3:
            reasons.append("Excessive subdomains, a pattern often used to disguise the real destination")
        if not reasons:
            reasons.append("URL structure and characteristics match known phishing patterns in training data")
        reasons.append("No matching entry in the trusted-domain list")

    else:  # safe
        if root_domain in TRUSTED_DOMAINS:
            reasons.append("Domain matches a known, trusted entry")
        elif f["suspicious_keyword_count"] == 0:
            reasons.append("No suspicious keywords or character substitutions found")
        else:
            reasons.append("Some cautionary keywords present, but overall URL structure still matches legitimate patterns")
        if f["has_ip_hostname"] == 0 and f["num_hyphens"] < 3:
            reasons.append("No major red flags in URL structure")

    return reasons[:4]  # keep it scannable — top 4 reasons max
