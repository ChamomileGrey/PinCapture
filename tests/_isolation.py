"""Side-effect-free helpers to keep tests away from the developer's real data.

- USERPROFILE/HOME point at a temp folder, so the real ~/.pincapture (config, log) is never touched.
- That temp home gets a config.json with a temporary save_dir. Needed because the default save folder
  comes from the Windows Known Folder API (Pictures), which does NOT follow USERPROFILE.
- PINCAP_RECENT_DIR is also inside that home, so closed-pin images from 0.8.0 stay out of %TEMP%.
- The single-instance channel name includes the home folder on Windows, so an isolated test can never
  send 'quit'/'show' to the developer's running PinCapture.
"""
import json
import os
from pathlib import Path


def make_isolated_home(home: Path) -> Path:
    """Create home/.pincapture/config.json with a temporary save folder (UTF-8, no BOM). Returns home."""
    home = Path(home)
    cfg_dir = home / ".pincapture"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (home / "captures").mkdir(exist_ok=True)
    (cfg_dir / "config.json").write_text(
        json.dumps({"save_dir": str(home / "captures")}), encoding="utf-8")
    return home


def isolated_env(home: Path) -> dict:
    """Environment for running pincapture.py in a separate process without touching real user data."""
    home = make_isolated_home(home)
    return dict(
        os.environ,
        QT_QPA_PLATFORM="offscreen",
        PINCAP_NO_LOG="1",
        PYTHONIOENCODING="utf-8",
        USERPROFILE=str(home),
        HOME=str(home),
        PINCAP_RECENT_DIR=str(home / "recent-pins"),
    )
