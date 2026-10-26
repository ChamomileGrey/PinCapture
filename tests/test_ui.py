"""v0.7.0 UI: welcome guide, About dialog, Ko-fi link, hotkey labels, config compatibility."""
import json

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from conftest import spin


def _blob(widget):
    return "\n".join(w.text() for w in widget.findChildren(QLabel))


def test_hotkey_label(pc):
    assert pc.hotkey_label("<ctrl>+<alt>+a") == "Ctrl+Alt+A"
    assert pc.hotkey_label("<ctrl>+<shift>+s") == "Ctrl+Shift+S"
    assert pc.hotkey_label("<print_screen>") == "PrintScreen"
    assert pc.hotkey_label("") == "없음"
    assert pc.hotkey_label("   ") == "없음"


def test_prepare_config_fresh_install_shows_welcome_later(pc, tmp_path, monkeypatch):
    cfg_dir = tmp_path / ".pincapture"
    path = cfg_dir / "config.json"
    monkeypatch.setattr(pc, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(pc, "CONFIG_PATH", path)
    cfg = pc.prepare_config()
    assert cfg["welcome_seen"] is False
    assert path.is_file()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["welcome_seen"] is False
    assert saved["hotkeys"]["region"] == "<ctrl>+<alt>+a"
    assert pc.should_auto_welcome(cfg, start_in_tray=False, tray_available=True) is True
    assert pc.should_auto_welcome(cfg, start_in_tray=True, tray_available=True) is False
    assert pc.should_auto_welcome(cfg, start_in_tray=True, tray_available=False) is True


def test_prepare_config_upgrade_does_not_nag(pc, tmp_path, monkeypatch):
    """0.6.x files have no welcome_seen. Treat them as people who already use the app."""
    cfg_dir = tmp_path / ".pincapture"
    cfg_dir.mkdir()
    path = cfg_dir / "config.json"
    path.write_text(json.dumps({
        "autosave": False,
        "filename_prefix": "샷",
        "hotkeys": {"region": "<ctrl>+<alt>+b"},
        "custom_future": {"keep": True},
    }, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(pc, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(pc, "CONFIG_PATH", path)
    cfg = pc.prepare_config()
    assert cfg["welcome_seen"] is True
    assert cfg["autosave"] is False
    assert cfg["filename_prefix"] == "샷"
    assert cfg["hotkeys"]["region"] == "<ctrl>+<alt>+b"
    assert cfg["hotkeys"]["window"] == "<ctrl>+<alt>+w"   # missing modes still get defaults
    assert cfg["custom_future"] == {"keep": True}
    assert pc.should_auto_welcome(cfg, start_in_tray=False, tray_available=False) is False
    again = json.loads(path.read_text(encoding="utf-8"))
    assert again["custom_future"] == {"keep": True}
    assert again["welcome_seen"] is True


def test_welcome_lists_hotkeys_and_pin_usage(pc):
    dlg = pc.WelcomeDialog(pc.DEFAULTS)
    blob = _blob(dlg)
    assert "Ctrl+Alt+A" in blob
    assert "Ctrl+Alt+W" in blob
    assert "Ctrl+Alt+F" in blob
    assert "Ctrl+Alt+Q" in blob
    assert "휠" in blob
    assert "핀" in blob
    buttons = [b.text() for b in dlg.findChildren(QPushButton)]
    assert "시작하기" in buttons
    assert "후원하기" not in buttons
    dlg.close()


def test_about_has_brand_license_and_kofi(pc, monkeypatch):
    opened = []

    def _open(url):
        opened.append(url.toString())
        return True

    monkeypatch.setattr(pc.QDesktopServices, "openUrl", _open)
    dlg = pc.AboutDialog()
    blob = _blob(dlg)
    assert pc.APP_VERSION in blob
    assert "캐모마일그레이" in blob
    assert "ChamomileGrey" in blob
    assert "All rights reserved" in blob
    assert "재배포" in blob
    buttons = {b.text(): b for b in dlg.findChildren(QPushButton)}
    assert "후원하기" in buttons
    assert "서드파티 고지 열기" in buttons
    buttons["후원하기"].click()
    assert opened == [pc.KOFI_URL]
    assert "knighft" not in pc.KOFI_URL.lower()
    buttons["서드파티 고지 열기"].click()
    assert opened[-1].endswith("THIRD_PARTY_NOTICES.txt")
    assert "knighft" not in opened[-1].lower()
    dlg.close()


def test_tray_menu_groups_and_donate(pc, toolbar, monkeypatch):
    opened = []
    monkeypatch.setattr(pc.QDesktopServices, "openUrl", lambda url: opened.append(url.toString()) or True)
    menu = toolbar._tray_menu()
    texts = [a.text() for a in menu.actions() if a.text()]
    assert texts[0] in ("창 열기", "창 숨기기")
    assert "후원하기" in texts
    assert "빠른 안내" in texts
    assert "정보" in texts
    assert "종료" in texts
    assert "창 보이기/숨기기" not in texts
    assert all("knighft" not in t.lower() for t in texts)
    for act in menu.actions():
        if act.text() == "후원하기":
            act.trigger()
    assert opened == [pc.KOFI_URL]
    menu.close()


def test_tooltips_follow_hotkeys(pc, toolbar):
    assert "없음" in toolbar.btn_region.toolTip()
    toolbar.cfg["hotkeys"] = dict(pc.DEFAULTS["hotkeys"])
    toolbar._update_tooltips()
    assert "Ctrl+Alt+A" in toolbar.btn_region.toolTip()
    assert "Ctrl+Alt+Q" in toolbar.btn_pin.toolTip()
    assert toolbar.btn_about.text() == "정보"
    assert toolbar.btn_help.text() == "안내"
    assert toolbar.b_copy.toolTip()
    assert toolbar.b_remove.text() == "목록에서 제거"


def test_show_welcome_marks_seen_without_a_second_popup(pc, toolbar, monkeypatch):
    saved = []
    monkeypatch.setattr(pc, "save_config", lambda cfg: saved.append(dict(cfg)))
    toolbar.cfg["welcome_seen"] = False
    QTimer.singleShot(0, lambda: QApplication.activeModalWidget().accept())
    toolbar.show_welcome()
    spin(20)
    assert toolbar.cfg["welcome_seen"] is True
    assert saved and saved[-1]["welcome_seen"] is True


def test_source_has_only_the_chamomilegrey_kofi_link():
    text = (pc_source()).lower()
    assert "ko-fi.com/chamomilegrey" in text
    assert "knighft" not in text


def pc_source():
    from pathlib import Path
    return Path(__file__).resolve().parent.parent.joinpath("pincapture.py").read_text(encoding="utf-8")
