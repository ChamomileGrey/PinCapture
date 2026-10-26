"""v0.9.0 pin markup, eyedropper, and ruler. OCR stays on the unmarked original."""
from PySide6.QtCore import QEvent, QPoint, QPointF, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QKeyEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import QApplication

from conftest import spin


def _img(w, h, color):
    im = QImage(w, h, QImage.Format.Format_RGB32)
    im.fill(QColor(color))
    return im


def _rgb(image, x, y):
    c = QColor(image.pixel(x, y))
    return (c.red(), c.green(), c.blue())


def _changed(before, after):
    w, h = before.width(), before.height()
    for y in range(h):
        for x in range(w):
            if _rgb(before, x, y) != _rgb(after, x, y):
                return True
    return False


def _press(widget, pos, button=Qt.MouseButton.LeftButton):
    local = QPointF(pos)
    global_pos = QPointF(widget.mapToGlobal(QPoint(pos)))
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress, local, global_pos,
        button, button, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(widget, event)


def _move(widget, pos):
    local = QPointF(pos)
    global_pos = QPointF(widget.mapToGlobal(QPoint(pos)))
    event = QMouseEvent(
        QEvent.Type.MouseMove, local, global_pos,
        Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(widget, event)


def _release(widget, pos):
    local = QPointF(pos)
    global_pos = QPointF(widget.mapToGlobal(QPoint(pos)))
    event = QMouseEvent(
        QEvent.Type.MouseButtonRelease, local, global_pos,
        Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(widget, event)


def _key(widget, key, mods=Qt.KeyboardModifier.NoModifier):
    event = QKeyEvent(QEvent.Type.KeyPress, key, mods)
    QApplication.sendEvent(widget, event)


def test_compose_arrow_box_highlight_and_mosaic(pc):
    white = _img(48, 48, "white")
    arrow = pc.compose_marks(white, [pc.Mark("arrow", 4, 24, 44, 24, "#E23B3B", 4)])
    assert _changed(white, arrow)
    assert _rgb(white, 24, 24) == (255, 255, 255)

    box = pc.compose_marks(white, [pc.Mark("box", 8, 8, 40, 40, "#E23B3B", 6)])
    assert _rgb(box, 24, 24) == (255, 255, 255)
    assert _rgb(box, 8, 24) != (255, 255, 255)

    hi = pc.compose_marks(white, [pc.Mark("highlight", 4, 4, 40, 40, "#F5C518", 4)])
    r, g, b = _rgb(hi, 20, 20)
    assert (r, g, b) != (255, 255, 255)
    assert b < 230 and r > 200 and g > 180
    assert _rgb(hi, 0, 0) == (255, 255, 255)

    checker = QImage(32, 32, QImage.Format.Format_RGB32)
    for y in range(32):
        for x in range(32):
            checker.setPixel(x, y, QColor("red" if (x + y) % 2 == 0 else "blue").rgb())
    mosaic = pc.compose_marks(checker, [pc.Mark("mosaic", 0, 0, 31, 31, "#000000", 8)])
    assert _rgb(mosaic, 0, 0) == _rgb(mosaic, 1, 0)
    assert _changed(checker, mosaic)


def test_undo_restores_pixels_and_redo_puts_them_back(pc):
    pin = pc.PinWindow(_img(40, 40, "white"), dpr=1.0)
    try:
        pin.show()
        pin.begin_markup("box")
        pin._commit_mark(pc.Mark("box", 4, 4, 36, 36, "#E23B3B", 6))
        assert _rgb(pin.rendered_image(), 4, 20) != (255, 255, 255)
        assert pin.undo_mark() is True
        assert _rgb(pin.rendered_image(), 4, 20) == (255, 255, 255)
        assert pin.redo_mark() is True
        assert _rgb(pin.rendered_image(), 4, 20) != (255, 255, 255)
        assert pin.undo_mark() is True
        _key(pin, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
        assert _rgb(pin.rendered_image(), 4, 20) != (255, 255, 255)
    finally:
        pin.close()


def test_copy_composites_marks_but_ocr_uses_original(pc, monkeypatch):
    pin = pc.PinWindow(_img(36, 36, "white"), dpr=1.0)
    seen = {}

    def fake(image):
        seen["image"] = image.copy()
        return pc.OcrResult(True, "가나다", pc.OCR_COPIED_MSG)

    monkeypatch.setattr(pc, "recognize_image", fake)
    try:
        pin.show()
        pin._commit_mark(pc.Mark("highlight", 0, 0, 35, 35, "#F5C518", 4))
        pin.copy_ocr()
        assert _rgb(seen["image"], 10, 10) == _rgb(pin._img, 10, 10)
        assert _rgb(pin.image_for_export(), 10, 10) != _rgb(pin._img, 10, 10)
        menu, acts = pin.build_menu()
        pin.apply_menu_action(acts["copy"], acts)
        copied = QApplication.clipboard().image()
        assert not copied.isNull()
        assert _rgb(copied, 10, 10) != (255, 255, 255)
        menu.close()
    finally:
        pin.close()


def test_editing_draws_without_moving_and_escape_ends_edit(pc):
    pin = pc.PinWindow(_img(80, 60, "#4488cc"), dpr=2.0)
    try:
        pin.show()
        origin = pin.pos()
        assert pin.begin_markup("arrow") is True
        assert pin._bar is not None and pin._bar.isVisible()
        assert pin._bar.windowTitle() == "표시"
        pin._bar._tools["mosaic"].click()
        pin._bar._colors["#2F6BFF"].click()
        pin._bar._widths[2].click()
        assert pin._tool == "mosaic" and pin._color == "#2F6BFF" and pin._width_preset == 2
        pin._bar._tools["arrow"].click()
        assert pin._tool == "arrow"
        _press(pin, QPoint(4, 4))
        _move(pin, QPoint(30, 20))
        assert pin.pos() == origin
        assert pin._drag is None
        assert pin._draft is not None
        _release(pin, QPoint(30, 20))
        assert len(pin._marks) == 1
        assert pin._marks[0].kind == "arrow"
        _key(pin, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        assert pin._marks == []
        assert pin._editing is True
        _key(pin, Qt.Key.Key_Escape)
        assert pin._editing is False
        assert pin.isVisible()
        assert pin._bar is None
        _key(pin, Qt.Key.Key_Escape)
        assert not pin.isVisible()
    finally:
        pin.close()


def test_click_through_refuses_markup_and_menu_starts_tools(pc, toolbar):
    pin = toolbar._make_pin(_img(24, 24, "white"), None)
    pin.set_click_through(True)
    assert pin.begin_markup("mosaic") is False
    assert pin._editing is False
    assert pin._bar is None
    pin.set_click_through(False)
    menu, acts = pin.build_menu()
    assert acts["tools"]["arrow"].text() == "화살표"
    assert acts["tools"]["mosaic"].text() == "모자이크"
    assert acts["eyedropper"].text() == "스포이트"
    assert acts["ruler"].text() == "자"
    called = []
    pin.on_eyedropper = lambda: called.append("eye")
    pin.on_ruler = lambda: called.append("ruler")
    pin.apply_menu_action(acts["tools"]["highlight"], acts)
    assert pin._editing and pin._tool == "highlight"
    pin.set_click_through(True)
    assert pin._editing is False and pin._bar is None
    pin.set_click_through(False)
    pin.apply_menu_action(acts["eyedropper"], acts)
    pin.apply_menu_action(acts["ruler"], acts)
    pin.apply_menu_action(acts["mark_end"], acts)
    assert called == ["eye", "ruler"]
    assert pin._editing is False
    assert pin.isVisible()
    menu.close()


def test_markup_hotkey_needs_a_pin(pc, toolbar):
    toolbar._on_hotkey("markup")
    assert "없어요" in toolbar._last_notice
    pin = toolbar._make_pin(_img(20, 20, "white"), None)
    assert toolbar.start_pin_markup() is pin
    assert pin._editing is True


def test_physical_mapping_and_eyedropper_hex(pc, toolbar):
    assert pc.scale_percent(QSize(100, 50), QSize(200, 100)) == 200
    assert pc.physical_point(QSize(100, 50), QSize(200, 100), QPoint(20, 10)) == QPoint(40, 20)
    measured = pc.measure_pixels(QPoint(0, 0), QPoint(100, 50))
    assert measured == {"dx": 100, "dy": 50, "distance": 112}

    screen = QGuiApplication.primaryScreen()
    image = QImage(200, 100, QImage.Format.Format_RGB32)
    image.fill(QColor("#3366CC"))
    image.setPixel(40, 20, QColor("#FF8800").rgb())
    overlay = pc.InspectOverlay(screen, QPixmap.fromImage(image), "eyedropper")
    picked = []
    try:
        overlay.resize(100, 50)
        overlay.show()
        overlay.picked.connect(picked.append)
        _press(overlay, QPoint(20, 10))
        assert picked and picked[0]["hex"] == "#FF8800"
        assert picked[0]["rgb"] == "R 255  G 136  B 0"
        assert picked[0]["r"] == 255 and picked[0]["g"] == 136 and picked[0]["b"] == 0
    finally:
        overlay.close()

    QApplication.clipboard().clear()
    toolbar._was_visible = False
    toolbar._capturing = True
    toolbar._finish_inspect(picked[0])
    assert QApplication.clipboard().text() == "#FF8800"
    assert "#FF8800" in toolbar._last_notice and "255" in toolbar._last_notice
    assert toolbar._capturing is False


def test_ruler_uses_physical_pixels_at_2x(pc, toolbar):
    screen = QGuiApplication.primaryScreen()
    frozen = QPixmap(200, 100)
    frozen.fill(QColor("#224466"))
    overlay = pc.InspectOverlay(screen, frozen, "ruler")
    picked = []
    try:
        overlay.resize(100, 50)
        overlay.show()
        overlay.picked.connect(picked.append)
        _press(overlay, QPoint(0, 0))
        assert picked == []
        assert overlay._anchor == QPoint(0, 0)
        _move(overlay, QPoint(50, 25))
        _press(overlay, QPoint(50, 25))
        assert picked[0]["mode"] == "ruler"
        assert picked[0]["distance"] == 112
        assert picked[0]["dx"] == 100 and picked[0]["dy"] == 50
        assert picked[0]["scale"] == 200
    finally:
        overlay.close()

    toolbar._was_visible = False
    toolbar._capturing = True
    toolbar._finish_inspect(picked[0])
    assert "112px" in toolbar._last_notice
    assert "가로 100px" in toolbar._last_notice and "세로 50px" in toolbar._last_notice
    assert "200%" in toolbar._last_notice


def test_inspect_skips_overlay_when_capture_blocked(pc, toolbar, monkeypatch):
    black = QPixmap(8, 8)
    black.fill(QColor(0, 0, 0))
    monkeypatch.setattr(pc, "grab_screen_raw", lambda _screen: black)
    session = pc.ScreenInspectSession("eyedropper")
    got = {}
    session.blocked.connect(lambda: got.setdefault("blocked", True))
    session.finished.connect(lambda result: got.setdefault("result", result))
    session.start()
    spin(30)
    assert got.get("blocked") is True
    assert got.get("result") is None
    assert session._overlays == []

    seen = {}
    monkeypatch.setattr(toolbar, "_capture_blocked", lambda: seen.setdefault("blocked", True))
    toolbar._on_hotkey("ruler")
    spin(250)
    assert seen.get("blocked") is True
    assert toolbar._capturing is False


def test_new_hotkeys_default_without_clashing_old_config(pc, tmp_path, monkeypatch):
    assert pc.DEFAULTS["hotkeys"]["markup"] == "<ctrl>+<alt>+m"
    assert pc.DEFAULTS["hotkeys"]["eyedropper"] == "<ctrl>+<alt>+c"
    assert pc.DEFAULTS["hotkeys"]["ruler"] == "<ctrl>+<alt>+d"
    combos = [v for v in pc.DEFAULTS["hotkeys"].values() if v]
    assert len(combos) == len(set(combos))
    assert "<ctrl>+<alt>+e" not in combos

    path = tmp_path / "config.json"
    path.write_text('{"autosave": false, "hotkeys": {"region": "<ctrl>+<alt>+b"}}', encoding="utf-8")
    monkeypatch.setattr(pc, "CONFIG_PATH", path)
    cfg = pc.load_config()
    assert cfg["hotkeys"]["region"] == "<ctrl>+<alt>+b"
    assert cfg["hotkeys"]["markup"] == "<ctrl>+<alt>+m"
    assert cfg["hotkeys"]["eyedropper"] == "<ctrl>+<alt>+c"
    assert cfg["hotkeys"]["ruler"] == "<ctrl>+<alt>+d"
    assert cfg["hotkeys"]["reopen_pin"] == "<ctrl>+<alt>+r"

    dlg = pc.SettingsDialog(cfg, hotkey_ok=False)
    assert dlg.ed_hk["markup"].text() == "<ctrl>+<alt>+m"
    assert dlg.ed_hk["eyedropper"].text() == "<ctrl>+<alt>+c"
    assert dlg.ed_hk["ruler"].text() == "<ctrl>+<alt>+d"
    dlg.ed_hk["ruler"].setText("<ctrl>+<alt>+9")
    dlg._reset_hotkeys()
    assert dlg.ed_hk["ruler"].text() == "<ctrl>+<alt>+d"
    dlg.close()
