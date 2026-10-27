# 개발자 안내

소스로 실행하고 고칠 때 알아야 할 동작을 정리했어요. 다른 내용은 아래 문서에 있어요.

| 찾는 것 | 문서 |
|---|---|
| 명령 요약, 작업 규칙, 불변 조건, 개인정보 규칙 | `AGENTS.md` |
| 코드 구조, 설정 키 목록, 환경 변수 | `docs/ARCHITECTURE.md` |
| 배포 절차, 수동 시험 | `docs/RELEASE.md` |
| 최종 사용자 안내 | `installer/docs/사용법.txt` |

경로의 `~`는 `%USERPROFILE%`(`Path.home()`)이에요. 예시 경로는 `C:\Users\<사용자>`로 적었어요.

## 1. 소스로 실행하기

```powershell
py -3.13 -m pip install -r requirements.txt
py -3.13 pincapture.py          # 콘솔에 오류가 보여요
pyw -3.13 pincapture.py         # 콘솔 없이. 오류는 로그와 메시지 박스로만 보여요
```

- pynput이 없어도 앱은 떠요. 단축키만 꺼지고, 설정 창의 단축키 그룹 제목에 "(현재 사용 불가)"가 붙어요. 로그에는 `[hotkey] pynput 사용 불가` 줄이 남아요.
- 설치판(EXE)과 소스 실행판은 같은 설정 폴더(`~/.pincapture`), 같은 실행 감지 뮤텍스(`PinCaptureRunning`), 같은 단일 인스턴스 파이프를 써요. 그래서 서로를 "이미 실행 중"으로 봐요.
  - 소스 실행판이 떠 있을 때 설치판을 실행하면 소스 실행판 창이 앞으로 와요.
  - 처음 설치할 때는 설치 폴더에 EXE가 없어 `--quit`을 보낼 수 없고, `taskkill` 대상도 `PinCapture.exe`뿐이에요. 그래서 설치 프로그램이 "실행 중이라 설치할 수 없습니다"라고 안내해요. 트레이에서 먼저 종료하세요.
  - 이미 설치판이 있으면 설치·제거 때 보내는 `--quit`이 소스 실행판도 닫아요.

이미 실행 중일 때 다시 실행하면 이렇게 동작해요.

| 상황 | 동작 |
|---|---|
| 일반 실행 | 기존 창이 앞으로 와요(`show` 신호). 새 프로세스는 전경 권한을 넘기고 바로 끝나요 |
| `--tray`로 실행 | 아무 일도 없어요(`tray` 신호) |
| 소스 실행 중인데 그 뒤 `pincapture.py`가 수정됨 | 일반 실행 한 번으로 기존 인스턴스가 **새 코드로 재시작**돼요. 소스 실행판의 업데이트 방법이에요 |
| 트레이 메뉴 `다시 시작 (업데이트 적용)` | `launch_argv()`로 새 프로세스를 띄우고 기존 프로세스는 끝나요(EXE는 `다시 시작`) |
| `--quit` | 종료를 요청하고 뮤텍스가 사라질 때까지 최대 10초 기다려요 |
| 홈 폴더(`USERPROFILE`)가 다름 | 단일 인스턴스 파이프 이름이 달라져서 별개 인스턴스로 떠요. 시험과 스크린샷 생성은 이 성질을 이용해요 |

수동 시험용 환경 변수 `PINCAP_TEST_RESTART`, `PINCAP_TEST_AUTOEXIT`는 `docs/ARCHITECTURE.md` 19절에 있어요.

수식(LaTeX)은 선택입니다. 사용자는 글자 복사의 **수식**에서 **설치**를 누를 때만 zip을 받아요. Python이나 pip는 필요 없어요. `requirements-math.txt`를 `requirements.txt`나 설치 파일에 넣지 않아요. `installer/PinCapture.spec`이 `onnxruntime`, `tokenizers`, `yaml`, `numpy`를 빼고, `build.py`의 묶음 검사가 경로에 `onnxruntime`, `tokenizers`, `pp_formulanet`, `pix2tex`가 있으면 빌드를 멈춰요. 릴리스에 붙는 zip은 `py -3.13 installer/build_math_pack.py`가 만들고, `pincapture.py`의 `MATH_PACK_SHA256`·`MATH_PACK_BYTES`와 같아야 해요. `--check`가 다르면 끝나요. 태그 빌드가 이 zip을 초안 릴리스에 넣어요. 초안은 공개 주소로 받을 수 없으니, 설치 버튼이 동작하려면 릴리스를 게시해야 해요.

## 2. Python 선택 함정

PC에 Python이 여러 개 있으면(python.org 3.13·3.12, Microsoft Store판, Miniconda 등) `python`이나 `py`가 가리키는 Python이 설치·업데이트 뒤에 바뀔 수 있어요. 그러면 PySide6가 없는 Python으로 실행돼요.

