# 변경 기록

이 파일은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따라요.
버전은 0.6.0부터 `X.Y.Z` 형식이고, 기준은 `pincapture.py`의 `APP_VERSION`과 파일 맨 위 이력 주석이에요.
항목 분류: **추가**, **변경**, **수정**, **제거**, **보안**(개인정보 포함).

## [Unreleased]

### 수정
- 시험이 실제 사진 폴더와 실행 중인 앱을 건드리지 않도록 `tests/_isolation.py`가 임시 홈과 `save_dir`를 만들어요. 기본 저장 폴더는 Windows 알려진 폴더라 `USERPROFILE`만으로는 격리되지 않아요. `conftest.py`, `test_process.py`, `quit_probe.py`가 써요.
- offscreen 클립보드에 남은 데이터 때문에 시험이 통과한 뒤 `0xC0000005`로 끝나던 문제를 `pytest_sessionfinish`에서 클립보드를 비우는 방식으로 막아요. Qt 정적 소멸자를 건너뛰는 `os._exit`은 그대로예요.
- `installer/build.py`가 `installer/build`를 비우지 못하면 실행 중인 `PinCapture.exe`나 탐색기 창을 닫으라고 안내해요. 연기 시험은 임시 홈에서 돌아요.

### 보안
- `installer/docs/사용법.txt`의 로그 보내기 안내에, 로그 경로에 Windows 사용자 이름이 들어 있다는 주의를 더했어요.

## [0.8.0] - 2026-10-26

### 추가
- 핀 우클릭 **글자 복사(OCR)**: Windows에 내장된 `Windows.Media.Ocr`(PyWinRT)로 핀 이미지의 글자를 읽어 클립보드에 복사하고, 짧은 토스트로 알려 줘요. 한국어를 영어보다 먼저 써요. OCR 모듈이나 언어 팩이 없으면 설치 방법을 안내하고 앱은 그대로 동작해요.
- 핀 투명도: 우클릭 메뉴에서 100% / 80% / 60% / 40%를 고르거나, Ctrl+휠로 그 단계를 오갈 수 있어요. 휠만 돌리면 예전처럼 크기가 바뀌어요.
- 핀 **클릭 통과**: 우클릭 메뉴에서 켜면 마우스가 핀 아래 창으로 전달돼요(`WS_EX_TRANSPARENT`). 켜진 뒤에는 핀을 클릭해서 끌 수 없어서, 트레이의 **클릭 통과 해제**와 전역 단축키 `Ctrl+Alt+X`로 끄게 했어요.
- **최근 핀 다시 열기**: 닫은 핀을 최근 10개(설정에서 1~50)까지 메모리와 임시 폴더에 보관해요. 트레이의 **최근 핀 다시 열기**와 전역 단축키 `Ctrl+Alt+R`로 가장 최근 것부터 다시 띄워요. 위치·크기·투명도를 복원해요.
- 새 설정 키 `recent_pin_limit`, `hotkeys.reopen_pin`, `hotkeys.clickthrough`. 예전 `config.json`은 그대로 읽고, 없는 키만 기본값으로 채워요.

### 변경
- 화면 캡처가 거의 전부 검은색이면(완전한 `#000000`만이 아니어도) 핀으로 띄우거나 저장하지 않고, "보안 프로그램 때문에 캡처가 막혔을 수 있어요"라고 안내해요. 캡처 방지를 우회하지는 않아요.
- Windows OCR용 PyWinRT 3.2.1(MIT)과 `typing_extensions` 4.15.0(PSF-2.0)을 설치 파일에 포함해요.

## [0.7.0] - 2026-10-26

### 추가
- 첫 실행 빠른 안내: 단축키와 핀 사용법을 보여 줘요. 설정 파일이 없을 때만 자동으로 열리고, 창을 닫으면 `welcome_seen` 으로 기억해요. Windows 시작 시 `--tray` 로 켜질 때는 띄우지 않아요. 트레이 메뉴의 **빠른 안내**와 메인 창의 **안내**에서 언제든 다시 볼 수 있어요.
- 정보 창: 버전, 캐모마일그레이(ChamomileGrey), 라이선스 요약(All rights reserved, 무료 사용, 코드 재배포 불가), 서드파티 고지 열기.
- 후원하기: 정보 창과 트레이 메뉴에서 기본 브라우저로 https://ko-fi.com/chamomilegrey 를 열어요. 실행을 가로채는 후원 창은 없어요.
- 시험 `tests/test_ui.py`: 안내·정보·후원 주소, 단축키 표기, 기존 설정 파일 호환.

