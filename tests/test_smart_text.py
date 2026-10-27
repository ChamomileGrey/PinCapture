"""v0.10.0 smart text: paragraph joining, table TSV/Markdown, optional offline math."""
import urllib.request

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication


def _img(w, h, color="white"):
    im = QImage(w, h, QImage.Format.Format_RGB32)
    im.fill(QColor(color))
    return im


def _w(text, x, y, w, h=18):
    return text, x, y, w, h


def _boxes(pc, specs, h=18):
    return [pc.OcrBox(text, x, y, w, h) for text, x, y, w in specs]


def test_english_hard_wrap_joins_and_blank_line_keeps_paragraphs(pc):
    words = _boxes(pc, [
        ("This", 0, 0, 40), ("is", 48, 0, 20), ("a", 76, 0, 14),
        ("long", 98, 0, 40), ("sentence", 146, 0, 70), ("that", 224, 0, 40),
        ("wraps", 272, 0, 50),
        ("across", 0, 24, 60), ("several", 68, 24, 60), ("visual", 136, 24, 50),
        ("lines", 194, 24, 40), ("because", 242, 24, 70),
        ("the", 0, 48, 30), ("column", 38, 48, 60), ("is", 106, 48, 20),
        ("narrow.", 134, 48, 70),
        ("A", 0, 96, 16), ("second", 24, 96, 60), ("paragraph", 92, 96, 90),
        ("starts", 190, 96, 50), ("here.", 248, 96, 40),
    ])
    text = pc.reconstruct_paragraphs(words)
    assert text == (
        "This is a long sentence that wraps across several visual lines because the column is narrow.\n\n"
        "A second paragraph starts here."
    )


def test_english_hyphenation_on_a_full_line_is_removed(pc):
    lines = [
        pc.OcrBox("The reconstruc-", 0, 0, 280, 20),
        pc.OcrBox("tion works well.", 0, 24, 160, 20),
    ]
    assert pc.join_paragraphs(lines) == "The reconstruction works well."


def test_short_english_sentences_stay_separate_paragraphs(pc):
    lines = [
        pc.OcrBox("Hello world.", 0, 0, 110, 20),
        pc.OcrBox("Next paragraph.", 0, 24, 150, 20),
    ]
    assert pc.join_paragraphs(lines) == "Hello world.\n\nNext paragraph."


def test_korean_word_wrap_keeps_spaces_and_paragraph_gap(pc):
    words = _boxes(pc, [
        ("오늘", 0, 0, 40), ("날씨가", 48, 0, 60), ("맑아서", 116, 0, 60), ("산에", 184, 0, 40),
        ("갔다.", 0, 22, 50),
        ("내일", 0, 70, 40), ("다시", 48, 70, 40), ("오자.", 96, 70, 50),
    ])
    assert pc.reconstruct_paragraphs(words) == "오늘 날씨가 맑아서 산에 갔다.\n\n내일 다시 오자."


def test_korean_syllable_cut_at_the_right_edge_joins_without_a_space(pc):
    words = _boxes(pc, [
        ("변수", 0, 0, 40), ("값", 48, 0, 20),
        ("이", 0, 22, 20), ("크다.", 28, 22, 50),
    ])
    assert pc.reconstruct_paragraphs(words) == "변수 값이 크다."


def test_mixed_korean_and_english_keeps_a_space_between_scripts(pc):
    lines = [
        pc.OcrBox("Status OK", 0, 0, 200, 20),
        pc.OcrBox("좋아요", 0, 24, 80, 20),
    ]
    assert pc.join_paragraphs(lines) == "Status OK 좋아요"


def test_two_columns_are_read_left_then_right(pc):
    words = _boxes(pc, [
        ("Left", 0, 0, 40), ("one", 48, 0, 40),
        ("Right", 320, 0, 50), ("one", 378, 0, 40),
        ("Left", 0, 24, 40), ("two", 48, 24, 40),
        ("Right", 320, 24, 50), ("two", 378, 24, 40),
    ])
    assert pc.reconstruct_paragraphs(words) == "Left one Left two\n\nRight one Right two"


