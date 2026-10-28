"""OCR feedback stays on screen when Windows hides tray balloons.

Notices use PinToast. A tray balloon is optional and never the only feedback.
Tests stay on the isolated toolbar fixture and never signal a real running app.
"""
from PySide6.QtGui import QColor, QGuiApplication, QImage
from PySide6.QtWidgets import QApplication


def _img(w, h, color="white"):
    image = QImage(w, h, QImage.Format.Format_RGB32)
    image.fill(QColor(color))
    return image


class _Tray:
    """Stand-in for QSystemTrayIcon. Records showMessage and touches no real session."""

    def __init__(self):
        self.messages = []

    def showMessage(self, *args):
        self.messages.append(args)


def _ocr_mods(engine):
    class Lang:
        def __init__(self, tag):
            self.language_tag = tag

    class OcrEngine:
        @staticmethod
        def is_language_supported(lang):
            return True

        @staticmethod
        def try_create_from_language(lang):
            return engine

    class DataWriter:
        def write_bytes(self, data):
            self.data = data

        def detach_buffer(self):
            return getattr(self, "data", b"")

    class SoftwareBitmap:
        @staticmethod
        def create_copy_from_buffer(buf, fmt, w, h):
            return ("bitmap", w, h)

    return {
        "Language": Lang,
        "OcrEngine": OcrEngine,
        "BitmapPixelFormat": type("F", (), {"RGBA8": 28}),
        "SoftwareBitmap": SoftwareBitmap,
        "DataWriter": DataWriter,
    }


def test_notice_toast_shows_when_a_tray_exists(pc, toolbar):
    tray = _Tray()
    toolbar._tray = tray
    toolbar.cfg["notify"] = True
    toolbar.hide()
    assert not toolbar.isVisible()
    toolbar._show_notice("글자를 복사했어요.")
    toast = toolbar._notice_toast
    assert toast is not None and toast.isVisible()
    assert "복사했어요" in toast.label.text()
    assert tray.messages and "복사했어요" in tray.messages[0][1]
    screen = QGuiApplication.primaryScreen()
    if screen is not None:
        assert screen.availableGeometry().intersects(toast.frameGeometry())


def test_notice_without_notify_does_not_need_a_balloon(pc, toolbar):
    tray = _Tray()
    toolbar._tray = tray
    toolbar.cfg["notify"] = False
    toolbar._show_notice("글자를 복사했어요.")
    assert toolbar._notice_toast is not None and toolbar._notice_toast.isVisible()
    assert "복사했어요" in toolbar._notice_toast.label.text()
    assert tray.messages == []


def test_toast_follows_the_window_and_stays_on_screen_when_hidden(pc, toolbar):
    toolbar.show()
    toolbar._show_notice("창 위에서 보여요.")
    near = toolbar._notice_toast
    assert near.isVisible()
    window = toolbar.frameGeometry()
    assert abs(near.frameGeometry().center().x() - window.center().x()) <= max(window.width(), 1)
    toolbar.hide()
    toolbar._show_notice("창이 없어도 보여요.")
    toast = toolbar._notice_toast
    assert not toolbar.isVisible()
    assert toast.isVisible()
    assert "없어도" in toast.label.text()
    screen = QGuiApplication.primaryScreen()
    assert screen is not None
    assert screen.availableGeometry().intersects(toast.frameGeometry())


def test_ocr_click_toasts_the_result_even_with_a_tray(pc, toolbar, monkeypatch):
    seen = []

    def recognize(image):
        seen.append(toolbar._notice_toast.label.text())
        assert image.cacheKey()
        return pc.OcrResult(True, "가나다", pc.OCR_COPIED_MSG)

    monkeypatch.setattr(pc, "recognize_image", recognize)
    tray = _Tray()
    toolbar._tray = tray
    toolbar.cfg["notify"] = True
    red = _img(32, 16, "red")
    toolbar.history = [pc.HistoryEntry(image=red)]
    toolbar.populate()
    QApplication.clipboard().clear()
    toolbar.btn_ocr.click()
    assert seen == [pc.OCR_BUSY_MSG]
    assert QApplication.clipboard().text() == "가나다"
    assert toolbar._notice_toast.label.text() == pc.OCR_COPIED_MSG
    assert toolbar._notice_toast.isVisible()
    assert any(pc.OCR_COPIED_MSG in message[1] for message in tray.messages)
    assert all(pc.OCR_BUSY_MSG not in message[1] for message in tray.messages)