### 변경
- 메인 창과 설정 창의 배치·문구·툴팁을 다듬었어요. 캡처 버튼과 보관함 동작을 나누고, 버튼에 아이콘과 설명을 달았어요.
- 트레이 메뉴를 창 열기/숨기기, 캡처, 안내·설정·정보·후원, 다시 시작·종료로 나눴어요.
- 고친 창의 문구를 해요체로 맞췄어요. 설정 키 이름과 `config.json` 형식은 그대로예요. `welcome_seen` 만 추가되고, 0.6.x 파일에는 그 키가 없으면 안내를 자동으로 띄우지 않아요.
- 설치 정보의 게시자 이름과 EXE 회사 이름을 `ChamomileGrey`로 맞췄어요(`installer/PinCapture.iss`, `installer/build.py`).
- CI 워크플로 `.github/workflows/build.yml` 를 다시 넣었어요. Inno Setup 설치가 재부팅 코드 3010 을 내도 성공으로 보고, `Korean.isl` 이 있는지도 확인해요.

### 수정
- 시험이 모두 통과한 뒤 PySide6 정적 소멸자에서 프로세스가 죽던 문제를 막았어요. `tests/conftest.py`가 요약을 출력한 다음 pytest 종료 코드로 끝나요. Windows CI는 그 충돌을 종료 코드 1로 보고 시험 실패로 오해했어요.
- 설치 빌드가 Windows CI의 cp1252 콘솔에서 `_배포안내.txt` 경로를 출력하다 `UnicodeEncodeError`로 죽던 문제를 막았어요. `installer/build.py`가 표준 출력을 UTF-8로 맞추고, CI 잡에 `PYTHONIOENCODING=utf-8`을 넣었어요.

## [0.6.1] - 2026-10-26

### 추가
- 화면 캡처 차단 감지: 모든 모니터의 캡처가 픽셀 하나 남김없이 `#000000`이면 보안 프로그램의 '화면 캡처 방지'로 판단해요(`is_pure_black`, `screens_capture_blocked`).
  - 영역·핀 캡처: 검은 정지 화면 오버레이를 띄우지 않아요.
  - 전체 화면·창 캡처: 검은 이미지를 저장·복사·보관하지 않아요. 한 모니터만 검거나 실제로 검은 창은 정상적으로 캡처해요.
  - 대신 원인과 해결 순서를 알려 주는 안내 창 "화면 캡처가 막혀 있어요"와 트레이 알림을 띄워요. 안내 창은 비모달이고 항상 위에 떠요.
  - 계기: 정부24 전자문서 뷰어(ezPDFReader 2.0G)와 함께 설치된 Teruten WebCube 사건(`docs/reviews/2026-10-26-black-capture.md`). 차단을 우회하지는 않아요.
- `installer/docs/사용법.txt` 8장에 "화면이 검게만 찍힘" 해결 방법을 추가했어요.
- 시험 묶음 `tests/`: 캡처 차단, 보관함 다중 선택, 종료·CLI·selftest 회귀 시험. Qt offscreen과 격리된 홈에서 돌아요.
- 저장소 파일: `README.md`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `.gitattributes`, CI 워크플로 `.github/workflows/build.yml`(아직 GitHub에서 실행 안 됨), `docs/`(개발·구조·배포 문서, 스크린샷), 에이전트 운영 문서 `AGENTS.md`·`GROK.md`.

### 변경
- `--selftest`가 실제 단축키 상태(`available`, `listener_alive`, `error`)를 출력해요.
- 중복 실행 방지 파이프 이름에 홈 폴더를 포함해요. 격리된 홈으로 도는 시험이 실제로 실행 중인 핀캡처에 `quit`이나 `show`를 보내지 않아요.
- 옛 개발 문서 `핀캡처_사용법.md`를 `docs/DEVELOPMENT.md`로 옮기고 새로 썼어요.

### 수정
- Qt 플랫폼이 `windows`가 아닐 때(offscreen 등) `force_foreground`가 가짜 창 핸들을 Win32에 넘기지 않아요.

## [0.6.0] - 2026-10-22

### 추가
- 설치 프로그램 배포: `installer/build.py` 한 명령으로 아이콘(16~256px `.ico`) → EXE 버전 정보 → PyInstaller onedir → 번들 내용 검사 → 빌드된 EXE의 `--selftest` 연기 시험 → Inno Setup → `PinCapture-Setup-<버전>.exe`, SHA-256 파일, 배포 안내문(`_배포안내.txt`)을 만들어요.
- Inno Setup 설치 프로그램(`installer/PinCapture.iss`):
  - 관리자 권한 없이 사용자별로 `%LOCALAPPDATA%\Programs\PinCapture`에 설치해요.
  - 시작 메뉴 `핀캡처`와 `핀캡처 사용법` 바로가기를 만들고, 바탕화면 바로가기와 자동 실행(`--tray`)은 선택이에요.
  - 설치·제거 전에 실행 중인 앱을 `--quit`으로 닫고, 안 되면 `taskkill`을 써요. 관리자 권한으로 실행된 인스턴스는 감지해서 안내해요.
  - 무인(`/SILENT`) 업데이트로 앱을 닫았다면 다시 실행해요.
  - 제거할 때 `~/.pincapture` 삭제 여부를 물어요.