def test_table_tsv_aligns_columns_and_keeps_multiword_cells(pc):
    words = _boxes(pc, [
        ("Name", 0, 0, 40), ("Age", 120, 0, 30), ("City", 240, 0, 40),
        ("Kim", 0, 30, 30), ("31", 120, 30, 20), ("Seoul", 240, 30, 50),
        ("Lee", 0, 60, 30), ("28", 120, 60, 20), ("Busan", 240, 60, 50),
        ("New", 0, 100, 36), ("York", 42, 100, 40), ("100", 200, 100, 30),
        ("Paris", 0, 128, 50), ("200", 200, 128, 30),
    ], h=16)
    # The last two rows are a second table stacked under the first. They share columns
    # only when the gap threshold splits "New"+"York" from the number.
    grid = pc.table_from_words(words[:9])
    assert grid == [
        ["Name", "Age", "City"],
        ["Kim", "31", "Seoul"],
        ["Lee", "28", "Busan"],
    ]
    assert pc.grid_to_tsv(grid) == "Name\tAge\tCity\nKim\t31\tSeoul\nLee\t28\tBusan"
    md = pc.grid_to_markdown(grid)
    assert md.splitlines()[0] == "| Name | Age | City |"
    assert md.splitlines()[1] == "| --- | --- | --- |"
    assert md.splitlines()[2] == "| Kim | 31 | Seoul |"

    pair = pc.table_from_words(words[9:])
    assert pair == [["New York", "100"], ["Paris", "200"]]
    assert pc.grid_to_tsv(pair) == "New York\t100\nParis\t200"
    assert pc.grid_to_markdown([["a|b", "c"]]).splitlines()[0] == "| a\\|b | c |"


def test_recognize_image_uses_word_boxes_for_paragraphs(pc, monkeypatch):
    class Rect:
        def __init__(self, x, y, w, h):
            self.x, self.y, self.width, self.height = x, y, w, h

    class Word:
        def __init__(self, text, x, y, w, h):
            self.text = text
            self.bounding_rect = Rect(x, y, w, h)

    class Line:
        def __init__(self, words):
            self.words = words
            self.text = " ".join(w.text for w in words)

    class Engine:
        async def recognize_async(self, bitmap):
            class Result:
                pass
            result = Result()
            line1 = Line([Word("Hello", 0, 0, 50, 18), Word("wraps", 58, 0, 50, 18)])
            line2 = Line([Word("here.", 0, 22, 40, 18)])
            line3 = Line([Word("Next.", 0, 70, 40, 18)])
            result.lines = [line1, line2, line3]
            result.text = "Hello wraps\nhere.\nNext."
            return result

    class Lang:
        def __init__(self, tag):
            self.language_tag = tag

    class OcrEngine:
        @staticmethod
        def is_language_supported(lang):
            return True

        @staticmethod
        def try_create_from_language(lang):
            return Engine()

    monkeypatch.setattr(pc, "_import_ocr_modules", lambda: {
        "Language": Lang,
        "OcrEngine": OcrEngine,
        "BitmapPixelFormat": type("F", (), {"RGBA8": 28}),
        "SoftwareBitmap": type("B", (), {"create_copy_from_buffer": staticmethod(
            lambda buf, fmt, w, h: ("bitmap", w, h))}),
        "DataWriter": type("D", (), {
            "write_bytes": lambda self, data: None,
            "detach_buffer": lambda self: b"",
        }),
    })
    # DataWriter is instantiated. Provide a real class.
    class DataWriter:
        def write_bytes(self, data):
            self.data = data

        def detach_buffer(self):
            return b""

    class SoftwareBitmap:
        @staticmethod
        def create_copy_from_buffer(buf, fmt, w, h):
            return ("bitmap", w, h)

    monkeypatch.setattr(pc, "_import_ocr_modules", lambda: {
        "Language": Lang,
        "OcrEngine": OcrEngine,
        "BitmapPixelFormat": type("F", (), {"RGBA8": 28}),
        "SoftwareBitmap": SoftwareBitmap,
        "DataWriter": DataWriter,
    })
    result = pc.recognize_image(_img(80, 40), "text")
    assert result.ok
    assert result.text == "Hello wraps here.\n\nNext."
    assert result.message == pc.OCR_COPIED_MSG


