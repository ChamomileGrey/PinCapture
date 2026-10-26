"""The installer build must print the Korean release-note name on a cp1252 console."""
import importlib.util
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTE = "PinCapture-Setup-0.7.0_배포안내.txt"


def _load_build():
    path = ROOT / "installer" / "build.py"
    spec = importlib.util.spec_from_file_location("pincapture_installer_build", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cp1252_console_cannot_encode_the_release_note_name():
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
    try:
        stream.write(NOTE)
        stream.flush()
    except UnicodeEncodeError:
        return
    raise AssertionError("cp1252 accepted the release-note name; the regression fixture is stale")


def test_configure_stdio_prints_the_korean_release_note_name():
    module = _load_build()
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
    module.configure_stdio_stream(stream)
    stream.write(f"release note: {NOTE}\n")
    stream.flush()
    assert NOTE.encode("utf-8") in raw.getvalue()
