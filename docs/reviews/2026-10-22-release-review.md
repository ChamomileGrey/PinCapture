> 이 문서는 v0.5.3 시점의 배포 전 검토 기록입니다. 이후 v0.6.0~0.6.1에서 반영된 항목은 `CHANGELOG.md`, 남은 항목은 `ROADMAP.md`를 기준으로 하세요. 줄 번호는 v0.5.3 기준이라 현재 코드와 다릅니다.

# 핀캡처 v0.5.3 배포 전 검토 (2026-10-22)

검토 대상: `pincapture.py`(2184줄), `핀캡처_사용법.md`
기준: `pyinstaller --onefile --noconsole`로 만든 EXE를 Python이 없는 다른 PC에 설치해 쓰는 사람

요약: 1번을 고치지 않으면 "아이콘을 눌러도 안 켜지는 프로그램"으로 배포됩니다.

| 묶음 | 항목 | 예상 시간 |
|---|---|---|
| 반드시 | 1–3 | 약 5시간 (EXE 실기 테스트 포함) |
| 하면 좋음 (medium) | 4–11 | 약 5시간 |
| 하면 좋음 (low) | 12–18 | 약 2.5시간 |

검토 방식: 5개 관점(EXE 패키징, 실행 안정성, UX·기능, 배포 리스크, 코드 품질)의 검토자가 낸 지적 36건을 건마다 반박 검증자가 실제 코드와 대조했습니다. 33건이 확인됐고, 기각·부분 기각 내용은 5절에 있습니다.

### EXE 실측 (이 PC, PyInstaller 6.22.3 `--onefile --noconsole`, Defender 실시간 검사 꺼진 상태)

| 항목 | 결과 |
|---|---|
| 자가 점검 `--selftest` | 통과 |
| 전체 화면 캡처 `--full` | 정상 저장 |
| 중복 실행 방지 | 정상 (두 번째 실행은 신호만 보내고 종료) |
| 바로가기 방식 실행 (exe + 스크립트 경로 인수) | **즉시 종료, 종료 코드 2** → 1번 항목 |
| 창이 뜨기까지 시간: onefile EXE | 5.9초, 13.9초 (2회) |
| 창이 뜨기까지 시간: pythonw + .py | 1.7초 |
| EXE 크기 | 약 49MB |
| 버전 정보 / 서명 | 비어 있음 / 서명 없음 |
| 강제 종료 후 `%TEMP%\_MEI*` | 남음 (정상 종료 시에는 정리됨) |

시작 시간 메모: 측정 PC는 Defender 실시간 검사가 꺼져 있었으므로, 일반 PC에서는 더 느릴 가능성이 높습니다. 앱이 이미 실행 중일 때 바로가기를 더블클릭해도 "show" 신호 하나를 보내려고 매번 이만큼 압축을 풉니다. 5절에서 검증자는 "zip 안에서 바로 실행하는 사고"를 이유로 onefile 유지를 권했지만, 이 측정값을 보면 1.0에서도 `--splash`로 로딩 화면을 띄우거나, onedir + Inno Setup 설치본(기능 표의 '나중' 항목)을 앞당기는 것을 검토할 만합니다.

---

## 1. 배포 전 반드시 (blocker/high)

### 1. [blocker] EXE에서는 바로가기, 자동 실행, 작업 표시줄 고정, 트레이 '다시 시작'이 모두 동작하지 않음

- **왜:** 코드에 `sys.frozen` 분기가 없습니다. EXE에서 `Path(__file__)`는 `%TEMP%\_MEIxxxx\pincapture.py`인데, 이 파일은 실제로 없고 폴더도 프로그램 종료 시 삭제됩니다. 그래서 모든 재실행 명령이 `PinCapture.exe "…\_MEI…\pincapture.py"`가 되고, argparse(2124)가 exit 2로 아무 표시 없이 끝냅니다. 현재 로그(`~/.pincapture/pincapture.log`)에도 테스트 빌드가 남긴 `unrecognized arguments` 줄이 있습니다.
- **증상:**
  - 바탕화면/시작 메뉴 아이콘을 눌러도 반응이 없습니다.
  - 부팅 시 자동 실행이 실패합니다.
  - 작업 표시줄 고정 아이콘이 반응하지 않습니다. 2167행이 실행할 때마다 재실행 명령을 심기 때문에, 설정을 건드리지 않아도 생깁니다.
  - 트레이 '다시 시작'을 누르면 앱이 사라집니다.
- **수정:**
  1. 43행 아래에 공용 헬퍼를 추가합니다.
     ```python
     FROZEN = bool(getattr(sys, "frozen", False))

     def launch_argv() -> list:
         if FROZEN:
             return [sys.executable]
         pyw = Path(sys.executable).with_name("pythonw.exe")
         return [str(pyw if pyw.exists() else Path(sys.executable)), str(Path(__file__).resolve())]

     def app_dir() -> Path:
         return Path(sys.executable).parent if FROZEN else Path(__file__).resolve().parent
     ```
  2. `relaunch_command()` 956-960: `return subprocess.list2cmdline(launch_argv())`
  3. `create_shortcut()` 1141-1155:
     - `argv = launch_argv()`, `q = lambda s: str(s).replace("'", "''")`로 둡니다.
     - `$s.TargetPath='{q(argv[0])}'`, `$s.Arguments='{q(subprocess.list2cmdline(argv[1:]))}'`(EXE에서는 빈 값), `$s.WorkingDirectory='{q(app_dir())}'`로 바꿉니다.
     - IconLocation은 기존 `app_icon_path()` .ico를 그대로 씁니다. `--icon` 없이 빌드해도 동작합니다.
     - 1168행의 "(pythonw로 실행돼서…)" 문구는 `not FROZEN`일 때만 붙입니다.
  4. `restart_app()` 1624-1629는 아래처럼 바꿉니다. 1534행 '다시 시작 (업데이트 적용)' 메뉴는 FROZEN이면 아예 추가하지 않습니다. 실행 중인 EXE는 잠겨 있어 교체가 불가능하므로 이 메뉴가 적용할 업데이트가 없습니다.
     ```python
     env = dict(os.environ); env.pop("PINCAP_REEXEC", None)
     if FROZEN:
         env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"   # 없으면 자식이 곧 지워질 부모의 _MEI 를 재사용 → 크래시 (프로브 빌드로 확인)
     subprocess.Popen(launch_argv(), cwd=str(app_dir()), env=env, creationflags=_NO_WINDOW, close_fds=True)
     ```
  5. `_handle_missing_deps()` 167행 첫 줄에 FROZEN 분기를 넣습니다. 이 분기는 다른 Python을 찾거나 재실행하지 않고, 엉뚱한 `PinCapture.exe -m pip …` 안내도 띄우지 않습니다.
     ```python
     if FROZEN:
         _msgbox("핀캡처 실행 실패", f"구성 요소(Qt)를 불러오지 못했어요.\n{err}\n\n"
                 "백신이 파일을 막았는지 확인하고 PinCapture.exe 를 다시 받아 주세요.\n"
                 f"Windows 10/11 64-bit 에서만 실행됩니다.\n로그: {LOG_PATH}")
         sys.exit(1)
     ```
     199-222행의 import는 QtCore/QtGui/QtNetwork/QtWidgets를 하나의 `try`로 합치고, 중복된 QtCore import(207-210)와 도달하지 않는 `raise`(206)는 지웁니다.
  6. 1342행은 `self._script_mtime = None if FROZEN else Path(__file__).stat().st_mtime`로 바꿉니다. 업데이트 감지는 4번 항목에서 다룹니다.
  7. (선택) 2124행을 `args, unknown = parser.parse_known_args()`로 바꾸고, `unknown`이 있으면 로그에 남깁니다.