def test_recognize_image_table_mode_copies_tsv(pc, monkeypatch):
    class Rect:
        def __init__(self, x, y, w, h):
            self.x, self.y, self.width, self.height = x, y, w, h

    class Word:
        def __init__(self, text, x, y, w, h):
            self.text, self.bounding_rect = text, Rect(x, y, w, h)

    class Line:
        def __init__(self, words):
            self.words = words
            self.text = " ".join(w.text for w in words)

    class Engine:
        async def recognize_async(self, bitmap):
            class Result:
                pass
            result = Result()
            result.lines = [
                Line([Word("A", 0, 0, 20, 16), Word("B", 80, 0, 20, 16)]),
                Line([Word("1", 0, 28, 20, 16), Word("2", 80, 28, 20, 16)]),
            ]
            result.text = "A B\n1 2"
            return result

    class Lang:
        def __init__(self, tag):
            self.language_tag = tag

    class OcrEngine:
        @staticmethod
        def is_language_supported(lang):
            return True

        @staticmethod
        def try_create_from_language(lang):
            return Engine()

    class DataWriter:
        def write_bytes(self, data):
            pass

        def detach_buffer(self):
            return b""

    class SoftwareBitmap:
        @staticmethod
        def create_copy_from_buffer(buf, fmt, w, h):
            return ("bitmap", w, h)

    monkeypatch.setattr(pc, "_import_ocr_modules", lambda: {
        "Language": Lang, "OcrEngine": OcrEngine,
        "BitmapPixelFormat": type("F", (), {"RGBA8": 28}),
        "SoftwareBitmap": SoftwareBitmap, "DataWriter": DataWriter,
    })
    result = pc.recognize_image(_img(120, 50), "table")
    assert result.ok and result.text == "A\tB\n1\t2"
    md = pc.recognize_image(_img(120, 50), "table-md")
    assert md.ok and md.text.splitlines()[0] == "| A | B |"
    assert "---" in md.text


