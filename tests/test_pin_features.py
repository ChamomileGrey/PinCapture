"""v0.8.0 pin tools: OCR copy (mocked Windows OCR), opacity, click-through, reopen recent pins."""
import json

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QWheelEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from conftest import spin


def _img(w, h, color):
    im = QImage(w, h, QImage.Format.Format_RGB32)
    im.fill(QColor(color))
    return im


def _wheel(pin, delta, ctrl=False):
    mods = Qt.KeyboardModifier.ControlModifier if ctrl else Qt.KeyboardModifier.NoModifier
    ev = QWheelEvent(
        QPointF(4, 4), QPointF(pin.mapToGlobal(QPoint(4, 4))),
        QPoint(0, 0), QPoint(0, delta),
        Qt.MouseButton.NoButton, mods, Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(pin, ev)


class _Lang:
    def __init__(self, tag):
        self.language_tag = tag


class _Engine:
    def __init__(self, text):
        self._text = text

    async def recognize_async(self, bitmap):
        self.bitmap = bitmap

        class _Result:
            pass

        result = _Result()
        result.text = self._text
        return result


def _install_fake_ocr(monkeypatch, pc, *, text="안녕 Hello", supported=None):
    """supported: language tag -> bool. Default: Korean yes, anything else no."""
    if supported is None:
        supported = lambda tag: tag.lower().startswith("ko")
    created = {}

    class OcrEngine:
        @staticmethod
        def is_language_supported(lang):
            return bool(supported(lang.language_tag))

        @staticmethod
        def try_create_from_language(lang):
            if not OcrEngine.is_language_supported(lang):
                return None
            created["tag"] = lang.language_tag
            engine = _Engine(text)
            created["engine"] = engine
            return engine

        @staticmethod
        def try_create_from_user_profile_languages():
            created["profile"] = True
            return None

    class BitmapPixelFormat:
        RGBA8 = 28

    class SoftwareBitmap:
        @staticmethod
        def create_copy_from_buffer(buf, fmt, w, h):
            return ("bitmap", len(buf), w, h, fmt)

    class DataWriter:
        def write_bytes(self, data):
            self.data = bytes(data)

        def detach_buffer(self):
            return self.data

    monkeypatch.setattr(pc, "_import_ocr_modules", lambda: {
        "Language": _Lang,
        "OcrEngine": OcrEngine,
        "BitmapPixelFormat": BitmapPixelFormat,
        "SoftwareBitmap": SoftwareBitmap,
        "DataWriter": DataWriter,
    })
    return created


def test_recognize_image_prefers_korean_and_returns_text(pc, monkeypatch):
    created = _install_fake_ocr(monkeypatch, pc, text="안녕 Hello")
    result = pc.recognize_image(_img(48, 48, "white"))
    assert result.ok and result.text == "안녕 Hello"
    assert result.message == pc.OCR_COPIED_MSG
    assert created["tag"].lower().startswith("ko")
    kind, nbytes, w, h, fmt = created["engine"].bitmap
    assert kind == "bitmap" and w == 48 and h == 48 and nbytes == 48 * 48 * 4 and fmt == 28


def test_recognize_image_falls_back_to_english(pc, monkeypatch):
    created = _install_fake_ocr(
        monkeypatch, pc, text="Hello",
        supported=lambda tag: tag.lower().startswith("en"))
    result = pc.recognize_image(_img(48, 40, "white"))
    assert result.ok and result.text == "Hello"
    assert created["tag"].lower().startswith("en")


def test_recognize_image_reports_missing_module(pc, monkeypatch):
    def boom():
        raise ImportError("winrt is not installed")

    monkeypatch.setattr(pc, "_import_ocr_modules", boom)
    result = pc.recognize_image(_img(48, 48, "white"))
    assert not result.ok and result.text == ""
    assert "OCR" in result.message and "한국어" in result.message


def test_recognize_image_reports_missing_language_pack(pc, monkeypatch):
    _install_fake_ocr(monkeypatch, pc, supported=lambda tag: False)
    result = pc.recognize_image(_img(48, 48, "white"))
    assert not result.ok
    assert "언어 팩" in result.message


def test_recognize_image_empty_text(pc, monkeypatch):
    _install_fake_ocr(monkeypatch, pc, text="   ")
    result = pc.recognize_image(_img(48, 48, "white"))
    assert not result.ok and result.message == pc.OCR_EMPTY_MSG


def test_pin_menu_ocr_copies_text_and_toasts(pc, toolbar, monkeypatch):
    monkeypatch.setattr(
        pc, "recognize_image",
        lambda img: pc.OcrResult(True, "가나다", pc.OCR_COPIED_MSG))
    pin = toolbar._make_pin(_img(40, 24, "white"), None)
    menu, acts = pin.build_menu()
    assert acts["ocr_menu"].title() == "글자 복사"
    assert [acts["ocr_modes"][mode].text() for mode, _label in pc.OCR_MODE_ACTIONS] == [
        label for _mode, label in pc.OCR_MODE_ACTIONS]
    assert [acts["opacity"][p].text() for p in (100, 80, 60, 40)] == ["100%", "80%", "60%", "40%"]
    assert acts["click"].text() == "클릭 통과"
    QApplication.clipboard().clear()
    pin.apply_menu_action(acts["ocr"], acts)
    assert QApplication.clipboard().text() == "가나다"
    assert pin._toast is not None and "복사했어요" in pin._toast.label.text()
    menu.close()


def test_opacity_steps_menu_and_ctrl_wheel(pc, toolbar):
    pin = toolbar._make_pin(_img(30, 30, "blue"), None)
    assert pin.opacity_percent == 100
    pin.set_opacity(80)
    assert pin.opacity_percent == 80
    assert abs(pin.windowOpacity() - 0.8) < 0.02
    scale = pin._scale
    _wheel(pin, -120, ctrl=True)
    assert pin.opacity_percent == 60 and pin._scale == scale
    _wheel(pin, 120, ctrl=True)
    assert pin.opacity_percent == 80
    _wheel(pin, 120, ctrl=False)
    assert pin.opacity_percent == 80 and pin._scale > scale
    menu, acts = pin.build_menu()
    assert acts["opacity"][80].isChecked()
    pin.apply_menu_action(acts["opacity"][40], acts)
    assert pin.opacity_percent == 40
    menu.close()


def test_click_through_released_by_hotkey_not_by_the_pin(pc, toolbar):
    toolbar.cfg["hotkeys"]["clickthrough"] = "<ctrl>+<alt>+x"
    pin = toolbar._make_pin(_img(30, 30, "red"), QPoint(15, 15))
    pin.show()
    spin(20)
    pin.set_click_through(True)
    assert pin.click_through
    assert pin.windowFlags() & Qt.WindowType.WindowTransparentForInput
    assert pin._toast is not None and "클릭 통과" in pin._toast.label.text()
    # The pin no longer receives clicks, so release goes through the global action.
    assert toolbar.clear_click_through() == 1
    assert not pin.click_through
    assert not (pin.windowFlags() & Qt.WindowType.WindowTransparentForInput)
    pin.set_click_through(True)
    toolbar._on_hotkey("clickthrough")
    assert not pin.click_through
    assert toolbar.clear_click_through() == 0


def test_reopen_recent_pin_restores_geometry_and_drops_oldest(pc, toolbar):
    colors = ["red", "green", "blue", "yellow", "cyan", "magenta",
              "gray", "orange", "purple", "brown", "pink", "navy"]
    for i, color in enumerate(colors):
        pin = toolbar._make_pin(_img(48, 32, color), QPoint(10 + i, 20 + i))
        pin._scale = 1.5
        pin._apply_size()
        pin.set_opacity(60)
        pin.close()
        spin(10)
    assert toolbar._pins == []
    assert toolbar._recent.count() == 10
    pngs = list(toolbar._recent.directory.glob("*.png"))
    assert len(pngs) == 10

    again = toolbar.reopen_recent_pin()
    assert again is not None and len(toolbar._pins) == 1
    assert again.opacity_percent == 60
    assert abs(again._scale - 1.5) < 0.01
    assert again.x() == 10 + 11 and again.y() == 20 + 11
    assert again._img.pixelColor(0, 0) == QColor("navy")
    assert toolbar._recent.count() == 9

    # Survives a new store reading the temp folder (app restart).
    restored = pc.RecentPinStore(limit=10, directory=toolbar._recent.directory)
    assert restored.count() == 9
    toolbar._on_hotkey("reopen_pin")
    assert len(toolbar._pins) == 2
    while toolbar._recent.count():
        assert toolbar.reopen_recent_pin() is not None
    assert toolbar.reopen_recent_pin() is None
    assert "없어요" in toolbar._last_notice


def test_default_hotkeys_do_not_collide_and_first_wins(pc):
    combos = [v for v in pc.DEFAULTS["hotkeys"].values() if v]
    assert len(combos) == len(set(combos))
    assert pc.DEFAULTS["hotkeys"]["reopen_pin"] == "<ctrl>+<alt>+r"
    assert pc.DEFAULTS["hotkeys"]["clickthrough"] == "<ctrl>+<alt>+x"
    assert pc.DEFAULTS["recent_pin_limit"] == 10
    kept = dict(pc.iter_hotkey_bindings({
        "region": "<ctrl>+<alt>+r",
        "reopen_pin": "<ctrl>+<alt>+r",
        "pin": "",
    }))
    assert kept == {"region": "<ctrl>+<alt>+r"}


def test_old_config_keeps_working_and_gains_defaults(pc, tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "autosave": False,
        "filename_prefix": "예전",
        "hotkeys": {"region": "<ctrl>+<alt>+b"},
    }), encoding="utf-8")
    monkeypatch.setattr(pc, "CONFIG_PATH", path)
    cfg = pc.load_config()
    assert cfg["autosave"] is False
    assert cfg["filename_prefix"] == "예전"
    assert cfg["clipboard"] is True
    assert cfg["hotkeys"]["region"] == "<ctrl>+<alt>+b"
    assert cfg["hotkeys"]["window"] == pc.DEFAULTS["hotkeys"]["window"]
    assert cfg["hotkeys"]["reopen_pin"] == "<ctrl>+<alt>+r"
    assert cfg["hotkeys"]["clickthrough"] == "<ctrl>+<alt>+x"
    assert cfg["hotkeys"]["markup"] == "<ctrl>+<alt>+m"
    assert cfg["hotkeys"]["eyedropper"] == "<ctrl>+<alt>+c"
    assert cfg["hotkeys"]["ruler"] == "<ctrl>+<alt>+d"
    assert cfg["recent_pin_limit"] == 10