- **작업량:**
  - 코드 40분
  - EXE 실기 테스트 1시간 (체크리스트 4절)

### 2. [high] pynput 저수준 키보드 훅을 Win32 `RegisterHotKey`로 교체

- **왜 1:** Ctrl+Alt+Del이나 잠금 화면에서는 Ctrl·Alt를 떼는 입력이 훅에 보이지 않아 pynput 내부 상태에 남습니다. 그러면 잠금을 해제한 뒤 그냥 a/w/f/q(한글 ㅁ/ㅈ/ㄹ/ㅂ)를 칠 때마다 캡처가 뜹니다. pynput 1.8.2의 `HotKey` 소스로 확인했습니다.
- **왜 2:** 훅은 키를 삼키지 않습니다. 그래서 Ctrl+Alt+F가 Word에도 전달되어 각주가 삽입되고, 다른 프로그램과 단축키가 겹쳐도 감지할 수 없습니다. 관리자 권한 창 위에서는 단축키가 동작하지 않는데, 사용법 88행은 그 해결책으로 "관리자로 실행"을 안내합니다. 배포용 안내로는 부적절합니다.
- **수정:**
  - `HotkeyManager`(885-933)를 교체합니다. 기존 `<ctrl>+<alt>+a` 형식은 그대로 받고, `Ctrl+Alt+A` 형식도 받게 합니다.
    ```python
    _u32 = ctypes.WinDLL("user32", use_last_error=True)
    _u32.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
    _u32.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
    _u32.VkKeyScanW.argtypes = (ctypes.c_wchar,); _u32.VkKeyScanW.restype = ctypes.c_short
    _MODS = {"ctrl": 0x2, "alt": 0x1, "shift": 0x4, "cmd": 0x8, "win": 0x8}
    _NAMED = {"print_screen": 0x2C, "space": 0x20, "tab": 0x09, "insert": 0x2D, "delete": 0x2E,
              "home": 0x24, "end": 0x23, "page_up": 0x21, "page_down": 0x22, "pause": 0x13,
              **{f"f{i}": 0x6F + i for i in range(1, 25)}}

    def parse_hotkey(s: str) -> "tuple[int, int]":
        mods, vk = 0, None
        for part in s.lower().replace(" ", "").split("+"):
            part = part.strip("<>")
            if part in _MODS: mods |= _MODS[part]
            elif vk is None and part in _NAMED: vk = _NAMED[part]
            elif vk is None and len(part) == 1 and part.isascii() and part.isalnum(): vk = ord(part.upper())
            elif vk is None and len(part) == 1:
                r = _u32.VkKeyScanW(part) & 0xFF          # 구두점은 ord() 금지 (',' → PrintScreen 이 됨)
                if r == 0xFF: raise ValueError(part)
                vk = r
            else: raise ValueError(part)
        if vk is None: raise ValueError("키 없음")
        return mods | 0x4000, vk                           # MOD_NOREPEAT

    class HotkeyManager(QObject):
        triggered = Signal(str)
        def __init__(self, hwnd: int):
            super().__init__(); self._hwnd = hwnd
            self.ids, self.failed, self.available, self.error = {}, {}, False, ""
        def restart(self, hotkeys: dict):
            self.stop(); self.failed = {}
            for i, (mode, combo) in enumerate(hotkeys.items(), 1):
                if not combo: continue
                try: mods, vk = parse_hotkey(combo)
                except ValueError: self.failed[mode] = "형식 오류"; continue
                if _u32.RegisterHotKey(self._hwnd, i, mods, vk): self.ids[i] = mode
                else:
                    e = ctypes.get_last_error()
                    self.failed[mode] = "다른 프로그램이 사용 중" if e == 1409 else f"등록 실패({e})"
            self.available = bool(self.ids)
            self.error = ", ".join(f"{hotkeys[m]}: {r}" for m, r in self.failed.items())
        def stop(self):
            for i in list(self.ids): _u32.UnregisterHotKey(self._hwnd, i)
            self.ids.clear()
    ```
  - 1369행은 `HotkeyManager(int(self.winId()))`로 바꿉니다. 창 HWND에 묶어야 트레이로 숨겨도 유지되고, 네이티브 모달 루프(파일 대화상자 등) 중에도 메시지가 버려지지 않습니다.
  - `MainToolbar`에 아래 메서드를 추가합니다.
    ```python
    def nativeEvent(self, et, message):
        hk = getattr(self, "hotkeys", None)
        if IS_WINDOWS and hk is not None and bytes(et) == b"windows_generic_MSG":
            m = wintypes.MSG.from_address(int(message))
            if m.message == 0x0312 and m.wParam in hk.ids:          # WM_HOTKEY
                mode = hk.ids[m.wParam]
                QTimer.singleShot(0, lambda: self.capture(mode))
                return True, 0
        return super().nativeEvent(et, message)
    ```
  - 충돌 표시:
    - 1371행과 2012행의 `restart()` 뒤에 `hotkeys.failed`가 비어 있지 않으면 트레이 메시지를 띄웁니다. 예: "Ctrl+Alt+F 를 다른 프로그램이 쓰고 있어요 → 설정에서 바꿔 주세요".
    - SettingsDialog에는 `failed`를 넘겨 줄마다 사유를 표시합니다. 1238행의 뭉뚱그린 "(현재 사용 불가)" 문구는 이것으로 대체합니다.
  - `SettingsDialog._accept` 1278-1291의 pynput 검증은 `parse_hotkey`로 대체합니다.
  - pynput 언급을 제거합니다: 118, 154, 189행, 사용법 21·23행.
  - 사용법 88행 수정:
    - 단축키는 관리자 창 위에서도 동작한다고 고칩니다.
    - 단, 그 창을 '창 캡처'하면 화면 잘라내기 방식으로 대체될 수 있다고 덧붙입니다.
  - 1247행 팁에 추가: `<print_screen>`을 쓰려면 Windows 설정 → 접근성 → 키보드 → 'Print Screen 키로 화면 캡처 열기'를 꺼야 합니다.
  - `restart_app`/`quit_app`이 `Popen` 전에 `hotkeys.stop()`을 부르는 순서(1620, 1638)는 그대로 둡니다. 새 프로세스가 1409를 받지 않게 하려면 이 순서가 필요합니다.
  - `force_foreground` 3단계(1097-1102, Alt 키 주입)는 삭제합니다.
    - 로그상 이 단계는 성공한 적이 없고(`attach_err=5` 반복), 다른 앱에 Alt 입력만 흘립니다.
    - `WM_HOTKEY`를 받은 프로세스는 전경 전환 권한을 얻기 때문에 이 단계가 필요 없습니다.
