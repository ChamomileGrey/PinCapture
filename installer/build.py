# PinCapture installer build — v0.6.0 — one command from source to setup.exe
# Created: 2026-10-22 by Claude Opus 5.5 via Claude Code
# Install path: D:/Tools/PinCapture/installer/build.py
# Changelog:
#   v0.6.0 2026-10-22 Claude Opus 5.5 — first version: icon -> version resource -> PyInstaller onedir
#                     -> bundle check -> smoke test -> Inno Setup -> SHA-256 + release note (배포안내.txt)
"""
Build PinCapture-Setup-<version>.exe.

    py -3.13 installer\\build.py            # full build
    py -3.13 installer\\build.py --no-setup # stop after the PyInstaller app folder

Steps
  1. Read APP_VERSION from pincapture.py (single source of truth).
  2. Render the app icon at 16-256 px and pack a multi-size .ico (Pillow).
  3. Write the Windows version resource (version_info.txt) for PinCapture.exe.
  4. PyInstaller onedir build from PinCapture.spec  -> build/dist/PinCapture/
  5. Smoke test: run the built EXE with --selftest (offscreen) and check it exits 0.
  6. Inno Setup (ISCC) compile PinCapture.iss      -> output/PinCapture-Setup-<version>.exe
  7. Print size and SHA-256 of the setup file (publish the hash with the download).

Requires: Python 3.13 with PySide6, pynput, pyinstaller, pillow; Inno Setup 6.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # installer/
ROOT = HERE.parent                              # project root
SRC = ROOT / "pincapture.py"
BUILD = HERE / "build"
OUT = HERE / "output"
ICON_SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
PUBLISHER = "PinCapture"                        # shown in EXE properties; keep in sync with PinCapture.iss


def step(msg: str) -> None:
    print(f"\n=== {msg}", flush=True)


def app_version() -> str:
    m = re.search(r'^APP_VERSION\s*=\s*"(\d+\.\d+\.\d+)"', SRC.read_text(encoding="utf-8"), re.M)
    if not m:
        sys.exit("APP_VERSION not found in pincapture.py")
    return m.group(1)


def make_icon(ico: Path) -> None:
    """Draw the app icon with the app's own make_app_icon() at every size, pack into one .ico."""
    os.environ["PINCAP_NO_LOG"] = "1"            # importing pincapture must not touch the user's log
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    sys.path.insert(0, str(ROOT))
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])   # noqa: F841 (needed for QPixmap)
    import pincapture as pc
    sys.excepthook = sys.__excepthook__          # importing the app installs its MessageBox hook; not in a build
    from PIL import Image
    images = []
    for s in ICON_SIZES:
        png = BUILD / f"icon_{s}.png"
        if not pc.make_app_icon(s).pixmap(s, s).save(str(png), "PNG"):
            sys.exit(f"icon render failed at {s}px")
        images.append(Image.open(png).convert("RGBA"))
    big = images[-1]
    big.save(ico, format="ICO", sizes=[(s, s) for s in ICON_SIZES], append_images=images[:-1])
    got = sorted(Image.open(ico).info.get("sizes", []))
    print(f"icon sizes: {got}")
    if len(got) != len(ICON_SIZES):
        sys.exit(f"icon has {len(got)} sizes, expected {len(ICON_SIZES)}")


def write_version_file(path: Path, ver: str) -> None:
    parts = tuple(int(x) for x in ver.split(".")) + (0,)
    path.write_text(f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(filevers={parts}, prodvers={parts}, mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([
      StringTable('041204B0', [
        StringStruct('CompanyName', '{PUBLISHER}'),
        StringStruct('FileDescription', '핀캡처 화면 캡처'),
        StringStruct('FileVersion', '{ver}'),
        StringStruct('InternalName', 'PinCapture'),
        StringStruct('LegalCopyright', 'Copyright (C) 2026'),
        StringStruct('OriginalFilename', 'PinCapture.exe'),
        StringStruct('ProductName', '핀캡처 (PinCapture)'),
        StringStruct('ProductVersion', '{ver}')])
    ]),
    VarFileInfo([VarStruct('Translation', [0x0412, 1200])])
  ]
)
""", encoding="utf-8")


def find_iscc() -> Path:
    cands = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Inno Setup 6/ISCC.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Inno Setup 6/ISCC.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Inno Setup 6/ISCC.exe",
    ]
    for c in cands:
        if c.is_file():
            return c
    found = shutil.which("iscc")
    if found:
        return Path(found)
    sys.exit("Inno Setup 6 (ISCC.exe) not found")


MUST_HAVE = ["PinCapture.exe", "_internal/PySide6/Qt6Core.dll", "_internal/PySide6/Qt6Gui.dll",
             "_internal/PySide6/Qt6Widgets.dll", "_internal/PySide6/Qt6Network.dll",
             "_internal/PySide6/plugins/platforms/qwindows.dll", "_internal/PySide6/plugins/imageformats/qjpeg.dll",
             "_internal/PySide6/plugins/imageformats/qico.dll", "_internal/pynput/keyboard/_win32.py"]
MUST_NOT = ["libssl-3-x64.dll", "libcrypto-3-x64.dll", "qopensslbackend.dll", "qtiff.dll", "qwebp.dll",
            "qsvg.dll", "opengl32sw.dll", "qt6pdf.dll"]


def check_contents(app: Path) -> None:
    """The notices (THIRD_PARTY_NOTICES.txt) describe exactly this set — fail if the bundle drifts."""
    missing = [p for p in MUST_HAVE if not (app / p).exists()]
    names = {f.name.lower() for f in app.rglob("*") if f.is_file()}
    present = [n for n in MUST_NOT if n.lower() in names]
    if missing or present:
        sys.exit(f"bundle check failed: missing={missing} unexpected={present}")
    print("bundle contents ok")


def write_release_note(path: Path, ver: str, setup_name: str, digest: str) -> None:
    """Text to paste into the download page / message — the install warnings happen before 사용법.txt exists."""
    path.write_text(f"""핀캡처 {ver} 설치 파일 안내