- 명령은 항상 `py -3.13`처럼 버전을 지정해요. 설치된 목록은 `py -0p`로 봐요.
- **자동 재실행**: 소스 실행에서 `import PySide6`가 실패하면 앱이 스스로 다른 Python을 찾아요(`_handle_missing_deps`, `_find_python_with_deps`).
  1. 후보를 이 순서로 모아요: `py -0p` 목록 → `%ProgramData%\Miniconda3`·`Anaconda3` → `~\miniconda3`·`~\anaconda3` → `%LOCALAPPDATA%\Programs\Python\Python3*`(폴더 이름의 문자열 역순이라, 섞여 있으면 `Python39`가 `Python313`보다 먼저). 지금 실행 중인 Python은 빼요.
  2. `PySide6`와 `pynput`이 둘 다 있는 Python을 먼저 고르고, 없으면 `PySide6`만 있는 Python을 골라요.
  3. 같은 인수로 다시 실행하고 `PINCAP_REEXEC=1`을 붙여 무한 반복을 막아요. 콘솔 없이 실행됐다면 `pythonw.exe`를 써요.
  4. 하나도 없으면 `"<그 Python>" -m pip install PySide6 pynput` 명령을 메시지 박스로 알려 줘요. 개발 환경에서는 버전이 고정된 `-r requirements.txt` 설치를 권해요.
  - 진행 상황은 로그의 `[deps]` 줄에 남아요. EXE는 이 과정을 거치지 않고 "구성 요소를 불러오지 못했습니다"를 안내해요.
- 소스 실행판 바로가기는 **만든 순간의 Python**(`sys.executable` 옆의 `pythonw.exe`)과 `pincapture.py`의 절대 경로를 기억해요. Python을 바꿨거나 파일을 옮겼다면 바로가기를 다시 만들어요(4장). 소유자의 바로가기가 저장소 루트의 `pincapture.py`를 가리키는 것도 이 때문이에요.

## 3. 설정·로그·임시 파일

| 경로 | 내용 |
|---|---|
| `~/.pincapture/config.json` | 설정. 시작할 때 읽은 직후 다시 저장하고, 설정 창에서 확인을 누를 때, `×`로 창을 트레이로 숨길 때, 종료·다시 시작할 때도 저장해요(Esc로 숨길 때는 저장하지 않아요). 키 목록은 `docs/ARCHITECTURE.md` 2절에 있어요 |
| `~/.pincapture/pincapture.log` | 실행 기록. 시작할 때 512 KB를 넘었으면 `pincapture.log.old`로 바꿔요. `PINCAP_NO_LOG=1`이면 기록하지 않아요 |
| `~/.pincapture/clipboard/` | 여러 캡처를 한꺼번에 복사할 때 만드는 임시 PNG. 다음 다중 복사 때 비우고, 종료해도 남아 있어요 |
| `~/.pincapture/pincapture.ico` | 소스 실행판 바로가기와 작업 표시줄용 아이콘(처음 한 번만 만들어요). EXE는 EXE에 들어 있는 아이콘을 써요 |
| 저장 폴더(기본 `사진\PinCapture`) | 캡처 이미지. 사진 폴더가 OneDrive로 옮겨진 PC에서는 그 안이에요. 기본값은 Windows Known Folder API의 사진 폴더라서 `USERPROFILE`을 바꿔도 따라가지 않아요. 홈을 격리해 실행할 때는 `config.json`에 `save_dir`도 따로 지정해요(`tests/_isolation.py`) |

손으로 `config.json`을 고칠 때 주의할 점:
- 앱을 끄고 고쳐요. 실행 중이면 창을 숨기거나 종료할 때 앱이 덮어써요.
- **BOM 없는 UTF-8**로 저장해요. BOM이 있거나 JSON 문법이 틀리면 읽기에 실패하고(`[config] 읽기 실패, 기본값 사용`), 시작하면서 기본값으로 파일을 **덮어써요**.
- 단축키는 pynput 형식이에요: `<ctrl>+<alt>+a`, `<ctrl>+<shift>+s`, `<print_screen>`. 빈 문자열이면 그 단축키를 쓰지 않아요. 형식이 틀린 항목은 건너뛰고 로그에 `[hotkey] '...' 형식 오류`를 남겨요.

## 4. 바로가기: 앱 설정 버튼과 설치 프로그램