- **임시책 (1.0에서 교체가 어려울 때):** 912행 콜백에서 `GetAsyncKeyState`로 조합의 수식키가 실제로 눌려 있을 때만 emit합니다. VK_CONTROL 0x11, VK_MENU 0x12, VK_SHIFT 0x10입니다. 이것으로는 '왜 1'만 막히고, 키 전달과 충돌 감지는 그대로입니다.
- **작업량:**
  - 교체: 2–3시간 (테스트 포함)
  - 임시책: 15분

### 3. [high, 문서] 사용법.md가 EXE 사용자에게 틀린 안내를 하고, SmartScreen 안내가 없음

- **왜:** 서명 없는 EXE라 받는 사람은 첫 실행에서 반드시 'Windows의 PC 보호' 화면을 만나는데, 문서에 대처법이 없습니다. 게다가 문서는 Python 3.8 설치와 pip 설치(16-28행), "아이콘 다시 더블클릭 = 업데이트"(49행, EXE에서는 사실이 아님), pythonw 바로가기(69-73행), Python 재실행(98행)을 설명합니다.
- **수정:** 문서를 둘로 나눕니다.
  - `사용법.md` (EXE 사용자용)에 담을 내용:
    1. 설치: zip을 받아 `%LOCALAPPDATA%\Programs\PinCapture` 같은 고정 폴더에 풉니다. 바로가기는 exe 경로를 기억하므로, exe를 옮기면 바로가기를 다시 만들어야 합니다.
    2. SmartScreen: '추가 정보 → 실행'을 누르거나, zip 우클릭 → 속성 → '차단 해제'를 체크한 뒤 압축을 풉니다.
    3. 업데이트: 트레이 → 종료 → exe 교체.
    4. 자동 실행 끄기: 설정 체크박스(16번) 또는 작업 관리자 → 시작 앱.
    5. 제거: exe와 `핀캡처.lnk`(바탕화면/시작 프로그램/시작 메뉴), `%USERPROFILE%\.pincapture`를 삭제합니다.
    6. 요구 사항: Windows 10/11 64-bit.
    7. 저장 폴더: 기본 저장 폴더(사진\PinCapture)는 OneDrive 폴더 백업이 켜져 있으면 동기화됩니다.
    8. 인터넷 통신: 이 앱은 인터넷에 연결하지 않습니다.
  - `개발.md`에 담을 내용: Python 설치, pythonw 바로가기, 빌드, Python 재실행 설명.
  - 1행 `v0.5`와 83행 `(v0.1)`의 버전 표기는 빼고, "버전은 트레이 아이콘 툴팁에서 확인"으로 바꿉니다.
- **작업량:** 40분

---

## 2. 하면 좋음 (medium/low)

### 4. [medium] EXE 업데이트 경로가 없음: 새 버전 EXE를 실행해도 옛 버전 창만 앞으로 옴

- **왜:**
  - EXE에서는 mtime 감지(1341-1344, 1606-1612)가 항상 None이라 동작하지 않습니다.
  - 새 `PinCapture (1).exe`를 실행하면 "show"만 보내고 종료합니다(2154-2159). 그래서 사용자는 업데이트가 됐다고 착각합니다.
- **수정:**
  - 2154행: `sock.write(f"show {APP_VERSION}".encode())`
  - `_on_singleton_msg` 1602-1614:
    - `parts = bytes(conn.readAll()).decode(errors="ignore").split()`로 보내온 버전을 읽습니다.
    - mtime 비교는 `if not FROZEN:` 안에만 둡니다.
    - FROZEN이고 버전이 다르면 `QTimer.singleShot(0, …)`로 안내를 띄웁니다: "v{APP_VERSION} 이 이미 실행 중이에요. 새 버전을 쓰려면 트레이 → 종료 후 새 파일을 실행해 주세요". 그 다음 `_bring_to_front()`를 호출합니다.
  - (선택) '더 새 버전이 이김' 자동 교대:
    - 버전 비교는 숫자 튜플로 합니다.
    - 기존 쪽이 `_release_singleton()` → `b"bye"` 응답 → `quit` 순서로 처리합니다.
    - 새 쪽은 `bye`를 받으면 계속 기동합니다.
    - 대략 20줄입니다. 1.0에서는 안내 방식이 더 안전합니다.
- **작업량:** 40분

### 5. [medium] 바로가기 생성이 숨김 `powershell -EncodedCommand`(1149-1161)를 씀

- **왜:**
  - 서명 없는 EXE가 인코딩된 PowerShell을 띄우면 기관 PC의 EDR이 경보를 내는 전형적인 패턴입니다.
  - 제한 언어 모드(AppLocker/WDAC)에서는 `WScript.Shell`이 차단되어 버튼이 실패합니다.
  - 경로에 작은따옴표(`O'Brien`)가 있으면 생성 명령이 깨집니다.
- **수정:** IShellLinkW로 프로세스 안에서 바로가기를 만듭니다. 기존 `_com_method`를 재사용합니다.
  - `CoCreateInstance(CLSID_ShellLink {00021401-0000-0000-C000-000000000046}, CLSCTX_INPROC_SERVER, IID_IShellLinkW {000214F9-0000-0000-C000-000000000046})`
  - vtable: `SetPath`=20, `SetArguments`=11, `SetWorkingDirectory`=9, `SetIconLocation`=17
  - `QueryInterface(IPersistFile {0000010B-0000-0000-C000-000000000046})` → `Save`=6 (`fRemember=TRUE`) → `Release`
  - 그 뒤 기존 `set_shortcut_app_id()`를 호출합니다.
  - 값은 1번의 `launch_argv()`/`app_dir()`에서 가져옵니다.
  - PowerShell을 남긴다면:
    - 절대 경로 `%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe`로 호출합니다.
    - `-EncodedCommand` 대신 `-NonInteractive -Command`를 씁니다.
    - 값에 `'`→`''` 이스케이프를 적용합니다.
  - `QFile.link`는 쓰지 않습니다. 기존 파일을 덮어쓰지 못하고 아이콘도 지정할 수 없습니다.
- **작업량:** 1시간

### 6. [medium] 영역 캡처가 영구히 잠김: 오버레이를 Alt+F4로 닫거나 실행 중 예외가 나면 `_capturing=True`로 고착

- **왜:**
  - `_capturing`은 `_finish`(1706)에서만 풀립니다. 그런데 오버레이에 `closeEvent`가 없어 Alt+F4로 닫으면 신호가 나가지 않습니다. 실제로 재현했습니다.
  - 이후 모든 단축키와 버튼이 1650행에서 무시되고, 창도 숨겨진 채로 남습니다.
  - 모니터가 여러 대면 `_cleanup`(683-685)이 이미 삭제된 오버레이에서 RuntimeError를 냅니다.
- **수정:**
  - `SelectionOverlay`에 추가합니다. `_cleanup`이 `close()` 전에 `blockSignals(True)`를 하므로 재진입은 없습니다.
    ```python
    def closeEvent(self, e):
        self.canceled.emit()
        super().closeEvent(e)
    ```
  - `_cleanup` 682-686: 오버레이마다 `try: ov.blockSignals(True); ov.close()` / `except RuntimeError: pass`
  - `capture()` 1658-1665: 각 runner를 감쌉니다. 예: `QTimer.singleShot(delay, lambda: self._safe_run(self._run_region, False))`
    ```python
    def _safe_run(self, fn, *a):
        try:
            fn(*a)
        except Exception:
            import traceback; traceback.print_exc()
            s, self._session = self._session, None
            if s is not None:
                s._done = True; s._cleanup()
            self._finish(None, None, pin=False)     # _capturing 해제 + 창 복구
    ```
    예외를 다시 던지지 않습니다. 다시 던지면 "종료돼" 메시지 박스가 뜨는데 실제로 앱은 계속 실행 중입니다.
  - `_excepthook` 110행 문구는 "오류가 발생했어요 (앱은 계속 실행 중). 자세한 내용: 로그"로 바꿉니다. 슬롯에서 난 예외는 앱을 종료시키지 않기 때문입니다.
