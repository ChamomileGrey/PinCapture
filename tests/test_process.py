"""Tests that need a separate process: quitting, CLI flags, the built-in --selftest."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "pincapture.py"


def _env(tmp_path):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PINCAP_NO_LOG="1", PYTHONIOENCODING="utf-8",
               USERPROFILE=str(tmp_path), HOME=str(tmp_path),
               PINCAP_RECENT_DIR=str(tmp_path / "recent-pins"))
    return env


@pytest.mark.parametrize("npins", [1, 3])
def test_quit_really_exits_with_pins_on_screen(npins):
    """Regression for the v0.6.0 zombie-process bug (quit ignored while pins are visible)."""
    for _ in range(3):
        r = subprocess.run([sys.executable, str(ROOT / "tests" / "quit_probe.py"), str(npins)],
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        assert "EXITED" in r.stdout, f"quit was ignored: {r.stdout!r} {r.stderr[-500:]!r}"


def test_version_flag(tmp_path):
    import pincapture as pc
    r = subprocess.run([sys.executable, str(APP), "--version"], capture_output=True, text=True,
                       encoding="utf-8", env=_env(tmp_path), timeout=60)
    assert r.returncode == 0
    assert pc.APP_VERSION in r.stdout


def test_quit_flag_without_running_instance(tmp_path):
    r = subprocess.run([sys.executable, str(APP), "--quit"], capture_output=True, text=True,
                       encoding="utf-8", env=_env(tmp_path), timeout=60)
    assert r.returncode == 0


def test_unknown_argument_does_not_crash(tmp_path):
    """Old shortcuts may pass a stale script path; the app must ignore it (parse_known_args)."""
    r = subprocess.run([sys.executable, str(APP), "--version", r"C:\stale\pincapture.py"],
                       capture_output=True, text=True, encoding="utf-8", env=_env(tmp_path), timeout=60)
    assert r.returncode == 0


def test_selftest_renders_every_window(tmp_path):
    r = subprocess.run([sys.executable, str(APP), "--selftest"], cwd=tmp_path, capture_output=True,
                       text=True, encoding="utf-8", env=_env(tmp_path), timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    pngs = sorted(p.name for p in (tmp_path / "selftest_out").glob("*.png"))
    assert pngs == ["about.png", "main.png", "overlay.png", "pin.png", "settings.png", "welcome.png"]


def test_launch_argv_script_mode(pc):
    argv = pc.launch_argv("--tray")
    assert argv[-1] == "--tray"
    assert Path(argv[-2]).resolve() == APP.resolve()          # script path, not a temp path
    assert Path(argv[0]).name.lower() in ("pythonw.exe", "python.exe", "python3", "python")
    assert pc.app_dir() == APP.parent.resolve()


def test_singleton_name_is_per_user(pc):
    if sys.platform == "win32":
        assert pc.SINGLETON_NAME.startswith("pincapture-single-instance-")
        assert pc.SINGLETON_NAME != "pincapture-single-instance"


def test_tests_never_talk_to_the_real_running_app(tmp_path):
    """The singleton name includes the home folder, so a test (isolated home) can never send
    'quit'/'show' to the developer's real PinCapture. (A test once quit the owner's running app.)"""
    code = "import pincapture as pc; print(pc.SINGLETON_NAME)"
    names = set()
    for home in (tmp_path / "a", tmp_path / "b"):
        home.mkdir()
        env = dict(_env(home))
        r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", env=env, timeout=60)
        assert r.returncode == 0, r.stderr[-500:]
        names.add(r.stdout.strip().splitlines()[-1])
    assert len(names) == 2