def test_math_missing_model_is_friendly_and_offline(pc, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("network")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    called = []
    monkeypatch.setattr(pc, "predict_latex", lambda image: called.append(image) or "x")
    result = pc.recognize_image(_img(32, 32), "math")
    assert not result.ok and result.text == ""
    assert called == []
    assert "설치를 누르기 전" in result.message
    assert pc.math_status() == "no-model"


def test_math_runtime_missing_when_files_exist(pc, monkeypatch):
    folder = pc.CONFIG_DIR / "models" / "formula"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "pp_formulanet_plus_s.onnx").write_bytes(b"not-a-model")
    (folder / "tokenizer.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(pc, "_math_modules_ready", lambda path: False)
    result = pc.recognize_image(_img(32, 32), "math")
    assert not result.ok
    assert "구성 요소" in result.message
    assert "글자와 표" in result.message
    assert pc.math_status() == "no-runtime"


def test_math_mode_copies_mocked_latex(pc, toolbar, monkeypatch):
    seen = {}

    def predict(image):
        seen["size"] = (image.width(), image.height())
        return r"\frac{1}{2}"

    monkeypatch.setattr(pc, "math_status", lambda: "ok")
    monkeypatch.setattr(pc, "predict_latex", predict)
    pin = toolbar._make_pin(_img(48, 24, "white"), None)
    menu, acts = pin.build_menu()
    QApplication.clipboard().clear()
    pin.apply_menu_action(acts["ocr_modes"]["math"], acts)
    assert seen["size"] == (48, 24)
    assert QApplication.clipboard().text() == r"\frac{1}{2}"
    assert "LaTeX" in pin._toast.label.text()
    menu.close()


def test_ocr_button_stays_icon_only_and_right_click_lists_modes(pc, toolbar):
    toolbar.history = [pc.HistoryEntry(image=_img(16, 16, "white"))]
    toolbar.populate()
    assert toolbar.btn_ocr.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
    assert toolbar.btn_ocr.menu() is None
    menu, acts = pc.build_ocr_mode_menu(toolbar.btn_ocr)
    assert [acts[mode].text() for mode, _label in pc.OCR_MODE_ACTIONS] == [
        "글자", "표 (엑셀)", "표 (Markdown)", "수식"]
    assert "ocr" not in pc.DEFAULTS["hotkeys"]
    assert pc.DEFAULTS["hotkeys"]["region"] == "<ctrl>+<alt>+a"
    assert pc.DEFAULTS["hotkeys"]["ruler"] == "<ctrl>+<alt>+d"
    menu.close()


def test_toolbar_right_click_math_uses_the_selected_capture(pc, toolbar, monkeypatch):
    red = _img(20, 12, "red")
    toolbar.history = [pc.HistoryEntry(image=red)]
    toolbar.populate()
    monkeypatch.setattr(pc, "math_status", lambda: "ok")

    def predict(image):
        assert image.cacheKey() == red.cacheKey()
        return "E=mc^2"

    monkeypatch.setattr(pc, "predict_latex", predict)
    QApplication.clipboard().clear()
    toolbar._ocr_current("math")
    assert QApplication.clipboard().text() == "E=mc^2"


class _Resp:
    def __init__(self, body, status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers or {}
        self._i = 0

    def read(self, n):
        block = self.body[self._i:self._i + n]
        self._i += len(block)
        return block

    def close(self):
        return None


def _zip_bytes(pc, onnx: bytes, tok: bytes, extra=()):
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr(pc.MATH_PACK_ONNX, onnx)
        archive.writestr(pc.MATH_PACK_TOKENIZER, tok)
        archive.writestr("math/onnxruntime/__init__.py", b"# runtime\n")
        for name, payload in extra:
            archive.writestr(name, payload)
    return buf.getvalue()


def test_math_install_box_is_install_or_cancel(pc):
    box = pc.build_math_install_box()
    assert box.text() == pc.MATH_INSTALL_TITLE
    assert "다운로드" in box.text()
    assert box._install_btn.text() == "설치"
    assert box._cancel_btn.text() == "취소"
    box.close()


def test_math_choice_cancel_does_not_download(pc, toolbar, monkeypatch):
    monkeypatch.setattr(pc, "math_status", lambda: "no-model")
    monkeypatch.setattr(pc, "confirm_math_install", lambda parent=None: False)

    def boom(*_a, **_k):
        raise AssertionError("download")

    monkeypatch.setattr(pc, "_run_math_install_dialog", boom)
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    pin = toolbar._make_pin(_img(16, 16, "white"), None)
    _menu, acts = pin.build_menu()
    QApplication.clipboard().clear()
    pin.apply_menu_action(acts["ocr_modes"]["math"], acts)
    assert "취소" in pin._toast.label.text()
    assert QApplication.clipboard().text() == ""


def test_math_choice_install_then_copies_latex(pc, toolbar, monkeypatch):
    phase = {"ready": False}

    def status():
        return "ok" if phase["ready"] else "no-model"

    monkeypatch.setattr(pc, "math_status", status)
    monkeypatch.setattr(pc, "confirm_math_install", lambda parent=None: True)

    def run(parent=None):
        phase["ready"] = True

    monkeypatch.setattr(pc, "_run_math_install_dialog", run)
    monkeypatch.setattr(pc, "predict_latex", lambda image: r"\sqrt{2}")
    pin = toolbar._make_pin(_img(12, 12, "white"), None)
    _menu, acts = pin.build_menu()
    QApplication.clipboard().clear()
    pin.apply_menu_action(acts["ocr_modes"]["math"], acts)
    assert QApplication.clipboard().text() == r"\sqrt{2}"


def test_toolbar_math_without_a_pin_asks_before_download(pc, toolbar, monkeypatch):
    monkeypatch.setattr(pc, "math_status", lambda: "no-model")
    monkeypatch.setattr(pc, "confirm_math_install", lambda parent=None: False)

    def boom(*_a, **_k):
        raise AssertionError("download")

    monkeypatch.setattr(pc, "_run_math_install_dialog", boom)
    red = _img(20, 12, "red")
    toolbar.history = [pc.HistoryEntry(image=red)]
    toolbar.populate()
    toolbar._ocr_current("math")
    assert toolbar._last_notice == pc.MATH_INSTALL_CANCELLED_MSG


def test_fetch_verifies_sha256_and_can_resume(pc, monkeypatch):
    import hashlib
    blob = b"abcdefghijklmnopqrstuvwxyz" * 50
    digest = hashlib.sha256(blob).hexdigest()
    monkeypatch.setattr(pc, "MATH_PACK_SHA256", digest)
    monkeypatch.setattr(pc, "MATH_PACK_BYTES", len(blob))
    dest = pc._math_download_path()
    if dest.exists():
        dest.unlink()

    def opener(req, timeout=None):
        header = req.get_header("Range")
        if not header:
            return _Resp(blob, 200, {"Content-Length": str(len(blob))})
        start = int(header.split("=", 1)[1].split("-", 1)[0])
        part = blob[start:]
        headers = {
            "Content-Range": f"bytes {start}-{len(blob) - 1}/{len(blob)}",
            "Content-Length": str(len(part)),
        }
        return _Resp(part, 206, headers)

    def cancel():
        return dest.exists() and dest.stat().st_size > 0

    try:
        pc.fetch_math_pack(dest, url="https://example.test/pack.zip", opener=opener,
                           cancelled=cancel, chunk=16)
    except pc.MathInstallCancelled:
        pass
    else:
        raise AssertionError("cancel did not stop the download")
    assert dest.is_file() and 0 < dest.stat().st_size < len(blob)
    seen = {}

    def opener_checked(req, timeout=None):
        seen["range"] = req.get_header("Range")
        return opener(req, timeout=timeout)

    pc.fetch_math_pack(dest, url="https://example.test/pack.zip", opener=opener_checked, chunk=16)
    assert seen["range"].startswith("bytes=")
    assert dest.read_bytes() == blob


def test_fetch_rejects_a_bad_hash_and_deletes_the_file(pc, monkeypatch):
    monkeypatch.setattr(pc, "MATH_PACK_SHA256", "0" * 64)
    monkeypatch.setattr(pc, "MATH_PACK_BYTES", 0)
    dest = pc._math_download_path()

    def opener(req, timeout=None):
        body = b"not-the-pack"
        return _Resp(body, 200, {"Content-Length": str(len(body))})

    try:
        pc.fetch_math_pack(dest, url="https://example.test/pack.zip", opener=opener)
    except pc.MathInstallError as exc:
        assert exc.message == pc.MATH_INSTALL_HASH_MSG
    else:
        raise AssertionError("bad hash was accepted")
    assert not dest.exists()


def test_extract_checks_inner_hashes_and_skips_path_escape(pc, monkeypatch):
    import hashlib
    onnx = b"formula-onnx"
    tok = b"tokenizer-yml"
    monkeypatch.setattr(pc, "MATH_ONNX_SHA256", hashlib.sha256(onnx).hexdigest())
    monkeypatch.setattr(pc, "MATH_TOKENIZER_SHA256", hashlib.sha256(tok).hexdigest())
    pc.remove_math_component()
    blob = _zip_bytes(pc, onnx, tok, extra=(
        ("../evil.txt", b"nope"),
        ("math/../../evil2.txt", b"nope"),
    ))
    pack = pc.CONFIG_DIR / "downloads" / "sample.zip"
    pack.parent.mkdir(parents=True, exist_ok=True)
    pack.write_bytes(blob)
    pc.extract_math_pack(pack)
    assert (pc.CONFIG_DIR / pc.MATH_PACK_ONNX).read_bytes() == onnx
    assert (pc.CONFIG_DIR / pc.MATH_PACK_TOKENIZER).read_bytes() == tok
    assert (pc.CONFIG_DIR / "math" / "onnxruntime" / "__init__.py").is_file()
    assert not (pc.CONFIG_DIR / "evil.txt").exists()
    assert not (pc.CONFIG_DIR / "evil2.txt").exists()
    assert not (pc.CONFIG_DIR.parent / "evil.txt").exists()
    pc.remove_math_component()


def test_install_math_pack_uses_the_opener_only_when_called(pc, monkeypatch):
    import hashlib
    onnx = b"formula-onnx"
    tok = b"tokenizer-yml"
    blob = _zip_bytes(pc, onnx, tok)
    monkeypatch.setattr(pc, "MATH_PACK_SHA256", hashlib.sha256(blob).hexdigest())
    monkeypatch.setattr(pc, "MATH_PACK_BYTES", len(blob))
    monkeypatch.setattr(pc, "MATH_ONNX_SHA256", hashlib.sha256(onnx).hexdigest())
    monkeypatch.setattr(pc, "MATH_TOKENIZER_SHA256", hashlib.sha256(tok).hexdigest())
    pc.remove_math_component()
    opened = []

    def opener(req, timeout=None):
        opened.append(req.full_url)
        return _Resp(blob, 200, {"Content-Length": str(len(blob))})

    pc.install_math_pack(url="https://example.test/pack.zip", opener=opener)
    assert opened == ["https://example.test/pack.zip"]
    assert (pc.CONFIG_DIR / pc.MATH_PACK_ONNX).read_bytes() == onnx
    assert not pc._math_download_path().exists()
    pc.remove_math_component()


def test_settings_remove_deletes_math_files_and_can_be_cancelled(pc, monkeypatch):
    pc.remove_math_component()
    cfg = pc.load_config()
    empty = pc.SettingsDialog(cfg, hotkey_ok=False)
    assert not empty.btn_math_remove.isEnabled()
    assert "아직" in empty.lbl_math.text()
    empty.close()

    folder = pc.CONFIG_DIR / "models" / "formula"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "pp_formulanet_plus_s.onnx"
    target.write_bytes(b"x")
    (pc.CONFIG_DIR / "math").mkdir(exist_ok=True)
    (pc.CONFIG_DIR / "math" / "marker.txt").write_text("a", encoding="utf-8")
    dlg = pc.SettingsDialog(cfg, hotkey_ok=False)
    assert dlg.btn_math_remove.isEnabled()
    monkeypatch.setattr(pc, "confirm_math_remove", lambda parent=None: False)
    dlg.btn_math_remove.click()
    assert target.is_file()
    monkeypatch.setattr(pc, "confirm_math_remove", lambda parent=None: True)
    dlg.btn_math_remove.click()
    assert not target.exists()
    assert not (pc.CONFIG_DIR / "math").exists()
    assert not dlg.btn_math_remove.isEnabled()
    dlg.close()