- **작업량:** 30분

### 7. [medium] 설정이나 저장 대화상자가 열린 채 단축키를 누르면, 입력이 막힌 오버레이가 모든 모니터를 덮음

- **왜:**
  - 모달 대화상자가 열려 있으면 그 뒤에 뜬 창은 Qt가 입력을 차단합니다. 오버레이에서 드래그, 우클릭, Esc가 모두 먹지 않고 `_capturing`도 고착됩니다.
  - 설정(2009-2010), 파일 대화상자(780, 1937, 1945), 메시지 박스(1273/1275/1972)가 모두 해당합니다.
- **수정:** `capture()` 1650행 바로 다음에 가드를 넣습니다.
  ```python
  modal = QApplication.activeModalWidget()
  if modal is not None or QGuiApplication.modalWindow() is not None:
      if modal is not None and modal.isVisible():
          modal.raise_(); modal.activateWindow()
          if IS_WINDOWS: force_foreground(int(modal.winId()))
      if self._tray is not None:
          self._tray.showMessage(APP_NAME, "열려 있는 설정/저장 창을 먼저 닫은 뒤 캡처해 주세요.",
                                 QSystemTrayIcon.MessageIcon.Warning, 2500)
      return
  pop = QApplication.activePopupWidget()
  if pop is not None: pop.close()
  ```
  SettingsDialog는 지금처럼 parent 없이 둡니다. parent를 주면 트레이에서 열었을 때 작업 표시줄 버튼이 사라집니다.
- **작업량:** 15분

### 8. [medium] 저장 실패가 조용함: 실패했는데 "클립보드에 복사됐어" 토스트만 뜸

- **왜:**
  - 다음 경우 `_save_image`(1743-1746, 1761-1763)는 로그만 남기고 None을 반환합니다:
    - USB나 NAS가 분리됨
    - 제어된 폴더 액세스가 서명 없는 exe의 '사진' 쓰기를 차단함
    - 접두어에 `/ : ? *`가 들어감
  - 이때 `_notify`(1784)는 성공처럼 보이는 토스트를 띄웁니다. 캡처는 메모리에만 있다가 종료하면 사라집니다.
  - 접두어의 `:`는 NTFS 대체 데이터 스트림에 쓰여 '성공'하고, 파일은 보이지 않게 됩니다.
- **수정:**
  - `_save_image`가 `(path, err)`를 반환하게 하고, `QImageWriter`로 저장합니다. 실패하면 `w.errorString()`을 씁니다.
  - `_finish` 1715-1716: `do_save and path is None`이면 `notify` 설정과 무관하게 경고를 띄우고 성공 토스트는 생략합니다. 문구: `showMessage("저장 실패", f"{save_dir}\n{err}\n캡처는 클립보드·보관함(메모리)에만 있어요.", Warning, 6000)`
  - 접두어 정리는 저장 시점과 `_accept` 1294행 두 곳에 적용합니다: `re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', prefix).strip(' .') or '캡처'`
  - `_accept`에서 저장 폴더가 쓰기 가능한지 확인합니다. `mkdir` 후 `.pincapture_test` 파일을 쓰고 지워 보고, 실패하면 `QMessageBox.question("이 폴더에 쓸 수 없어요: … 그래도 사용할까요?")`을 띄웁니다. NAS가 잠시 오프라인일 수도 있으므로 거부가 아니라 질문으로 합니다.
  - 784행(핀 저장)과 1941행(단일 저장)의 `save()` 반환값을 확인하고, 실패하면 경고를 띄웁니다.
- **작업량:** 45분

### 9. [medium] 보관함이 이미 파일로 저장된 캡처의 원본 QImage를 RAM에 계속 들고 있음 (최대 150개)

- **왜:** 1723행이 저장 성공 후에도 `image=img`를 유지하고, 이를 해제하는 코드가 없습니다. 트레이에 몇 주 상주하면 메모리가 이만큼 쌓입니다:

  | 캡처 종류 | 장당 크기 | 150장 |
  |---|---|---|
  | 1080p 전체 화면 | 8.3MB | 약 1.2GB |
  | 4K 전체 화면 | 33MB | 약 5GB |

- **수정:**
  - `_finish`에서 `self.add_entry(entry)` 다음 줄에 `if path: entry._image = None`을 넣습니다. 미리보기는 `_cur_img`가 계속 들고 있습니다.
  - `_trim_history`(1804)에서 메모리에만 있는 항목은 최신 30개만 남깁니다. 캐시 폴더는 만들지 않습니다.
  - (선택) `full_image()`에 경로를 키로 하는 2–3칸 `OrderedDict` 캐시를 두어, 행을 오갈 때마다 PNG를 다시 디코드하지 않게 합니다.
- **작업량:** 20분

### 10. [medium] 트레이 메뉴의 '창 캡처'가 작업 표시줄이나 바탕화면을 찍음

- **왜:**
  - `_own_hwnds()`(1675)는 QWidget만 제외합니다. `Shell_TrayWnd`, `Progman`/`WorkerW`, Qt 내부 창은 걸러지지 않습니다.
  - `_track_foreground`(1688)도 작업 표시줄을 '직전 외부 창'으로 기억합니다.
  - 535-536행은 실패하면 모니터 전체를 반환합니다.
- **수정:**
  - `_capturable(hwnd)`를 추가합니다. 다음 중 하나면 False를 반환합니다:
    - `IsWindow`/`IsWindowVisible`가 아니거나 `IsIconic`
    - `GetWindowThreadProcessId`로 얻은 pid가 `os.getpid()`와 같음 (자기 프로세스 창)
    - `GetClassNameW`가 {Shell_TrayWnd, Shell_SecondaryTrayWnd, Progman, WorkerW, NotifyIconOverflowWindow, TopLevelWindowForOverflowXamlIsland, Windows.UI.Core.CoreWindow, XamlExplorerHostIslandWindow} 중 하나
    - `DwmGetWindowAttribute(14 CLOAKED)`가 0이 아님
  - `_track_foreground`과 `capture_active_window`에 이 필터를 적용합니다. 순서는 전경 창 → `fallback_hwnd` → 커서 아래 루트 창입니다.
  - 535-536행은 None을 반환하게 바꿉니다.
  - 화면은 `screen_under_cursor()` 대신 `QGuiApplication.screenAt(창 중심)`으로 고릅니다. 오프셋은 `er.left - sg.x()`로 계산합니다. 배율이 걸린 보조 모니터에서는 `sg.x()*dpr`이 틀린 값이 됩니다.
  - `_run_window`에서 결과가 None이면 토스트를 띄웁니다: "캡처할 창을 찾지 못했어요. 창을 클릭한 뒤 Ctrl+Alt+W 를 눌러 주세요".