| | 설정 창 `바탕화면 아이콘 만들기` | 설정 창 `부팅 시 자동 실행 등록` | 설치 프로그램(`PinCapture.iss`) |
|---|---|---|---|
| 만드는 곳 | 바탕화면 + 시작 메뉴 | 시작 프로그램 + 시작 메뉴 | 시작 메뉴 `핀캡처`·`핀캡처 사용법`, 바탕화면(선택), 시작 프로그램(선택) |
| 파일 이름 | `핀캡처.lnk` | `핀캡처.lnk` | `핀캡처.lnk`, `핀캡처 사용법.lnk` |
| 대상 | `launch_argv()`: 소스면 `pythonw.exe "<경로>\pincapture.py"`, EXE면 `PinCapture.exe` | 같음 + `--tray` | `{app}\PinCapture.exe`(자동 실행은 `--tray`) |
| 시작 위치 | `app_dir()` | `app_dir()` | `{app}` |
| AppUserModelID | `set_shortcut_app_id`로 기록 | 같음 | `[Icons]`의 `AppUserModelID` |
| 만드는 방법 | 숨김 PowerShell `WScript.Shell`(`-EncodedCommand`) | 같음 | Inno Setup |

- 이름이 같아서 나중에 만든 쪽이 덮어써요. 설치판을 **제거하면** 바탕화면·시작 프로그램·시작 메뉴의 `핀캡처.lnk`를 모두 지워요(`[UninstallDelete]`). 같은 계정에 소스 실행판 바로가기가 있었다면 그것도 사라지니 설정 창에서 다시 만들어요.
- 자동 실행을 끄는 버튼은 앱에 없어요. Windows 설정 → 앱 → 시작 프로그램에서 끄거나 `shell:startup` 폴더의 `핀캡처.lnk`를 지워요.
- 작업 표시줄 고정: 메인 창에는 처음 보이기 전에 AppID, 재실행 명령(`relaunch_command()`), 이름, 아이콘을 기록해요(`set_window_taskbar_identity`). 예전에 Python 아이콘으로 고정해 둔 것은 `pythonw.exe` 자체를 고정한 거예요. 고정을 해제하고 실행 중인 창에서 다시 고정해요.

## 5. 문제 해결

### 로그부터 봐요

```powershell
Get-Content "$env:USERPROFILE\.pincapture\pincapture.log" -Tail 60 -Encoding UTF8
```

실행마다 `===== <날짜 시각>  핀캡처 <버전> (exe|py)  python <버전>  <실행 파일>  args=[...]` 줄로 시작해요. 처리되지 않은 예외는 Traceback으로 기록되고 메시지 박스로도 떠요. 로그를 남에게 보낼 때는 실행 파일 경로의 사용자 이름을 가려요.

| 접두어 | 내용 |
|---|---|
| `[deps]` | PySide6를 찾지 못함, 다른 Python으로 재실행 |
| `[hotkey]` | pynput 사용 불가, 단축키 형식 오류, 등록 실패 |
| `[capture]` | 화면 캡처 차단 감지 |
| `[window]` | 캡처 후 창을 앞으로 가져오지 못함 |
| `[singleton]` | 다른 실행에서 신호를 받음, `listen` 실패 |
| `[taskbar]` | 작업 표시줄 식별 정보·바로가기 AppID 기록 실패 |
| `[config]`, `[save]` | 설정 읽기·쓰기 실패, 일괄 저장 실패 |
| `[history]` | 저장 폴더의 기존 캡처 스캔 실패(보관함이 비어 보일 때) |
| `[quit]`, `[restart]`, `[args]`, `[mutex]` | `--quit` 결과, 재시작 실패, 무시한 인수, 뮤텍스 생성 실패 |

### 캡처가 검게 나와요

- **판정**: 모든 모니터의 캡처가 픽셀 하나 남김없이 `#000000`이면 차단으로 봐요(`screens_capture_blocked`). 그러면 오버레이·파일·클립보드·보관함에 남기지 않고 안내 창 "화면 캡처가 막혀 있어요"를 띄워요. 로그에는 `[capture] 모든 모니터가 완전한 검정으로 캡처됨` 줄이 남아요.
- **흔한 원인**: 정부24·홈택스·은행 사이트의 전자문서 뷰어나 보안 프로그램의 '화면 캡처 방지'예요. 2026-10-26 사례에서는 정부24 '전자문서 전용 Viewer'(Unidocs ezPDFReader 2.0G)가 Teruten WebCube를 몰래 함께 설치했어요(`TUCtlSystem` 자동 시작 서비스, `TDepend`/`TDepend64` 주입기, `T_Prevent64.dll`). 이 모듈은 핀캡처와 캡처 도구를 포함해 약 300개 프로세스에 주입됐어요. 새로 띄운 프로세스도 약 3초 뒤 주입되면 검게 찍혀서, 주입기가 도는 동안은 **핀캡처를 다시 시작해도 소용없어요.** 자세한 기록은 `docs/reviews/2026-10-26-black-capture.md`에 있어요.
- **확인**:
  ```powershell
  tasklist /m T_Prevent64.dll      # 이 DLL이 주입된 프로세스 목록
  sc.exe query TUCtlSystem         # 서비스 상태
  ```
