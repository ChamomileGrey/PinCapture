"""History pane (보관함): multi-select copy / save / pin / remove (v0.5.3)."""
import os
import pathlib

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from conftest import spin


def _img(w, h, color):
    im = QImage(w, h, QImage.Format.Format_RGB32)
    im.fill(QColor(color))
    return im


def _setup(pc, toolbar, tmp_path):
    save = pathlib.Path(toolbar.cfg["save_dir"])
    save.mkdir(parents=True, exist_ok=True)
    for i, c in enumerate(["red", "green", "blue"]):
        f = save / f"캡처_2026102{i}_120000.png"
        _img(300 + i * 10, 200, c).save(str(f), "PNG")
        os.utime(f, (1e9 + i, 1e9 + i))
    toolbar.history = []
    toolbar._scan_existing_files()
    toolbar.history.insert(0, pc.HistoryEntry(image=_img(400, 240, "yellow")))   # unsaved, in memory
    toolbar.populate()
    toolbar.show()
    spin(50)
    return save


def test_multi_select_actions(pc, toolbar, tmp_path, monkeypatch):
    _setup(pc, toolbar, tmp_path)
    L = toolbar.listw
    assert L.count() == 4 and toolbar._selected_rows() == [0]

    L.clearSelection()
    L.item(0).setSelected(True)
    L.item(2).setSelected(True)
    spin(20)
    assert toolbar._selected_rows() == [0, 2]
    assert "2개 선택" in toolbar.info.text()
    assert toolbar.b_remove.text() == "목록에서 제거 (2)"

    toolbar._copy_selected()
    md = QApplication.clipboard().mimeData()
    urls = [u.toLocalFile() for u in md.urls()]
    assert len(urls) == 2 and all(pathlib.Path(u).exists() for u in urls)
    assert md.hasImage()

    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(out)))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    toolbar._save_selected_as()
    assert len(list(out.iterdir())) == 2

    toolbar._pin_selected()
    spin(20)
    assert len(toolbar._pins) == 2
    assert len({(p.x(), p.y()) for p in toolbar._pins}) == 2       # cascaded, not stacked

    toolbar._remove_selected()
    spin(20)
    assert len(toolbar.history) == 2 and L.count() == 2
    assert toolbar._selected_rows() == [0]


def test_keyboard_shortcuts(pc, toolbar, tmp_path):
    _setup(pc, toolbar, tmp_path)
    L = toolbar.listw
    toolbar.activateWindow()
    L.setFocus()
    QTest.keyClick(L, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    assert len(toolbar._selected_rows()) == 4
    QApplication.clipboard().clear()
    QTest.keyClick(L, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    md = QApplication.clipboard().mimeData()
    assert md.hasUrls() and len(md.urls()) == 4                      # files, not item text
    QTest.keyClick(L, Qt.Key.Key_Delete)
    assert L.count() == 0 and not toolbar.history
    assert "아직 캡처가 없어요" in toolbar.info.text()