==========================

파일: {setup_name}
SHA-256: {digest}

설치 방법
  1. 설치 파일을 받아 실행합니다. 관리자 권한은 필요 없습니다.
  2. 브라우저에서 "일반적으로 다운로드되지 않습니다" 경고가 뜨면
       Edge  : 다운로드 목록의 [⋯] → [유지] → [그래도 계속]
       Chrome: 다운로드 목록에서 [계속] 또는 [유지]
  3. 파란 "Windows의 PC 보호" 창이 뜨면 [추가 정보] → [실행]
     (개인이 만든 무료 프로그램이라 Microsoft 인증서 서명이 없어서 나오는 안내입니다.)
  4. Windows 11 에서 "스마트 앱 컨트롤"이 켜져 있으면 서명 없는 프로그램이 차단되어 설치할 수 없습니다.

설치 후
  · 시작 메뉴의 [핀캡처 사용법]에 단축키와 사용법이 있습니다.
  · 기본 단축키: 영역 Ctrl+Alt+A / 창 Ctrl+Alt+W / 전체 Ctrl+Alt+F / 핀 고정 Ctrl+Alt+Q
  · 업데이트: 새 설치 파일을 실행하면 됩니다. 제거: 시작 메뉴에서 핀캡처 우클릭 → [제거]
  · 핀캡처는 인터넷에 연결하지 않습니다.
""", encoding="utf-8-sig")


def smoke_test(exe: Path) -> None:
    """Run the built EXE headless; --selftest renders every window and exits 0."""
    work = BUILD / "smoke"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PINCAP_NO_LOG="1")
    r = subprocess.run([str(exe), "--selftest"], cwd=work, env=env, timeout=120)
    pngs = sorted(p.name for p in (work / "selftest_out").glob("*.png"))
    print(f"selftest exit={r.returncode} outputs={pngs}")
    if r.returncode != 0 or len(pngs) < 4:
        sys.exit("smoke test failed")
    shutil.rmtree(work, ignore_errors=True)


def main() -> None:
    no_setup = "--no-setup" in sys.argv
    ver = app_version()
    print(f"PinCapture {ver}")
    shutil.rmtree(BUILD, ignore_errors=True)
    BUILD.mkdir(parents=True)
    OUT.mkdir(parents=True, exist_ok=True)

    step("1/5 icon")
    ico = BUILD / "pincapture.ico"
    make_icon(ico)

    step("2/5 version resource")
    write_version_file(BUILD / "version_info.txt", ver)

    step("3/5 PyInstaller (onedir)")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--log-level", "WARN",
                    "--distpath", str(BUILD / "dist"), "--workpath", str(BUILD / "work"),
                    str(HERE / "PinCapture.spec")], cwd=HERE, check=True)
    app = BUILD / "dist" / "PinCapture"
    exe = app / "PinCapture.exe"
    size_mb = sum(f.stat().st_size for f in app.rglob("*") if f.is_file()) / 1e6
    print(f"app folder: {app}  ({size_mb:.0f} MB)")
    check_contents(app)

    step("4/5 smoke test")
    smoke_test(exe)
    if no_setup:
        return

    step("5/5 Inno Setup")
    iscc = find_iscc()
    subprocess.run([str(iscc), "/Q", f"/DAppVersion={ver}", str(HERE / "PinCapture.iss")], cwd=HERE, check=True)
    setup = OUT / f"PinCapture-Setup-{ver}.exe"
    digest = hashlib.sha256(setup.read_bytes()).hexdigest()
    print(f"\nsetup:   {setup}")
    print(f"size:    {setup.stat().st_size / 1e6:.1f} MB")
    print(f"SHA-256: {digest}")
    (OUT / f"PinCapture-Setup-{ver}.sha256.txt").write_text(f"{digest}  {setup.name}\n", encoding="utf-8")
    note = OUT / f"PinCapture-Setup-{ver}_배포안내.txt"
    write_release_note(note, ver, setup.name, digest)
    print(f"release note: {note}")


if __name__ == "__main__":
    main()