- **해결 순서**: 전자문서 보기 창 닫기 → 그 사이트의 브라우저 창 닫기 → PC 다시 시작 → 설정 → 앱에서 `ezPDFReader 2.0G` 제거(서비스는 남을 수 있어요).
- **오탐**: 모니터가 하나뿐인 PC에서 화면 전체가 실제로 검으면(전체 화면 게임 등) 같은 안내가 뜰 수 있어요. 반대로 한 모니터만 검게 만드는 제품은 감지하지 못해요.
- **정책**: 감지와 안내만 해요. 우회 코드는 넣지 않아요(`AGENTS.md` 6장).

### 단축키가 안 먹어요

- 설정 창의 단축키 그룹 제목과 로그의 `[hotkey]` 줄을 먼저 봐요.
- **관리자 권한 창이 앞에 있을 때**: Windows의 권한 분리(UIPI) 때문에, 일반 권한으로 실행된 핀캡처의 키보드 훅(pynput)에는 관리자 권한 창으로 가는 입력이 오지 않아요. 이때는 핀캡처 창이나 트레이 메뉴로 캡처해요. 핀캡처를 관리자 권한으로 실행할 수도 있지만, 그러면 설치 프로그램이 앱을 닫지 못하니 업데이트 전에 직접 종료해야 해요. `RegisterHotKey`로 바꿀지는 소유자 결정 대기 항목이에요.
- **다른 프로그램과 겹칠 때**(카카오톡 등): pynput은 키를 가로채지 않아서 두 프로그램이 모두 반응할 수 있어요. 설정에서 다른 조합으로 바꿔요.
- 단축키는 자동으로 시험할 수 없어요. pynput이 프로그램이 보낸 키 입력을 무시하기 때문이에요. 실제 키보드로 확인해요.

### 캡처 후 창이 앞으로 안 와요

Windows는 최근 입력을 받지 않은 프로세스가 창을 앞으로 가져오는 것을 막아요. `force_foreground`는 `SetForegroundWindow` → `AttachThreadInput` → Alt 키 → TOPMOST 순서로 시도해요. 모두 실패하면 로그에 `[window] 전경 전환 안 됨: ...`이 남아요. Qt 플랫폼이 `windows`가 아니면(offscreen) 아무것도 하지 않아요.

### 실행하자마자 꺼져요

1. `py -3.13 pincapture.py`로 콘솔에서 실행해 오류를 봐요.
2. 로그의 `[deps]` 줄을 확인해요(엉뚱한 Python으로 실행됐는지).
3. 이미 실행 중이면 새 프로세스는 신호만 보내고 끝나요. 트레이(작업 표시줄 오른쪽 `^`)에 아이콘이 있는지 봐요.

### 설정이 초기화됐어요

`config.json`이 깨졌거나 BOM이 붙어 있었을 가능성이 커요(3장). 앱은 기본값으로 시작하면서 파일을 덮어써요.

## 6. DPI와 다중 모니터

- 앱은 DPI 인식 모드를 따로 설정하지 않아요. Qt 6 기본값(모니터별 DPI 인식)을 그대로 써요.
- 화면 캡처는 `grab_screen_raw`가 `screen.grabWindow(0)`으로 **물리 픽셀** 이미지를 받고 DPR을 1로 맞춰요.
- 영역 선택은 모니터마다 오버레이를 하나씩 띄워요. 그래서 모니터를 가로지르는 선택은 안 돼요. 위젯 좌표(논리)는 `_to_phys`가 `정지 화면 폭 / 위젯 폭` 비율로 물리 픽셀로 바꿔요. 저장되는 이미지와 크기 표시(`W × H px`)는 물리 픽셀 기준이에요.
- 창 캡처는 `PrintWindow(PW_RENDERFULLCONTENT)`로 찍고, `DwmGetWindowAttribute(DWMWA_EXTENDED_FRAME_BOUNDS)`로 그림자 테두리를 잘라내요(물리 좌표). 실패하면 마우스가 있는 모니터의 화면 캡처에서 창 영역을 잘라내요. 창이 다른 모니터에 있거나 배율이 다른 보조 모니터에 있으면 잘못 잘리거나 모니터 전체가 찍힐 수 있어요(`docs/ROADMAP.md` FIX-05).
- 핀은 마우스가 있는 모니터의 배율로 나눈 논리 크기로 띄워서, 원래 화면과 같은 크기로 보여요. 배율이 다른 모니터로 옮겨도 크기를 다시 계산하지 않아요.
- `--selftest`는 200% 배율 좌표 변환을 검사해 `dpi_mapping_ok`나 `dpi_mapping_FAIL`을 출력해요(실패해도 종료 코드는 0이니 출력을 확인해요). 실제 125%·150%·배율이 섞인 다중 모니터는 손으로 시험해요(`docs/RELEASE.md` 4장).
