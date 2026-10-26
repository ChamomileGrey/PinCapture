#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 핀캡처 (PinCapture) — 화면 캡처 도구
#
# 출처 / 이력 (주석이라 배포용 EXE 의 바이트코드에는 들어가지 않음)
#   v0.1   2026-08-04  claude.ai 채팅에서 Claude 가 생성
#   v0.2~4             보관함 통합, 단일 인스턴스, 바로가기 생성 등 추가
#   v0.5   2026-09-03  Claude Code (Claude Fable 5.1) — 실행 환경 보호: PySide6 없는 Python 이면
#                      다른 Python 으로 자동 재실행, ~/.pincapture/pincapture.log, 예외 메시지 박스
#   v0.5.1 2026-09-14  Claude Code (Claude Fable 5.1) — 작업 표시줄 고정용 AppUserModelID·재실행 정보,
#                      시작 메뉴 바로가기
#   v0.5.2 2026-09-14  Claude Code (Claude Fable 5.1) — 캡처 후 창을 전경으로 (AttachThreadInput 우회)
#   v0.5.3 2026-10-21  Claude Code (Claude Fable 5.1) — 보관함 다중 선택 (복사/저장/핀/제거 일괄)
#   v0.6.0 2026-10-22  Claude Code (Claude Opus 5.5) — 설치 프로그램(Inno Setup) 배포 대응:
#                      EXE 실행 시 바로가기·작업 표시줄 고정·다시 시작이 깨지던 문제 수정,
#                      --tray(트레이로 시작) / --quit(설치·제거 시 실행 중인 앱 종료) / --version,
#                      설치 프로그램용 실행 감지 뮤텍스, 로그에 앱 버전 기록,
#                      종료를 취소 불가능한 exit(0) 로 (핀 창이 있으면 quit() 가 무시되던 버그),
#                      중복 실행 방지 채널을 사용자·세션별로 분리
#   v0.6.1 2026-10-26  Claude Code (Claude Opus 5.5) — 화면 캡처가 통째로 검게 나올 때(보안 프로그램의
#                      '화면 캡처 방지' 등) 검은 화면을 모니터에 띄우거나 저장하지 않고 원인·해결법 안내
#   v0.7.0 2026-10-26  Grok (Grok 4.7) — 메인·설정 창 문구와 배치를 다듬고, 첫 실행 빠른 안내·정보 창·
#                      트레이 메뉴를 정리. 정보 창과 트레이에 후원하기(Ko-fi). 설정 파일 형식은 그대로
#   v0.8.0 2026-10-26  Grok (Grok 4.7) — 핀 우클릭 글자 복사(Windows OCR), 투명도·클릭 통과,
#                      최근 핀 다시 열기, 거의 검은 캡처는 핀 대신 보안 프로그램 안내
#   Created: 2026-08-04 by Claude via claude.ai / Modified: 2026-10-26 by Grok 4.7 via Cursor
#   빌드: installer/build.py  (PyInstaller onedir + Inno Setup → PinCapture-Setup-<버전>.exe)
"""
핀캡처 (PinCapture) — 화면 캡처 도구

기능
  · 영역 지정 캡처 (드래그, 화면 정지 방식)
  · 창 캡처 (현재 활성 창, Windows에서 PrintWindow 사용)
  · 전체 화면 캡처 (마우스가 있는 모니터)
  · 핀 고정 (캡처한 이미지를 항상 위 창으로 화면에 고정)
  · 핀 우클릭: 글자 복사(Windows OCR), 투명도, 클릭 통과
  · 닫은 핀 다시 열기 (전역 단축키·트레이)
  · 전역 단축키, 트레이 상주, 자동 저장 + 클립보드 복사

실행:  PinCapture.exe  (개발: python pincapture.py)
옵션:  --region --window --full --pin   (시작 직후 해당 캡처 1회 실행)
       --tray                            (창을 띄우지 않고 트레이로 시작 — 자동 실행용)
       --quit                            (실행 중인 핀캡처를 종료 — 설치/제거 프로그램용)
       --selftest                        (UI 렌더링 자가 점검, 개발용)

설정 파일: ~/.pincapture/config.json  (설정 창에서도 변경 가능)
"""

import sys
import os
import json
import argparse
import datetime
import tempfile
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0   # subprocess.CREATE_NO_WINDOW

APP_NAME = "핀캡처"
APP_VERSION = "0.8.0"
APP_PUBLISHER = "캐모마일그레이"                 # 정보 창에 보이는 이름
APP_PUBLISHER_EN = "ChamomileGrey"             # 설치 정보·EXE 속성과 같은 영문 이름
KOFI_URL = "https://ko-fi.com/chamomilegrey"   # 후원하기. 이 주소만 연다
APP_USER_MODEL_ID = "pincapture.app"           # 작업 표시줄 그룹/고정 식별자 (설치 프로그램 바로가기와 동일해야 함)
APP_MUTEX_NAME = "PinCaptureRunning"           # 설치 프로그램이 '실행 중' 여부를 확인하는 뮤텍스 (PinCapture.iss 와 동일)
FROZEN = bool(getattr(sys, "frozen", False))   # PyInstaller 로 만든 EXE 로 실행 중인지
_APP_MUTEX = None                              # 위 뮤텍스 핸들 (프로세스가 끝날 때까지 유지)


def launch_argv(*extra: str) -> "list[str]":
    """이 프로그램을 다시 실행하는 명령. 바로가기 대상·작업 표시줄 재실행·'다시 시작' 공용.
    EXE 면 EXE 하나, 스크립트면 pythonw.exe + 이 .py 파일.
    (EXE 에서 __file__ 은 존재하지 않는 임시 경로라 절대 인수로 넘기면 안 된다)"""
    if FROZEN:
        return [sys.executable, *extra]
    pyw = Path(sys.executable).with_name("pythonw.exe")
    return [str(pyw if pyw.exists() else Path(sys.executable)), str(Path(__file__).resolve()), *extra]


def app_dir() -> Path:
    """프로그램이 놓인 폴더 (바로가기 '시작 위치')."""
    return Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# 실행 환경 보호
#   · pythonw 로 실행되면 콘솔이 없어 오류가 그냥 사라짐 → ~/.pincapture/pincapture.log 에 기록
#   · 처리되지 않은 예외는 메시지 박스로도 표시
#   · PySide6 가 없는 Python 으로 실행되면(파이썬 업데이트로 기본 python 이 바뀐 경우 등)
#     PySide6 가 설치된 다른 Python 을 찾아 자동으로 그쪽으로 다시 실행
# ---------------------------------------------------------------------------
_CONFIG_DIR = Path.home() / ".pincapture"
LOG_PATH = _CONFIG_DIR / "pincapture.log"


def _msgbox(title: str, text: str, error: bool = True) -> None:
    if IS_WINDOWS:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, text, title, 0x10 if error else 0x40)
            return
        except Exception:
            pass
    print(f"{title}: {text}", file=(sys.stderr or sys.stdout))


class _Tee:
    """콘솔과 로그 파일에 동시에 쓰는 스트림."""
    def __init__(self, *streams):
        self._streams = [s for s in streams if s is not None]

    def write(self, s):
        for st in self._streams:
            try:
                st.write(s)
            except Exception:
                pass
        return len(s)

    def flush(self):
        for st in self._streams:
            try:
                st.flush()
            except Exception:
                pass

    def isatty(self):
        return False


def _setup_logging() -> None:
    if os.environ.get("PINCAP_NO_LOG"):            # 빌드 스크립트가 아이콘만 그릴 때 로그를 건드리지 않게
        return
    try:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        try:   # 다른 인스턴스가 로그를 열고 있으면 회전만 건너뜀
            if LOG_PATH.exists() and LOG_PATH.stat().st_size > 512 * 1024:
                LOG_PATH.replace(LOG_PATH.with_suffix(".log.old"))
        except Exception:
            pass
        f = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
        sys.stdout = _Tee(sys.__stdout__, f)
        sys.stderr = _Tee(sys.__stderr__, f)
        print(f"\n===== {datetime.datetime.now():%Y-%m-%d %H:%M:%S}  "
              f"{APP_NAME} {APP_VERSION} ({'exe' if FROZEN else 'py'})  "
              f"python {sys.version.split()[0]}  {sys.executable}  args={sys.argv[1:]}")
    except Exception:
        pass


def _excepthook(t, v, tb):
    import traceback
    msg = "".join(traceback.format_exception(t, v, tb))
    print(msg, file=sys.stderr)
    _msgbox("핀캡처 오류",
            f"예상치 못한 오류로 종료돼.\n\n{msg[-1200:]}\n\n전체 로그: {LOG_PATH}")


_setup_logging()
sys.excepthook = _excepthook


def _find_python_with_deps() -> "str | None":
    """PySide6(가능하면 pynput 도)가 설치된 다른 Python 실행 파일을 찾는다."""
    import re
    import subprocess
    cands = []
    if IS_WINDOWS:
        try:  # py 런처에 등록된 모든 Python
            r = subprocess.run(["py", "-0p"], capture_output=True, text=True,
                               timeout=10, creationflags=_NO_WINDOW)
            for line in r.stdout.splitlines():
                m = re.match(r"^\s*-V:\S+\s+\*?\s*(.+?\.exe)\s*$", line, re.I)
                if m:
                    cands.append(m.group(1))
        except Exception:
            pass
        home = Path.home()
        pd = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
        lad = Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local"))
        for p in [pd / "Miniconda3/python.exe", pd / "Anaconda3/python.exe",
                  home / "miniconda3/python.exe", home / "anaconda3/python.exe",
                  *sorted((lad / "Programs/Python").glob("Python3*/python.exe"), reverse=True)]:
            cands.append(str(p))
    seen, ordered = set(), []
    for c in cands:
        try:
            key = str(Path(c).resolve()).lower()
        except Exception:
            continue
        if key in seen or not Path(c).exists():
            continue
        seen.add(key)
        if key == str(Path(sys.executable).resolve()).lower():
            continue
        ordered.append(c)
    fallback = None
    for c in ordered:
        try:
            r = subprocess.run([c, "-c", "import PySide6, pynput"], capture_output=True,
                               timeout=30, creationflags=_NO_WINDOW)
            if r.returncode == 0:
                return c
            r = subprocess.run([c, "-c", "import PySide6"], capture_output=True,
                               timeout=30, creationflags=_NO_WINDOW)
            if r.returncode == 0 and fallback is None:
                fallback = c
        except Exception:
            pass
    return fallback


def _handle_missing_deps(err: Exception) -> None:
    if FROZEN:
        # 설치된 EXE 에서 Qt 를 못 불러온 경우: 다른 Python 을 찾거나 pip 안내를 하면 안 됨
        print(f"[deps] EXE 에서 Qt 구성 요소를 불러오지 못함: {err}")
        _msgbox(f"{APP_NAME} 실행 실패",
                "프로그램 구성 요소를 불러오지 못했습니다.\n\n"
                "· 백신 프로그램이 핀캡처 파일을 차단하거나 격리했는지 확인해 주세요.\n"
                "· 설치 파일로 핀캡처를 다시 설치해 주세요.\n"
                "· Windows 10 / 11 (64비트)에서만 실행됩니다.\n\n"
                f"오류: {err}\n로그: {LOG_PATH}")
        sys.exit(1)
    import subprocess
    print(f"[deps] 이 Python({sys.executable}) 에 PySide6 가 없음: {err}")
    alt = None if os.environ.get("PINCAP_REEXEC") else _find_python_with_deps()
    if alt:
        exe = Path(alt)
        pyw = exe.with_name("pythonw.exe")
        if IS_WINDOWS and pyw.exists() and sys.__stdout__ is None:
            exe = pyw   # 콘솔 없이 실행된 경우(pythonw/바로가기)엔 계속 콘솔 없이
        print(f"[deps] PySide6 가 설치된 Python 으로 다시 실행: {exe}")
        env = dict(os.environ, PINCAP_REEXEC="1")
        try:
            subprocess.Popen([str(exe), str(Path(__file__).resolve()), *sys.argv[1:]],
                             env=env, creationflags=_NO_WINDOW, close_fds=True)
            sys.exit(0)
        except Exception as e:
            print(f"[deps] 재실행 실패: {e}")
    pip_py = sys.executable
    _msgbox("핀캡처 — 필요한 패키지가 없음",
            "이 Python 에는 PySide6 가 설치돼 있지 않아서 실행할 수 없어.\n\n"
            f"실행한 Python: {pip_py}\n\n"
            "해결 (명령 프롬프트에서):\n"
            f'    "{pip_py}" -m pip install PySide6 pynput\n\n'
            "또는 PySide6 가 설치된 Python 으로 실행하면 돼. "
            "(설정 창의 '바탕화면 아이콘 만들기'는 현재 실행 중인 Python 을 기억함)\n\n"
            f"로그: {LOG_PATH}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Qt import
# ---------------------------------------------------------------------------
try:
    from PySide6.QtCore import (
        Qt, QObject, QPoint, QPointF, QRect, QSize, QStandardPaths, QTimer, QUrl,
        Signal,
    )
except ImportError as _e:
    _handle_missing_deps(_e)
    raise
from PySide6.QtCore import (
    Qt, QItemSelectionModel, QMimeData, QObject, QPoint, QPointF, QRect, QSize,
    QStandardPaths, QTimer, QUrl, Signal,
)
from PySide6.QtGui import (
    QBrush, QColor, QCursor, QDesktopServices, QFont, QFontDatabase, QGuiApplication, QIcon,
    QImage, QImageReader, QKeySequence, QPainter, QPen, QPixmap, QShortcut,
)
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListView,
    QGridLayout, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton, QSpinBox,
    QSplitter, QSystemTrayIcon, QToolButton, QVBoxLayout, QWidget,
)

def _singleton_name() -> str:
    """중복 실행 방지용 로컬 소켓(Windows 에선 명명 파이프) 이름.
    파이프 이름은 PC 전체에서 하나라서, 고정 이름이면 한 PC 의 다른 Windows 계정끼리 충돌한다
    (두 번째 계정은 접근 거부 → 중복 실행, --quit 불가). 사용자·세션별로 분리해 뮤텍스 범위와 맞춘다."""
    base = "pincapture-single-instance"
    if not IS_WINDOWS:
        return base
    try:
        import ctypes
        import hashlib
        # 홈 폴더도 포함: 같은 계정이라도 홈(=설정 폴더)이 다르면 다른 인스턴스로 본다.
        # (시험은 임시 홈을 쓰므로, 시험의 --quit 이 실제로 켜져 있는 핀캡처를 끄는 일이 없게 됨)
        who = (os.environ.get("USERDOMAIN", "") + "\\" + os.environ.get("USERNAME", "")
               + "|" + str(Path.home())).lower()
        sess = ctypes.c_ulong(0)
        ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(sess))
        return f"{base}-{hashlib.sha1(who.encode('utf-8')).hexdigest()[:10]}-{sess.value}"
    except Exception:
        return base


SINGLETON_NAME = _singleton_name()

# 색상 테마 (알캡처 느낌의 밝은 UI + 파란 포인트)
ACCENT = "#2F6BFF"
ACCENT_DARK = "#1F4FD0"
BG = "#FAFBFD"
BORDER = "#D5DCE6"
TEXT = "#2B3442"
TEXT_SUB = "#6B7686"

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
CONFIG_DIR = _CONFIG_DIR
CONFIG_PATH = CONFIG_DIR / "config.json"


def _default_save_dir() -> str:
    pictures = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
    base = Path(pictures) if pictures else Path.home()
    return str(base / "PinCapture")


DEFAULTS = {
    "save_dir": "",                    # 비어 있으면 첫 실행 때 사진/PinCapture 로 설정
    "file_format": "png",              # png | jpg
    "jpg_quality": 92,
    "filename_prefix": "캡처",
    "autosave": True,                  # 캡처 시 자동 저장
    "clipboard": True,                 # 캡처 시 클립보드 복사
    "notify": True,                    # 캡처 후 트레이 알림
    "hide_during_capture": True,       # 캡처하는 동안 툴바 숨김
    "pin_after_capture": False,        # 모든 캡처를 핀으로도 고정
    "pin_autosave": False,             # 핀 캡처도 파일로 저장할지
    "show_viewer_after_capture": True, # 캡처 후 보관함 창 열기
    "hotkeys": {
        "region": "<ctrl>+<alt>+a",
        "window": "<ctrl>+<alt>+w",
        "full":   "<ctrl>+<alt>+f",
        "pin":    "<ctrl>+<alt>+q",
        "reopen_pin": "<ctrl>+<alt>+r",    # 최근 핀 다시 열기
        "clickthrough": "<ctrl>+<alt>+x",  # 클릭 통과 해제 (핀은 클릭을 받지 못함)
    },
    "recent_pin_limit": 10,            # 닫은 핀을 다시 열 수 있게 보관하는 개수
    "toolbar_pos": None,               # 창 위치 [x, y]
    "window_size": None,               # 창 크기 [w, h]
    "welcome_seen": False,             # 첫 실행 빠른 안내를 닫았는지. 0.6.x 파일에는 없음
}


