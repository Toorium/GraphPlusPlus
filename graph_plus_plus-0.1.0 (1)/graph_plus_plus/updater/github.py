"""GitHub API helper — separate from the operator for testability."""
import json
import urllib.request
from .. import GPP_GITHUB_OWNER, GPP_GITHUB_REPO


def fetch_latest_release(owner=None, repo=None, timeout=10):
    """Return dict with keys: tag_name, html_url, zipball_url, body, published_at.

    Raises RuntimeError on network/parse errors.
    """
    owner = owner or GPP_GITHUB_OWNER
    repo = repo or GPP_GITHUB_REPO
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"

    req = urllib.request.Request(url, headers={"User-Agent": "GraphPlusPlus-Blender-Addon"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    return {
        "tag_name": data.get("tag_name", "v0.0.0"),
        "html_url": data.get("html_url", ""),
        "zipball_url": data.get("zipball_url", ""),
        "body": data.get("body", ""),
        "published_at": data.get("published_at", ""),
    }


def compare_versions(v1, v2):
    """Compare two 'X.Y.Z' version strings. Returns -1, 0, or 1."""
    def parse(v):
        parts = v.lstrip("v").split(".")
        try:
            return [int(x) for x in parts]
        except ValueError:
            return [0]
    a = parse(v1)
    b = parse(v2)
    # Pad
    while len(a) < len(b): a.append(0)
    while len(b) < len(a): b.append(0)
    for x, y in zip(a, b):
        if x < y: return -1
        if x > y: return 1
    return 0
