"""v0.6.1: when security software makes every screen grab pure black (e.g. a government-site
document viewer's 'screen capture protection'), PinCapture must not cover the monitors with a black
overlay or save black files — it explains the cause instead."""
import glob

from PySide6.QtGui import QColor, QGuiApplication, QImage, QPixmap

from conftest import spin


def _pixmap(screen, color):
    g = screen.geometry()
    pm = QPixmap(g.width(), g.height())
    pm.fill(color)
    return pm


def _visible_overlays(pc):
    from PySide6.QtWidgets import QApplication
    return [w for w in QApplication.topLevelWidgets() if isinstance(w, pc.SelectionOverlay) and w.isVisible()]


# ---------- detector ----------

def test_pure_black_detected(pc):
    img = QImage(2560, 1440, QImage.Format.Format_RGB32)
    img.fill(QColor(0, 0, 0))
    assert pc.is_pure_black(img)
    assert pc.is_pure_black(QPixmap.fromImage(img))


def test_single_non_black_pixel_is_not_black(pc):
    img = QImage(800, 600, QImage.Format.Format_RGB32)
    img.fill(QColor(0, 0, 0))
    img.setPixelColor(400, 300, QColor(1, 0, 0))
    assert not pc.is_pure_black(img)


def test_format_independent_and_null_safe(pc):
    argb = QImage(64, 64, QImage.Format.Format_ARGB32_Premultiplied)
    argb.fill(QColor(0, 0, 0, 255))
    assert pc.is_pure_black(argb)
    assert not pc.is_pure_black(None)
    assert not pc.is_pure_black(QImage())


def test_blocked_only_when_every_screen_is_black(pc):
    black, gray = QPixmap(10, 10), QPixmap(10, 10)
    black.fill(QColor(0, 0, 0))
    gray.fill(QColor(90, 90, 90))
    assert pc.screens_capture_blocked([black, black])
    assert not pc.screens_capture_blocked([black, gray])
    assert not pc.screens_capture_blocked([])


# ---------- app flows ----------

def test_blocked_region_pin_full_show_explanation_not_black_screen(pc, toolbar, monkeypatch):
    monkeypatch.setattr(pc, "grab_screen_raw", lambda s: _pixmap(s, QColor(0, 0, 0)))
    for mode in ("region", "pin", "full"):
        before = len(toolbar.history)
        toolbar.capture(mode)
        spin(500)
        assert not _visible_overlays(pc), f"{mode}: black overlay was shown"
        assert len(toolbar.history) == before, f"{mode}: a black capture was kept"
        assert not glob.glob(toolbar.cfg["save_dir"] + "/*"), f"{mode}: a black file was saved"
        assert toolbar._capturing is False and toolbar._session is None
        assert toolbar._blocked_box is not None and toolbar._blocked_box.isVisible()
        toolbar._blocked_box.hide()


def test_blocked_window_capture(pc, toolbar, monkeypatch):
    primary = QGuiApplication.primaryScreen()
    monkeypatch.setattr(pc, "grab_screen_raw", lambda s: _pixmap(s, QColor(0, 0, 0)))
    monkeypatch.setattr(pc, "capture_active_window", lambda ex, fb=None: _pixmap(primary, QColor(0, 0, 0)).toImage())
    toolbar.capture("window")
    spin(500)
    assert len(toolbar.history) == 0
    assert toolbar._blocked_box.isVisible()


def test_genuinely_black_window_is_still_captured(pc, toolbar, monkeypatch):
    primary = QGuiApplication.primaryScreen()
    monkeypatch.setattr(pc, "grab_screen_raw", lambda s: _pixmap(s, QColor(30, 60, 90)))
    monkeypatch.setattr(pc, "capture_active_window", lambda ex, fb=None: _pixmap(primary, QColor(0, 0, 0)).toImage())
    toolbar.capture("window")
    spin(500)
    assert len(toolbar.history) == 1


def test_explanation_points_to_the_viewer_not_a_restart(pc, toolbar, monkeypatch):
    """Restarting PinCapture does not help while the blocker's injector runs (new processes get the hook
    within seconds), so the dialog must not offer it; the first step is closing the protected viewer."""
    called = []
    monkeypatch.setattr(toolbar, "restart_app", lambda: called.append(True))
    toolbar._capture_blocked()
    box = toolbar._blocked_box
    assert all("다시 시작" not in b.text() for b in box.buttons())
    assert "전자문서" in box.text() and "닫" in box.text()
    box.button(box.StandardButton.Ok).click()
    spin(50)
    assert called == [] and not box.isVisible()


def test_normal_captures_unaffected(pc, toolbar, monkeypatch):
    monkeypatch.setattr(pc, "grab_screen_raw", lambda s: _pixmap(s, QColor(120, 130, 140)))
    toolbar.capture("full")
    spin(500)
    assert len(toolbar.history) == 1
    assert len(glob.glob(toolbar.cfg["save_dir"] + "/*.png")) == 1
    toolbar.capture("region")
    spin(500)
    overlays = _visible_overlays(pc)
    assert len(overlays) == len(QGuiApplication.screens())
    for o in overlays:
        o.canceled.emit()
    spin(200)
    assert toolbar._capturing is False
