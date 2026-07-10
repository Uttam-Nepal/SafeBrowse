"""
reputation.py — a small, illustrative allowlist of well-known domains,
checked BEFORE any model runs. This mirrors how real anti-phishing
products work in practice: a fast reputation-list check first, ML
classification as the fallback for anything not already known.

This list is intentionally small and for demo purposes — in a real
deployment this would be a much larger maintained list (e.g. Tranco
top 1M) or a call to a reputation API, not a hardcoded set.
"""

TRUSTED_DOMAINS = {
    "google.com", "youtube.com", "facebook.com", "wikipedia.org",
    "instagram.com", "twitter.com", "x.com", "amazon.com", "reddit.com",
    "yahoo.com", "linkedin.com", "microsoft.com", "apple.com",
    "netflix.com", "github.com", "stackoverflow.com", "mozilla.org",
    "wordpress.com", "office.com", "live.com", "bing.com", "zoom.us",
    "adobe.com", "dropbox.com", "paypal.com", "ebay.com", "spotify.com",
    "twitch.tv", "whatsapp.com", "gmail.com",
}


def root_domain(hostname):
    parts = hostname.lower().split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else hostname.lower()


def is_trusted(url):
    from app.feature_extraction import normalize_url
    normalized = normalize_url(url)
    hostname = normalized.split("/")[0]
    return root_domain(hostname) in TRUSTED_DOMAINS
