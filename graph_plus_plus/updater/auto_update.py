"""Auto-update helper — file staging.

Since Blender locks Python files while running, we can't hot-swap the
addon. Instead, we download to a temp dir and store the path in
preferences; on next restart, the user installs via
Preferences > Extensions > Install from Disk.
"""
import os
import shutil
import tempfile
import urllib.request


def download_zip(url, dest_dir=None, timeout=60):
    """Download a zip from `url` to dest_dir. Returns the local file path."""
    dest_dir = dest_dir or tempfile.gettempdir()
    os.makedirs(dest_dir, exist_ok=True)
    zip_path = os.path.join(dest_dir, "graph_plus_plus_update.zip")

    req = urllib.request.Request(url, headers={"User-Agent": "GraphPlusPlus-Blender-Addon"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        with open(zip_path, "wb") as f:
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                f.write(chunk)

    return zip_path


def extract_zip(zip_path, dest_dir):
    """Extract a zip to dest_dir. Returns the path to the extracted folder."""
    import zipfile
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(dest_dir)
    # The first member is usually the top-level folder
    with zipfile.ZipFile(zip_path, 'r') as zf:
        names = zf.namelist()
    if names:
        top = names[0].split("/")[0]
        return os.path.join(dest_dir, top)
    return dest_dir
