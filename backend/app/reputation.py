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
    "mihe.com.au",  # user's institution — demo-critical, verified safe
}


def is_trusted(url):
    """Exact or subdomain match against TRUSTED_DOMAINS.

    NOTE: this used to derive a 'root domain' by taking the last 2
    dot-separated labels (e.g. hostname.split('.')[-2:]) and comparing
    that against the list. That breaks for compound TLDs — 'mihe.com.au'
    would reduce to 'com.au', which never matches the literal entry
    'mihe.com.au' in the set above. Suffix-matching against the full
    trusted strings avoids that assumption entirely and handles both
    simple ('google.com') and compound ('mihe.com.au') TLDs correctly.
    """
    from app.feature_extraction import normalize_url
    normalized = normalize_url(url)
    hostname = normalized.split("/")[0].lower()

    for domain in TRUSTED_DOMAINS:
        if hostname == domain or hostname.endswith("." + domain):
            return True
    return False