- **작업량:** 45분

### 11. [medium] 첫 실행 UX: 단축키와 저장 위치가 보이지 않고, 자동 실행 때마다 창이 뜨며, 창에 '종료'가 없음

- **왜:**
  - 빈 화면 문구(866, 1872)에 단축키와 자동 저장 폴더가 나오지 않습니다. 단축키는 툴팁에만 있습니다.
  - 2168행은 항상 `show()`를 호출하므로, 부팅 자동 실행 때마다 1020×660 창이 뜹니다.
  - 종료는 트레이 우클릭에만 있는데, Windows 11은 새 트레이 아이콘을 ^ 안에 숨깁니다.
- **수정:**
  - `PreviewPane`에 `set_hint(text)`를 추가하고, 866행 고정 문구 대신 이 hint를 그립니다.
  - `_update_tooltips`에서 hint를 만듭니다: "영역 Ctrl+Alt+A · 창 … · 전체 … · 핀 …\n어느 프로그램에서든 단축키로 캡처돼요\n자동 저장: {save_dir}". 단축키 등록에 실패했으면 `hotkeys.error`를 대신 표시합니다.
  - `--tray` 인자를 추가하고, 2168행을 `if not args.tray or toolbar._tray is None: toolbar.show()`로 바꿉니다. `create_shortcut`은 `place == "Startup"`일 때만 Arguments에 `--tray`를 붙입니다.
  - 톱니 버튼(1437)에 `QMenu`(설정…, 저장 폴더 열기, 종료)를 달고 `InstantPopup`으로 설정합니다. 1550행 문구에는 "작업 표시줄 오른쪽 ^ 안"을 명시합니다.
- **작업량:** 45분

### 12. [low] 단일 인스턴스 이름이 PC 전체에서 공용이고, `listen()` 결과를 확인하지 않음 (226, 2160-2162)

- **왜:**
  - 공용 PC에서 A 계정이 핀캡처를 켜 둔 상태면, B 계정은 연결도 `listen()`도 실패합니다.
  - 그 결과 B는 단일 인스턴스 보호 없이 실행되어, 실행할 때마다 앱이 중복으로 뜹니다(트레이 아이콘 여러 개, 단축키 중복 동작).
  - 2160행 `removeServer`는 Windows에서 아무 일도 하지 않습니다.
- **수정:**
  - 이름을 `"pincapture-" + sha1(f"{USERDOMAIN}\\{USERNAME}|{세션ID}")[:16]`로 바꿉니다. 세션 ID는 `ProcessIdToSessionId`로 얻으며 `IS_WINDOWS`일 때만 씁니다.
  - `server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)`를 설정합니다.
  - `if not server.listen(...)`이면 `errorString()`을 로그에 남깁니다.
  - 연결에 성공한 뒤의 `return 0`은 유지합니다. 쓰기에 실패했다고 정상 기동으로 넘어가면 중복 실행이 생깁니다.
  - 주의: 이름이 바뀌므로 v0.5.3이 실행 중이면 업데이트 후 한 번은 수동으로 종료해야 합니다.
- **작업량:** 15분

### 13. [low] 설정 파일이 손상되면 조용히 기본값으로 덮어씀 (272-294, 2146)

- **왜:**
  - 사용법 53행이 직접 편집을 권하는데, `"D:\캡처"`처럼 쓰면 JSON 문법 오류가 납니다.
  - 그러면 282행에서 기본값을 쓰고, 2146행이 그 기본값으로 파일을 덮어써 모든 설정이 사라집니다.
  - 타입 검사가 없어서 `"hotkeys": ""` 같은 값이 들어가면 실행할 때마다 크래시합니다.
- **수정:**
  - 파싱이 실패하면 `config.bad-YYYYmmddHHMMSS.json`으로 백업합니다. `replace` 자체도 try로 감쌉니다. 그 다음 기본값으로 시작하고 `main()`에서 안내 메시지 박스를 띄웁니다.
  - 키별 타입은 `DEFAULTS`와 비교해 맞는 값만 받습니다. `file_format`은 png/jpg 외의 값을 거부합니다.
  - 저장은 `.tmp`에 쓴 뒤 `os.replace`로 바꿔 끼웁니다. 기존 try/except는 유지합니다.
  - 사용법 53행의 경로 예시는 `/` 또는 `\\`를 쓰도록 고칩니다.
- **작업량:** 30분

### 14. [low] 보관함 스캔과 목록 정리 (1789-1802, 1995-2005, 2008-2013)

- **왜:**
  - 스캔 중 파일 하나만 `stat()`에 실패해도 보관함 전체가 비게 됩니다.
  - 저장 폴더를 다운로드 폴더로 지정하면 관계없는 이미지까지 섞입니다.
  - 저장 폴더를 바꿔도 다시 스캔하지 않습니다.
  - '목록에서 제거'한 항목이 재시작하면 돌아옵니다.
- **수정:**
  - `os.scandir`로 파일마다 `try: entry.stat()`를 개별 처리합니다.
  - 파일명 정규식 `r'_\d{8}_\d{6}(_\d+)?\.(png|jpe?g)$'`으로 이 앱이 만든 파일만 고릅니다. 현재 접두어로 거르면 접두어를 바꾼 뒤 예전 캡처가 사라지므로, 접두어 필터는 쓰지 않습니다.
  - `open_settings`에서 `save_dir`이 바뀌었으면 메모리 항목은 유지한 채 다시 스캔하고 `populate()`를 호출합니다.
  - 제거 버튼은 이름을 '목록에서 숨기기'로 바꾸거나, `cfg["hidden_paths"]`(최대 500개)에 저장해 스캔에서 건너뜁니다.
- **작업량:** 30분

### 15. [low] 클립보드용 임시 PNG가 종료 후에도 남음 (1896-1912)