- 명령줄 옵션: `--tray`(창 없이 트레이로 시작), `--quit`(실행 중인 앱 종료, 최대 10초 대기), `--version`.
- 설치 프로그램용 실행 감지 뮤텍스 `PinCaptureRunning`.
- 로그 시작 줄에 앱 버전과 실행 형태(`exe`/`py`)를 기록해요.
- 오픈소스 고지: `THIRD_PARTY_NOTICES.txt`, `licenses/`(LGPL-3.0, GPL-3.0, Apache-2.0, MIT, Python PSF, six MIT, Qt 6.11.2 `qt_attribution.json`에서 만든 `Qt-third-party.txt`).
- 최종 사용자 안내 `installer/docs/사용법.txt`(설치 폴더와 시작 메뉴에 설치).

### 변경
- 모르는 명령줄 인수는 무시해요(`parse_known_args`). 옛 바로가기가 남긴 인수 때문에 꺼지지 않아요.
- 중복 실행 방지 채널을 사용자·세션별로 나누고, 같은 사용자만 연결할 수 있게 했어요(`UserAccessOption`).
- 두 번째로 실행하면 `AllowSetForegroundWindow`로 전경 권한을 넘겨서 기존 창이 확실히 앞으로 와요.
- 설정 창의 '부팅 시 자동 실행 등록' 바로가기는 `--tray`로 시작해요.
- 쓰지 않는 Qt 플러그인과 Qt 전용 OpenSSL 사본을 설치 파일에서 뺐어요.

### 수정
- EXE로 실행하면 바로가기, 작업 표시줄 고정, 트레이 '다시 시작'이 깨지던 문제를 고쳤어요(`launch_argv()`/`app_dir()`. EXE에는 실제 `__file__`이 없어요).
- 핀 창이 떠 있으면 종료가 무시되어 트레이도 단축키도 없는 유령 프로세스가 남던 문제를 고쳤어요. 이제 취소할 수 없는 `exit(0)`으로 종료해요.

### 보안
- 독스트링에 있던 개인 이메일과 로컬 경로를 지웠어요(EXE에 함께 들어가던 문제).

## [0.5.3] - 2026-10-21

### 추가
- 보관함 다중 선택: Ctrl+클릭, Shift+클릭, 빈 곳에서 드래그, Ctrl+A.
  - 복사: 파일 묶음으로 복사해요. 저장 안 된 캡처는 `~/.pincapture/clipboard/`에 임시 PNG로 만들고, 이미지만 받는 앱에는 첫 장이 붙어요.
  - 다른 이름으로 저장: 고른 폴더에 한꺼번에 저장해요.
  - 핀 고정: 전부 계단식으로 띄워요.
  - 목록에서 제거: 파일은 지우지 않아요.

## [0.5.2] - 2026-09-14

### 수정
- 캡처 후 핀캡처 창이 앞으로 나오지 않고 작업 표시줄만 깜빡이던 문제를 고쳤어요. 이제 단계적으로 전경 전환을 시도해요: `SetForegroundWindow` → `AttachThreadInput` → Alt 키 → TOPMOST.

## [0.5.1] - 2026-09-14

### 추가
- 작업 표시줄 고정: 창과 바로가기에 같은 AppUserModelID(`pincapture.app`)와 재실행 정보를 기록해요. 고정하면 Python 아이콘이 아니라 핀캡처 아이콘으로 고정돼요.
- 바로가기를 만들 때 시작 메뉴 바로가기도 함께 만들어요.

## [0.5] - 2026-09-03

### 추가
- 실행 환경 보호:
  - PySide6가 없는 Python으로 실행되면 PySide6가 설치된 다른 Python을 찾아 자동으로 다시 실행해요(`PINCAP_REEXEC`).
  - 실행 기록 `~/.pincapture/pincapture.log`를 남겨요.
  - 처리되지 않은 예외는 메시지 박스로 보여 줘요.

## [0.1 – 0.4] - 2026-08-04 ~

- 0.1(2026-08-04): claude.ai 채팅에서 Claude가 만든 첫 버전이에요. 영역 지정(화면 정지 방식), 활성 창, 전체 화면, 핀 고정 캡처와 전역 단축키, 트레이 상주, 자동 저장, 클립보드 복사를 지원했어요.
- 0.2~0.4(날짜 기록 없음): 캡처 기능함과 보관함을 한 창으로 통합했어요. 단일 인스턴스와 바탕화면·시작 프로그램 바로가기 생성을 추가했어요.
