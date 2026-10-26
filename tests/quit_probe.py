"""Helper for test_quit.py (runs in its own process because quitting ends the Qt event loop).

Shows the main window plus N pinned images, then calls MainToolbar.quit_app().
Prints EXITED if the event loop really ended, STUCK if the quit was ignored.
Before v0.6.0 quit_app() used QApplication.quit(), which Qt 6 cancels when the main window refuses to
close (it hides to the tray) and a pin window is still visible — leaving an invisible zombie process.
"""
import os
import sys
import tempfile

NPINS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PINCAP_NO_LOG"] = "1"
home = tempfile.mkdtemp(prefix="pincapture-quit-home-")
os.environ["USERPROFILE"] = os.environ["HOME"] = home
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.argv = [sys.argv[0]]

from PySide6.QtCore import QTimer               # noqa: E402
from PySide6.QtGui import QColor, QImage        # noqa: E402
from PySide6.QtWidgets import QApplication      # noqa: E402

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
import pincapture as pc                         # noqa: E402

sys.excepthook = sys.__excepthook__
pc.save_config = lambda c: None
cfg = pc.load_config()
cfg.update(hotkeys={"region": "", "window": "", "full": "", "pin": ""}, notify=False)
tb = pc.MainToolbar(cfg, None)
if tb._tray is None:            # offscreen has no tray: fake one so closeEvent refuses to close (the trigger)
    class _FakeTray:
        def hide(self):
            pass

        def showMessage(self, *a):
            pass
    tb._tray = _FakeTray()
tb.show()
for _ in range(NPINS):
    im = QImage(160, 90, QImage.Format.Format_RGB32)
    im.fill(QColor("orange"))
    tb._make_pin(im, None)
app.processEvents()


def stuck():
    print("STUCK", flush=True)
    os._exit(3)


QTimer.singleShot(300, tb.quit_app)
QTimer.singleShot(2500, stuck)
app.exec()
print("EXITED", flush=True)
os._exit(0)