- **왜:**
  - 자동 저장을 일부러 끈 사용자의 민감한 캡처가 `%USERPROFILE%\.pincapture\clipboard\`에 무기한 남습니다.
  - 사용법 44행은 이 파일을 '임시'라고 설명합니다.
- **수정:** 2162행 `listen` 바로 다음에 넣습니다.
  ```python
  shutil.rmtree(CONFIG_DIR / "clipboard", ignore_errors=True)
  app.aboutToQuit.connect(lambda: shutil.rmtree(CONFIG_DIR / "clipboard", ignore_errors=True))
  ```
  단일 인스턴스 검사보다 앞에 두면 안 됩니다. 두 번째 실행이 기존 인스턴스가 클립보드에 올려 둔 파일을 지워 버립니다. 사용법 44행에는 "종료 시 삭제"를 명시합니다.
- **작업량:** 5분

### 16. [low] 자동 실행을 끄는 UI가 없음 (1225-1228)

- **왜:** 등록 버튼만 있고 현재 상태도 표시되지 않습니다. 작업 관리자 → 시작 앱에서 끌 수는 있지만, 앱 안에서는 끌 방법이 없습니다.
- **수정:**
  - 등록 버튼을 `QCheckBox("Windows 시작 시 자동 실행")`로 바꿉니다. 초기 체크 상태는 `(_special_folder("Startup")/"핀캡처.lnk").exists()`로 정합니다.
  - `_accept`에서 체크되어 있으면 `create_shortcut("Startup")`을, 해제되어 있으면 Startup 링크만 `unlink(missing_ok=True)` 합니다. 시작 메뉴 링크는 작업 표시줄 고정에 필요하므로 지우지 않습니다.
  - 트레이에 '로그 폴더 열기' 메뉴를 추가합니다.
- **작업량:** 20분

### 17. [low] 로그에 앱 버전이 없고 네이티브 크래시가 기록되지 않음 (91-102, 225)

- **왜:**
  - 사용자가 보내 준 로그가 어느 빌드에서 나온 것인지 알 수 없습니다. `APP_VERSION`이 `_setup_logging()`(113) 다음인 225행에서 정의되기 때문입니다.
  - ctypes COM 호출(994-1021)이나 `PrintWindow`에서 접근 위반이 나면 앱이 흔적 없이 사라집니다.
- **수정:**
  - `APP_VERSION`을 42행 근처로 옮깁니다.
  - 99행 헤더를 `f"… 핀캡처 {APP_VERSION} {'exe' if FROZEN else 'py'} python {…} win {platform.version()} {sys.executable}"`로 바꿉니다. `sys.executable`은 그대로 남깁니다.
  - 96행 다음에 `faulthandler.enable(file=f, all_threads=False)`를 추가합니다. Windows에서는 처리된 예외도 'Windows fatal exception'으로 찍힐 수 있으니 힌트로만 봅니다.
  - Qt 버전은 `main()`에서 QApplication을 만든 뒤 출력합니다.
- **작업량:** 10분

### 18. [low] 독스트링에 개인 이메일과 로컬 경로가 있어 EXE에 들어감 (7, 19행)

- **왜:** PyInstaller는 기본 최적화 수준에서 독스트링을 보존합니다. 그래서 pyinstxtractor로 EXE를 풀면 작성자 이메일과 로컬 폴더 구조가 나옵니다. 버전 표기도 4행 v0.5, 225행 0.5.3, 사용법 1행 v0.5와 83행 v0.1로 제각각입니다.
- **수정:**
  - 6-19행의 이력을 독스트링 위 `#` 주석으로 옮기거나, 배포하지 않는 `CHANGELOG.md`로 뺍니다. 주석은 바이트코드에 들어가지 않습니다.
  - 4행과 사용법 3행의 '알캡처 스타일' 표현은 배포본에서 뺍니다. ESTsoft의 제품명입니다.
- **작업량:** 10분

---

## 3. 기능 추가 제안

| 기능 | 1.0 필수/나중/제외 | 이유 | 작업량 |
|---|---|---|---|
| UI 문구 해요체 통일 + 문자열을 한 곳(dict)에 모음 | 1.0 필수 | 받는 사람이 선배·교수입니다. 반말 문구가 약 15곳 있습니다(110, 186, 866, 1168, 1288, 1550, 1785, 1872, 1924, 1971 등). dict로 모아 두면 영어 UI도 쉬워집니다 | 30–45분 |
| 지연 캡처 3/5/10초 | 나중 (여유 있으면 1.0) | 지금은 Ctrl+Alt를 누르는 순간 메뉴와 툴팁이 닫혀 캡처할 수 없습니다. 카운트다운은 트레이 툴팁에 표시합니다(화면 라벨은 캡처에 찍힘). 영역 모드는 `RegionCaptureSession.start()` 전에 지연시키고, 지연 중에도 `_capturing=True`를 유지합니다 | 30–45분 |
| 주석 편집기 (사각형·화살표·가리기, Ctrl+Z, 새 파일로 저장) | 나중 (1.1) | 경쟁 도구와 비교해 가장 큰 공백입니다. 그래도 1.0 수정 작업과 일정이 겹치고, 당장은 Windows 기본 도구로 대신할 수 있습니다. ID 가리기에는 모자이크 대신 단색을 씁니다(고배율 DPI에서는 모자이크가 읽힘). 원본 파일은 덮어쓰지 않습니다. '캡처 후 바로 편집'을 넣는다면 `_finish`(1715-1718)가 원본을 먼저 저장하거나 클립보드에 올리지 않게 순서를 바꿔야 합니다 | 3–4시간 (~150줄) |
| 마우스로 창 골라 찍기 (hover-pick) | 나중 (0.6) | 1.0은 10번 보강으로 충분합니다. 현재 오버레이는 단순 클릭을 무시하므로 나중에 충돌 없이 추가할 수 있습니다. DPI가 섞인 다중 모니터 처리가 까다롭습니다 | 3시간 |
| 핀: 트레이 '모든 핀 닫기', Ctrl+휠 투명도, 저장 대화상자를 save_dir에서 시작(781, 1938, 1945) | 나중 | 핀을 여러 개 고정하면 하나씩 더블클릭해 닫아야 합니다 | 30분 |
| 탐색기에서 선택 파일 보기 (`explorer /select,`) | 나중 | '저장 폴더 열기'는 폴더만 열기 때문에 파일을 직접 찾아야 합니다 | 10분 |
| 보관함 드래그 아웃, 휴지통 삭제, 이름 바꾸기, 우클릭 메뉴 | 나중 (1.1) | 다른 캡처 도구에서 흔한 흐름이지만 출시를 막을 정도는 아닙니다. 단일 항목 복사는 지금처럼 비트맵으로 유지합니다 | 2시간 |
| 영역 선택 돋보기, 조절 핸들, 방향키 미세조정 | 나중 | 2px만 빗나가도 다시 그려야 합니다. 선택 후 확정하는 2단계 상태 처리가 필요합니다 | 2–3시간 |
| 영어 UI | 나중 | 외국인 연구실 구성원이 쓸 때만 필요합니다 | 2시간 (문자열 dict 이후) |
| Inno Setup 사용자별 설치본 (onedir) | 나중 | 제거 프로그램, 고정 경로, 빠른 재실행이 장점입니다. 1.0은 onefile 단일 exe가 가장 덜 깨집니다 | 2시간 |
| 스크롤 캡처 | 제외 | 500줄 이상이고 스크롤 주입과 이어붙이기가 필요하며, 다른 도구에서도 불안정합니다. 브라우저 전체 페이지 캡처를 안내합니다 | — |
| 모니터에 걸친 영역 선택 | 제외 | 비용에 비해 수요가 적습니다 | — |
| 파일명 패턴 설정 | 제외 | 대부분의 사용자가 바꾸지 않습니다 | — |
| 첫 실행 OneDrive 경고 대화상자 | 제외 | Windows 기본 캡처 도구도 같은 위치에 저장합니다. 문서 한 줄로 충분합니다 | — |
| 코드 서명 인증서 | 제외 (규모가 커지면 재검토) | 비용에 비해 효과가 낮습니다. EV도 2024년부터는 SmartScreen을 즉시 통과하지 않습니다 | — |

---

## 4. 빌드·배포 체크리스트

### 빌드
- [ ] PyInstaller 6.9 이상인지 확인합니다. 현재 6.22.3입니다. `PYINSTALLER_RESET_ENVIRONMENT`를 쓰려면 6.9 이상이 필요합니다.
- [ ] 아이콘을 만듭니다.
  - `make_app_icon(size=64)`에 `p.scale(size/64, size/64)`를 넣어 256px로 렌더한 뒤 Pillow로 저장합니다: `Image.open(png).save("pincapture.ico", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])`
  - 만든 ico 파일은 저장소에 넣습니다.
