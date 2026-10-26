"""Shared test setup.

Every test runs headless (Qt offscreen) with an isolated home folder, so the developer's real
~/.pincapture (config, log) and save folder are never touched.
Run:  py -3.13 -m pytest -q
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_HOME = Path(tempfile.mkdtemp(prefix="pincapture-test-home-"))

# Must be set before `import pincapture`: CONFIG_DIR and the log path are computed at import time.
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PINCAP_NO_LOG"] = "1"
os.environ["USERPROFILE"] = str(_HOME)      # Path.home() on Windows
os.environ["HOME"] = str(_HOME)
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QEventLoop, QTimer        # noqa: E402
from PySide6.QtWidgets import QApplication           # noqa: E402

_app = QApplication.instance() or QApplication([])
_app.setQuitOnLastWindowClosed(False)

import pincapture  # noqa: E402

sys.excepthook = sys.__excepthook__                   # the app installs a MessageBox hook on import


def spin(ms: int) -> None:
    """Run the Qt event loop for `ms` milliseconds (lets QTimer.singleShot work happen)."""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


@pytest.fixture(scope="session")
def pc():
    """The pincapture module (imported once, isolated home)."""
    assert str(pincapture.CONFIG_DIR).startswith(str(_HOME)), "config dir is not isolated"
    return pincapture


@pytest.fixture
def toolbar(pc, tmp_path, monkeypatch):
    """A MainToolbar with no hotkeys, no notifications and a temporary save folder."""
    monkeypatch.setattr(pc, "save_config", lambda cfg: None)
    cfg = pc.load_config()
    cfg.update(save_dir=str(tmp_path / "captures"), notify=False, clipboard=False,
               hide_during_capture=False, show_viewer_after_capture=False,
               autosave=True, pin_autosave=True,
               hotkeys={"region": "", "window": "", "full": "", "pin": ""})
    tb = pc.MainToolbar(cfg, None)
    tb.history = []
    tb.populate()
    yield tb
    tb.hotkeys.stop()
    for p in list(tb._pins):
        p.close()
    box = getattr(tb, "_blocked_box", None)
    if box is not None:
        box.hide()
    tb.hide()
    spin(50)


# pytest's verdict, captured once the session has actually run.
# None means we never got that far (usage error, --help) and must exit normally.
_session = None


def pytest_sessionfinish(session, exitstatus):
    """Remember the session so pytest_unconfigure can leave with its final code.

    `exitstatus` is the value when this hook starts. The terminal reporter may
    still adjust `session.exitstatus` afterwards, so the hard exit reads that.
    """
    global _session
    _session = session
    del exitstatus


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    """Stop before Qt's C++ static destructors run.

    The summary is already printed: the terminal reporter writes it from a
    pytest_sessionfinish wrapper, and that hook finishes before unconfigure.
    A normal process exit then finalizes Python and libc runs Qt's static
    destructors. Those call back into shiboken (_PyErr_Fetch) and segfault.
    Every test has passed, but the process dies — Linux exit 139, and GitHub
    Actions' pwsh wrapper reports the Windows crash as exit code 1.

    os._exit keeps pytest's own code and skips atexit plus those destructors.
    Do not remove this. Real failures still propagate: the code is session.exitstatus.
    """
    del config
    if _session is None:
        return
    code = int(getattr(_session, "exitstatus", 0))
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