def test_settings_saves_new_fields_and_rejects_clashes(pc, monkeypatch):
    cfg = pc.load_config()
    dlg = pc.SettingsDialog(cfg, hotkey_ok=False)
    assert dlg.ed_hk["reopen_pin"].text() == "<ctrl>+<alt>+r"
    assert dlg.ed_hk["clickthrough"].text() == "<ctrl>+<alt>+x"
    assert dlg.sp_recent.value() == 10
    dlg.ed_hk["reopen_pin"].setText("<ctrl>+<alt>+e")
    dlg.sp_recent.setValue(4)
    dlg._accept()
    assert cfg["hotkeys"]["reopen_pin"] == "<ctrl>+<alt>+e"
    assert cfg["recent_pin_limit"] == 4
    dlg.close()

    dlg2 = pc.SettingsDialog(cfg, hotkey_ok=False)
    dlg2.ed_hk["clickthrough"].setText("<ctrl>+<alt>+e")
    warned = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warned.append(a))
    dlg2._accept()
    assert warned and "겹" in warned[0][2]
    assert cfg["hotkeys"]["clickthrough"] == "<ctrl>+<alt>+x"
    dlg2.close()


def test_tray_menu_exposes_reopen_and_click_through(pc, toolbar):
    if toolbar._tray is None:
        toolbar._build_tray()
    labels = [a.text() for a in toolbar._tray.contextMenu().actions() if a.text()]
    assert "최근 핀 다시 열기" in labels
    assert "클릭 통과 해제" in labels