- [ ] 최초 1회 다음 명령으로 빌드합니다.
  ```
  pyinstaller --onefile --noconsole --noupx --name PinCapture --icon pincapture.ico pincapture.py
  ```
  - onefile을 유지합니다. 비전문 사용자에게는 단일 exe가 가장 덜 깨집니다.
  - `--noupx`는 문서화를 위해 명시합니다.
- [ ] 생성된 `PinCapture.spec`을 커밋하고, 이후에는 `pyinstaller PinCapture.spec`으로만 빌드합니다. spec에서 안 쓰는 DLL을 basename으로 비교해 제외합니다. dest 경로에 `PySide6\` 접두사가 붙어 있으므로 startswith로는 걸러지지 않습니다.
  ```python
  import os
  DROP = {"opengl32sw.dll", "qt6pdf.dll", "qpdf.dll", "qt6quick.dll", "qt6qml.dll", "qt6qmlmodels.dll"}
  a.binaries = [b for b in a.binaries if os.path.basename(b[0]).lower() not in DROP]
  ```
  - 이렇게 하면 추출량이 약 25–30% 줄어듭니다.
  - 빌드한 뒤 PNG/JPG 저장과 썸네일이 정상인지 확인합니다.
- [ ] (선택) `--version-file version_info.txt`를 추가합니다. 값은 FileVersion 1.0.0.0, ProductName PinCapture, FileDescription 핀캡처로 하고 손으로 작성한 파일 하나면 충분합니다. 효과는 탐색기 '자세히' 탭에 정보가 표시되는 것뿐이고, SmartScreen에는 영향이 없습니다.
- [ ] icon을 넣어 빌드했다면 `app_icon_path()` 맨 앞에 `if FROZEN: return Path(sys.executable)`를 둘 수 있습니다. 1045행과 1145행이 이미 `,0`을 붙이므로 이것만으로 동작합니다.
- [ ] pynput을 유지하는 경우(2번 미적용) EXE에서 단축키가 실제로 동작하는지 확인합니다. 안 되면 `--hidden-import pynput.keyboard._win32`를 추가합니다.
- [ ] 빌드 전에 `APP_VERSION`을 올리고, 독스트링의 이메일과 경로를 제거했는지 확인합니다(18번).

### 배포 zip에 넣을 파일
- [ ] `PinCapture.exe`
- [ ] `사용법.md` (EXE 사용자용, 3번)
- [ ] `LICENSE` (MIT, 작성자 이름)
- [ ] `THIRD_PARTY_NOTICES.txt` 내용:
  - "Qt 6.11.2 / PySide6·shiboken6 6.11.2 (및 pynput 1.8.2) 를 GNU LGPL v3 로 사용, 수정하지 않음"
  - 소스 링크: download.qt.io/official_releases/QtForPython, pypi.org/project/pynput/1.8.2
  - "재링크: source\requirements.txt 설치(또는 수정본) 후 source\BUILD.txt 명령 실행"
  - Qt 서드파티 목록(https://doc.qt.io/qt-6/licenses-used-in-qt.html, FreeType 크레딧 포함)
  - Python 3.13(PSF-2.0)과 six(MIT) 각 한 줄
- [ ] `licenses\` 폴더: `LGPL-3.0.txt`, `GPL-3.0.txt`(site-packages의 `PySide6_Essentials-6.11.2.dist-info`에서 복사), `PSF-2.0.txt`, `six-MIT.txt`
- [ ] `source\` 폴더: `pincapture.py`, `requirements.txt`, `BUILD.txt`(정확한 빌드 명령과 spec)
  - requirements.txt 고정 버전: `PySide6==6.11.2`, `pyinstaller==6.22.3`, 그리고 pynput을 유지하면 `pynput==1.8.2`, `six==1.17.0`
- [ ] 정보/라이선스 대화상자는 필요 없습니다. 앱이 실행 중에 저작권 고지를 표시하지 않으므로 LGPL §4(c)에 해당하지 않습니다.

### 서명·SmartScreen 대응
- [ ] 인증서는 사지 않습니다. Azure Artifact Signing은 개인의 경우 미국·캐나다만 가능하고, EV도 즉시 통과시켜 주지 않습니다. 배포가 커지면 Certum 오픈소스 인증서를 검토합니다.
- [ ] 배포 메시지(메신저나 메일)와 사용법에 같은 문장을 넣습니다: "처음 실행할 때 'Windows의 PC 보호'가 뜨면 '추가 정보' → '실행'을 눌러 주세요. 또는 zip 우클릭 → 속성 → '차단 해제' 체크 후 압축을 풀어 주세요."
- [ ] SHA-256을 공개합니다: `Get-FileHash PinCapture.exe -Algorithm SHA256`
- [ ] 릴리스마다 VirusTotal에서 검사합니다. 오탐이 나오면 Microsoft WDSI, AhnLab(V3), ESTsecurity(알약)에 제출한 뒤 배포합니다.

### 테스트 절차 (Python 없는 Windows 10/11 x64 PC나 VM, 가능하면 두 번째 Windows 계정에서)
- [ ] zip을 브라우저나 카톡으로 받아 MOTW가 붙은 상태에서 SmartScreen 흐름을 확인합니다. 그 다음 `%LOCALAPPDATA%\Programs\PinCapture`에 풉니다.
- [ ] 첫 실행: 창과 단축키 안내가 표시되는지, 로그 헤더에 버전과 `exe`가 찍히는지 확인합니다.
- [ ] 캡처 4종을 단축키, 버튼, 트레이 메뉴로 각각 실행합니다. 다중 모니터와 125/150% DPI에서도 확인합니다.
- [ ] 트레이 메뉴 '창 캡처'를 실행했을 때 작업 표시줄이 아니라 직전 앱 창이 찍히는지 확인합니다.
- [ ] Word를 연 상태에서 Ctrl+Alt+F를 눌러 각주가 생기지 않는지 확인합니다.
- [ ] Ctrl+Alt+Del → 잠금 → 해제 후 한글로 ㅁㅈㄹㅂ을 쳐서 캡처가 뜨지 않는지 확인합니다.
- [ ] 작업 관리자(관리자 권한 창)에 포커스를 둔 상태에서 단축키가 동작하는지 확인합니다.
- [ ] 단축키 하나를 카톡 등이 쓰는 조합으로 바꿔 '다른 프로그램이 사용 중' 표시가 나오는지 확인합니다.
- [ ] 설정 → 바로가기 3종을 만든 뒤 .lnk 속성을 확인합니다. 대상은 exe만 있어야 하고(인자 없음, 시작 프로그램용만 `--tray`), 시작 위치는 exe 폴더여야 합니다. 앱이 실행 중일 때와 종료한 뒤에 각각 더블클릭해 봅니다.
- [ ] 작업 표시줄에 고정 → 종료 → 고정 아이콘을 클릭해 실행되는지 확인합니다.
- [ ] 로그오프 후 다시 로그온하거나 재부팅해서 자동 실행되는지, 그리고 창 없이 트레이에만 뜨는지 확인합니다.
- [ ] 이름이 다른 새 버전 exe를 실행해 업데이트 안내나 교대가 되는지 확인합니다. 실행 중인 exe를 덮어쓰려 하면 잠겨 있음을 안내하는지도 확인합니다.
- [ ] 저장 폴더를 없는 드라이브로 바꾸고 캡처해 '저장 실패' 경고가 뜨는지 확인합니다. 접두어에 `:`를 넣었을 때 거부되는지도 확인합니다.
- [ ] 설정 창을 열어 둔 채 단축키를 눌러 캡처가 거부되고 안내가 뜨는지 확인합니다.
- [ ] 영역 오버레이에서 Alt+F4를 누른 뒤에도 다음 캡처가 정상인지 확인합니다.
- [ ] 4K 전체 화면 캡처를 30회 한 뒤 작업 관리자에서 메모리 사용량을 확인합니다.
- [ ] 다중 선택 복사 → 종료 후 `.pincapture\clipboard`가 비어 있는지 확인합니다.
- [ ] 종료 후 `%TEMP%\_MEI*` 폴더가 남지 않았는지, 로그에 Traceback이 없는지 확인합니다.
- [ ] V3나 알약이 설치된 PC에서 실행해 봅니다.

---

## 5. 반영하지 않은 지적

**기각된 지적**
- **"단축키 등록 실패가 사용자에게 안 보임 → 풍선 알림 추가"**
  - pynput은 `SetWindowsHookEx`를 리스너 스레드 안에서 호출하고, 실패해도 결과를 확인하지 않고 그대로 넘어갑니다. 그래서 922-925행의 except에 도달하지 않습니다.
  - 다른 프로그램과 충돌해도 '실패'가 아니라 '양쪽 모두 동작'이 됩니다. 따라서 제안된 알림은 실행될 일이 없는 코드입니다.
  - 실제 감지는 2번(`RegisterHotKey` 1409)에서 처리했습니다.
- **"로그 회전 실패 시 print가 전부 유실됨"**
  - 회전 실패는 'show'만 보내고 바로 끝나는 두 번째 인스턴스에서만 현실적으로 일어납니다.
  - faulthandler는 진단 개선 수준이라 17번에 선택 사항으로만 넣었습니다.
- **"테스트·릴리스 게이트 없음 (--selftest 항상 0, import 부작용, 6개 모듈로 분리)"**
  - 최종 사용자에게 영향이 없습니다. JPG/ICO 플러그인은 PySide6 훅이 기본으로 수집합니다.
  - 로깅을 `main()`으로 옮기면 import 단계(`_handle_missing_deps`)의 진단이 깨집니다. 모듈 분리는 단일 파일 설계와 맞지 않습니다.
  - 대신 4절의 '다른 PC 실기 테스트'로 대체했습니다.

**부분 기각된 주장**

| 주장 | 기각 사유 |
|---|---|
| AltGr+Q가 핀 캡처를 일으킴 | pynput은 AltGr을 `alt_gr`로 따로 구분하므로 일어나지 않습니다 |
| 키보드 훅과 `keybd_event`가 백신 탐지의 원인 | 코드는 PYZ 안에 압축된 바이트코드라 정적 검사에 보이지 않습니다. 오탐의 주원인은 서명 없는 onefile 부트로더입니다 |
| UPX가 Qt DLL을 몰래 압축함 | PyInstaller 6.22.3은 CFG가 켜진 DLL과 Qt 플러그인에 UPX를 자동으로 끕니다. PATH에 upx도 없습니다 |
| 런타임 ICO가 64→256으로 늘어나 흐릿함 | `QIcon.pixmap()`은 확대하지 않습니다. 실제 파일은 64×64 한 장입니다 |
| onedir + zip 배포 권장 | 사용자가 zip 안에서 바로 실행하거나 exe만 옮기면 python313.dll 로드에 실패합니다. 몇 초 늦게 뜨는 것보다 나쁘므로 onefile을 유지합니다 |
| 공용 PC의 다른 계정은 앱을 아예 못 켬 | 실제로는 반대입니다. 연결이 거부되고 listen도 실패해서 단일 인스턴스 없이 중복 실행됩니다(12번에 반영) |
| OneDrive로 '몰래' 업로드됨 | 저장 경로가 토스트, 정보줄, 문서에 표시되고 Windows 기본 캡처 도구와 같은 동작입니다. 문서 한 줄만 반영했습니다 |
| 의존성 누락 시 최대 1분 멈춤 | Python이 없는 PC에서는 ms 단위로 끝납니다. 엉뚱한 안내가 나오는 문제만 1번 5단계에 반영했습니다 |
| 메모리 부족(OOM)으로 앱이 죽음 | 64-bit 환경에서는 페이징되어 그럴 가능성이 낮습니다. 실제 증상은 메모리 사용량이 수백 MB에서 수 GB까지 커지는 것입니다(9번) |
| "자동 실행을 끌 방법이 없음" | 작업 관리자 → 시작 앱에서 끌 수 있습니다. 앱 안의 체크박스만 16번에 반영했습니다 |
| `%ProgramData%\Miniconda3` 경로에 프로그램을 심거나, `py`/`powershell` 같은 경로 없는 이름이 바꿔치기됨 | 이론적인 위험이고 EXE에서는 거의 실행되지 않는 경로입니다. powershell 절대 경로만 5번에 반영했습니다 |
| "Windows 10 21H2 이상" 요구 문구 | 검증되지 않았습니다. "Windows 10/11 64-bit"로만 적습니다 |
| 영역 선택 지연 카운트다운을 화면 라벨로 표시 | 라벨이 캡처에 찍힙니다. 트레이 툴팁으로 바꿨습니다 |
| 120초 watchdog | 정상적으로 느리게 선택하는 경우도 취소합니다. 6번의 `closeEvent`로 필요가 없어졌습니다 |
| 설정 대화상자 `parent=self` | 트레이에서 열면 작업 표시줄 버튼이 사라집니다 |
| 업데이트 교대 3초 폴링 | 기존 쪽이 서버를 먼저 닫으면 필요 없습니다 |
| 버튼에 단축키 둘째 줄 표시 | 58×56 고정 크기라 잘립니다. 빈 화면 hint로 대체했습니다 |
| 트레이 `messageClicked`로 탐색기 열기 | 모든 풍선 클릭에 반응해 오동작합니다 |
| 첫 닫기 때 '트레이로/종료' 묻는 대화상자 + `close_to_tray` 설정 | 트레이로 최소화는 표준 동작이라 필요 없습니다 |
| 단일 항목 복사를 파일 URL로 | Office와 카톡의 붙여넣기 동작이 바뀝니다 |
| 메모리 전용 캡처를 `~/.pincapture/unsaved`에 보존 | 자동 저장을 끈 사용자의 선택과 어긋납니다 |
| `IconLocation = sys.executable,0` | `--icon`이 없으면 PyInstaller 기본 아이콘이 표시됩니다. 기존 .ico를 유지합니다 |
| 정보/라이선스 대화상자 필수, 또는 LGPL 때문에 onedir 필수 | §4(c)에 해당하지 않습니다. 소스와 빌드 방법을 동봉하면 §4(d)(0)을 충족합니다 |
| `--optimize 2`로 독스트링 제거 | 주석으로 옮기는 편이 위험이 없습니다 |