def _clamp_recent_limit(value, default: int = 10) -> int:
    """닫은 핀 보관 개수. 잘못된 값은 기본값, 범위는 1~50."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(50, n))


def load_config() -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))  # deep copy
    try:
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            for k, v in data.items():
                if k == "hotkeys" and isinstance(v, dict):
                    cfg["hotkeys"].update(v)
                else:
                    cfg[k] = v
    except Exception as e:
        print(f"[config] 읽기 실패, 기본값 사용: {e}")
    if not cfg["save_dir"]:
        cfg["save_dir"] = _default_save_dir()
    cfg["recent_pin_limit"] = _clamp_recent_limit(cfg.get("recent_pin_limit", DEFAULTS["recent_pin_limit"]))
    return cfg


def save_config(cfg: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[config] 저장 실패: {e}")


def prepare_config() -> dict:
    """설정을 읽고, 첫 실행과 업그레이드를 구분한 뒤 저장한다.

    welcome_seen 은 0.7.0 에서 추가됐다. 키가 없는 기존 파일은 이미 쓰던 사람으로 보고
    빠른 안내를 자동으로 띄우지 않는다. 파일이 없으면 첫 실행이다.
    그 밖의 키는 load_config 가 기본값과 합치고, 모르는 키도 그대로 둔다.
    """
    fresh = not CONFIG_PATH.is_file()
    prior_keys: set = set()
    if not fresh:
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                prior_keys = set(data)
        except Exception:
            prior_keys = set()
    cfg = load_config()
    if "welcome_seen" not in prior_keys:
        cfg["welcome_seen"] = False if fresh else True
    save_config(cfg)
    return cfg


def should_auto_welcome(cfg: dict, start_in_tray: bool, tray_available: bool) -> bool:
    """첫 실행 안내를 지금 자동으로 열지.

    이미 본 경우와, Windows 시작 시 --tray 로 켜진 경우에는 작업을 끊지 않는다.
    트레이가 없는 환경은 --tray 여도 창이 뜨므로 안내를 보여 준다.
    """
    if cfg.get("welcome_seen"):
        return False
    if start_in_tray and tray_available:
        return False
    return True


def hotkey_label(combo: str) -> str:
    """pynput 형식(<ctrl>+<alt>+a)을 화면에 보일 표기(Ctrl+Alt+A)로 바꾼다."""
    if not combo or not str(combo).strip():
        return "없음"
    names = {
        "ctrl": "Ctrl", "control": "Ctrl", "alt": "Alt", "alt_gr": "AltGr",
        "shift": "Shift", "cmd": "Win", "super": "Win", "win": "Win",
        "print_screen": "PrintScreen", "esc": "Esc", "escape": "Esc",
        "space": "Space", "tab": "Tab", "enter": "Enter", "backspace": "Backspace",
    }
    out = []
    for part in str(combo).split("+"):
        raw = part.strip()
        if not raw:
            continue
        key = raw[1:-1] if (raw.startswith("<") and raw.endswith(">") and len(raw) > 2) else raw
        key_l = key.lower()
        if key_l in names:
            out.append(names[key_l])
        elif len(key) == 1:
            out.append(key.upper())
        else:
            out.append(key.replace("_", " ").title().replace(" ", ""))
    return "+".join(out) if out else "없음"


def third_party_notices_path() -> Path:
    """설치본은 프로그램 폴더, 소스 실행은 installer/docs 의 고지 파일."""
    bundled = app_dir() / "THIRD_PARTY_NOTICES.txt"
    if bundled.is_file():
        return bundled
    return app_dir() / "installer" / "docs" / "THIRD_PARTY_NOTICES.txt"


def open_kofi() -> None:
    """기본 브라우저로 후원 페이지만 연다. 앱 안에 창을 띄우지 않는다."""
    QDesktopServices.openUrl(QUrl(KOFI_URL))


def apply_ui_font(app=None) -> None:
    """한글이 있는 환경의 고딕을 고른다. 없으면 Qt 기본 글꼴을 그대로 쓴다."""
    app = app or QApplication.instance()
    if app is None:
        return
    families = set(QFontDatabase.families())
    for name in ("Malgun Gothic", "맑은 고딕", "Noto Sans CJK KR", "Noto Sans CJK JP", "Noto Sans KR"):
        if name in families:
            app.setFont(QFont(name, 10))
            return


def _polish_dialog(dlg: QDialog) -> None:
    dlg.setStyleSheet(f"""
        QDialog {{ background: white; color: {TEXT}; }}
        QGroupBox {{
            font-weight: 600; border: 1px solid {BORDER}; border-radius: 8px;
            margin-top: 14px; padding: 14px 12px 10px 12px; background: {BG};
        }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {TEXT}; }}
        QLabel {{ color: {TEXT}; }}
        QLineEdit, QComboBox, QSpinBox {{
            padding: 4px 8px; border: 1px solid {BORDER}; border-radius: 6px;
            background: white; min-height: 22px;
        }}
        QCheckBox {{ spacing: 8px; padding: 3px 0; }}
        QPushButton {{
            padding: 6px 14px; border: 1px solid {BORDER}; border-radius: 6px;
            background: white; color: {TEXT};
        }}
        QPushButton:hover {{ background: #EDF3FE; }}
        QPushButton:disabled {{ color: {TEXT_SUB}; background: #F3F5F8; }}
        QPushButton#primary {{
            background: {ACCENT}; color: white; border: 1px solid {ACCENT_DARK}; font-weight: 600;
        }}
        QPushButton#primary:hover {{ background: {ACCENT_DARK}; }}
    """)


# ---------------------------------------------------------------------------
# 아이콘 (외부 파일 없이 QPainter 로 직접 그림)
# ---------------------------------------------------------------------------

def _make_pixmap(size: int, draw_fn, color: str = TEXT) -> QPixmap:
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    draw_fn(p, size, QColor(color))
    p.end()
    return pm


def _draw_region(p: QPainter, s: int, c: QColor):
    pen = p.pen()
    pen.setStyle(Qt.PenStyle.DashLine)
    p.setPen(pen)
    p.drawRect(4, 5, s - 9, s - 11)
    pen.setStyle(Qt.PenStyle.SolidLine)
    pen.setColor(QColor(ACCENT))
    p.setPen(pen)
    m = s - 5
    p.drawLine(m - 4, m, m + 2, m)
    p.drawLine(m - 1, m - 3, m - 1, m + 3)


def _draw_window(p: QPainter, s: int, c: QColor):
    p.drawRoundedRect(4, 5, s - 8, s - 10, 2, 2)
    p.drawLine(4, 9, s - 4, 9)
    p.setBrush(QBrush(QColor(ACCENT)))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(6.5, 7.2), 1.1, 1.1)


def _draw_full(p: QPainter, s: int, c: QColor):
    p.drawRoundedRect(3, 4, s - 6, s - 11, 2, 2)
    p.drawLine(9, s - 4, s - 9, s - 4)
    p.drawLine(s // 2, s - 7, s // 2, s - 4)


def _draw_pin(p: QPainter, s: int, c: QColor):
    p.save()
    p.translate(s / 2.0, s / 2.0)
    p.rotate(40)
    p.setBrush(QBrush(QColor(ACCENT)))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(-3, -9, 6, 9, 2, 2)   # 머리
    p.setBrush(QBrush(QColor(c)))
    p.drawRect(-4, 0, 8, 2)                 # 받침
    pen = QPen(QColor(c)); pen.setWidthF(1.6)
    p.setPen(pen)
    p.drawLine(0, 2, 0, 9)                  # 바늘
    p.restore()


def _draw_gear(p: QPainter, s: int, c: QColor):
    p.save()
    p.translate(s / 2.0, s / 2.0)
    for i in range(8):
        p.save()
        p.rotate(i * 45)
        p.drawLine(0, -7, 0, -9)
        p.restore()
    p.drawEllipse(QPointF(0, 0), 5.2, 5.2)
    p.drawEllipse(QPointF(0, 0), 1.8, 1.8)
    p.restore()


def _draw_close(p: QPainter, s: int, c: QColor):
    p.drawLine(6, 6, s - 6, s - 6)
    p.drawLine(s - 6, 6, 6, s - 6)


def _draw_list(p: QPainter, s: int, c: QColor):
    y0, dy = s * 0.30, s * 0.22
    for i in range(3):
        y = round(y0 + i * dy)
        p.drawLine(round(s * 0.20), y, round(s * 0.28), y)
        p.drawLine(round(s * 0.42), y, round(s * 0.80), y)


def _draw_help(p: QPainter, s: int, c: QColor):
    p.drawEllipse(QPointF(s / 2, s / 2), s / 2 - 3.2, s / 2 - 3.2)
    p.setBrush(QBrush(c))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(s / 2, s * 0.72), 1.15, 1.15)
    pen = QPen(c)
    pen.setWidthF(1.7)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(int(s * 0.32), int(s * 0.22), int(s * 0.36), int(s * 0.32), 30 * 16, 280 * 16)
    p.drawLine(QPointF(s / 2, s * 0.52), QPointF(s / 2, s * 0.60))


def _draw_info(p: QPainter, s: int, c: QColor):
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(s / 2, s / 2), s / 2 - 3.2, s / 2 - 3.2)
    p.setBrush(QBrush(c))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(s / 2, s * 0.34), 1.2, 1.2)
    pen = QPen(c)
    pen.setWidthF(1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(QPointF(s / 2, s * 0.48), QPointF(s / 2, s * 0.72))


def _draw_copy(p: QPainter, s: int, c: QColor):
    p.drawRoundedRect(8, 8, s - 13, s - 13, 2, 2)
    p.drawRoundedRect(4, 4, s - 13, s - 13, 2, 2)


def _draw_folder(p: QPainter, s: int, c: QColor):
    p.drawLine(4, 9, 9, 9)
    p.drawLine(9, 6, 13, 9)
    p.drawRoundedRect(3, 9, s - 6, s - 13, 2, 2)


def _draw_save(p: QPainter, s: int, c: QColor):
    mid = s / 2
    p.drawLine(QPointF(mid, 4), QPointF(mid, s - 8))
    p.drawLine(QPointF(mid - 4, s - 12), QPointF(mid, s - 8))
    p.drawLine(QPointF(mid + 4, s - 12), QPointF(mid, s - 8))
    p.drawLine(QPointF(4, s - 4), QPointF(s - 4, s - 4))


def _draw_trash(p: QPainter, s: int, c: QColor):
    p.drawLine(5, 7, s - 5, 7)
    p.drawLine(9, 5, s - 9, 5)
    p.drawRect(7, 8, s - 14, s - 13)
    p.drawLine(10, 11, 10, s - 7)
    p.drawLine(s - 10, 11, s - 10, s - 7)


def make_icon(kind: str, color: str = TEXT, size: int = 24) -> QIcon:
    fn = {
        "region": _draw_region, "window": _draw_window, "full": _draw_full,
        "pin": _draw_pin, "gear": _draw_gear, "close": _draw_close,
        "list": _draw_list, "help": _draw_help, "info": _draw_info,
        "copy": _draw_copy, "folder": _draw_folder, "save": _draw_save,
        "trash": _draw_trash,
    }[kind]
    return QIcon(_make_pixmap(size, fn, color))


def make_app_icon(size: int = 64) -> QIcon:
    """트레이/창용 앱 아이콘: 파란 바탕 + 핀. (64px 기준 좌표로 그리고 size 에 맞게 배율 조정 —
    빌드 스크립트가 16~256px 을 각각 그려 EXE 아이콘(.ico)을 만든다)"""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.scale(size / 64.0, size / 64.0)
    p.setBrush(QBrush(QColor(ACCENT)))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(2, 2, 60, 60, 14, 14)
    p.translate(32, 34)
    p.rotate(40)
    p.setBrush(QBrush(QColor("white")))
    p.drawRoundedRect(-8, -24, 16, 22, 5, 5)
    p.drawRect(-11, -2, 22, 5)
    pen = QPen(QColor("white")); pen.setWidth(4); pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(0, 5, 0, 22)
    p.end()
    return QIcon(pm)


# ---------------------------------------------------------------------------
# 캡처 백엔드
# ---------------------------------------------------------------------------

def grab_screen_raw(screen) -> QPixmap:
    """해당 모니터 전체를 물리 픽셀 단위로 캡처 (DPR 메타데이터 제거)."""
    pm = screen.grabWindow(0)
    pm.setDevicePixelRatio(1.0)
    return pm


def is_pure_black(img) -> bool:
    """이미지 전체가 완전한 검정(#000000)인지.
    은행·홈택스 등의 보안 프로그램이 '화면 캡처 방지'를 켜면 화면 캡처 결과가 이렇게 통째로 검게 나온다.
    실제 모니터 화면은 작업 표시줄·글자·커서 영역 때문에 픽셀 하나 남김없이 #000000 일 수가 없다.
    (픽셀 비교는 Qt 의 C++ 비교라 2560x1440 도 수 ms)"""
    if img is None:
        return False
    if isinstance(img, QPixmap):
        img = img.toImage()
    if img.isNull() or img.width() <= 0 or img.height() <= 0:
        return False
    im = img.convertToFormat(QImage.Format.Format_RGB32)
    black = QImage(im.size(), QImage.Format.Format_RGB32)
    black.fill(QColor(0, 0, 0))
    return im == black


# 보안 모듈(예: Teruten)은 픽셀이 한두 개만 검정이 아닐 때도 있다. 표본의 이 비율 이상이
# 거의 검정(채널당 0~16)이면 캡처가 막힌 것으로 본다.
MOSTLY_BLACK_RATIO = 0.985
_NEAR_BLACK_MAX = 16


def is_mostly_black(img, ratio: float = MOSTLY_BLACK_RATIO) -> bool:
    """이미지가 거의 전부 검정인지. 완전한 #000000 은 is_pure_black.
    큰 이미지는 격자에서 최대 약 64×64 점을 뽑아 비교한다 (전체 스캔은 하지 않음)."""
    if img is None:
        return False
    if isinstance(img, QPixmap):
        img = img.toImage()
    if img.isNull() or img.width() <= 0 or img.height() <= 0:
        return False
    im = img.convertToFormat(QImage.Format.Format_RGB32)
    w, h = im.width(), im.height()
    step_x = max(1, w // 64)
    step_y = max(1, h // 64)
    total = dark = 0
    for y in range(0, h, step_y):
        for x in range(0, w, step_x):
            c = im.pixel(x, y)
            total += 1
            if ((c & 0xFF) <= _NEAR_BLACK_MAX and ((c >> 8) & 0xFF) <= _NEAR_BLACK_MAX
                    and ((c >> 16) & 0xFF) <= _NEAR_BLACK_MAX):
                dark += 1
    return total > 0 and (dark / total) >= ratio


def screens_capture_blocked(grabs: "list | None" = None) -> bool:
    """모든 모니터의 캡처가 거의 전부 검정이면 True = 보안 프로그램 등이 화면 캡처를 막고 있음.
    grabs 를 주면 이미 찍은 화면들로 판단 (다시 찍지 않음)."""
    if grabs is None:
        grabs = [grab_screen_raw(s) for s in QGuiApplication.screens()]
    return bool(grabs) and all(is_mostly_black(g) for g in grabs)


def screen_under_cursor():
    s = QGuiApplication.screenAt(QCursor.pos())
    return s or QGuiApplication.primaryScreen()


# ---- Windows 전용: 활성 창 캡처 ----
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.windll.user32
    _gdi32 = ctypes.windll.gdi32

    class _BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
            ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
            ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class _BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", _BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

    def _foreground_hwnd(exclude: set):
        hwnd = _user32.GetForegroundWindow()
        if not hwnd or hwnd in exclude:
            pt = wintypes.POINT()
            _user32.GetCursorPos(ctypes.byref(pt))
            h = _user32.WindowFromPoint(pt)
            GA_ROOT = 2
            hwnd = _user32.GetAncestor(h, GA_ROOT) if h else 0
            if hwnd in exclude:
                hwnd = 0
        return hwnd or None

    def _window_rects(hwnd):
        """(보이는 프레임 rect, GetWindowRect) 물리 픽셀 좌표로 반환."""
        wr = wintypes.RECT()
        _user32.GetWindowRect(hwnd, ctypes.byref(wr))
        er = wintypes.RECT()
        DWMWA_EXTENDED_FRAME_BOUNDS = 9
        try:
            ok = ctypes.windll.dwmapi.DwmGetWindowAttribute(
                hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(er), ctypes.sizeof(er))
            if ok != 0:
                er = wr
        except Exception:
            er = wr
        return er, wr

    def _print_window(hwnd) -> "QImage | None":
        """PrintWindow 로 창 내용을 직접 렌더링 (가려져 있어도 캡처됨)."""
        er, wr = _window_rects(hwnd)
        w, h = wr.right - wr.left, wr.bottom - wr.top
        if w <= 0 or h <= 0:
            return None
        hdc_screen = _user32.GetDC(0)
        memdc = _gdi32.CreateCompatibleDC(hdc_screen)
        bmi = _BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h  # top-down
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0  # BI_RGB
        bits = ctypes.c_void_p()
        hbmp = _gdi32.CreateDIBSection(hdc_screen, ctypes.byref(bmi), 0,
                                       ctypes.byref(bits), None, 0)
        img = None
        if hbmp:
            old = _gdi32.SelectObject(memdc, hbmp)
            PW_RENDERFULLCONTENT = 0x00000002
            ok = _user32.PrintWindow(hwnd, memdc, PW_RENDERFULLCONTENT)
            if ok:
                buf = ctypes.string_at(bits, w * h * 4)
                img = QImage(buf, w, h, w * 4, QImage.Format.Format_RGB32).copy()
                # 보이는 프레임만 남기고 그림자·투명 테두리 제거
                dx, dy = er.left - wr.left, er.top - wr.top
                ew, eh = er.right - er.left, er.bottom - er.top
                crop = QRect(dx, dy, ew, eh).intersected(QRect(0, 0, w, h))
                if crop.isValid() and crop != QRect(0, 0, w, h):
                    img = img.copy(crop)
            _gdi32.SelectObject(memdc, old)
            _gdi32.DeleteObject(hbmp)
        _gdi32.DeleteDC(memdc)
        _user32.ReleaseDC(0, hdc_screen)
        return img

    def capture_active_window(exclude_hwnds: set, fallback_hwnd=None) -> "QImage | None":
        hwnd = _foreground_hwnd(exclude_hwnds)
        if not hwnd and fallback_hwnd and fallback_hwnd not in exclude_hwnds:
            hwnd = fallback_hwnd    # 직전에 활성화돼 있던 외부 창
        if not hwnd:
            return None
        img = _print_window(hwnd)
        if img is not None and not img.isNull():
            return img
        # 폴백: 화면에서 창 영역을 잘라냄
        er, _ = _window_rects(hwnd)
        s = screen_under_cursor()
        raw = grab_screen_raw(s)
        dpr = s.devicePixelRatio()
        sg = s.geometry()
        phys = QRect(int(er.left - sg.x() * dpr), int(er.top - sg.y() * dpr),
                     er.right - er.left, er.bottom - er.top)
        phys = phys.intersected(QRect(0, 0, raw.width(), raw.height()))
        if not phys.isValid():
            return raw.toImage()
        return raw.copy(phys).toImage()
else:
    def capture_active_window(exclude_hwnds: set, fallback_hwnd=None) -> "QImage | None":
        # Windows 외 환경(테스트용): 마우스가 있는 모니터 전체로 대체
        return grab_screen_raw(screen_under_cursor()).toImage()


# ---------------------------------------------------------------------------
# 영역 선택 오버레이 (화면 정지 방식, 모니터별 1개)
# ---------------------------------------------------------------------------
class SelectionOverlay(QWidget):
    selected = Signal(QImage, QPoint)   # (잘라낸 이미지, 선택 영역의 전역 논리 좌표)
    canceled = Signal()

    def __init__(self, screen, frozen: QPixmap):
        super().__init__(None)
        self._screen = screen
        self._frozen = frozen           # 물리 픽셀 pixmap (DPR=1)
        self._origin = None             # 드래그 시작점 (위젯 좌표)
        self._current = None
        self._mouse = QPoint(-1, -1)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(screen.geometry())

    # --- 좌표 매핑: 위젯(논리) → frozen pixmap(물리) ---
    def _to_phys(self, r: QRect) -> QRect:
        sx = self._frozen.width() / max(1, self.width())
        sy = self._frozen.height() / max(1, self.height())
        return QRect(round(r.x() * sx), round(r.y() * sy),
                     round(r.width() * sx), round(r.height() * sy))

    def _sel_rect(self) -> "QRect | None":
        if self._origin is None or self._current is None:
            return None
        return QRect(self._origin, self._current).normalized()

    # --- 이벤트 ---
    def enterEvent(self, e):
        self.activateWindow()
        self.setFocus(Qt.FocusReason.MouseFocusReason)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.canceled.emit()
        else:
            super().keyPressEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._origin = e.position().toPoint()
            self._current = self._origin
            self.update()
        elif e.button() == Qt.MouseButton.RightButton:
            self.canceled.emit()

    def mouseMoveEvent(self, e):
        self._mouse = e.position().toPoint()
        if self._origin is not None:
            self._current = self._mouse
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton or self._origin is None:
            return
        sel = self._sel_rect()
        self._origin = self._current = None
        if sel is None or sel.width() < 4 or sel.height() < 4:
            self.update()   # 클릭만 한 경우: 취소 아님, 다시 드래그 대기
            return
        phys = self._to_phys(sel).intersected(self._frozen.rect())
        img = self._frozen.copy(phys).toImage()
        gpos = sel.topLeft() + self._screen.geometry().topLeft()
        self.selected.emit(img, gpos)

    # --- 그리기 ---
    def paintEvent(self, e):
        p = QPainter(self)
        p.drawPixmap(self.rect(), self._frozen)           # 정지 화면
        p.fillRect(self.rect(), QColor(0, 0, 0, 110))     # 어둡게
        sel = self._sel_rect()
        if sel is not None and sel.isValid():
            src = self._to_phys(sel)
            p.drawPixmap(sel, self._frozen, src)          # 선택 영역만 밝게
            pen = QPen(QColor(ACCENT)); pen.setWidth(2)
            p.setPen(pen)
            p.drawRect(sel.adjusted(0, 0, -1, -1))
            self._draw_size_label(p, sel)
        elif self._mouse.x() >= 0:
            pen = QPen(QColor(255, 255, 255, 150)); pen.setWidth(1)
            p.setPen(pen)
            p.drawLine(0, self._mouse.y(), self.width(), self._mouse.y())
            p.drawLine(self._mouse.x(), 0, self._mouse.x(), self.height())
            hint = "드래그해서 영역을 고르세요  ·  Esc 또는 우클릭으로 취소"
            self._draw_tag(p, QPoint(self._mouse.x() + 14, self._mouse.y() + 18), hint)
        p.end()

    def _draw_size_label(self, p: QPainter, sel: QRect):
        phys = self._to_phys(sel)
        text = f"{phys.width()} × {phys.height()} px"
        pos = QPoint(sel.x(), sel.y() - 26)
        if pos.y() < 4:
            pos.setY(sel.y() + 6)
        self._draw_tag(p, pos, text)

    def _draw_tag(self, p: QPainter, pos: QPoint, text: str):
        f = QFont(self.font()); f.setPointSize(9)
        p.setFont(f)
        br = p.fontMetrics().boundingRect(text)
        r = QRect(pos, QSize(br.width() + 14, br.height() + 8))
        r.moveLeft(min(r.left(), self.width() - r.width() - 4))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 26, 36, 215))
        p.drawRoundedRect(r, 4, 4)
        p.setPen(QColor("white"))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, text)


class RegionCaptureSession(QObject):
    """모든 모니터에 오버레이를 띄우고 첫 선택/취소를 받아 정리."""
    finished = Signal(object, object)   # (QImage | None, QPoint | None)
    blocked = Signal()                  # 화면 캡처가 차단됨 (모든 모니터가 거의 전부 검정)

    def __init__(self):
        super().__init__()
        self._overlays = []
        self._done = False

    def start(self):
        screens = QGuiApplication.screens()
        frozens = [grab_screen_raw(s) for s in screens]
        if screens_capture_blocked(frozens):
            # 검은 화면을 모니터 전체에 띄우면 '화면이 꺼진 것처럼' 보이므로 띄우지 않고 알린다
            self._done = True
            QTimer.singleShot(0, self._emit_blocked)
            return
        for screen, frozen in zip(screens, frozens):
            ov = SelectionOverlay(screen, frozen)
            ov.selected.connect(self._on_selected)
            ov.canceled.connect(self._on_canceled)
            self._overlays.append(ov)
            ov.show()
        cur = screen_under_cursor()
        for ov in self._overlays:
            if ov._screen is cur:
                ov.activateWindow()
                ov.setFocus()

    def _emit_blocked(self):
        self.finished.emit(None, None)   # 먼저 캡처 상태 해제·창 복구
        self.blocked.emit()

    def _cleanup(self):
        for ov in self._overlays:
            ov.blockSignals(True)
            ov.close()
        self._overlays.clear()

    def _on_selected(self, img: QImage, gpos: QPoint):
        if self._done:
            return
        self._done = True
        self._cleanup()
        self.finished.emit(img, gpos)

    def _on_canceled(self):
        if self._done:
            return
        self._done = True
        self._cleanup()
        self.finished.emit(None, None)


# ---------------------------------------------------------------------------
# 핀 창 (항상 위 이미지 고정) + OCR + 최근 핀
# ---------------------------------------------------------------------------
OPACITY_STEPS = (100, 80, 60, 40)   # 핀 메뉴·Ctrl+휠 이 오가는 투명도 (%)

OCR_UNAVAILABLE_MSG = (
    "Windows OCR을 사용할 수 없어요.\n"
    "Windows 설정 → 시간 및 언어 → 언어 및 지역에서 한국어 또는 영어를 추가하고, "
    "그 언어의 '광학 문자 인식'을 설치한 뒤 다시 시도해 주세요."
)
OCR_NO_LANGUAGE_MSG = (
    "글자를 읽을 언어 팩이 없어요.\n"
    "Windows 설정 → 시간 및 언어 → 언어 및 지역에서 한국어나 영어를 추가하고, "
    "해당 언어의 '광학 문자 인식'을 설치해 주세요."
)
OCR_EMPTY_MSG = "이미지에서 글자를 찾지 못했어요."
OCR_FAILED_MSG = "글자를 읽지 못했어요. 잠시 뒤 다시 시도해 주세요."
OCR_COPIED_MSG = "글자를 복사했어요."
_OCR_LANG_ORDER = ("ko-KR", "ko", "en-US", "en")


class OcrResult:
    """recognize_image 의 결과. message 는 사용자에게 보여줄 한국어 문장."""

    def __init__(self, ok: bool, text: str, message: str):
        self.ok = ok
        self.text = text
        self.message = message


def format_hotkey(combo: str) -> str:
    """pynput 표기 `<ctrl>+<alt>+x` 를 `Ctrl+Alt+X` 로."""
    names = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "cmd": "Win"}
    parts = []
    for raw in (combo or "").split("+"):
        key = raw.strip().strip("<>").lower()
        if not key:
            continue
        parts.append(names.get(key, key.upper()))
    return "+".join(parts)


def iter_hotkey_bindings(hotkeys: dict):
    """(모드, 조합) 을 순서대로. 빈 조합과 이미 쓴 조합(먼저 등록된 모드가 이김)은 건너뜀."""
    seen = set()
    for mode, combo in hotkeys.items():
        combo = (combo or "").strip()
        if not combo:
            continue
        if combo in seen:
            print(f"[hotkey] '{combo}' 가 이미 쓰여 '{mode}' 는 건너뜀")
            continue
        seen.add(combo)
        yield mode, combo


def duplicate_hotkey(hotkeys: dict) -> str:
    """두 모드가 같은 비어 있지 않은 조합을 쓰면 그 조합을, 없으면 빈 문자열."""
    seen = set()
    for _mode, combo in hotkeys.items():
        combo = (combo or "").strip()
        if not combo:
            continue
        if combo in seen:
            return combo
        seen.add(combo)
    return ""


def _import_ocr_modules() -> dict:
    """Windows.Media.Ocr (PyWinRT). 없거나 Windows 가 아니면 ImportError 등으로 실패한다."""
    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage.streams import DataWriter
    return {
        "Language": Language,
        "BitmapPixelFormat": BitmapPixelFormat,
        "SoftwareBitmap": SoftwareBitmap,
        "OcrEngine": OcrEngine,
        "DataWriter": DataWriter,
    }


def _pick_ocr_engine(OcrEngine, Language):
    """한국어를 먼저, 그다음 영어. 둘 다 없으면 사용자 프로필 언어."""
    for tag in _OCR_LANG_ORDER:
        try:
            lang = Language(tag)
        except Exception:
            continue
        try:
            supported = bool(OcrEngine.is_language_supported(lang))
        except Exception:
            supported = False
        if not supported:
            continue
        try:
            engine = OcrEngine.try_create_from_language(lang)
        except Exception:
            engine = None
        if engine is not None:
            return engine
    langs = []
    for name in ("get_available_recognizer_languages", "try_get_available_languages"):
        fn = getattr(OcrEngine, name, None)
        if fn is None:
            continue
        try:
            langs = list(fn() or [])
        except Exception:
            langs = []
        if langs:
            break

    def tag_of(lang) -> str:
        return (getattr(lang, "language_tag", "") or "").lower()

    for prefixes in (("ko",), ("en",)):
        for lang in langs:
            t = tag_of(lang)
            if not any(t == p or t.startswith(p + "-") for p in prefixes):
                continue
            try:
                engine = OcrEngine.try_create_from_language(lang)
            except Exception:
                engine = None
            if engine is not None:
                return engine
    try:
        return OcrEngine.try_create_from_user_profile_languages()
    except Exception:
        return None


def _prepare_ocr_image(image: QImage) -> QImage:
    """Windows OCR 이 받는 크기(대략 40~2000px)로 맞춘다."""
    im = image
    w, h = im.width(), im.height()
    long_side = max(w, h)
    if long_side > 2000:
        scale = 2000 / long_side
        im = im.scaled(max(1, round(w * scale)), max(1, round(h * scale)),
                       Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
        w, h = im.width(), im.height()
    if w < 40 or h < 40:
        canvas = QImage(max(w, 40), max(h, 40), QImage.Format.Format_ARGB32)
        canvas.fill(QColor(255, 255, 255))
        painter = QPainter(canvas)
        painter.drawImage(0, 0, im)
        painter.end()
        im = canvas
    return im


def _rgba_bytes(image: QImage) -> "tuple[bytes, int, int]":
    im = image.convertToFormat(QImage.Format.Format_RGBA8888)
    w, h = im.width(), im.height()
    bpl = im.bytesPerLine()
    mv = memoryview(im.constBits())
    row = w * 4
    if bpl == row:
        return bytes(mv[:h * row]), w, h
    out = bytearray(h * row)
    for y in range(h):
        out[y * row:(y + 1) * row] = mv[y * bpl:y * bpl + row]
    return bytes(out), w, h


def _bitmap_from_rgba(data: bytes, w: int, h: int, mods: dict):
    writer = mods["DataWriter"]()
    try:
        writer.write_bytes(data)
    except TypeError:
        writer.write_bytes(list(data))
    buf = writer.detach_buffer()
    fmt = mods["BitmapPixelFormat"].RGBA8
    bitmap_cls = mods["SoftwareBitmap"]
    if hasattr(bitmap_cls, "create_copy_from_buffer"):
        return bitmap_cls.create_copy_from_buffer(buf, fmt, w, h)
    bitmap = bitmap_cls(fmt, w, h)
    bitmap.copy_from_buffer(buf)
    return bitmap


def _await_ocr(operation):
    if hasattr(operation, "__await__"):
        import asyncio
        try:
            return asyncio.run(operation)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(operation)
            finally:
                loop.close()
    if hasattr(operation, "get"):
        return operation.get()
    return operation


def recognize_image(image: QImage) -> OcrResult:
    """핀 이미지에서 글자를 읽는다. 모듈·언어 팩이 없으면 안내 문장을 돌려준다.
    Windows.Media.Ocr 을 쓰며, 한국어를 영어보다 먼저 고른다. 화면 보호를 우회하지 않는다."""
    if image is None or (hasattr(image, "isNull") and image.isNull()):
        return OcrResult(False, "", "이미지가 없어요.")
    try:
        mods = _import_ocr_modules()
    except Exception as e:
        print(f"[ocr] 모듈을 불러오지 못함: {e}")
        return OcrResult(False, "", OCR_UNAVAILABLE_MSG)
    try:
        engine = _pick_ocr_engine(mods["OcrEngine"], mods["Language"])
    except Exception as e:
        print(f"[ocr] 엔진 준비 실패: {e}")
        return OcrResult(False, "", OCR_NO_LANGUAGE_MSG)
    if engine is None:
        return OcrResult(False, "", OCR_NO_LANGUAGE_MSG)
    try:
        prepared = _prepare_ocr_image(image)
        data, w, h = _rgba_bytes(prepared)
        bitmap = _bitmap_from_rgba(data, w, h, mods)
        result = _await_ocr(engine.recognize_async(bitmap))
        text = (getattr(result, "text", "") or "").strip()
    except Exception as e:
        print(f"[ocr] 인식 실패: {e}")
        return OcrResult(False, "", OCR_FAILED_MSG)
    if not text:
        return OcrResult(False, "", OCR_EMPTY_MSG)
    return OcrResult(True, text, OCR_COPIED_MSG)


def _set_win32_click_through(hwnd: int, on: bool) -> None:
    """WS_EX_TRANSPARENT (+ LAYERED when on). 끄면 TRANSPARENT 만 뺀다 (투명도용 LAYERED 는 유지)."""
    if not IS_WINDOWS or not hwnd:
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        # windll 의 전역 프로토타입은 건드리지 않는다 (다른 호출과 겹치지 않게).
        get_name = "GetWindowLongPtrW" if hasattr(user32, "GetWindowLongPtrW") else "GetWindowLongW"
        set_name = "SetWindowLongPtrW" if hasattr(user32, "SetWindowLongPtrW") else "SetWindowLongW"
        get_long = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_int)((get_name, user32))
        set_long = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t)((set_name, user32))
        style = int(get_long(hwnd, GWL_EXSTYLE) or 0)
        if on:
            style |= WS_EX_LAYERED | WS_EX_TRANSPARENT
        else:
            style &= ~WS_EX_TRANSPARENT
        set_long(hwnd, GWL_EXSTYLE, style)
    except Exception as e:
        print(f"[pin] 클릭 통과 스타일 변경 실패: {e}")


class PinToast(QWidget):
    """핀 옆에 잠깐 떴다 사라지는 안내. 클릭 통과 중인 핀과 따로 떠 있다."""

    def __init__(self, text: str, anchor: "QWidget | None" = None, msec: int = 1800):
        super().__init__(None)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.Tool
                            | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setMaximumWidth(360)
        self.label.setStyleSheet(
            "background:#1F2430; color:white; padding:8px 12px; border-radius:8px; font-size:12px;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.label)
        self.adjustSize()
        if anchor is not None:
            g = anchor.frameGeometry()
            x = g.center().x() - self.width() // 2
            y = g.top() - self.height() - 8
            screen = QGuiApplication.screenAt(g.center()) or QGuiApplication.primaryScreen()
            if screen is not None:
                bounds = screen.availableGeometry()
                x = min(max(x, bounds.left() + 4), bounds.right() - self.width() - 4)
                y = min(max(y, bounds.top() + 4), bounds.bottom() - self.height() - 4)
            self.move(x, y)
        self.show()
        QTimer.singleShot(max(400, int(msec)), self.close)


def recent_pin_dir() -> Path:
    """닫은 핀 PNG 를 두는 임시 폴더. 시험은 PINCAP_RECENT_DIR 로 격리한다."""
    override = os.environ.get("PINCAP_RECENT_DIR")
    return Path(override) if override else Path(tempfile.gettempdir()) / "pincapture-recent-pins"


class RecentPinStore:
    """닫은 핀을 최신 순으로 최대 N개. 메모리의 QImage 와 임시 폴더의 PNG 를 함께 둔다."""

    def __init__(self, limit: int = 10, directory: "Path | None" = None):
        self.directory = Path(directory) if directory is not None else recent_pin_dir()
        self.limit = _clamp_recent_limit(limit)
        self.items: list = []
        self._seq = 0
        self._load()

    def count(self) -> int:
        return len(self.items)

    def set_limit(self, limit: int) -> None:
        self.limit = _clamp_recent_limit(limit)
        self._trim()

    def remember(self, pin: "PinWindow") -> None:
        img = getattr(pin, "_img", None)
        if img is None or img.isNull():
            return
        png = meta = None
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            self._seq += 1
            stamp = f"{datetime.datetime.now():%Y%m%d_%H%M%S_%f}_{self._seq:04d}"
            png = self.directory / f"{stamp}.png"
            meta = self.directory / f"{stamp}.json"
            if not img.save(str(png), "PNG"):
                print(f"[recent] PNG 저장 실패: {png}")
                return
            info = {
                "x": int(pin.x()),
                "y": int(pin.y()),
                "scale": float(pin._scale),
                "opacity": int(pin._opacity),
                "dpr": float(pin._dpr),
            }
            meta.write_text(json.dumps(info), encoding="utf-8")
        except Exception as e:
            print(f"[recent] 보관 실패: {e}")
            for path in (png, meta):
                if path is not None:
                    try:
                        path.unlink(missing_ok=True)
                    except Exception:
                        pass
            return
        self.items.insert(0, {"id": stamp, "png": png, "meta": meta, "image": img.copy(), **info})
        self._trim()

    def pop_latest(self) -> "dict | None":
        while self.items:
            item = self.items.pop(0)
            img = item.get("image")
            if img is None or (hasattr(img, "isNull") and img.isNull()):
                loaded = QImage(str(item.get("png", "")))
                img = loaded if not loaded.isNull() else None
            self._unlink(item)
            if img is not None and not img.isNull():
                item["image"] = img
                return item
        return None

    def _trim(self) -> None:
        while len(self.items) > self.limit:
            self._unlink(self.items.pop())

    def _unlink(self, item: dict) -> None:
        for key in ("png", "meta"):
            path = item.get(key)
            if not path:
                continue
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass

    def _load(self) -> None:
        try:
            if not self.directory.is_dir():
                return
            metas = sorted(self.directory.glob("*.json"), reverse=True)
        except Exception as e:
            print(f"[recent] 목록 읽기 실패: {e}")
            return
        for meta in metas:
            if len(self.items) >= self.limit:
                self._unlink({"png": meta.with_suffix(".png"), "meta": meta})
                continue
            try:
                info = json.loads(meta.read_text(encoding="utf-8"))
                png = meta.with_suffix(".png")
                img = QImage(str(png))
                if img.isNull():
                    self._unlink({"png": png, "meta": meta})
                    continue
                self.items.append({
                    "id": meta.stem,
                    "png": png,
                    "meta": meta,
                    "image": img,
                    "x": int(info.get("x", 0)),
                    "y": int(info.get("y", 0)),
                    "scale": float(info.get("scale", 1.0)),
                    "opacity": int(info.get("opacity", 100)),
                    "dpr": float(info.get("dpr", 1.0)),
                })
            except Exception as e:
                print(f"[recent] {meta.name} 읽기 실패: {e}")


class PinWindow(QWidget):
    closed = Signal(object)

    def __init__(self, image: QImage, dpr: float = 1.0):
        super().__init__(None)
        self._img = image
        self._pm = QPixmap.fromImage(image)
        self._dpr = max(1.0, dpr)
        self._scale = 1.0
        self._opacity = 100
        self._click_through = False
        self._drag = None
        self._toast = None
        self.release_hotkey = ""          # 클릭 통과를 끄는 전역 단축키 (표시용)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle("핀 고정")
        self._apply_size()
        self.setToolTip("드래그로 옮기고, 휠로 크기를 조절해요. Ctrl+휠은 투명도, 우클릭은 메뉴, 더블클릭이나 Esc는 닫기예요.")

    @property
    def opacity_percent(self) -> int:
        return self._opacity

    @property
    def click_through(self) -> bool:
        return self._click_through

    def _logical_size(self) -> QSize:
        return QSize(max(1, round(self._pm.width() / self._dpr * self._scale)),
                     max(1, round(self._pm.height() / self._dpr * self._scale)))

    def _apply_size(self):
        self.resize(self._logical_size())

    def set_opacity(self, percent: int) -> None:
        percent = int(percent)
        if percent not in OPACITY_STEPS:
            percent = min(OPACITY_STEPS, key=lambda step: abs(step - percent))
        self._opacity = percent
        self.setWindowOpacity(percent / 100.0)

    def adjust_opacity_step(self, direction: int) -> None:
        """direction +1 은 더 불투명(휠 위), -1 은 더 투명."""
        if self._opacity in OPACITY_STEPS:
            idx = OPACITY_STEPS.index(self._opacity)
        else:
            idx = min(range(len(OPACITY_STEPS)), key=lambda i: abs(OPACITY_STEPS[i] - self._opacity))
        idx = max(0, min(len(OPACITY_STEPS) - 1, idx - direction))
        self.set_opacity(OPACITY_STEPS[idx])

    def set_click_through(self, on: bool) -> None:
        """클릭을 뒤 창으로 통과시킨다. 켜면 이 핀의 메뉴·드래그로는 끌 수 없다."""
        on = bool(on)
        if on == self._click_through:
            return
        self._click_through = on
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, on)
        self.setWindowOpacity(self._opacity / 100.0)
        self.show()
        _set_win32_click_through(int(self.winId()), on)
        self.setWindowOpacity(self._opacity / 100.0)
        if on:
            hint = format_hotkey(self.release_hotkey) or "단축키"
            self.show_toast(
                "클릭 통과를 켰어요. 마우스가 핀 아래 창으로 전달돼요.\n"
                f"끄려면 트레이의 '클릭 통과 해제' 또는 {hint} 를 눌러 주세요.",
                msec=4200)

    def show_toast(self, text: str, msec: int = 1800) -> PinToast:
        if self._toast is not None:
            try:
                self._toast.close()
            except Exception:
                pass
        self._toast = PinToast(text, self, msec)
        return self._toast

    def copy_ocr(self) -> OcrResult:
        result = recognize_image(self._img)
        if result.ok and result.text:
            QApplication.clipboard().setText(result.text)
        self.show_toast(result.message, 1800 if result.ok else 4200)
        return result

    def build_menu(self) -> "tuple[QMenu, dict]":
        m = QMenu(self)
        acts = {
            "ocr": m.addAction("글자 복사(OCR)"),
            "copy": m.addAction("클립보드에 복사"),
            "save": m.addAction("다른 이름으로 저장…"),
            "orig": m.addAction("원본 크기 (100%)"),
        }
        opacity_menu = m.addMenu("투명도")
        acts["opacity"] = {}
        for pct in OPACITY_STEPS:
            act = opacity_menu.addAction(f"{pct}%")
            act.setCheckable(True)
            act.setChecked(pct == self._opacity)
            acts["opacity"][pct] = act
        acts["click"] = m.addAction("클릭 통과")
        acts["click"].setCheckable(True)
        acts["click"].setChecked(self._click_through)
        m.addSeparator()
        acts["close"] = m.addAction("닫기")
        return m, acts

    def apply_menu_action(self, chosen, acts: dict) -> None:
        if chosen is None:
            return
        if chosen == acts["ocr"]:
            self.copy_ocr()
        elif chosen == acts["copy"]:
            QApplication.clipboard().setImage(self._img)
        elif chosen == acts["save"]:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path, _ = QFileDialog.getSaveFileName(
                self, "저장", str(Path.home() / f"핀캡처_{ts}.png"),
                "PNG (*.png);;JPEG (*.jpg)")
            if path:
                self._img.save(path)
        elif chosen == acts["orig"]:
            self._scale = 1.0
            self._apply_size()
        elif chosen in acts["opacity"].values():
            for pct, act in acts["opacity"].items():
                if chosen == act:
                    self.set_opacity(pct)
                    break
        elif chosen == acts["click"]:
            self.set_click_through(acts["click"].isChecked())
        elif chosen == acts["close"]:
            self.close()

    # --- 이벤트 ---
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.drawPixmap(self.rect(), self._pm)
        pen = QPen(QColor(ACCENT)); pen.setWidth(2)
        p.setPen(pen)
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        p.end()

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.adjust_opacity_step(1 if e.angleDelta().y() > 0 else -1)
            e.accept()
            return
        step = 1.1 if e.angleDelta().y() > 0 else 1 / 1.1
        self._scale = min(5.0, max(0.15, self._scale * step))
        self._apply_size()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None and (e.buttons() & Qt.MouseButton.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def mouseDoubleClickEvent(self, e):
        self.close()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.close()

    def closeEvent(self, e):
        self.closed.emit(self)
        super().closeEvent(e)

    def contextMenuEvent(self, e):
        menu, acts = self.build_menu()
        chosen = menu.exec(e.globalPos())
        self.apply_menu_action(chosen, acts)


# ---------------------------------------------------------------------------
# 보관함 (캡처 기록): 메인에 최신/선택 캡처, 우측에 이전 캡처 썸네일 리스트
# ---------------------------------------------------------------------------
class HistoryEntry:
    """캡처 1건: 메모리 이미지 또는 저장된 파일 경로."""
    THUMB_W = 168

    def __init__(self, image: "QImage | None" = None, path: "str | None" = None,
                 ts: "datetime.datetime | None" = None):
        self._image = image
        self.path = path
        self.ts = ts or datetime.datetime.now()
        self._thumb = None
        self._size = (image.width(), image.height()) if image is not None else None

    def full_image(self) -> "QImage | None":
        if self._image is not None:
            return self._image
        if self.path and Path(self.path).exists():
            img = QImage(self.path)
            if not img.isNull():
                self._size = (img.width(), img.height())
                return img
        return None

    def thumbnail(self) -> "QPixmap | None":
        if self._thumb is not None:
            return self._thumb
        pm = None
        if self._image is not None:
            img = self._image
            if img.width() > self.THUMB_W:
                img = img.scaledToWidth(self.THUMB_W,
                                        Qt.TransformationMode.SmoothTransformation)
            pm = QPixmap.fromImage(img)
        elif self.path and Path(self.path).exists():
            reader = QImageReader(self.path)
            sz = reader.size()
            if sz.isValid():
                self._size = (sz.width(), sz.height())
                if sz.width() > self.THUMB_W:
                    reader.setScaledSize(QSize(
                        self.THUMB_W,
                        max(1, round(sz.height() * self.THUMB_W / sz.width()))))
            img = reader.read()
            if not img.isNull():
                pm = QPixmap.fromImage(img)
        self._thumb = pm
        return pm

    def label(self) -> str:
        fmt = "%H:%M:%S" if self.ts.date() == datetime.date.today() else "%m/%d %H:%M"
        t = self.ts.strftime(fmt)
        return f"{t}\n{self._size[0]}×{self._size[1]}" if self._size else t


class PreviewPane(QWidget):
    """보관함 메인 미리보기 (비율 유지, 100% 이상 확대 안 함)."""

    def __init__(self):
        super().__init__()
        self._pm = None
        self.setMinimumSize(320, 240)

    def set_image(self, img: "QImage | None"):
        self._pm = QPixmap.fromImage(img) if (img is not None and not img.isNull()) else None
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#2B303A"))
        if self._pm is None:
            p.setPen(QColor("#8A93A3"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "아직 캡처가 없어요\n위쪽 버튼이나 단축키로 화면을 찍어 보세요")
            p.end()
            return
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        area = self.rect().adjusted(14, 14, -14, -14)
        size = self._pm.size().scaled(area.size(), Qt.AspectRatioMode.KeepAspectRatio)
        if size.width() >= self._pm.width():
            size = self._pm.size()      # 원본보다 크게 늘리지 않음
        target = QRect(QPoint(0, 0), size)
        target.moveCenter(area.center())
        p.drawPixmap(target, self._pm)
        p.setPen(QPen(QColor("#4A5160")))
        p.drawRect(target.adjusted(-1, -1, 0, 0))
        p.end()


# ---------------------------------------------------------------------------
# 전역 단축키 (pynput — 실패해도 앱은 동작)
# ---------------------------------------------------------------------------
class HotkeyManager(QObject):
    triggered = Signal(str)   # region | window | full | pin | reopen_pin | clickthrough

    def __init__(self):
        super().__init__()
        self._listener = None
        self.available = False
        self.error = ""

    def restart(self, hotkeys: dict):
        self.stop()
        try:
            from pynput import keyboard
        except Exception as e:
            self.available = False
            self.error = f"pynput 사용 불가: {e}"
            print(f"[hotkey] {self.error}")
            return
        mapping = {}
        for mode, combo in iter_hotkey_bindings(hotkeys):
            try:
                keyboard.HotKey.parse(combo)
            except Exception as e:
                print(f"[hotkey] '{combo}' 형식 오류, 건너뜀: {e}")
                continue
            mapping[combo] = (lambda m=mode: self.triggered.emit(m))
        if not mapping:
            self.available = False
            return
        try:
            self._listener = keyboard.GlobalHotKeys(mapping)
            self._listener.daemon = True
            self._listener.start()
            self.available = True
            self.error = ""
        except Exception as e:
            self.available = False
            self.error = str(e)
            print(f"[hotkey] 등록 실패: {e}")

    def stop(self):
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None


# ---------------------------------------------------------------------------
# 작업 표시줄 식별 (Windows)
#   창과 바로가기에 같은 AppUserModelID 를 심고, 창에는 재실행 명령/이름/아이콘까지 기록한다.
#   이게 없으면 '작업 표시줄에 고정' 했을 때 Windows 가 pythonw.exe 자체를 고정해 Python 아이콘이 뜬다.
# ---------------------------------------------------------------------------
def app_icon_path() -> "Path | None":
    """바로가기/작업 표시줄에 쓸 아이콘 파일. EXE 는 자기 자신(아이콘 내장),
    스크립트 실행이면 ~/.pincapture/pincapture.ico (없으면 생성)."""
    if FROZEN:
        return Path(sys.executable)
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        ico = CONFIG_DIR / "pincapture.ico"
        if not ico.exists() and not make_app_icon().pixmap(256, 256).save(str(ico), "ICO"):
            return None
        return ico
    except Exception:
        return None


def relaunch_command() -> str:
    """작업 표시줄 고정 아이콘이 실행할 명령 (EXE 면 PinCapture.exe, 스크립트면 pythonw.exe "pincapture.py")."""
    import subprocess
    return subprocess.list2cmdline(launch_argv())


if IS_WINDOWS:
    import ctypes as _ct
    from ctypes import wintypes as _wt

    class _GUID(_ct.Structure):
        _fields_ = [("Data1", _ct.c_ulong), ("Data2", _ct.c_ushort), ("Data3", _ct.c_ushort),
                    ("Data4", _ct.c_ubyte * 8)]

        def __init__(self, s=None):
            super().__init__()
            if s:
                _ct.windll.ole32.CLSIDFromString(_ct.c_wchar_p(s), _ct.byref(self))

    class _PROPERTYKEY(_ct.Structure):
        _fields_ = [("fmtid", _GUID), ("pid", _wt.DWORD)]

    class _PROPVARIANT(_ct.Structure):
        _fields_ = [("vt", _ct.c_ushort), ("r1", _ct.c_ushort), ("r2", _ct.c_ushort),
                    ("r3", _ct.c_ushort), ("data", _ct.c_byte * 16)]

    _IID_IPropertyStore = _GUID("{886d8eeb-8cf2-4446-8d02-cdba1dbdcf99}")
    _FMTID_AppUserModel = "{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"
    _PKEY = {"RelaunchCommand": 2, "RelaunchIconResource": 3,      # System.AppUserModel.*
             "RelaunchDisplayNameResource": 4, "ID": 5}
    _CSIDL = {"Desktop": 0x10, "Startup": 0x07, "Programs": 0x02}

    def _special_folder(name: str) -> Path:
        buf = _ct.create_unicode_buffer(260)
        _ct.windll.shell32.SHGetFolderPathW(None, _CSIDL[name], None, 0, buf)
        return Path(buf.value)

    def _com_method(obj, index, *argtypes):
        vtable = _ct.cast(obj, _ct.POINTER(_ct.c_void_p))[0]
        fn = _ct.cast(vtable, _ct.POINTER(_ct.c_void_p))[index]
        return _ct.WINFUNCTYPE(_ct.c_long, _ct.c_void_p, *argtypes)(fn)

    def _propstore_set(ps, props: dict) -> None:
        """IPropertyStore 에 문자열 속성을 쓰고 Commit. vtable: 0-2 IUnknown, 5 GetValue, 6 SetValue, 7 Commit."""
        SetValue = _com_method(ps, 6, _ct.POINTER(_PROPERTYKEY), _ct.POINTER(_PROPVARIANT))
        Commit = _com_method(ps, 7)
        Release = _com_method(ps, 2)
        try:
            for name, val in props.items():
                key = _PROPERTYKEY(_GUID(_FMTID_AppUserModel), _PKEY[name])
                pv = _PROPVARIANT()
                pv.vt = 31                                        # VT_LPWSTR
                p = _ct.c_void_p()
                if _ct.windll.shlwapi.SHStrDupW(_ct.c_wchar_p(val), _ct.byref(p)) != 0:
                    raise OSError("SHStrDupW 실패")
                _ct.cast(pv.data, _ct.POINTER(_ct.c_void_p))[0] = p.value
                hr = SetValue(ps, _ct.byref(key), _ct.byref(pv))
                _ct.windll.ole32.PropVariantClear(_ct.byref(pv))
                if hr < 0:
                    raise OSError(f"SetValue({name}) hr={hr & 0xffffffff:#x}")
            hr = Commit(ps)
            if hr < 0:
                raise OSError(f"Commit hr={hr & 0xffffffff:#x}")
        finally:
            Release(ps)

    def set_shortcut_app_id(lnk: "str | Path") -> bool:
        """바로가기(.lnk) 파일에 System.AppUserModel.ID 를 기록."""
        try:
            ps = _ct.c_void_p()
            hr = _ct.windll.shell32.SHGetPropertyStoreFromParsingName(
                _ct.c_wchar_p(str(lnk)), None, 2, _ct.byref(_IID_IPropertyStore), _ct.byref(ps))  # GPS_READWRITE
            if hr < 0:
                raise OSError(f"SHGetPropertyStoreFromParsingName hr={hr & 0xffffffff:#x}")
            _propstore_set(ps, {"ID": APP_USER_MODEL_ID})
            return True
        except Exception as e:
            print(f"[taskbar] 바로가기 AppID 기록 실패 ({lnk}): {e}")
            return False

    def set_window_taskbar_identity(hwnd: int) -> bool:
        """메인 창에 AppID + 재실행 명령/이름/아이콘을 기록 → 실행 중 창에서 고정해도 핀캡처로 고정됨."""
        try:
            props = {"ID": APP_USER_MODEL_ID,
                     "RelaunchCommand": relaunch_command(),
                     "RelaunchDisplayNameResource": APP_NAME}
            ico = app_icon_path()
            if ico:
                props["RelaunchIconResource"] = f"{ico},0"
            ps = _ct.c_void_p()
            hr = _ct.windll.shell32.SHGetPropertyStoreForWindow(
                _wt.HWND(hwnd), _ct.byref(_IID_IPropertyStore), _ct.byref(ps))
            if hr < 0:
                raise OSError(f"SHGetPropertyStoreForWindow hr={hr & 0xffffffff:#x}")
            _propstore_set(ps, props)
            return True
        except Exception as e:
            print(f"[taskbar] 창 식별 정보 설정 실패: {e}")
            return False

    def force_foreground(hwnd: int) -> bool:
        """창을 확실히 전경으로. Windows 는 마지막 입력을 받지 않은 프로세스의 SetForegroundWindow 를
        막고 작업 표시줄만 깜빡이게 한다. 단계적으로 우회:
          1) 그냥 SetForegroundWindow
          2) 전경 창의 입력 스레드에 잠시 붙어서(AttachThreadInput) 전환
          3) Alt 키를 누른 상태로 전환하고 놓기 (놓는 입력은 이미 전경이 된 우리 창으로 감)
          4) 그래도 안 되면 TOPMOST 켰다 끄기로 화면 맨 앞에라도 두고 작업 표시줄 깜빡임"""
        if QGuiApplication.platformName() != "windows":
            return False          # offscreen 등: winId 가 실제 HWND 가 아니므로 Win32 에 넘기지 않음
        u = _ct.windll.user32
        k = _ct.windll.kernel32
        h = _wt.HWND(hwnd)
        VK_MENU, KEYEVENTF_KEYUP = 0x12, 0x0002

        def is_fg() -> bool:
            return u.GetForegroundWindow() == hwnd

        try:
            if u.IsIconic(h):
                u.ShowWindow(h, 9)                                  # SW_RESTORE
            if is_fg():
                return True
            u.BringWindowToTop(h)
            u.SetForegroundWindow(h)                                # 1)
            if is_fg():
                return True

            fg = u.GetForegroundWindow()
            cur_tid = k.GetCurrentThreadId()
            fg_tid = u.GetWindowThreadProcessId(fg, None) if fg else 0
            attached = bool(fg_tid and fg_tid != cur_tid and u.AttachThreadInput(fg_tid, cur_tid, True))
            attach_err = 0 if attached else k.GetLastError()
            try:
                if attached:
                    u.BringWindowToTop(h)
                    u.SetForegroundWindow(h)                        # 2)
            finally:
                if attached:
                    u.AttachThreadInput(fg_tid, cur_tid, False)
            if is_fg():
                return True

            u.keybd_event(VK_MENU, 0, 0, 0)                         # 3)
            try:
                u.BringWindowToTop(h)
                u.SetForegroundWindow(h)
            finally:
                u.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
            if is_fg():
                return True

            flags = 0x0001 | 0x0002 | 0x0010                        # 4) SWP_NOSIZE|NOMOVE|NOACTIVATE
            u.SetWindowPos(h, _wt.HWND(-1), 0, 0, 0, 0, flags)      # HWND_TOPMOST
            u.SetWindowPos(h, _wt.HWND(-2), 0, 0, 0, 0, flags)      # HWND_NOTOPMOST
            print(f"[window] 전경 전환 안 됨: fg={fg} fg_tid={fg_tid} attached={attached} "
                  f"attach_err={attach_err} now={u.GetForegroundWindow()}")
            return False
        except Exception as e:
            print(f"[window] 전경 전환 실패: {e}")
            return False
else:
    def set_shortcut_app_id(lnk) -> bool:
        return False

    def set_window_taskbar_identity(hwnd: int) -> bool:
        return False

    def force_foreground(hwnd: int) -> bool:
        return False


# ---------------------------------------------------------------------------
# 바로가기 만들기 (Windows): 바탕화면 / 시작 프로그램 / 시작 메뉴
# ---------------------------------------------------------------------------
_SHORTCUT_PLACES = {"Desktop": "바탕화면", "Startup": "시작 프로그램", "Programs": "시작 메뉴"}


def create_shortcut(where: str) -> "tuple[bool, str]":
    """where: 'Desktop' | 'Startup' | 'Programs'. (성공 여부, 메시지) 반환.
    Desktop/Startup 을 만들 때는 시작 메뉴(Programs) 바로가기도 함께 갱신한다 —
    Windows 는 실행 중인 창을 작업 표시줄에 고정할 때 AppID 가 같은 시작 메뉴 바로가기를 찾아 쓴다."""
    if not IS_WINDOWS:
        return False, "Windows에서만 만들 수 있어요."
    try:
        import base64
        import subprocess

        def q(s) -> str:                     # PowerShell 작은따옴표 문자열 이스케이프
            return str(s).replace("'", "''")

        ico = app_icon_path()
        ico_line = f"$s.IconLocation='{q(ico)},0';" if ico else ""
        places = [where] if where == "Programs" else [where, "Programs"]
        made = []
        for place in places:
            # 시작 프로그램(자동 실행)은 창 없이 트레이로 시작
            argv = launch_argv("--tray") if place == "Startup" else launch_argv()
            ps = (
                f"$d=[Environment]::GetFolderPath('{place}');"
                "$s=(New-Object -ComObject WScript.Shell)"
                ".CreateShortcut(\"$d\\핀캡처.lnk\");"
                f"$s.TargetPath='{q(argv[0])}';"
                f"$s.Arguments='{q(subprocess.list2cmdline(argv[1:]))}';"
                f"$s.WorkingDirectory='{q(app_dir())}';"
                f"{ico_line}"
                "$s.Save()"
            )
            enc = base64.b64encode(ps.encode("utf-16-le")).decode()
            r = subprocess.run(["powershell", "-NoProfile", "-EncodedCommand", enc],
                               capture_output=True, timeout=30, creationflags=_NO_WINDOW)
            if r.returncode != 0:
                err = (r.stderr or b"").decode(errors="replace")[:300]
                return False, f"바로가기 생성 실패 ({_SHORTCUT_PLACES[place]}): {err}"
            set_shortcut_app_id(_special_folder(place) / "핀캡처.lnk")   # 작업 표시줄 고정용 AppID
            made.append(_SHORTCUT_PLACES[place])
        note = "" if FROZEN else " pythonw로 실행해서 터미널 창 없이 켜져요."
        return True, f"{' · '.join(made)}에 '핀캡처' 바로가기를 만들었어요.{note}"
    except Exception as e:
        return False, f"바로가기 생성 실패: {e}"


# ---------------------------------------------------------------------------
# 빠른 안내 / 정보
# ---------------------------------------------------------------------------
_WELCOME_MODES = (
    ("region", "영역 지정", "화면이 멈추면 드래그로 골라요. Esc나 우클릭으로 취소해요."),
    ("window", "창 캡처", "지금 쓰는 창을 찍어요. 일부가 가려져 있어도 창 내용이 나와요."),
    ("full", "전체 화면", "마우스가 있는 모니터 전체를 찍어요."),
    ("pin", "핀 고정", "고른 영역이 항상 위에 떠 있는 창이 돼요."),
)


def _muted(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setWordWrap(True)
    lab.setStyleSheet(f"color:{TEXT_SUB}; font-weight: 400;")
    return lab


class WelcomeDialog(QDialog):
    """단축키와 핀 사용법. 첫 실행에 한 번, 그 뒤엔 메뉴에서만 연다."""

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} 빠른 안내")
        self.setWindowIcon(make_app_icon())
        self.setMinimumWidth(520)
        _polish_dialog(self)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 16)
        v.setSpacing(10)

        title = QLabel("핀캡처에 오신 것을 환영해요")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        v.addWidget(title)
        v.addWidget(_muted(
            "화면을 찍어 저장하고, 필요한 부분은 다른 창 위에 핀으로 남겨 둘 수 있어요. "
            "이 안내는 처음 한 번만 자동으로 열리고, 트레이 메뉴의 빠른 안내에서 언제든 다시 볼 수 있어요."
        ))

        g = QGroupBox("단축키")
        gv = QVBoxLayout(g)
        gv.setSpacing(8)
        hk = cfg.get("hotkeys") or {}
        for mode, label, desc in _WELCOME_MODES:
            line = QLabel(f"{label}    {hotkey_label(hk.get(mode, DEFAULTS['hotkeys'].get(mode, '')))}")
            line.setStyleSheet("font-weight: 700;")
            gv.addWidget(line)
            gv.addWidget(_muted(desc))
        v.addWidget(g)

        g2 = QGroupBox("핀은 이렇게 써요")
        gv2 = QVBoxLayout(g2)
        gv2.addWidget(_muted(
            "· 드래그로 옮기고, 마우스 휠로 크기를 조절해요. Ctrl+휠은 투명도예요.\n"
            "· 우클릭하면 글자 복사(OCR), 복사, 다른 이름으로 저장, 투명도, 클릭 통과 메뉴가 나와요.\n"
            "· 클릭 통과를 켜면 핀을 누를 수 없어요. 트레이의 클릭 통과 해제나 단축키로 꺼 주세요.\n"
            "· 더블클릭이나 Esc로 닫아요. 닫은 핀은 단축키로 다시 열 수 있어요.\n"
            "· 핀 고정으로 찍은 이미지는 기본적으로 파일로 저장하지 않고 클립보드에만 복사해요. "
            "파일로 남기려면 설정에서 ‘핀 캡처도 파일로 저장해요’를 켜 주세요."
        ))
        v.addWidget(g2)
        v.addWidget(_muted(
            "창의 ×를 눌러도 트레이에서 단축키는 계속 동작해요. "
            "끝내려면 트레이 아이콘을 우클릭하고 종료를 눌러 주세요."
        ))

        btn = QPushButton("시작하기")
        btn.setObjectName("primary")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(btn)
        v.addLayout(row)


class AboutDialog(QDialog):
    """버전, 브랜드, 라이선스 요약, 서드파티 고지, 후원."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} 정보")
        self.setWindowIcon(make_app_icon())
        self.setMinimumWidth(460)
        _polish_dialog(self)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 16)
        v.setSpacing(10)

        head = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(make_app_icon(48).pixmap(48, 48))
        head.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)
        titles = QVBoxLayout()
        name = QLabel(f"{APP_NAME}  {APP_VERSION}")
        name.setStyleSheet("font-size: 18px; font-weight: 700;")
        brand = QLabel(f"{APP_PUBLISHER}  ·  {APP_PUBLISHER_EN}")
        brand.setStyleSheet("font-size: 13px; font-weight: 600;")
        titles.addWidget(name)
        titles.addWidget(brand)
        titles.addWidget(_muted("화면을 캡처해 저장·복사하고, 필요한 부분은 화면 위에 핀으로 고정하는 Windows 트레이 앱이에요."))
        head.addLayout(titles, 1)
        v.addLayout(head)

        lic = QGroupBox("라이선스")
        lv = QVBoxLayout(lic)
        lv.addWidget(_muted(
            "All rights reserved.\n"
            "누구나 개인적·상업적 목적으로 무료로 사용할 수 있어요.\n"
            "코드의 재배포·수정·판매는 저작권자의 허락 없이 할 수 없어요."
        ))
        notices = QPushButton("서드파티 고지 열기")
        notices.setCursor(Qt.CursorShape.PointingHandCursor)
        notices.setToolTip("Qt, pynput 등 설치본에 포함된 오픈소스 고지를 열어요.")
        notices.clicked.connect(self._open_notices)
        lv.addWidget(notices, alignment=Qt.AlignmentFlag.AlignLeft)
        v.addWidget(lic)

        donate = QGroupBox("후원")
        dv = QVBoxLayout(donate)
        dv.addWidget(_muted(
            "핀캡처가 도움이 되었다면, 부담 없이 후원할 수 있어요. "
            "후원하지 않아도 모든 기능은 그대로 무료예요."
        ))
        gift = QPushButton("후원하기")
        gift.setCursor(Qt.CursorShape.PointingHandCursor)
        gift.setToolTip("브라우저에서 Ko-fi 페이지를 열어요.")
        gift.clicked.connect(open_kofi)
        dv.addWidget(gift, alignment=Qt.AlignmentFlag.AlignLeft)
        v.addWidget(donate)

        close = QPushButton("닫기")
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close)
        v.addLayout(row)

    def _open_notices(self):
        path = third_party_notices_path()
        if not path.is_file():
            QMessageBox.information(
                self, "서드파티 고지",
                "고지 파일을 찾지 못했어요.\n설치 폴더의 THIRD_PARTY_NOTICES.txt를 확인해 주세요.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


# ---------------------------------------------------------------------------
# 설정 창
# ---------------------------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, hotkey_ok: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} 설정")
        self.setWindowIcon(make_app_icon())
        self.setMinimumWidth(760)
        _polish_dialog(self)
        self._cfg = cfg
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 12)
        v.setSpacing(8)

        intro = _muted("저장 위치, 캡처한 뒤의 동작, 전역 단축키를 바꿔요. 확인을 눌러야 저장돼요.")
        v.addWidget(intro)

        cols = QHBoxLayout()
        cols.setSpacing(12)
        left = QVBoxLayout()
        right = QVBoxLayout()

        g1 = QGroupBox("저장")
        f1 = QFormLayout(g1)
        f1.setHorizontalSpacing(10)
        f1.setVerticalSpacing(8)
        f1.addRow(_muted("캡처 파일이 쌓이는 곳이에요. 사진 폴더가 클라우드에 있으면 캡처도 함께 동기화돼요."))
        h = QHBoxLayout()
        self.ed_dir = QLineEdit(cfg["save_dir"])
        self.ed_dir.setToolTip("캡처 이미지를 저장할 폴더예요.")
        btn_browse = QPushButton("찾아보기")
        btn_browse.setToolTip("저장할 폴더를 골라 주세요.")
        btn_browse.clicked.connect(self._browse)
        h.addWidget(self.ed_dir)
        h.addWidget(btn_browse)
        f1.addRow("저장 폴더", h)
        self.ed_prefix = QLineEdit(cfg["filename_prefix"])
        self.ed_prefix.setToolTip("파일 이름 앞부분이에요. 뒤에는 날짜와 시각이 붙어요.")
        f1.addRow("파일 이름", self.ed_prefix)
        self.cb_format = QComboBox()
        self.cb_format.addItems(["png", "jpg"])
        self.cb_format.setCurrentText(cfg["file_format"])
        self.cb_format.setToolTip("png는 그대로 저장하고, jpg는 용량이 더 작아요.")
        f1.addRow("파일 형식", self.cb_format)
        self.sp_quality = QSpinBox()
        self.sp_quality.setRange(50, 100)
        self.sp_quality.setValue(int(cfg["jpg_quality"]))
        self.sp_quality.setToolTip("jpg로 저장할 때의 화질이에요. png에는 적용되지 않아요.")
        f1.addRow("JPG 품질", self.sp_quality)
        left.addWidget(g1)

        g_sc = QGroupBox("바로가기")
        sc = QVBoxLayout(g_sc)
        sc.addWidget(_muted("Windows 바탕화면, 시작 메뉴, 로그인할 때 자동 실행을 등록해요."))
        btn_desktop = QPushButton("바탕화면 아이콘 만들기")
        btn_startup = QPushButton("부팅 시 자동 실행 등록")
        btn_desktop.setToolTip("바탕화면과 시작 메뉴에 핀캡처 바로가기를 만들어요.")
        btn_startup.setToolTip("Windows에 로그인할 때 창 없이 트레이로 시작하게 등록해요.")
        btn_desktop.clicked.connect(lambda: self._make_shortcut("Desktop"))
        btn_startup.clicked.connect(lambda: self._make_shortcut("Startup"))
        if not IS_WINDOWS:
            btn_desktop.setEnabled(False)
            btn_startup.setEnabled(False)
            btn_desktop.setToolTip("Windows에서만 만들 수 있어요.")
            btn_startup.setToolTip("Windows에서만 만들 수 있어요.")
        sc.addWidget(btn_desktop)
        sc.addWidget(btn_startup)
        left.addWidget(g_sc)
        left.addStretch(1)

        g2 = QGroupBox("캡처할 때")
        v2 = QVBoxLayout(g2)
        self.ck_autosave = QCheckBox("캡처하면 파일로 저장해요")
        self.ck_clip = QCheckBox("캡처하면 클립보드에 복사해요")
        self.ck_notify = QCheckBox("캡처 후 트레이 알림을 보여 줘요")
        self.ck_hide = QCheckBox("캡처하는 동안 이 창을 숨겨요")
        self.ck_pin_all = QCheckBox("모든 캡처를 핀으로도 고정해요")
        self.ck_pin_save = QCheckBox("핀 캡처도 파일로 저장해요")
        self.ck_viewer = QCheckBox("캡처 후 이 창을 열어 방금 찍은 이미지를 보여 줘요")
        tips = {
            self.ck_autosave: "영역·창·전체 화면 캡처를 저장 폴더에 바로 저장해요.",
            self.ck_clip: "캡처한 이미지를 클립보드에 넣어, 다른 곳에 바로 붙여 넣을 수 있어요.",
            self.ck_notify: "캡처가 끝나면 트레이에 짧은 알림을 띄워요.",
            self.ck_hide: "캡처하는 동안 핀캡처 창이 화면이나 찍힌 이미지에 나오지 않아요.",
            self.ck_pin_all: "영역·창·전체 화면으로 찍은 이미지도 핀으로 띄워요.",
            self.ck_pin_save: "핀 고정으로 찍은 이미지도 파일로 남겨요. 끄면 클립보드에만 복사해요.",
            self.ck_viewer: "캡처가 끝나면 이 창을 열어 방금 찍은 이미지를 크게 보여 줘요.",
        }
        for ck, key in [(self.ck_autosave, "autosave"), (self.ck_clip, "clipboard"),
                        (self.ck_notify, "notify"), (self.ck_hide, "hide_during_capture"),
                        (self.ck_pin_all, "pin_after_capture"), (self.ck_pin_save, "pin_autosave"),
                        (self.ck_viewer, "show_viewer_after_capture")]:
            ck.setChecked(bool(cfg[key]))
            ck.setToolTip(tips[ck])
            v2.addWidget(ck)
        recent_row = QHBoxLayout()
        recent_row.addWidget(QLabel("닫은 핀 보관 개수"))
        self.sp_recent = QSpinBox()
        self.sp_recent.setRange(1, 50)
        self.sp_recent.setValue(_clamp_recent_limit(cfg.get("recent_pin_limit", 10)))
        self.sp_recent.setToolTip("닫은 핀을 다시 열 수 있게 임시로 보관하는 개수예요.")
        recent_row.addWidget(self.sp_recent)
        recent_row.addStretch(1)
        v2.addLayout(recent_row)
        right.addWidget(g2)

        cols.addLayout(left, 1)
        cols.addLayout(right, 1)
        v.addLayout(cols)

        g3 = QGroupBox("전역 단축키" + ("" if hotkey_ok else "  (현재 사용 불가)"))
        grid = QGridLayout(g3)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        self.ed_hk = {}
        labels = (("region", "영역 지정"), ("window", "창 캡처"),
                  ("full", "전체 화면"), ("pin", "핀 고정"),
                  ("reopen_pin", "최근 핀 다시 열기"), ("clickthrough", "클릭 통과 해제"))
        for i, (mode, label) in enumerate(labels):
            ed = QLineEdit(cfg["hotkeys"].get(mode, ""))
            ed.setPlaceholderText("비우면 사용 안 함")
            ed.setToolTip("예: <ctrl>+<alt>+a")
            self.ed_hk[mode] = ed
            grid.addWidget(QLabel(label), i // 2, (i % 2) * 2)
            grid.addWidget(ed, i // 2, (i % 2) * 2 + 1)
        tip = _muted("형식은 <ctrl>+<alt>+a, <print_screen> 이에요. 비우면 그 단축키를 쓰지 않아요. "
                     "다른 프로그램과 겹치면 여기 조합을 바꿔 주세요.")
        grid.addWidget(tip, 3, 0, 1, 4)
        btn_reset = QPushButton("단축키를 기본값으로")
        btn_reset.setToolTip(
            "영역 Ctrl+Alt+A, 창 Ctrl+Alt+W, 전체 Ctrl+Alt+F, 핀 Ctrl+Alt+Q, "
            "최근 핀 Ctrl+Alt+R, 클릭 통과 해제 Ctrl+Alt+X 로 되돌려요.")
        btn_reset.clicked.connect(self._reset_hotkeys)
        grid.addWidget(btn_reset, 4, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)
        v.addWidget(g3)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                              | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = bb.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = bb.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_btn is not None:
            ok_btn.setText("확인")
            ok_btn.setObjectName("primary")
        if cancel_btn is not None:
            cancel_btn.setText("취소")
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "저장할 폴더를 골라 주세요", self.ed_dir.text())
        if d:
            self.ed_dir.setText(d)

    def _reset_hotkeys(self):
        for mode, ed in self.ed_hk.items():
            ed.setText(DEFAULTS["hotkeys"][mode])

    def _make_shortcut(self, where: str):
        ok, msg = create_shortcut(where)
        if ok:
            QMessageBox.information(self, "바로가기", msg)
        else:
            QMessageBox.warning(self, "바로가기", msg)

    def _accept(self):
        # 단축키 형식 검증 (pynput 있을 때만)
        try:
            from pynput import keyboard
            for mode, ed in self.ed_hk.items():
                s = ed.text().strip()
                if s:
                    try:
                        keyboard.HotKey.parse(s)
                    except Exception:
                        QMessageBox.warning(self, "단축키 형식 오류",
                                            f"'{s}' 는 올바른 형식이 아니에요.\n예: <ctrl>+<alt>+a")
                        return
        except Exception:
            pass
        pending = {mode: ed.text().strip() for mode, ed in self.ed_hk.items()}
        clash = duplicate_hotkey(pending)
        if clash:
            QMessageBox.warning(self, "단축키 겹침",
                                f"'{clash}' 가 두 기능에 겹쳐요. 서로 다르게 정해 주세요.")
            return
        c = self._cfg
        c["save_dir"] = self.ed_dir.text().strip() or _default_save_dir()
        c["filename_prefix"] = self.ed_prefix.text().strip() or "캡처"
        c["file_format"] = self.cb_format.currentText()
        c["jpg_quality"] = self.sp_quality.value()
        c["autosave"] = self.ck_autosave.isChecked()
        c["clipboard"] = self.ck_clip.isChecked()
        c["notify"] = self.ck_notify.isChecked()
        c["hide_during_capture"] = self.ck_hide.isChecked()
        c["pin_after_capture"] = self.ck_pin_all.isChecked()
        c["pin_autosave"] = self.ck_pin_save.isChecked()
        c["show_viewer_after_capture"] = self.ck_viewer.isChecked()
        c["recent_pin_limit"] = self.sp_recent.value()
        for mode, ed in self.ed_hk.items():
            c["hotkeys"][mode] = ed.text().strip()
        self.accept()


# ---------------------------------------------------------------------------
# 메인 툴바
# ---------------------------------------------------------------------------
class ToolButton(QToolButton):
    def __init__(self, icon: QIcon, text: str, tip: str = ""):
        super().__init__()
        self.setIcon(icon)
        self.setText(text)
        self.setToolTip(tip or text)
        self.setIconSize(QSize(26, 26))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setFixedSize(88, 72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QToolButton {{
                border: none; border-radius: 8px; color: {TEXT};
                font-size: 12px; background: transparent; padding: 4px 2px 2px 2px;
            }}
            QToolButton:hover {{ background: #EDF3FE; }}
            QToolButton:pressed {{ background: #DDE9FD; }}
        """)


class MainToolbar(QWidget):
    """핀캡처 메인 창: 위쪽 = 캡처 기능함, 아래 = 보관함(미리보기 + 기록 리스트)."""

    def __init__(self, cfg: dict, server: "QLocalServer | None" = None):
        super().__init__(None)
        apply_ui_font()
        self.cfg = cfg
        self._server = server              # 단일 인스턴스 수신용
        if server is not None:
            server.newConnection.connect(self._on_singleton_msg)
        try:   # .py 갱신 감지(개발용). EXE 는 설치 프로그램이 교체·재실행하므로 사용 안 함
            self._script_mtime = None if FROZEN else Path(__file__).stat().st_mtime
        except Exception:
            self._script_mtime = None
        self._capturing = False
        self._was_visible = True
        self._pins = []
        self._recent = RecentPinStore(limit=cfg.get("recent_pin_limit", 10))
        self._notice_toast = None
        self._session = None
        self._tray = None
        self._toast_shown = False
        self.history = []              # HistoryEntry 목록 (0 = 최신)
        self._cur_img = None           # 미리보기에 떠 있는 이미지 (현재 항목)
        self._scan_existing_files()    # 저장 폴더의 기존 캡처를 기록에 채움

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(make_app_icon())
        self.setMinimumSize(800, 520)
        size = cfg.get("window_size")
        if isinstance(size, (list, tuple)) and len(size) == 2:
            self.resize(int(size[0]), int(size[1]))
        else:
            self.resize(1080, 700)

        self._build_ui()
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._build_tray()

        # 전역 단축키
        self.hotkeys = HotkeyManager()
        self.hotkeys.triggered.connect(self._on_hotkey)
        self.hotkeys.restart(cfg["hotkeys"])
        self._update_tooltips()

        # 활성 창 추적 (창 캡처용: 이 창이 포커스를 가져도 직전 앱 창을 기억)
        if IS_WINDOWS:
            self._last_ext_hwnd = None
            self._fg_timer = QTimer(self)
            self._fg_timer.timeout.connect(self._track_foreground)
            self._fg_timer.start(400)

        # 위치 복원 (화면 밖으로 나가지 않게 보정)
        pos = cfg.get("toolbar_pos")
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            self.move(int(pos[0]), int(pos[1]))
            self._clamp_to_screen()

        self.populate()

    def _clamp_to_screen(self):
        scr = (QGuiApplication.screenAt(self.frameGeometry().center())
               or QGuiApplication.primaryScreen())
        g = scr.availableGeometry()
        x = min(max(self.x(), g.left()), max(g.left(), g.right() - self.width() + 1))
        y = min(max(self.y(), g.top()), max(g.top(), g.bottom() - self.height() + 1))
        self.move(x, y)

    # ---------- UI ----------
    def _build_ui(self):
        self.setObjectName("mainRoot")
        self.setStyleSheet(f"""
            #mainRoot {{ background: white; color: {TEXT}; }}
            QPushButton {{
                padding: 6px 12px; border: 1px solid {BORDER}; color: {TEXT};
                border-radius: 6px; background: {BG}; font-size: 12px;
            }}
            QPushButton:hover {{ background: #EDF3FE; }}
            QPushButton:pressed {{ background: #DDE9FD; }}
            QToolButton#headerBtn {{
                border: 1px solid {BORDER}; border-radius: 6px; background: {BG};
                color: {TEXT}; padding: 4px 10px; font-size: 12px;
            }}
            QToolButton#headerBtn:hover {{ background: #EDF3FE; }}
            QListWidget {{
                background: #F2F4F8; border: 1px solid {BORDER}; border-radius: 8px;
                font-size: 11px; color: {TEXT_SUB};
            }}
            QListWidget::item {{ border-radius: 6px; padding: 3px; }}
            QListWidget::item:selected {{ background: #D6E4FC; color: {TEXT}; }}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        head = QHBoxLayout()
        head.setSpacing(10)
        mark = QLabel()
        mark.setPixmap(make_app_icon(28).pixmap(28, 28))
        head.addWidget(mark, alignment=Qt.AlignmentFlag.AlignTop)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        subtitle = QLabel("화면을 찍어 보관하고, 필요한 부분은 핀으로 고정해요.")
        subtitle.setStyleSheet(f"color:{TEXT_SUB}; font-size: 12px;")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        head.addLayout(titles)
        head.addStretch(1)
        self.btn_help = self._header_btn("help", "안내", "단축키와 핀 사용법을 다시 봐요.", self.show_welcome)
        self.btn_about = self._header_btn("info", "정보", "버전, 만든 이, 라이선스, 후원을 봐요.", self.show_about)
        self.btn_settings = self._header_btn("gear", "설정", "저장 폴더, 동작, 단축키를 바꿔요.", self.open_settings)
        for b in (self.btn_help, self.btn_about, self.btn_settings):
            head.addWidget(b, alignment=Qt.AlignmentFlag.AlignTop)
        root.addLayout(head)

        cap_title = QLabel("캡처")
        cap_title.setStyleSheet("font-weight: 700;")
        root.addWidget(cap_title)

        cap = QHBoxLayout()
        cap.setSpacing(6)
        self.btn_region = ToolButton(make_icon("region"), "영역 지정")
        self.btn_window = ToolButton(make_icon("window"), "창 캡처")
        self.btn_full = ToolButton(make_icon("full"), "전체 화면")
        self.btn_pin = ToolButton(make_icon("pin"), "핀 고정")
        self.btn_region.clicked.connect(lambda: self.capture("region"))
        self.btn_window.clicked.connect(lambda: self.capture("window"))
        self.btn_full.clicked.connect(lambda: self.capture("full"))
        self.btn_pin.clicked.connect(lambda: self.capture("pin"))
        for b in (self.btn_region, self.btn_window, self.btn_full):
            cap.addWidget(b)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color:{BORDER};")
        cap.addWidget(sep)
        cap.addWidget(self.btn_pin)
        cap.addStretch(1)
        root.addLayout(cap)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"color:{BORDER}; background:{BORDER}; max-height:1px;")
        root.addWidget(divider)

        hist_title = QLabel("보관함")
        hist_title.setStyleSheet("font-weight: 700;")
        root.addWidget(hist_title)
        hist_hint = QLabel("왼쪽이 지금 보는 캡처, 오른쪽이 이전 캡처예요. 목록에서 빼도 파일은 지워지지 않아요.")
        hist_hint.setWordWrap(True)
        hist_hint.setStyleSheet(f"color:{TEXT_SUB}; font-size: 11px;")
        root.addWidget(hist_hint)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.b_copy = self._action_btn("copy", "클립보드에 복사",
                                       "선택한 캡처를 클립보드에 복사해요. 여러 개면 파일 묶음으로 복사해요.")
        self.b_save = self._action_btn("save", "다른 이름으로 저장",
                                       "선택한 캡처를 다른 곳에 저장해요. 여러 개면 폴더를 하나 골라 한꺼번에 저장해요.")
        self.b_pin_sel = self._action_btn("pin", "화면에 고정",
                                          "선택한 캡처를 항상 위에 보이는 핀으로 띄워요.")
        self.b_folder = self._action_btn("folder", "저장 폴더 열기",
                                         "캡처가 저장되는 폴더를 열어요.")
        self.b_remove = self._action_btn("trash", "목록에서 제거",
                                         "목록에서만 빼요. 저장해 둔 파일은 지우지 않아요.")
        self.b_copy.clicked.connect(self._copy_selected)
        self.b_save.clicked.connect(self._save_selected_as)
        self.b_pin_sel.clicked.connect(self._pin_selected)
        self.b_folder.clicked.connect(self._open_folder)
        self.b_remove.clicked.connect(self._remove_selected)
        for b in (self.b_copy, self.b_save, self.b_pin_sel, self.b_folder):
            bar.addWidget(b)
        bar.addStretch(1)
        bar.addWidget(self.b_remove)
        root.addLayout(bar)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.preview = PreviewPane()
        self.listw = QListWidget()
        self.listw.setViewMode(QListView.ViewMode.IconMode)
        self.listw.setResizeMode(QListView.ResizeMode.Adjust)
        self.listw.setMovement(QListView.Movement.Static)
        self.listw.setIconSize(QSize(HistoryEntry.THUMB_W, 118))
        self.listw.setGridSize(QSize(HistoryEntry.THUMB_W + 28, 170))
        self.listw.setWordWrap(True)
        self.listw.setMinimumWidth(HistoryEntry.THUMB_W + 46)
        self.listw.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.listw.setToolTip("클릭하면 크게 봐요. Ctrl이나 Shift를 누른 채 클릭하거나 드래그하면 여러 개를 골라요. "
                              "Ctrl+A는 전체, Ctrl+C는 복사, Delete는 목록에서 제거예요.")
        self.listw.currentRowChanged.connect(self._on_row_changed)
        self.listw.itemSelectionChanged.connect(self._refresh_info)
        for seq, slot in ((QKeySequence.StandardKey.Copy, self._copy_selected),
                          (QKeySequence(Qt.Key.Key_Delete), self._remove_selected),
                          (QKeySequence.StandardKey.SelectAll, self.listw.selectAll)):
            sc = QShortcut(seq, self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(slot)
        split.addWidget(self.preview)
        split.addWidget(self.listw)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        split.setSizes([780, HistoryEntry.THUMB_W + 52])
        root.addWidget(split, 1)

        self.info = QLabel("")
        self.info.setStyleSheet(f"color:{TEXT_SUB}; font-size: 12px;")
        root.addWidget(self.info)

    def _header_btn(self, kind: str, text: str, tip: str, slot) -> QToolButton:
        b = QToolButton()
        b.setObjectName("headerBtn")
        b.setIcon(make_icon(kind, TEXT, 16))
        b.setIconSize(QSize(16, 16))
        b.setText(text)
        b.setToolTip(tip)
        b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(slot)
        return b

    def _action_btn(self, kind: str, text: str, tip: str) -> QPushButton:
        b = QPushButton(make_icon(kind, TEXT, 16), text)
        b.setIconSize(QSize(16, 16))
        b.setToolTip(tip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        return b

    def _update_tooltips(self):
        hk = self.cfg["hotkeys"]
        tips = (
            ("region", self.btn_region, "드래그로 영역을 골라 캡처해요. Esc나 우클릭으로 취소해요."),
            ("window", self.btn_window, "지금 쓰는 창을 캡처해요. 일부가 가려져 있어도 창 내용이 나와요."),
            ("full", self.btn_full, "마우스가 있는 모니터 전체를 캡처해요."),
            ("pin", self.btn_pin, "영역을 고르면 그 부분이 항상 위에 떠 있는 핀이 돼요."),
        )
        for mode, btn, text in tips:
            combo = hk.get(mode, "")
            if combo:
                btn.setToolTip(f"{text}\n단축키: {hotkey_label(combo)}")
            else:
                btn.setToolTip(f"{text}\n단축키: 없음 (설정에서 지정할 수 있어요)")

    def _tray_menu(self) -> QMenu:
        """트레이 우클릭 메뉴. 캡처, 안내, 후원을 나눠 두었어요."""
        m = QMenu()
        self._act_toggle = m.addAction(
            "창 숨기기" if self.isVisible() else "창 열기", self._toggle_window)
        m.addSeparator()
        m.addAction("영역 지정", lambda: self.capture("region"))
        m.addAction("창 캡처", lambda: self.capture("window"))
        m.addAction("전체 화면", lambda: self.capture("full"))
        m.addAction("핀 고정", lambda: self.capture("pin"))
        m.addSeparator()
        self._act_reopen = m.addAction("최근 핀 다시 열기", self.reopen_recent_pin)
        self._act_release_ct = m.addAction("클릭 통과 해제", self.clear_click_through)
        m.addSeparator()
        m.addAction("빠른 안내", self.show_welcome)
        m.addAction("설정", self.open_settings)
        m.addAction("정보", self.show_about)
        m.addAction("후원하기", open_kofi)
        m.addSeparator()
        m.addAction("다시 시작" if FROZEN else "다시 시작 (업데이트 적용)", self.restart_app)
        m.addAction("종료", self.quit_app)
        m.aboutToShow.connect(self._sync_tray_labels)
        return m

    def _sync_tray_labels(self):
        if getattr(self, "_act_toggle", None) is not None:
            self._act_toggle.setText("창 숨기기" if self.isVisible() else "창 열기")

    def _build_tray(self):
        self._tray = QSystemTrayIcon(make_app_icon(), self)
        self._tray.setToolTip(f"{APP_NAME} {APP_VERSION}  ·  {APP_PUBLISHER_EN}")
        self._tray.setContextMenu(self._tray_menu())
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def show_welcome(self):
        """빠른 안내. 닫으면 welcome_seen 을 저장해서 다음 실행부터는 자동으로 열지 않아요."""
        if getattr(self, "_welcome_open", False):
            return
        self._welcome_open = True
        try:
            WelcomeDialog(self.cfg, self).exec()
        finally:
            self._welcome_open = False
            self.cfg["welcome_seen"] = True
            save_config(self.cfg)

    def show_about(self):
        AboutDialog(self).exec()

    # ---------- 창 동작 ----------
    def closeEvent(self, e):
        if self._tray is not None:
            e.ignore()
            self.hide()
            self._save_geometry()
            if not self._toast_shown:
                self._toast_shown = True
                self._tray.showMessage(
                    APP_NAME,
                    "트레이에서 계속 실행 중이에요. 단축키도 그대로 동작하고, 끝내려면 트레이 아이콘을 우클릭한 뒤 종료를 눌러 주세요.",
                    QSystemTrayIcon.MessageIcon.Information, 3000)
        else:
            self.quit_app()
            e.accept()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape and self._tray is not None:
            self.hide()
        else:
            super().keyPressEvent(e)

    def _bring_to_front(self, _retry: int = 3):
        """창을 보이고 전경으로. (캡처 직후·트레이 클릭·바로가기 재실행 공통)
        Windows 에선 Qt 의 activateWindow 가 먼저 실패하면 잠깐 전경 잠금이 걸리므로 우회 전환을 먼저 한다."""
        self.show()
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        if IS_WINDOWS:
            if not force_foreground(int(self.winId())) and _retry > 0:
                QTimer.singleShot(150, lambda: self._bring_to_front(_retry - 1))
                return
        self.activateWindow()

    def _toggle_window(self):
        if self.isVisible():
            self.hide()
        else:
            self._bring_to_front()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self._toggle_window()

    def _save_geometry(self):
        self.cfg["toolbar_pos"] = [self.x(), self.y()]
        self.cfg["window_size"] = [self.width(), self.height()]
        save_config(self.cfg)

    def _release_singleton(self):
        if self._server is not None:
            try:
                self._server.close()
            except Exception:
                pass
            QLocalServer.removeServer(SINGLETON_NAME)
            self._server = None

    def _on_singleton_msg(self):
        """다른 실행이 보낸 신호 처리.
        show = 창 앞으로 (바로가기 재실행), tray = 아무것도 안 함 (자동 실행 중복),
        quit = 종료 (설치/제거 프로그램이 파일을 교체하기 전에 보냄), 빈 연결 = 무시."""
        conn = self._server.nextPendingConnection() if self._server else None
        msg = b""
        if conn is not None:
            if not conn.bytesAvailable():
                conn.waitForReadyRead(300)
            msg = bytes(conn.readAll())
            conn.disconnectFromServer()
        cmd = msg.decode(errors="ignore").strip().lower()
        if cmd == "quit":
            print("[singleton] 종료 요청을 받음 (설치/제거 프로그램)")
            QTimer.singleShot(0, self.quit_app)
            return
        if cmd != "show":
            return
        try:
            cur = None if FROZEN else Path(__file__).stat().st_mtime
        except Exception:
            cur = None
        if cur and self._script_mtime and cur > self._script_mtime + 0.5:
            print("[singleton] pincapture.py 가 갱신됨 → 새 버전으로 다시 시작")
            self.restart_app()
        else:
            self._bring_to_front()

    def restart_app(self):
        """같은 프로그램으로 새 프로세스를 띄우고 이 프로세스는 종료."""
        import subprocess
        self._save_geometry()
        self.hotkeys.stop()
        self._release_singleton()
        if self._tray is not None:
            self._tray.hide()
        env = dict(os.environ)
        env.pop("PINCAP_REEXEC", None)
        if FROZEN:
            # 없으면 자식이 곧 정리될 부모의 PyInstaller 런타임 환경을 물려받음 → 독립 실행으로 리셋
            env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        try:
            if IS_WINDOWS:
                subprocess.Popen(launch_argv(), cwd=str(app_dir()), env=env,
                                 creationflags=_NO_WINDOW, close_fds=True)
            else:
                subprocess.Popen(launch_argv(), cwd=str(app_dir()), env=env, start_new_session=True)
        except Exception as e:
            print(f"[restart] 재시작 실패: {e}")
        self._exit_now()

    def quit_app(self):
        self._save_geometry()
        self.hotkeys.stop()
        self._release_singleton()
        if self._tray is not None:
            self._tray.hide()
        self._exit_now()

    def _exit_now(self):
        """이벤트 루프를 확실히 끝낸다.
        QApplication.quit() 는 Qt 6 에서 '취소 가능한 요청'이라, 이 창의 closeEvent 가 닫기를 거부(트레이로 숨김)하고
        핀 창이 화면에 남아 있으면 종료가 무시된다 → 트레이·단축키 없는 유령 프로세스가 남아 업데이트/제거를 막음.
        exit(0) 은 취소되지 않는다. 핀 창은 먼저 닫아 정리."""
        for p in list(self._pins):
            try:
                p.close()
            except Exception:
                pass
        QApplication.instance().exit(0)

    # ---------- 캡처 파이프라인 ----------
    def _on_hotkey(self, mode: str):
        if mode == "reopen_pin":
            self.reopen_recent_pin()
            return
        if mode == "clickthrough":
            self.clear_click_through()
            return
        self.capture(mode)

    def _show_notice(self, text: str, title: str = APP_NAME, msec: int = 2200) -> None:
        self._last_notice = text
        if self._tray is not None:
            self._tray.showMessage(title, text, QSystemTrayIcon.MessageIcon.Information, msec)
            return
        self._notice_toast = PinToast(text, self if self.isVisible() else None, msec)

    def reopen_recent_pin(self):
        """가장 최근에 닫은 핀을 다시 띄운다. 없으면 짧은 안내만 한다."""
        item = self._recent.pop_latest()
        if item is None:
            self._show_notice("다시 열 핀이 없어요.")
            return None
        return self._make_pin(
            item["image"], QPoint(int(item["x"]), int(item["y"])),
            scale=float(item["scale"]), opacity=int(item["opacity"]), dpr=float(item["dpr"]))

    def clear_click_through(self) -> int:
        """클릭 통과 중인 핀을 모두 끈다. 핀 자체는 클릭을 받지 못하므로 트레이·단축키가 이 일을 한다."""
        n = 0
        for pin in list(self._pins):
            if pin.click_through:
                pin.set_click_through(False)
                n += 1
        if n:
            self._show_notice("클릭 통과를 껐어요.")
        else:
            self._show_notice("클릭 통과 중인 핀이 없어요.")
        return n

    def capture(self, mode: str):
        """mode: region | window | full | pin"""
        if self._capturing:
            return
        self._capturing = True
        self._was_visible = self.isVisible()
        delay = 30
        if self.cfg["hide_during_capture"] and self._was_visible:
            self.hide()   # 이 창이 캡처에 찍히지 않게
            delay = 220
        if mode == "region":
            QTimer.singleShot(delay, lambda: self._run_region(pin=False))
        elif mode == "pin":
            QTimer.singleShot(delay, lambda: self._run_region(pin=True))
        elif mode == "window":
            QTimer.singleShot(max(delay, 150), self._run_window)
        elif mode == "full":
            QTimer.singleShot(delay, self._run_full)
        else:
            self._capturing = False

    def _run_region(self, pin: bool):
        self._session = RegionCaptureSession()
        self._session.finished.connect(
            lambda img, gpos, pin=pin: self._finish(img, gpos, pin=pin))
        self._session.blocked.connect(self._capture_blocked)
        self._session.start()

    def _own_hwnds(self) -> set:
        s = set()
        for w in QApplication.topLevelWidgets():
            try:
                s.add(int(w.winId()))
            except Exception:
                pass
        return s

    def _track_foreground(self):
        """(Windows) 주기적으로 외부 활성 창을 기억 — 창 캡처 버튼용."""
        try:
            h = _user32.GetForegroundWindow()
            if h and h not in self._own_hwnds():
                self._last_ext_hwnd = h
        except Exception:
            pass

    def _run_window(self):
        exclude = self._own_hwnds() if IS_WINDOWS else set()
        fallback = self._last_ext_hwnd if IS_WINDOWS else None
        img = capture_active_window(exclude, fallback)
        if is_mostly_black(img) and screens_capture_blocked():
            self._finish(None, None, pin=False)
            self._capture_blocked()
            return
        self._finish(img, None, pin=False)

    def _run_full(self):
        s = screen_under_cursor()
        pm = grab_screen_raw(s)
        # 이 모니터가 완전한 검정일 때만 나머지 모니터도 확인 (한 모니터만 검정이면 실제로 검은 화면일 수 있음)
        if is_mostly_black(pm) and screens_capture_blocked():
            self._finish(None, None, pin=False)
            self._capture_blocked()
            return
        self._finish(pm.toImage(), s.geometry().topLeft(), pin=False)

    def _capture_blocked(self):
        """화면 캡처가 통째로 검게 나올 때: 검은 화면을 띄우거나 저장하지 않고 이유를 알린다.
        (보안 프로그램의 캡처 방지를 우회하지는 않는다 — 사용자가 직접 해제하도록 안내만)"""
        print("[capture] 모든 모니터가 거의 전부 검정으로 캡처됨 — 보안 프로그램의 화면 캡처 방지로 추정")
        # 실제 사례(2026-10-26): 정부24 전자문서 뷰어(ezPDFReader 2.0G)와 함께 설치된 화면 캡처 방지 모듈
        # (Teruten WebCube: TUCtlSystem 서비스 + T_Prevent64.dll)이 실행 중인 거의 모든 프로그램에 주입되어
        # 캡처가 검게 됨. 새로 띄운 프로그램도 수 초 안에 주입되므로 핀캡처 재시작은 도움이 안 된다.
        # → 1순위 해결책은 '문서 뷰어 닫기', 안 되면 재부팅·해당 뷰어 제거. (우회는 하지 않는다)
        title = "화면 캡처가 막혀 있어요"
        text = ("보안 프로그램 때문에 캡처가 막혔을 수 있어요.\n\n"
                "화면이 거의 전부 검은색으로만 캡처되고 있어요.\n\n"
                "정부24·홈택스·은행 같은 사이트의 전자문서 뷰어나 보안 프로그램이 '화면 캡처 방지' 기능을 "
                "켜 두면 이렇게 됩니다. 이 기능은 실행 중인 다른 프로그램에도 들어가기 때문에 "
                "다른 캡처 프로그램도 검게 찍힐 수 있어요.\n\n"
                "해결 방법\n"
                "  1. 열려 있는 전자문서 보기 창(예: 정부24 '전자문서 전용 Viewer')을 닫고 다시 캡처해 보세요.\n"
                "  2. 그래도 검게 나오면 그 사이트의 브라우저 창도 닫아 보세요.\n"
                "  3. 계속되면 컴퓨터를 다시 시작하거나, Windows 설정 → 앱에서 그때 설치된\n"
                "     문서 뷰어(예: ezPDFReader)나 화면 보안 프로그램(예: WebCube)을 제거해 주세요.")
        if self._tray is not None:
            self._tray.showMessage(title, "보안 프로그램 때문에 캡처가 막혔을 수 있어요. 안내 창을 확인해 주세요.",
                                   QSystemTrayIcon.MessageIcon.Warning, 4000)
        box = getattr(self, "_blocked_box", None)
        if box is None:
            box = QMessageBox(QMessageBox.Icon.Warning, title, text, QMessageBox.StandardButton.Ok)
            box.setWindowModality(Qt.WindowModality.NonModal)   # 캡처 단축키를 막지 않게
            box.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            self._blocked_box = box
        box.show()
        box.raise_()
        box.activateWindow()
        if IS_WINDOWS:
            force_foreground(int(box.winId()))

    def _finish(self, img, gpos, pin: bool):
        self._session = None
        self._capturing = False
        if img is None or (hasattr(img, "isNull") and img.isNull()):
            if self._was_visible:
                self.show()             # 취소: 창 원상 복구
            return

        do_pin = pin or self.cfg["pin_after_capture"]
        do_save = self.cfg["pin_autosave"] if pin else self.cfg["autosave"]
        path = None
        if do_save:
            path = self._save_image(img)
        if self.cfg["clipboard"]:
            QApplication.clipboard().setImage(img)
        if do_pin:
            self._make_pin(img, gpos)

        # 보관함 기록: 방금 캡처가 맨 위(메인), 이전 캡처들이 우측 리스트
        entry = HistoryEntry(image=img, path=path)
        self.history.insert(0, entry)
        self.add_entry(entry)
        self._trim_history()

        # 창 복귀: 일반 캡처면 결과를 바로 보여주고, 핀 캡처면 이전 상태만 복구
        if not pin and self.cfg.get("show_viewer_after_capture", True):
            self._bring_to_front()
        elif self._was_visible:
            self.show()

        self._notify(path)

        if os.environ.get("PINCAP_TEST_AUTOEXIT"):
            print(f"SAVED:{path}")
            QTimer.singleShot(300, self.quit_app)

    def _save_image(self, img: QImage) -> "str | None":
        d = Path(self.cfg["save_dir"])
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[save] 폴더 생성 실패: {e}")
            return None
        ext = self.cfg["file_format"].lower()
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"{self.cfg['filename_prefix']}_{ts}"
        path = d / f"{base}.{ext}"
        n = 1
        while path.exists():
            path = d / f"{base}_{n}.{ext}"
            n += 1
        out = img
        if ext in ("jpg", "jpeg"):
            out = img.convertToFormat(QImage.Format.Format_RGB32)
            ok = out.save(str(path), "JPG", int(self.cfg["jpg_quality"]))
        else:
            ok = out.save(str(path), "PNG")
        if not ok:
            print(f"[save] 저장 실패: {path}")
            return None
        return str(path)

    def _make_pin(self, img: QImage, gpos, *, scale: float = 1.0, opacity: int = 100,
                  dpr: "float | None" = None):
        scr = screen_under_cursor()
        if dpr is None:
            dpr = scr.devicePixelRatio() if scr is not None else 1.0
        pin = PinWindow(img, dpr=dpr)
        pin.release_hotkey = self.cfg.get("hotkeys", {}).get("clickthrough", "")
        if scale != 1.0:
            pin._scale = float(scale)
            pin._apply_size()
        if int(opacity) != 100:
            pin.set_opacity(int(opacity))
        pin.closed.connect(self._on_pin_closed)
        self._pins.append(pin)
        if isinstance(gpos, QPoint):
            pin.move(gpos)
        else:
            g = scr.availableGeometry()
            pin.move(g.center() - QPoint(pin.width() // 2, pin.height() // 2))
        pin.show()
        return pin

    def _on_pin_closed(self, pin):
        if pin in self._pins:
            self._pins.remove(pin)
        try:
            self._recent.remember(pin)
        except Exception as e:
            print(f"[recent] 보관 실패: {e}")

    def _notify(self, path):
        if not self.cfg["notify"] or self._tray is None:
            return
        if path:
            self._tray.showMessage("캡처 완료", f"저장했어요: {path}",
                                   QSystemTrayIcon.MessageIcon.Information, 2200)
        elif self.cfg["clipboard"]:
            self._tray.showMessage("캡처 완료", "클립보드에 복사했어요.",
                                   QSystemTrayIcon.MessageIcon.Information, 1800)

    # ---------- 보관함 ----------
    def _scan_existing_files(self):
        """저장 폴더의 기존 캡처(최신 60개)를 기록 목록에 채움."""
        try:
            d = Path(self.cfg["save_dir"])
            if not d.is_dir():
                return
            files = [f for pat in ("*.png", "*.jpg", "*.jpeg") for f in d.glob(pat)]
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            for f in files[:60]:
                self.history.append(HistoryEntry(
                    path=str(f),
                    ts=datetime.datetime.fromtimestamp(f.stat().st_mtime)))
        except Exception as e:
            print(f"[history] 기존 파일 스캔 실패: {e}")

    def _trim_history(self, limit: int = 150):
        while len(self.history) > limit:
            self.history.pop()
            if self.listw.count() > limit:
                self.listw.takeItem(self.listw.count() - 1)

    def populate(self):
        self.listw.blockSignals(True)
        self.listw.clear()
        for e in self.history:
            self.listw.addItem(self._make_item(e))
        self.listw.blockSignals(False)
        self._select_only(0 if self.listw.count() else -1)

    def add_entry(self, entry: HistoryEntry):
        self.listw.insertItem(0, self._make_item(entry))
        self._select_only(0)

    def _select_only(self, row: int):
        """해당 행만 선택하고 현재 항목으로. (다중 선택 모드에선 setCurrentRow 가 기존 선택을 안 지움)"""
        self.listw.blockSignals(True)
        if 0 <= row < self.listw.count():
            self.listw.setCurrentRow(row, QItemSelectionModel.SelectionFlag.ClearAndSelect)
        else:
            self.listw.clearSelection()
            row = -1
        self.listw.blockSignals(False)
        self._on_row_changed(row)

    def _make_item(self, e: HistoryEntry) -> QListWidgetItem:
        thumb = e.thumbnail()
        icon = QIcon(thumb) if thumb is not None else make_app_icon()
        item = QListWidgetItem(icon, e.label())
        item.setToolTip(e.path or "저장하지 않은 캡처 (메모리)")
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
        return item

    def _current_entry(self) -> "HistoryEntry | None":
        row = self.listw.currentRow()
        if 0 <= row < len(self.history):
            return self.history[row]
        return None

    def _selected_rows(self) -> "list[int]":
        """선택된 행 번호(오름차순). 선택이 없으면 현재 행 하나."""
        rows = sorted({ix.row() for ix in self.listw.selectedIndexes()
                       if 0 <= ix.row() < len(self.history)})
        if not rows:
            cur = self.listw.currentRow()
            if 0 <= cur < len(self.history):
                rows = [cur]
        return rows

    def _selected_entries(self) -> "list[HistoryEntry]":
        return [self.history[r] for r in self._selected_rows()]

    def _on_row_changed(self, row: int):
        e = self._current_entry()
        self._cur_img = e.full_image() if e else None
        self.preview.set_image(self._cur_img)
        self._refresh_info()

    def _refresh_info(self):
        rows = self._selected_rows()
        e = self._current_entry()
        n = len(rows)
        self.b_remove.setText(f"목록에서 제거 ({n})" if n > 1 else "목록에서 제거")
        if e is None or not rows:
            self.info.setText("아직 캡처가 없어요. 위쪽 버튼이나 단축키로 화면을 찍어 보세요.")
            return
        if n > 1:
            self.info.setText(f"{n}개 선택   ·   복사하면 파일 묶음으로 복사하고, 저장하면 폴더에 한꺼번에 저장해요."
                              "   ·   핀은 모두 고정하고, Delete는 목록에서만 제거해요. 파일은 지우지 않아요.")
            return
        img = getattr(self, "_cur_img", None)
        where = e.path if e.path else "저장하지 않은 캡처 (메모리에만 있어요)"
        if img is None:
            self.info.setText(f"(이미지를 읽을 수 없음)   ·   {where}")
        else:
            self.info.setText(f"{img.width()}×{img.height()} px   ·   {where}")

    def _copy_selected(self):
        entries = self._selected_entries()
        if not entries:
            return
        if len(entries) == 1:
            img = entries[0].full_image()
            if img is not None:
                QApplication.clipboard().setImage(img)
            return
        # 여러 개: 파일 묶음으로 복사 (탐색기·메신저·메일에 붙여넣기 가능).
        # 저장 안 된 캡처는 ~/.pincapture/clipboard/ 에 임시 저장해 포함. 이미지만 받는 앱을 위해 첫 장도 같이 실음.
        tmp_dir = CONFIG_DIR / "clipboard"
        try:
            tmp_dir.mkdir(parents=True, exist_ok=True)
            for old in tmp_dir.glob("*.png"):
                old.unlink(missing_ok=True)
        except Exception:
            pass
        urls, first_img = [], None
        for i, e in enumerate(entries):
            p = Path(e.path) if e.path else None
            if p is None or not p.exists():
                img = e.full_image()
                if img is None:
                    continue
                p = tmp_dir / f"캡처_{e.ts:%Y%m%d_%H%M%S}_{i}.png"
                if not img.save(str(p), "PNG"):
                    continue
            if first_img is None:
                first_img = e.full_image()
            urls.append(QUrl.fromLocalFile(str(p)))
        if not urls:
            return
        md = QMimeData()
        md.setUrls(urls)
        if first_img is not None:
            md.setImageData(first_img)
        QApplication.clipboard().setMimeData(md)
        if self._tray is not None and self.cfg["notify"]:
            self._tray.showMessage("복사 완료", f"{len(urls)}개를 클립보드에 복사했어요.",
                                   QSystemTrayIcon.MessageIcon.Information, 1800)

    def _save_selected_as(self):
        entries = self._selected_entries()
        if not entries:
            return
        if len(entries) == 1:
            e = entries[0]
            img = e.full_image()
            if img is None:
                return
            ts = e.ts.strftime("%Y%m%d_%H%M%S")
            path, _ = QFileDialog.getSaveFileName(
                self, "다른 이름으로 저장", str(Path.home() / f"캡처_{ts}.png"),
                "PNG (*.png);;JPEG (*.jpg)")
            if path:
                img.save(path)
            return
        # 여러 개: 폴더를 고르면 각각 저장 (파일이 있는 건 그대로 복사, 메모리 캡처는 PNG 로)
        import shutil
        d = QFileDialog.getExistingDirectory(self, "저장할 폴더를 골라 주세요", str(Path.home()))
        if not d:
            return
        saved, failed = 0, 0
        for e in entries:
            src = Path(e.path) if e.path and Path(e.path).exists() else None
            base = src.stem if src else f"캡처_{e.ts:%Y%m%d_%H%M%S}"
            ext = src.suffix if src else ".png"
            out = Path(d) / f"{base}{ext}"
            n = 1
            while out.exists():
                out = Path(d) / f"{base}_{n}{ext}"
                n += 1
            try:
                if src:
                    shutil.copy2(src, out)
                    saved += 1
                else:
                    img = e.full_image()
                    if img is not None and img.save(str(out), "PNG"):
                        saved += 1
                    else:
                        failed += 1
            except Exception as ex:
                print(f"[save] 일괄 저장 실패 {out}: {ex}")
                failed += 1
        msg = f"{saved}개를 저장했어요.\n{d}" + (f"\n(실패 {failed}개)" if failed else "")
        QMessageBox.information(self, "저장", msg)

    def _pin_selected(self):
        entries = self._selected_entries()
        shown = 0
        for e in entries:
            img = e.full_image()
            if img is None:
                continue
            self._make_pin(img, None)
            if shown and self._pins:                      # 여러 장이면 계단식으로 어긋나게
                p = self._pins[-1]
                p.move(p.pos() + QPoint(32 * shown, 32 * shown))
            shown += 1

    def _open_folder(self):
        d = Path(self.cfg["save_dir"])
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))

    def _remove_selected(self):
        """선택된 항목을 모두 목록에서 제거 (파일은 지우지 않음)."""
        rows = self._selected_rows()
        if not rows:
            return
        self.listw.blockSignals(True)
        for row in reversed(rows):              # 뒤에서부터 지워야 앞 인덱스가 안 밀림
            del self.history[row]
            self.listw.takeItem(row)
        self.listw.blockSignals(False)
        self._select_only(min(rows[0], self.listw.count() - 1))

    # ---------- 설정 ----------
    def open_settings(self):
        dlg = SettingsDialog(self.cfg, self.hotkeys.available)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            save_config(self.cfg)
            self._recent.set_limit(self.cfg.get("recent_pin_limit", 10))
            hint = self.cfg.get("hotkeys", {}).get("clickthrough", "")
            for pin in self._pins:
                pin.release_hotkey = hint
            self.hotkeys.restart(self.cfg["hotkeys"])
            self._update_tooltips()


# ---------------------------------------------------------------------------
# 자가 점검 (--selftest): 헤드리스 환경에서 위젯을 만들어 PNG 로 저장
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    out = Path("selftest_out")
    out.mkdir(exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    apply_ui_font(app)
    cfg = load_config()
    results = []

    def grab(widget, name, size=None):
        if size:
            widget.resize(*size)
        widget.show()
        app.processEvents()
        pm = widget.grab()
        p = out / f"{name}.png"
        pm.save(str(p))
        results.append((name, pm.width(), pm.height()))
        widget.hide()

    # 1) 메인 창 (위: 기능함, 아래: 보관함) — 더미 캡처 3개
    def _dummy(w, h, base):
        im = QImage(w, h, QImage.Format.Format_RGB32)
        q = QPainter(im)
        for y in range(h):
            q.setPen(QColor((base + y // 4) % 256, (base * 2 + y // 6) % 256,
                            (255 - base + y // 5) % 256))
            q.drawLine(0, y, w, y)
        q.setPen(QColor("white"))
        ff = QFont(); ff.setPointSize(14); q.setFont(ff)
        q.drawText(im.rect(), Qt.AlignmentFlag.AlignCenter, f"{w}×{h}")
        q.end()
        return im

    tb = MainToolbar(cfg)
    tb.history = [HistoryEntry(image=_dummy(900, 560, 60)),
                  HistoryEntry(image=_dummy(640, 400, 130)),
                  HistoryEntry(image=_dummy(500, 700, 200))]
    tb.populate()
    grab(tb, "main", size=(1080, 720))

    # 2) 설정 창
    dlg = SettingsDialog(cfg, hotkey_ok=tb.hotkeys.available)
    dlg.adjustSize()
    grab(dlg, "settings")

    welcome = WelcomeDialog(cfg)
    welcome.adjustSize()
    grab(welcome, "welcome")
    about = AboutDialog()
    about.adjustSize()
    grab(about, "about")

    # 3) 핀 창 (그라데이션 더미 이미지)
    img = QImage(420, 260, QImage.Format.Format_RGB32)
    pt = QPainter(img)
    for y in range(260):
        pt.setPen(QColor(40 + y // 3, 90 + y // 4, 200 - y // 3))
        pt.drawLine(0, y, 420, y)
    pt.setPen(QColor("white"))
    f = QFont(); f.setPointSize(16); pt.setFont(f)
    pt.drawText(img.rect(), Qt.AlignmentFlag.AlignCenter, "PIN TEST 420×260")
    pt.end()
    pin = PinWindow(img)
    grab(pin, "pin")

    # 4) 영역 선택 오버레이 (더미 정지 화면 + 가짜 선택 영역)
    frozen = QPixmap(1280, 800)
    pf = QPainter(frozen)
    for y in range(800):
        pf.setPen(QColor(30 + y // 8, 60 + y // 10, 110 + y // 9))
        pf.drawLine(0, y, 1280, y)
    pf.setPen(QColor(255, 255, 255, 200))
    f2 = QFont(); f2.setPointSize(22); pf.setFont(f2)
    pf.drawText(frozen.rect(), Qt.AlignmentFlag.AlignCenter, "FROZEN SCREEN (dummy)")
    pf.end()
    scr = app.primaryScreen()
    ov = SelectionOverlay(scr, frozen)
    ov.resize(1280, 800)
    ov._origin = QPoint(340, 220)
    ov._current = QPoint(820, 540)
    grab(ov, "overlay", size=(1280, 800))
    sel = ov._sel_rect()
    phys = ov._to_phys(sel)
    results.append(("overlay_mapping", phys.width(), phys.height()))
    ov.blockSignals(True); ov.close()

    # 5) 좌표 매핑 단위 확인 (200% DPI 시뮬레이션)
    frozen2x = QPixmap(2560, 1600)
    frozen2x.fill(QColor("gray"))
    ov2 = SelectionOverlay(scr, frozen2x)
    ov2.resize(1280, 800)
    r = ov2._to_phys(QRect(100, 50, 300, 200))
    expect = QRect(200, 100, 600, 400)
    ok = (r == expect)
    results.append(("dpi_mapping_ok" if ok else "dpi_mapping_FAIL", r.width(), r.height()))
    ov2.blockSignals(True); ov2.close()

    hk = tb.hotkeys
    alive = hk._listener.is_alive() if hk._listener is not None else None
    tb.hotkeys.stop()
    for name, w, h in results:
        print(f"[selftest] {name}: {w}x{h}")
    print(f"[selftest] hotkeys available={hk.available} listener_alive={alive} error={hk.error!r}")
    print(f"[selftest] version={APP_VERSION} frozen={FROZEN}")
    print(f"[selftest] launch_argv={launch_argv()}  tray_argv={launch_argv('--tray')}")
    print(f"[selftest] relaunch_command={relaunch_command()}")
    print(f"[selftest] app_dir={app_dir()}  icon={app_icon_path()}")
    print("[selftest] done ->", out.resolve())
    return 0


def _send_quit_to_running() -> int:
    """--quit: 실행 중인 핀캡처에 종료를 요청하고 실제로 끝날 때까지 최대 10초 기다린다.
    설치/제거 프로그램이 파일을 바꾸기 전에 호출한다. 실행 중이 아니면 바로 0."""
    import time
    sock = QLocalSocket()
    sock.connectToServer(SINGLETON_NAME)
    if not sock.waitForConnected(1000):
        print("[quit] 실행 중인 핀캡처 없음")
        return 0
    sock.write(b"quit")
    sock.flush()
    sock.waitForBytesWritten(1000)
    sock.disconnectFromServer()
    if not IS_WINDOWS:
        return 0
    import ctypes
    k32 = ctypes.windll.kernel32
    SYNCHRONIZE = 0x00100000
    for _ in range(100):                     # 뮤텍스가 사라지면 = 프로세스 종료
        time.sleep(0.1)
        h = k32.OpenMutexW(SYNCHRONIZE, False, APP_MUTEX_NAME)
        if not h:
            print("[quit] 종료 확인")
            return 0
        k32.CloseHandle(h)
    print("[quit] 10초 안에 종료되지 않음")
    return 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} {APP_VERSION}")
    parser.add_argument("--selftest", action="store_true", help="UI 자가 점검 (개발용)")
    parser.add_argument("--region", action="store_true", help="시작 직후 영역 캡처")
    parser.add_argument("--window", action="store_true", help="시작 직후 창 캡처")
    parser.add_argument("--full", action="store_true", help="시작 직후 전체 캡처")
    parser.add_argument("--pin", action="store_true", help="시작 직후 핀 캡처")
    parser.add_argument("--tray", action="store_true", help="창 없이 트레이로 시작 (자동 실행용)")
    parser.add_argument("--quit", action="store_true", help="실행 중인 핀캡처 종료 (설치/제거 프로그램용)")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION}")
    # 모르는 인수가 있어도 죽지 않게 (예전 버전이 만든 바로가기 등)
    args, unknown = parser.parse_known_args()
    if unknown:
        print(f"[args] 알 수 없는 인수 무시: {unknown}")

    if args.selftest and not IS_WINDOWS and not os.environ.get("DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    if IS_WINDOWS:
        try:  # 작업표시줄 아이콘 그룹핑
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("PinCapture")
    app.setApplicationDisplayName(APP_NAME)
    app.setWindowIcon(make_app_icon())
    app.setQuitOnLastWindowClosed(False)

    if args.selftest:
        return run_selftest()
    if args.quit:
        return _send_quit_to_running()

    cfg = prepare_config()  # 첫 실행이면 안내를 띄울 준비를 하고, 없으면 기본 설정 파일을 만든다

    # 단일 인스턴스: 이미 실행 중이면 신호만 보내고 이 프로세스는 종료.
    # 기존 인스턴스는 창을 앞으로 띄운다 (개발용 .py 실행이면 파일이 갱신됐을 때 재시작).
    sock = QLocalSocket()
    sock.connectToServer(SINGLETON_NAME)
    if sock.waitForConnected(300):
        if IS_WINDOWS and not args.tray:
            # 바로가기로 실행된 이 프로세스가 받은 '전경 전환 권한'을 이미 실행 중인 창에 넘겨줌
            # (없으면 기존 창이 앞으로 오지 못하고 작업 표시줄만 깜빡일 수 있음)
            try:
                import ctypes
                ctypes.windll.user32.AllowSetForegroundWindow(-1)   # ASFW_ANY
            except Exception:
                pass
        sock.write(b"tray" if args.tray else b"show")
        sock.flush()
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        print("이미 실행 중이에요. 기존 창을 앞으로 가져왔어요.")
        return 0
    QLocalServer.removeServer(SINGLETON_NAME)   # 비정상 종료 잔여물 정리
    server = QLocalServer()
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)   # 같은 사용자만 연결 가능
    if not server.listen(SINGLETON_NAME):
        print(f"[singleton] listen 실패: {server.errorString()}")

    if IS_WINDOWS:
        # 설치/제거 프로그램이 '실행 중'을 감지하는 뮤텍스. 프로세스가 끝나면 OS 가 자동 해제.
        try:
            import ctypes
            global _APP_MUTEX
            _APP_MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, APP_MUTEX_NAME)
        except Exception as e:
            print(f"[mutex] 생성 실패: {e}")

    toolbar = MainToolbar(cfg, server)
    if IS_WINDOWS:
        # 창을 보이기 전에 작업 표시줄 식별 정보를 심어야 '고정' 시 핀캡처 아이콘/명령이 쓰인다
        set_window_taskbar_identity(int(toolbar.winId()))
    if not args.tray or toolbar._tray is None:   # 트레이가 없는 환경이면 --tray 여도 창을 띄움
        toolbar.show()
    if should_auto_welcome(cfg, args.tray, toolbar._tray is not None):
        # 첫 실행에만. --tray(자동 실행)에서는 띄우지 않아 로그인을 끊지 않는다.
        QTimer.singleShot(400, toolbar.show_welcome)

    for flag, mode in [(args.region, "region"), (args.window, "window"),
                       (args.full, "full"), (args.pin, "pin")]:
        if flag:
            QTimer.singleShot(600, lambda m=mode: toolbar.capture(m))
            break

    if os.environ.get("PINCAP_TEST_RESTART"):
        QTimer.singleShot(1500, toolbar.restart_app)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