def test_ocr_click_toasts_empty_and_errors(pc, toolbar, monkeypatch, capsys):
    tray = _Tray()
    toolbar._tray = tray
    toolbar.cfg["notify"] = True
    red = _img(32, 16, "red")
    toolbar.history = [pc.HistoryEntry(image=red)]
    toolbar.populate()

    monkeypatch.setattr(
        pc, "recognize_image",
        lambda image: pc.OcrResult(False, "", pc.OCR_EMPTY_MSG))
    toolbar.btn_ocr.click()
    assert toolbar._notice_toast.label.text() == pc.OCR_EMPTY_MSG
    assert toolbar._notice_toast.isVisible()

    def boom(image):
        raise OSError("WinRT RoGetActivationFactory failed")

    monkeypatch.setattr(pc, "recognize_image", boom)
    QApplication.clipboard().clear()
    toolbar.btn_ocr.click()
    assert toolbar._notice_toast.label.text() == pc.OCR_FAILED_MSG
    assert toolbar._notice_toast.isVisible()
    assert QApplication.clipboard().text() == ""
    err = capsys.readouterr().err
    assert "OSError" in err and "RoGetActivationFactory" in err


def test_ocr_click_without_a_target_toasts_with_a_tray(pc, toolbar):
    tray = _Tray()
    toolbar._tray = tray
    toolbar.cfg["notify"] = True
    assert toolbar.btn_ocr.isEnabled()
    toolbar.btn_ocr.click()
    assert toolbar._notice_toast is not None and toolbar._notice_toast.isVisible()
    assert "없어요" in toolbar._notice_toast.label.text()
    assert any("없어요" in message[1] for message in tray.messages)


def test_pin_copy_ocr_toasts_busy_then_result_and_logs_errors(pc, toolbar, monkeypatch, capsys):
    pin = toolbar._make_pin(_img(24, 16, "white"), None)
    seen = []

    def recognize(image):
        seen.append(pin._toast.label.text())
        return pc.OcrResult(True, "가나다", pc.OCR_COPIED_MSG)

    monkeypatch.setattr(pc, "recognize_image", recognize)
    QApplication.clipboard().clear()
    result = pin.copy_ocr()
    assert result.ok and result.message == pc.OCR_COPIED_MSG
    assert seen == [pc.OCR_BUSY_MSG]
    assert pin._toast.label.text() == pc.OCR_COPIED_MSG
    assert QApplication.clipboard().text() == "가나다"

    def boom(image):
        seen.append(pin._toast.label.text())
        raise OSError("frozen WinRT OCR")

    monkeypatch.setattr(pc, "recognize_image", boom)
    failed = pin.copy_ocr()
    assert not failed.ok and failed.message == pc.OCR_FAILED_MSG
    assert pin._toast.isVisible()
    assert pin._toast.label.text() == pc.OCR_FAILED_MSG
    assert seen[-1] == pc.OCR_BUSY_MSG
    err = capsys.readouterr().err
    assert "frozen WinRT OCR" in err


def test_pin_math_shows_busy_before_the_result(pc, toolbar, monkeypatch):
    pin = toolbar._make_pin(_img(20, 12, "white"), None)
    monkeypatch.setattr(pc, "math_status", lambda: "ok")

    def predict(image):
        assert pin._toast.label.text() == pc.OCR_BUSY_MSG
        return r"\frac{1}{2}"

    monkeypatch.setattr(pc, "predict_latex", predict)
    QApplication.clipboard().clear()
    result = pin.copy_ocr("math")
    assert result.ok
    assert QApplication.clipboard().text() == r"\frac{1}{2}"
    assert "LaTeX" in pin._toast.label.text()


def test_missing_ocr_module_is_logged(pc, monkeypatch, capsys):
    def boom():
        raise OSError("WinRT RoGetActivationFactory failed")

    monkeypatch.setattr(pc, "_import_ocr_modules", boom)
    result = pc.recognize_image(_img(16, 16))
    assert not result.ok and result.message == pc.OCR_UNAVAILABLE_MSG
    err = capsys.readouterr().err
    assert "OSError" in err and "RoGetActivationFactory" in err


def test_unfinished_winrt_async_is_not_reported_as_empty(pc, monkeypatch, capsys):
    class IAsyncOperation:
        pass

    class Engine:
        def recognize_async(self, bitmap):
            return IAsyncOperation()

    monkeypatch.setattr(pc, "_import_ocr_modules", lambda: _ocr_mods(Engine()))
    result = pc.recognize_image(_img(48, 48))
    assert not result.ok
    assert result.message == pc.OCR_FAILED_MSG
    assert result.message != pc.OCR_EMPTY_MSG
    err = capsys.readouterr().err
    assert "IAsyncOperation" in err
    assert "RuntimeError" in err
