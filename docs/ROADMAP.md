# 핀캡처 로드맵

> 이 문서는 2026-10-26 로컬 0.6.1 작업 트리의 백로그를 옮긴 것입니다. 기준 코드는 GitHub의 0.8.0입니다(0.7.0의 안내·정보·후원, 0.8.0의 OCR·투명도·클릭 통과·최근 핀·거의 검은 화면 안내). 이 문서와 코드, `AGENTS.md`, `.github/workflows/build.yml`이 다르면 코드와 그 문서가 맞습니다. CI 설명 중 `contents: read`나 별도의 release job, Inno Setup 6.7.1 고정은 로컬 초안이고 저장소 워크플로가 우선입니다.
>
> 이미 정해진 값: 라이선스 All rights reserved(`LICENSE`, MIT 아님), 게시자 ChamomileGrey, 저장소 https://github.com/ChamomileGrey/PinCapture, 후원 https://ko-fi.com/chamomilegrey. REL-02 표에도 이렇게 적혀 있습니다. 코드 서명과 pynput을 `RegisterHotKey`로 바꿀지만 미정입니다.
>
> 로컬 PC에서 빈 저장소를 만들어 처음 푸시하는 절차는 없습니다. 이 저장소가 기준입니다.

v0.6.1(`APP_VERSION`) 기준으로 2026-10-26에 작성한 백로그입니다. 다음 운영자가 위에서부터 차례로 처리합니다. 이 문서와 코드가 다르면 코드가 맞고, 이 문서를 고칩니다. 줄 번호는 금방 어긋나므로 함수 이름으로 찾으세요. `docs/reviews/2026-10-22-release-review.md`의 줄 번호도 v0.5.3 기준이라 지금 코드와 맞지 않습니다.

## 읽는 법

| 표기 | 뜻 |
|---|---|
| `UI-` | 이미 있는 화면 다듬기 |
| `FEAT-` | 새 기능 |
| `FIX-` | 버그·견고성 |
| `REL-` | 공개 배포 준비 |
| P0 | 공개 1.0 전에 반드시 |
| P1 | 1.0 직후 (1.0.x) |
| P2 | 1.1 이후 |
| 크기 S / M / L | 테스트 포함 1시간 이하 / 2–4시간 / 하루 이상 |

## 완료의 정의 (모든 항목 공통)

1. `py -3.13 -m pytest -q`가 전부 통과해야 합니다. 작성 시점에는 20개입니다. 새 동작마다 `tests/`에 테스트를 추가합니다.
   - 테스트는 Qt offscreen이라 트레이가 없습니다(`toolbar._tray is None`).
   - 실제 전역 단축키는 자동 테스트가 불가능합니다. pynput이 주입된 키를 무시하기 때문입니다. 이런 항목은 '수동' 확인 결과를 작업 보고에 적어 소유자에게 전합니다. 소유자가 커밋할 때 커밋 메시지에 넣습니다.
   - `conftest.py`의 `toolbar` fixture를 씁니다. 단축키를 비우고, 알림을 끄고, 임시 저장 폴더를 쓰는 fixture입니다.
   - `pincapture.py`를 별도 프로세스로 실행하는 테스트는 `tests/_isolation.py`의 `isolated_env(home)`을 환경으로 넘깁니다. 홈 폴더만 바꾸면 격리가 안 됩니다. 기본 저장 폴더는 Windows Known Folder API(사진)에서 오므로 `USERPROFILE`을 따르지 않습니다. 그래서 `make_isolated_home(home)`이 임시 `save_dir`가 든 `config.json`도 함께 씁니다.
   - `quit_app`을 부르는 테스트는 `_exit_now`를 monkeypatch합니다. 그래야 테스트용 QApplication이 끝나지 않습니다.
   - 실제 휴지통, 시작 프로그램 폴더, 레지스트리는 테스트에서 건드리지 않습니다. 모두 monkeypatch합니다.
2. `pincapture.py`가 띄우는 문구(창·버튼·메뉴·알림·대화상자)는 해요체로 씁니다. UI-01 이후에는 `STRINGS`에만 추가합니다. `installer/docs/사용법.txt`, `installer/PinCapture.iss` 메시지, `README.md`는 지금 말투 그대로 두고, 화면 이름이 바뀌면 이름만 맞춥니다(`AGENTS.md` 5장 6번).
3. 사용자가 보는 동작이 바뀌면 `installer/docs/사용법.txt`를 고칩니다. 이 파일은 UTF-8 BOM + CRLF를 유지해야 합니다.
4. 릴리스할 때마다 `APP_VERSION`을 올리고 `pincapture.py` 맨 위 이력 주석에 한 줄을 추가합니다. 태그 `vX.Y.Z`는 `APP_VERSION`과 같아야 하며, CI가 이를 검사합니다.
5. 화면이 바뀌면 작업 보고에 '스크린샷 갱신 필요'로 적습니다. 개별 항목에서는 다시 만들지 않고, `docs/images/screenshot-*.png` 재생성은 작업 순서 6의 마무리에서 한 번 합니다. 창이 화면에 뜨므로 소유자 승인을 받은 뒤 `AGENTS.md` 9장의 'README 스크린샷을 다시 만드는 방법' 절차를 그대로 따릅니다.
   - 지금 selftest 그림에는 빈 화면 문구, 영역 오버레이의 안내 태그, 트레이 메뉴, 알림, 안내 창(`QMessageBox`), 핀 우클릭 메뉴가 나오지 않습니다. 문구는 테스트(UI-01 테스트 6번)로 확인하고, 그림은 배치 확인에 씁니다.
   - 캡처 버튼(`ToolButton`)은 58×56 고정 크기에 글자 11px입니다. 버튼 문구는 짧게 유지합니다.
6. 새 서드파티 의존성은 원칙적으로 추가하지 않습니다. 꼭 필요하면 `installer/docs/THIRD_PARTY_NOTICES.txt`에 고지를 추가하고 라이선스 전문을 넣습니다.
7. 항목을 끝낼 때마다 `CHANGELOG.md`의 `[Unreleased]`에 맞는 분류(추가·변경·수정·제거·보안)로 한 줄 이상을 반드시 적습니다. 배포할 때 이 섹션이 그대로 버전 항목이 됩니다(`docs/RELEASE.md` 1장).
8. git 명령(커밋, 푸시, 태그)은 소유자가 직접 하거나 소유자가 명시적으로 요청할 때만 실행합니다.

## 깨면 안 되는 것

| 규칙 | 위치 |
|---|---|
| `APP_USER_MODEL_ID` = `AppUserModelID`, `APP_MUTEX_NAME` = `AppMutex` | `pincapture.py`, `installer/PinCapture.iss` |
| Inno `AppId` GUID는 바꾸지 않습니다. 바꾸면 업그레이드가 깨집니다 | `installer/PinCapture.iss` |
| 재실행·바로가기 명령은 `launch_argv()`/`app_dir()`로만 만듭니다. EXE에는 실제 `__file__`이 없습니다 | `pincapture.py` |
| 종료는 `MainToolbar._exit_now`(`QApplication.exit(0)`)로만 합니다. `quit()`는 핀이 떠 있으면 취소되어 유령 프로세스가 남습니다 | `pincapture.py` |
| 단일 인스턴스 이름은 `SINGLETON_NAME`(사용자·홈 폴더·세션별)을 쓰고, 서버는 `UserAccessOption`을 씁니다 | `pincapture.py` |
| 화면 캡처 방지를 우회하는 코드는 넣지 않습니다(DXGI, WGC, 훅 해제, 표시 속성 변경). 감지하고 안내만 합니다 | 전체 |
| PyInstaller는 onedir을 유지합니다. pynput은 `.py`로 수집하고, `build.py`의 `MUST_HAVE`/`MUST_NOT`을 지킵니다 | `installer/` |
| `.iss`, `installer/docs/*.txt`, `installer/docs/licenses/*`는 UTF-8 BOM + CRLF입니다(`AGENTS.md` 6장). 라이선스 문장은 원문을 바꾸지 않습니다 | `.gitattributes` |
| `pincapture.py`는 저장소 루트에 둡니다. 바로가기, spec, tests가 이 경로를 씁니다 | 루트 |
| 바로가기 이름은 `핀캡처.lnk`입니다. 설치 프로그램 `[UninstallDelete]`가 이 이름으로 지웁니다 | `create_shortcut`, `.iss` |

## 완료 (2026-10-22 검토 대비, 코드로 확인)

| 검토 | 내용 | 코드 근거 |
|---|---|---|
| 1 | EXE에서 바로가기·자동 실행·작업 표시줄 고정·다시 시작이 깨짐 | `FROZEN`, `launch_argv()`, `app_dir()`, `relaunch_command()`, `create_shortcut`(argv 사용), `restart_app`(`PYINSTALLER_RESET_ENVIRONMENT`), `_handle_missing_deps`의 FROZEN 분기, `_script_mtime`, `parse_known_args`. Qt import 정리만 남음 → FIX-11 |
| 3 | 사용자용 사용법 분리, SmartScreen 안내 | `installer/docs/사용법.txt`(설치 폴더·시작 메뉴), `docs/DEVELOPMENT.md` |
| 4 | EXE 업데이트 경로 | 설치 프로그램으로 대체: `--quit`(`_send_quit_to_running`), `.iss`의 `CloseRunningApp`, 무인 업데이트 뒤 `--tray` 재실행 |
| 11 일부 | 자동 실행 때마다 창이 뜸 | `--tray`, 시작 프로그램 바로가기에 `--tray`(`create_shortcut`, `.iss` `[Icons]`) |
| 12 | 단일 인스턴스 이름이 PC 전체에서 공용 | `_singleton_name()`, `UserAccessOption`, `listen` 실패 로그 |
| 17 일부 | 로그에 버전이 없음 | `APP_VERSION`을 상단으로 옮김, `_setup_logging` 헤더에 버전과 exe/py 표시 |
| 18 | 독스트링에 이메일·로컬 경로, 타사 제품명 표현 | 이력을 `#` 주석으로 옮기고 이메일 제거. 색상 테마 주석(`ACCENT` 위)의 타사 제품명 제거 |
| 4절 | 서드파티 고지·라이선스 | `installer/docs/THIRD_PARTY_NOTICES.txt`, `installer/docs/licenses/` |
| 기능표 | Inno Setup 사용자별 설치본(onedir) | `installer/build.py`, `PinCapture.spec`, `PinCapture.iss` |
| 검토 밖 | 핀이 떠 있으면 종료가 무시되는 유령 프로세스 | `_exit_now`, `tests/test_process.py` |
| 검토 밖 | 보안 프로그램 때문에 화면이 통째로 검게 찍힘 | `is_pure_black`, `screens_capture_blocked`, `_capture_blocked`, `tests/test_capture_blocked.py` |
| 검토 밖 | 시험의 `--quit`가 소유자의 실제 실행 중인 핀캡처에 닿아 종료시킴 | `_singleton_name()`이 `USERDOMAIN\USERNAME` + 홈 폴더의 해시와 세션 ID를 씀(사용자·홈·세션별), `tests/test_process.py::test_tests_never_talk_to_the_real_running_app` |
| 검토 밖 | 시험이 실제 저장 폴더(사진)를 읽음. 기본 저장 폴더는 Known Folder API라 `USERPROFILE`을 따르지 않음 | `tests/_isolation.py`(`make_isolated_home`, `isolated_env`). `conftest.py`, `test_process.py`, `quit_probe.py`가 씀. `conftest.py`·`quit_probe.py`의 임시 홈은 끝나면 지우고, `test_process.py`는 pytest `tmp_path`(pytest가 최근 3회분 보관) |
| 검토 밖 | pytest가 모두 통과한 뒤 0xC0000005로 끝남(CI 실패 원인). offscreen 클립보드에 남은 `QMimeData`를 Qt가 해석기 종료 뒤에 지움. 실제 Windows 클립보드는 정상 | `tests/conftest.py`의 `pytest_sessionfinish`가 클립보드를 비움 |
| 검토 밖 | `build.py` 연기 시험이 실제 `config.json`·저장 폴더를 읽음 | `smoke_test`가 `installer/build/smoke`를 임시 홈(자체 `config.json`·`save_dir`)으로 씀 |
| 검토 밖 | CI 워크플로 보강 | `.github/workflows/build.yml`: 기본 권한 `contents: read`(릴리스 job만 `contents: write`), 태그·`APP_VERSION` 검사를 맨 앞에, `timeout-minutes: 30`, Inno Setup 6.3+(`Korean.isl`) 확인, `if-no-files-found: error`, 초안 릴리스는 `.exe`·`.sha256.txt`만 첨부하고 본문은 `_배포안내.txt`. GitHub 실행은 REL-01 |
| 검토 밖 | `build.py`가 CI 콘솔(cp1252)에서 한글 파일 이름을 출력하다 실패할 수 있음, 실행 중인 EXE가 `installer/build`를 잠그면 `FileExistsError` | `installer/build.py`: stdout/stderr를 UTF-8로 재설정, 정리에 실패하면 안내 메시지로 종료 |

남은 검토 항목이 이 문서의 어느 ID로 옮겨졌는지:

| 검토 항목 | ID |
|---|---|
| 2 | FEAT-06 (임시책 FIX-08) |
| 5 | FIX-07 |
| 6 | FIX-01 |
| 7 | FIX-02 |
| 8 | FIX-03 |
| 9 | FIX-04 |
| 10 | FIX-05 |
| 11 나머지 | UI-02, UI-03 |
| 13 | FIX-09 |
| 14 | FIX-10 |
| 15 | FIX-06 |
| 16 | UI-05 (로그 폴더 열기는 UI-04) |
| 17 나머지 | FIX-11 |
| 3절 기능표 | UI-01, FEAT-01·02·03·07·08·09·10·11 |

## 작업 순서 (P0)

1. UI-01: 이후 모든 항목이 `STRINGS`와 `_toast`를 쓰므로 맨 먼저 합니다.
2. FIX-01 → FIX-02 → FIX-06 → FIX-04: 작고 서로 독립적입니다.
3. FIX-03, FIX-05, FIX-08
4. UI-02 → UI-03 → UI-04: UI-04가 UI-03의 `resource_path`를 씁니다.
5. FIX-07 → UI-05
6. 마무리: 스크린샷 재생성 → `사용법.txt` 갱신 → `0.7.0` → REL-01 → REL-02 → `1.0.0` 태그

---

## P0: 공개 1.0 전

### UI-01 · UI 문구를 해요체로 통일하고 한 곳(`STRINGS`)에 모으기 · M
- **왜:**
  - 반말이 남은 곳: `_excepthook`, `_handle_missing_deps`, `PreviewPane.paintEvent`, `create_shortcut`, `SettingsDialog._accept`, `MainToolbar.closeEvent`, `_notify`, `_refresh_info`, `_copy_selected`, `_save_selected_as`.
  - `_excepthook`의 "종료돼"는 사실과도 다릅니다. 슬롯에서 난 예외로는 앱이 계속 실행됩니다.
  - 합니다체도 섞여 있습니다. `_handle_missing_deps`의 EXE 분기("불러오지 못했습니다.", "실행됩니다.")와 0.6.1에서 추가한 `_capture_blocked`의 "켜 두면 이렇게 됩니다."입니다. `_capture_blocked`의 나머지 문구는 해요체라 한 창 안에서도 말투가 섞입니다.
  - 같은 기능의 이름이 화면마다 다릅니다. 툴바 '핀 고정', 설정 '핀 캡처', 트레이 '핀 고정 캡처'.
  - 문자열이 흩어져 있으면 영어 UI(FEAT-11)도 만들 수 없습니다.
- **완료 기준:**
  - 순수 dict `STRINGS`와 조회 함수 `T(key, **kw)`를 `APP_*` 상수 바로 아래(Qt import `try`보다 위)에 둡니다. Qt import가 실패하면 `_handle_missing_deps`가 곧바로 불리고, `_excepthook`도 import 도중에 설치되기 때문입니다.
    - 이름을 `tr`로 하지 않습니다. Qt의 `QObject.tr`과 겹쳐서, 위젯 안에서 `self.tr("key")`로 잘못 쓰면 오류 없이 키 문자열이 화면에 나옵니다.
    - 없는 키를 조회하면 키를 그대로 돌려주고 로그를 남기며, 예외를 내지 않습니다. 드물게만 도는 `_excepthook`과 `_handle_missing_deps`에서 키 오타 때문에 오류 안내 자체가 실패하면 안 됩니다.
  - 사용자에게 보이는 한글 리터럴이 0개입니다. 예외는 아래 목록뿐이며, 테스트 4번의 허용 목록도 똑같이 맞춥니다.
    - 주석, 독스트링, 로그용 `print` 인수
    - `APP_NAME`
    - `DEFAULTS["filename_prefix"]`의 `"캡처"`와 `SettingsDialog._accept`의 대체값 `or "캡처"`
    - `"핀캡처.lnk"`(깨면 안 되는 것 표). `create_shortcut`의 PowerShell 명령 안에 있는 것도 포함합니다.
    - 저장 파일 이름 앞부분 `캡처_`/`핀캡처_`(`_copy_selected`, `_save_selected_as`, `PinWindow.contextMenuEvent`). `STRINGS`로 옮길지는 이 항목에서 정합니다.
    - 로그에만 남는 예외 메시지. 예: `OSError("SHStrDupW 실패")`
    - `main()`의 argparse `help=` 7개(콘솔 전용). 역시 `STRINGS`로 옮길지 이 항목에서 정합니다.
  - 합니다체는 쓰지 않고 모두 해요체로 바꿉니다.
  - `_excepthook` 문구는 여기서 최종 문구로 한 번에 바꿉니다: "오류가 생겼어요. 앱은 계속 실행 중이에요"와 로그 경로. FIX-01은 이 문구를 다시 고치지 않습니다. 단, `app.exec()` 전(시작 단계)에 난 예외는 실제로 종료되므로 그 경우의 문구를 따로 둡니다.
  - 용어를 하나로 맞춥니다: 영역 지정 / 창 캡처 / 전체 화면 / 핀 고정.
    - '핀 고정'은 캡처 버튼 `btn_pin`(영역을 지정해 핀으로 띄움)에만 씁니다. 목록 동작 버튼 `b_pin_sel`(선택한 항목을 핀으로 띄움)은 다른 이름(예: '핀으로 띄우기')을 씁니다. FEAT-02 메뉴와 FEAT-08 버튼도 이 이름을 따릅니다.
    - 기록 목록의 이름은 '목록'과 '보관함' 중 하나로 정합니다. 지금 화면(`목록에서 제거`)과 `installer/docs/사용법.txt`('오른쪽 목록', '목록에서 제거')는 '목록'을, `README.md` 기능 제목·`docs/ARCHITECTURE.md`·이 문서의 FEAT 제목은 '보관함'을 씁니다. 정한 쪽으로 화면 문구와 세 문서를 맞추고, FIX-10·FEAT-02의 '목록에서 숨기기'도 그 이름에 맞춰 고칩니다.
  - 트레이 알림은 전부 새 `MainToolbar._toast(title, text, level)` 하나로 보냅니다.
    - `_toast`는 항상 먼저 `self._last_toast = (title, text, level)`를 기록하고, `_tray`가 있을 때만 `showMessage`를 부릅니다. offscreen 테스트에서는 `_tray`가 None이어도 이 기록으로 확인합니다.
    - `cfg["notify"]` 판단은 호출하는 쪽이 합니다. FIX-03의 저장 실패 경고처럼 설정과 관계없이 띄워야 하는 알림이 있습니다.
  - 트레이 메뉴 생성을 `_build_tray_menu() -> QMenu`로 분리합니다. 트레이가 없는 offscreen에서도 테스트가 메뉴를 만들어 확인할 수 있습니다. UI-02·UI-03·FEAT-01·FEAT-10의 트레이 메뉴 변경도 이 함수에서 합니다.
  - 문구 안에서 다른 버튼·메뉴 이름을 언급할 때는 이름을 직접 쓰지 않고 그 버튼의 키를 자리표시자로 넣습니다. 이름을 바꿔도 안내가 화면과 어긋나지 않습니다.
- **손댈 곳:**
  - 위 '왜'의 함수들
  - `_build_ui`, `_build_tray`(새 `_build_tray_menu`), `_update_tooltips`, `SettingsDialog.__init__`
  - `PinWindow.__init__`(창 제목), `PinWindow`의 툴팁·메뉴, `SelectionOverlay.paintEvent`의 안내 태그, `_capture_blocked`
  - `MainToolbar._make_item`(툴팁 "저장 안 된 캡처 (메모리)"), `SettingsDialog._browse`, `SettingsDialog._make_shortcut`, `_SHORTCUT_PLACES`
  - `HotkeyManager.restart`의 `error` 문구(UI-02에서 화면에 나옵니다)
  - `main()`의 `help=`(옮기기로 정한 경우)
- **함께 고칠 곳:** 버튼·메뉴 이름이 바뀌면 다른 파일의 안내도 맞춥니다.
  - `installer/PinCapture.iss`의 `CloseFailedMessage`(트레이 '종료'를 언급). UTF-8 BOM + CRLF 파일입니다.
  - `installer/docs/사용법.txt`의 해당 행(예: "영역 지정 캡처"). BOM + CRLF 확인 명령은 `AGENTS.md` 6장에 있습니다.
  - `README.md` 기능 목록
  - `docs/ARCHITECTURE.md` 21장 'UI 문구' 행. "번역 테이블 없음"이 낡은 설명이 됩니다.
  - `AGENTS.md` 작업 규칙 6
  - `docs/RELEASE.md` 4장 수동 시험표: '트레이 메뉴·알림·안내 창·핀 메뉴 문구 확인' 행이 없으면 추가합니다.
- **테스트:** 새 `tests/test_strings.py`를 만들고 기존 테스트를 고칩니다.
  1. 값을 `\n` 단위 줄로 나누고 줄 끝의 `{…}` 자리표시자를 뗀 뒤, 각 줄을 다시 `re.split(r'(?<=[.?!])\s+', 줄)`로 문장 단위로 나눠 문장마다 판정합니다. 줄 끝만 보면 한 줄 안의 앞 문장(예: `_capture_blocked`의 "켜 두면 이렇게 됩니다. 이 기능은 … 있어요.")을 놓칩니다. 마침표나 물음표로 끝나는 문장은 `요` 바로 뒤에 그 부호가 와야 하고, `다.`(합니다체)는 실패입니다. 회귀 표본: "불러오지 못했습니다.", "실행됩니다.", "…기능을 켜 두면 이렇게 됩니다. 이 기능은 … 있어요."(앞 문장이 걸려야 함)
  2. 어떤 문장도 `(어|야|돼|여|져|해|줘|봐|지|네)[.)]?$`에 걸리지 않아야 합니다. 명사로 끝나는 짧은 라벨이 걸리면(예: '이미지') 그 키만 허용 목록에 명시합니다. 회귀 표본: "실행할 수 없어.", "실행하면 돼. (설정 창의 … 기억함)"(앞 문장이 걸려야 함), " (pythonw로 실행돼서 터미널 창 없이 켜져)"
  3. 키마다 `string.Formatter().parse`로 뽑은 자리표시자를 채워 `T()`가 예외 없이 돌아야 합니다.
  4. `pincapture.py`를 AST로 검사합니다. 한글이 든 모든 `ast.Constant`(f-string `JoinedStr`의 조각 포함)는 `STRINGS` dict 리터럴 안, 독스트링, `print(...)` 인수, 완료 기준의 허용 목록 중 하나에 속하지 않으면 실패입니다. 특정 API(`setText` 등)에 직접 넣는 경우만 찾는 방식은 쓰지 않습니다. 변수를 거치는 문구(`hint` → `_draw_tag`), 직접 만든 함수(`_msgbox`, `ToolButton`, `_title_btn`)나 목록에 없는 Qt API(`drawText`, `addRow`, `QFileDialog.*`)로 가는 문구를 놓치기 때문입니다.
  5. AST로 `T("…")`의 첫 인수 상수를 모아 모두 `STRINGS` 키에 있는지, 각 호출의 keyword 이름이 그 값의 자리표시자를 모두 덮는지 확인합니다. 쓰이지 않는 키도 보고합니다. `.tr(` 속성 호출은 없어야 합니다. 없는 키를 조회하면 예외 없이 키가 그대로 나와야 합니다.
  6. 런타임 순회: `toolbar`, `SettingsDialog`, `PinWindow`에서 `findChildren`으로 모은 `text()`/`toolTip()`/`title()`과 `_build_tray_menu()`의 동작 이름에 1·2번 규칙을 적용합니다. selftest 그림에 나오지 않는 문구도 여기서 확인합니다.
  7. `tests/test_history.py`의 `"2개 선택"`, `"목록에서 제거 (2)"`, `"아직 캡처가 없어"` 단언과 `tests/test_capture_blocked.py`의 문구 단언(`"전자문서"`, `"닫"`, 버튼에 `"다시 시작"` 없음)을 `T()` 기준으로 바꿉니다.

### UI-02 · 빈 화면과 메인 창에 단축키·저장 폴더 표시 · S
- **왜:** 처음 쓰는 사람은 단축키를 알 방법이 거의 없습니다.
  - `PreviewPane.paintEvent`는 고정 문구만 그립니다.
  - 단축키는 버튼 툴팁(`_update_tooltips`)에만 있습니다.
  - 자동 저장 폴더는 캡처한 뒤 정보줄에만 나옵니다.
  - 트레이 메뉴에도 단축키가 없습니다.
- **완료 기준:**
  - 캡처가 없을 때 미리보기에 다음을 표시합니다.
    1. 단축키 4개. `Ctrl+Alt+A  영역 지정` 형식이고 값은 `cfg["hotkeys"]`에서 가져옵니다. 비어 있으면 '사용 안 함'.
    2. "어느 프로그램에서든 단축키로 캡처할 수 있어요"
    3. 자동 저장 폴더. `autosave`가 꺼져 있으면 '자동 저장 꺼짐'.
    4. 단축키 등록에 실패했으면 `hotkeys.error`.
  - 설정을 바꾸면 바로 반영됩니다.
  - 선택이 없을 때 정보줄에도 저장 폴더를 표시합니다.
  - 트레이 메뉴 항목에 단축키를 붙입니다. 예: `"영역 지정\tCtrl+Alt+A"`.
- **손댈 곳:**
  - `PreviewPane`에 새 `set_hint()`를 추가하고 `paintEvent`에서 그립니다.
  - `_update_tooltips`(힌트 생성), `_refresh_info`, `_build_tray`
  - 새 `format_hotkey(s)`: `<ctrl>+<alt>+a` → `Ctrl+Alt+A`, `<print_screen>` → `PrintScreen`. FEAT-05에서 다시 씁니다.
- **테스트:**
  - `format_hotkey` 입력·출력 표 테스트
  - 단축키를 채운 cfg로 빈 목록을 만들면 힌트에 `Ctrl+Alt+A`와 `save_dir`가 들어 있어야 합니다. fixture는 단축키가 빈 값이므로 cfg를 직접 채웁니다.
  - cfg를 바꾸고 `_update_tooltips()`를 부르면 힌트가 바뀌어야 합니다.
  - `run_selftest`에 빈 화면(`main-empty.png`)을 추가하면 `test_selftest_renders_every_window`의 파일 목록도 고칩니다.

### UI-03 · 톱니 버튼 메뉴 (설정 / 저장 폴더 / 사용법 / 정보 / 종료) · S
- **왜:**
  - 톱니(`btn_settings`)는 설정 창만 엽니다.
  - 종료는 트레이 우클릭에만 있는데, Windows 11은 새 트레이 아이콘을 ^ 안에 숨깁니다.
  - 사용법은 시작 메뉴 바로가기로만 열 수 있습니다.
- **완료 기준:**
  - 톱니를 누르면 `QMenu`(`InstantPopup`)가 열립니다: 설정… / 저장 폴더 열기 / 사용법 / 정보… / ─ / 종료.
  - 사용법 파일 위치: 설치본은 `app_dir()/사용법.txt`, 소스 실행은 `installer/docs/사용법.txt`. 파일이 없으면(`build.py --no-setup` 결과물 등) 경고를 띄웁니다.
  - '종료'는 `quit_app`을 부릅니다.
  - 트레이 메뉴에도 사용법과 정보를 추가합니다.
  - 트레이로 숨길 때의 알림(`closeEvent`)에 "작업 표시줄 오른쪽 ^ 안"을 넣습니다.
  - 톱니 버튼에 `setAccessibleName`을 지정합니다.
- **손댈 곳:**
  - `_build_ui`, `_title_btn`, `_build_tray`, `closeEvent`
  - 새 `resource_path(name)`: 설치본은 `app_dir()/name`, 소스는 `app_dir()/"installer"/"docs"/name`
  - 새 `_open_manual`
- **테스트:**
  - `btn_settings.menu()`의 동작 이름과 순서
  - 소스 모드에서 `resource_path("사용법.txt").exists()`
  - `QDesktopServices.openUrl`을 monkeypatch해 `_open_manual`이 그 파일을 여는지 확인
  - '종료'가 `quit_app`을 부르는지 확인

### UI-04 · 정보(About) 대화상자 · M
- **왜:**
  - 지금은 버전이 트레이 툴팁에만 나옵니다.
  - 라이선스, 서드파티 고지, 로그 위치를 앱 안에서 찾을 수 없습니다. LGPL상 필수는 아니지만(검토 4절) 문의에 대응하려면 필요합니다.
- **완료 기준:** 새 `AboutDialog`에 다음을 넣습니다.
  - 표시 내용:
    - 앱 이름, `APP_VERSION`, exe/py 구분
    - Python, Qt(`qVersion()`), PySide6 버전
    - 앱 라이선스 한 줄. REL-02에서 결정되기 전에는 표시하지 않습니다.
    - "인터넷에 연결하지 않아요" 한 줄
  - 버튼:
    - 서드파티 고지 열기(`THIRD_PARTY_NOTICES.txt`)
    - 라이선스 폴더 열기(`licenses`)
    - 로그 폴더 열기(`CONFIG_DIR`)
    - 버전 정보 복사. 버전, Python, Qt, Windows 빌드를 클립보드에 넣습니다(이슈 제보용).
  - 대상 파일이 없으면 해당 버튼을 비활성화합니다.
- **손댈 곳:**
  - 새 `AboutDialog(QDialog)`
  - UI-03의 `resource_path`
  - 진입점: UI-03 메뉴와 트레이
  - `run_selftest`에 about 렌더 추가
- **테스트:**
  - 라벨에 `APP_VERSION`과 `qVersion()`이 들어 있어야 합니다.
  - 소스 모드에서 `installer/docs/THIRD_PARTY_NOTICES.txt`와 `installer/docs/licenses`가 존재해야 합니다.
  - '버전 정보 복사' 후 클립보드에 `APP_VERSION`이 있어야 합니다.
  - selftest에 `about.png`를 추가하면 `test_selftest_renders_every_window`의 목록도 고칩니다.

### UI-05 · 자동 실행 켜기/끄기 토글 · S (FIX-07 먼저)
- **왜:**
  - 설정에는 '부팅 시 자동 실행 등록' 버튼만 있습니다. 현재 상태가 안 보이고, 끌 방법도 없습니다. `사용법.txt` 5절은 끄는 방법으로 Windows 설정을 안내합니다.
  - 설치 프로그램의 autostart 작업과 이 버튼은 같은 `{userstartup}\핀캡처.lnk`(`--tray`)를 만듭니다.
- **완료 기준:**
  - 설정에 `QCheckBox("Windows 시작 시 자동 실행 (트레이에서 대기)")`를 둡니다. 초기값은 `_special_folder("Startup") / "핀캡처.lnk"`가 있는지로 정합니다.
  - OK를 누르면 값이 바뀐 경우에만 처리합니다.
    - 켬: `create_shortcut("Startup")`
    - 끔: Startup 링크만 지웁니다. 시작 메뉴 링크는 작업 표시줄 고정에 필요하므로 남깁니다.
    - 실패하면 경고를 띄웁니다.
  - 'Windows 설정 → 시작 앱'에서 끈 상태를 반영할지는 실기 확인 후 정합니다. 그 상태는 `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder`의 `핀캡처.lnk` 값에 있습니다.
  - '바탕화면 아이콘 만들기' 버튼은 그대로 둡니다.
  - `사용법.txt` 5절에 앱 안 토글을 추가합니다.
- **손댈 곳:**
  - `SettingsDialog.__init__`(바로가기 그룹), `SettingsDialog._accept`
  - 새 `startup_enabled()`, `set_startup(on)`
- **테스트:** Windows 전용(`skipif`)입니다.
  - `_special_folder`는 tmp를, `create_shortcut`은 가짜 파일을 만들도록 monkeypatch합니다.
  - 켬 / 끔 / 변경 없음 세 경우를 확인합니다.
  - 끔에서도 Programs 쪽 가짜 링크는 남아야 합니다.

### FIX-01 · 오버레이를 Alt+F4로 닫거나 캡처 중 예외가 나면 캡처가 영구히 잠김 · S
- **왜:**
  - 정상 캡처 모드(region/pin/window/full)에서 `_capturing`은 `_finish`에서만 풀립니다. 모르는 mode만 `capture`의 마지막 `else`에서 바로 풉니다.
  - `SelectionOverlay`에 `closeEvent`가 없어서 Alt+F4로 닫으면 `canceled`가 나가지 않습니다.
  - 그러면 이후 모든 단축키와 버튼이 `capture()` 첫 줄에서 무시되고, 창도 숨겨진 채로 남습니다.
  - 닫힌 오버레이는 `WA_DeleteOnClose`로 삭제됩니다. 그래서 다른 모니터를 정리할 때(`RegionCaptureSession._cleanup`) RuntimeError가 납니다.
  - `_run_region`/`_run_window`/`_run_full` 안에서 예외가 나도 똑같이 잠깁니다.
- **완료 기준:**
  - 오버레이 하나를 닫으면 모든 오버레이가 닫히고, `_capturing`은 False, `_session`은 None이 되며, 원래 보이던 창이 다시 나타납니다.
  - 러너에서 예외가 나면 traceback은 로그에 남기고, 상태를 복구하고, 메시지 박스는 띄우지 않습니다.
  - 바로 다음 캡처가 정상으로 동작합니다.
  - `_excepthook` 문구는 UI-01에서 최종 문구로 바꾸므로 여기서는 고치지 않습니다.
- **손댈 곳:**
  - `SelectionOverlay.closeEvent`: `canceled.emit()`을 보냅니다. `_cleanup`이 먼저 `blockSignals(True)`를 하므로 다시 들어오지 않습니다.
  - `RegionCaptureSession._cleanup`: 오버레이마다 `try … except RuntimeError`로 감쌉니다.
  - `MainToolbar.capture`: 러너를 새 `_safe_run(fn, *a)`로 감쌉니다.
- **테스트:** 새 `tests/test_capture_state.py`
  - 회색 화면으로 `capture("region")`을 시작하고 첫 오버레이를 `close()`합니다. 상태가 복구되고 남은 오버레이가 0개여야 합니다.
  - `grab_screen_raw`가 예외를 던지게 monkeypatch하고 `capture("full")`을 부르면 `_capturing`이 False여야 합니다. 이어서 정상 캡처가 1건 되어야 합니다.

### FIX-02 · 모달 창이 열린 채 캡처하면 입력이 막힌 오버레이가 화면을 덮음 · S
- **왜:**
  - 설정 창(`open_settings`의 `dlg.exec()`), 파일 대화상자, `QMessageBox`가 열려 있으면 Qt는 그 뒤에 뜬 창의 입력을 막습니다.
  - 그래서 오버레이에서 드래그, Esc, 우클릭이 모두 먹지 않고 `_capturing`이 잠깁니다.
  - 단축키 신호는 모달 루프 안에서도 처리되므로 이 상황이 실제로 생깁니다.
  - `_blocked_box`는 비모달이라 해당하지 않습니다.
- **완료 기준:**
  - `QApplication.activeModalWidget()`이나 `QGuiApplication.modalWindow()`가 있으면 캡처하지 않습니다. 대신 그 창을 앞으로 가져오고 "열려 있는 창을 먼저 닫은 뒤 캡처해 주세요" 알림을 띄웁니다.
  - `activePopupWidget()`(열린 메뉴)은 닫고 캡처를 진행합니다.
  - `SettingsDialog`는 지금처럼 parent 없이 둡니다. parent를 주면 트레이에서 열었을 때 작업 표시줄 버튼이 사라집니다.
- **손댈 곳:** `MainToolbar.capture` 맨 앞
- **테스트:**
  - `QDialog`에 `ApplicationModal`을 지정하고 `exec()` 대신 `show()`로 띄웁니다.
  - 이 상태에서 `capture("region")`을 부르면 오버레이 0개, `_capturing` False, `_last_toast` 기록이어야 합니다.
  - 대화상자를 닫은 뒤에는 캡처가 정상이어야 합니다.

### FIX-03 · 저장 실패가 조용함, 파일 이름 접두어 검증 없음 · M
- **왜:**
  - `_save_image`는 다음 경우에 실패해도 `None`만 반환합니다.
    - USB나 NAS가 분리됨
    - '제어된 폴더 액세스'가 서명 없는 EXE의 사진 폴더 쓰기를 차단함
    - 접두어에 `/ : ? *`가 들어감
  - 그런데 `_notify`는 "클립보드에 복사됐어"라는 성공 알림을 띄웁니다. 캡처는 메모리에만 있다가 종료하면 사라집니다.
  - 접두어의 `:`는 NTFS 대체 데이터 스트림에 써져서 '성공'으로 처리되고 파일은 보이지 않습니다.
  - 핀 저장(`PinWindow.contextMenuEvent`)과 단일 '다른 이름으로 저장'(`_save_selected_as`)은 `save()` 결과를 확인하지 않습니다.
- **완료 기준:**
  - `_save_image`는 `(path, err)`를 반환합니다. `QImageWriter`로 저장하고 실패 사유는 `errorString()`에서 가져옵니다.
  - 실패하면 `notify` 설정과 관계없이 경고 알림을 띄웁니다. 저장 폴더, 이유, "캡처는 클립보드와 목록에만 있어요"를 넣고 성공 알림은 띄우지 않습니다.
  - 저장 시점과 `SettingsDialog._accept` 두 곳에서 접두어를 정리합니다: `re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', p).strip(' .') or '캡처'`.
  - `_accept`에서 저장 폴더에 쓸 수 있는지 시험합니다. 폴더를 만들고 시험 파일을 썼다가 지웁니다. 실패하면 "그래도 사용할까요?"라고 묻습니다. NAS가 잠깐 꺼져 있을 수도 있으므로 거부하지 않습니다.
  - 핀 저장과 단일 저장이 실패하면 `QMessageBox.warning`을 띄웁니다.
- **손댈 곳:** `_save_image`, `_finish`, `_notify`, `SettingsDialog._accept`, `PinWindow.contextMenuEvent`, `_save_selected_as`
- **테스트:**
  - `save_dir`를 이미 있는 *파일* 경로로 바꾸고 `capture("full")`(회색 화면 monkeypatch)을 부르면, 기록 1건의 `path`가 None이고 `_last_toast`가 경고 수준이어야 합니다.
  - 접두어 `a:b?c`로 저장한 파일 이름은 `a_b_c_`로 시작해야 합니다.
  - 없는 폴더로 핀을 저장하면 `QMessageBox.warning`이 호출되어야 합니다(monkeypatch).

### FIX-04 · 저장된 캡처의 원본 이미지를 메모리에서 해제 · S
- **왜:**
  - `_finish`는 저장에 성공해도 `HistoryEntry(image=img, path=path)`로 원본 `QImage`를 계속 들고 있습니다.
  - 기록은 최대 150개(`_trim_history`)입니다. 4K 전체 화면이면 장당 약 33MB라 수 GB까지 쌓입니다.
- **완료 기준:**
  - 저장에 성공한 항목은 썸네일과 크기를 계산한 뒤 `_image = None`으로 둡니다. 미리보기는 `_cur_img`가 들고 있고, 다시 볼 때는 파일에서 읽습니다.
  - 메모리 전용 항목(자동 저장 끔, 핀 캡처)은 최신 30개만 남깁니다.
  - (선택) `full_image()`에 경로를 키로 하는 2–3칸 LRU 캐시를 둡니다.
- **손댈 곳:** `_finish`의 `add_entry` 다음, `HistoryEntry`에 새 `release_image()`, `_trim_history`
- **테스트:**
  - 자동 저장을 켜고 `capture("full")`을 부르면 `history[0]._image is None`이고 `full_image()`는 파일에서 읽혀야 합니다.
  - 자동 저장을 끄고 35회 캡처하면 메모리 전용 항목이 30개 이하여야 합니다.

### FIX-05 · 트레이 '창 캡처'가 작업 표시줄·바탕화면을 찍음 · M
- **왜:**
  - 트레이 메뉴를 누르는 순간 전경 창은 작업 표시줄이 됩니다.
  - `_own_hwnds`는 Qt 위젯만 제외합니다. `_track_foreground`도 작업 표시줄을 '직전 외부 창'으로 기억합니다.
  - `capture_active_window`의 화면 잘라내기 폴백은 영역이 틀리면 모니터 전체(`raw.toImage()`)를 돌려줍니다.
  - 폴백은 창이 아니라 커서 위치(`screen_under_cursor`)로 화면을 고릅니다.
  - `sg.x() * dpr` 오프셋은 배율이 다른 보조 모니터에서 틀린 값이 됩니다.
- **완료 기준:**
  - 트레이, 버튼, 단축키 어디서 실행해도 직전에 쓰던 실제 앱 창을 찍습니다.
  - 작업 표시줄, 바탕화면, 숨김(cloaked) 창, 자기 프로세스 창은 대상이 되지 않습니다.
  - 찍을 창이 없으면 아무것도 저장하지 않고 "캡처할 창을 찾지 못했어요. 찍을 창을 한 번 클릭한 뒤 다시 눌러 주세요"라고 안내합니다.
  - 폴백 잘라내기는 창 중심이 있는 화면을 기준으로 합니다.
- **손댈 곳:**
  - 새 `_capturable(hwnd)`가 False를 반환하는 경우:
    - `IsWindow`/`IsWindowVisible`가 아니거나 `IsIconic`
    - `GetWindowThreadProcessId`의 pid가 `os.getpid()`와 같음
    - `GetClassNameW`가 `Shell_TrayWnd`, `Shell_SecondaryTrayWnd`, `Progman`, `WorkerW`, `NotifyIconOverflowWindow`, `TopLevelWindowForOverflowXamlIsland`, `Windows.UI.Core.CoreWindow`, `XamlExplorerHostIslandWindow` 중 하나
    - `DwmGetWindowAttribute(14 = DWMWA_CLOAKED)`가 0이 아님
  - 판정 자체는 순수 함수 `_capturable_info(cls, pid, visible, iconic, cloaked)`로 분리합니다.
  - `_foreground_hwnd`, `capture_active_window`(폴백 실패 시 `None`), `MainToolbar._track_foreground`, `_run_window`
- **테스트:**
  - `_capturable_info` 표 테스트: 작업 표시줄 클래스, 자기 pid, cloaked는 모두 False여야 합니다.
  - `capture_active_window`가 `None`을 돌려주게 monkeypatch하고 `capture("window")`를 부르면 기록 0건, 알림 기록, `_capturing` False여야 합니다.
  - 수동: 트레이 → 창 캡처, 125%/150% 보조 모니터에 있는 창

### FIX-06 · 클립보드용 임시 PNG가 종료 후에도 남음 · S
- **왜:**
  - `_copy_selected`는 저장 안 된 캡처를 `~/.pincapture/clipboard/`에 PNG로 쓰고, 다음 다중 복사 때만 지웁니다.
  - 그래서 자동 저장을 일부러 끈 사용자의 캡처가 무기한 남습니다.
  - `사용법.txt` 7절은 이 파일을 '임시'라고 설명합니다.
- **완료 기준:**
  - 시작할 때 폴더를 비웁니다. 단일 인스턴스 `listen`이 성공한 뒤에 해야 합니다. 그 전에 지우면 두 번째 실행이 기존 인스턴스가 클립보드에 올려 둔 파일을 지웁니다.
  - `quit_app`과 `restart_app`에서도 비웁니다.
  - `사용법.txt` 7절에 "종료할 때 지워져요"를 넣습니다. 종료 뒤에는 그 파일을 붙여넣을 수 없다는 점도 적습니다.
- **손댈 곳:**
  - 새 `_clear_clipboard_cache()`
  - `main()`의 `server.listen` 다음, `quit_app`, `restart_app`
  - FEAT-03 드래그도 같은 폴더를 씁니다.
- **테스트:**
  - 폴더에 파일을 만들고 `_clear_clipboard_cache()`를 부르면 폴더가 비어 있어야 합니다.
  - `quit_app()`을 부른 뒤에도 비어 있어야 합니다.

### FIX-07 · 바로가기를 PowerShell 없이 만들기 (IShellLinkW) · M
- **왜:**
  - `create_shortcut`은 숨김 `powershell -NoProfile -EncodedCommand`를 경로 없이 실행합니다.
  - 서명 없는 EXE가 인코딩된 PowerShell을 띄우는 것은 백신과 EDR이 경보를 내는 전형적인 패턴입니다.
  - 제한 언어 모드(AppLocker/WDAC)에서는 실패합니다.
  - UI-05가 이 함수를 씁니다.
- **완료 기준:**
  - `create_shortcut`에 `subprocess`와 `powershell`이 없어야 합니다.
  - 프로세스 안에서 바로가기를 만듭니다:
    1. `CoCreateInstance(CLSID_ShellLink)`로 `IShellLinkW`를 얻습니다.
    2. `SetPath`(20), `SetArguments`(11), `SetWorkingDirectory`(9), `SetIconLocation`(17)을 호출합니다.
    3. `QueryInterface(IPersistFile)` → `Save`(6) → `Release`
    4. 그다음 기존 `set_shortcut_app_id`를 호출합니다.
  - 대상, 인수, 시작 위치, 아이콘은 지금과 같습니다: `launch_argv()`(Startup만 `--tray`), `app_dir()`, `app_icon_path()`. 파일 이름은 `핀캡처.lnk`를 유지합니다.
  - `CoInitializeEx`는 방어적으로 호출합니다. 이미 초기화돼 있어 S_FALSE나 RPC_E_CHANGED_MODE가 나오면 무시합니다.
- **손댈 곳:**
  - `create_shortcut`. 기존 `_com_method`와 `_GUID`를 재사용합니다.
  - CLSID_ShellLink `{00021401-0000-0000-C000-000000000046}`
  - IID_IShellLinkW `{000214F9-0000-0000-C000-000000000046}`
  - IID_IPersistFile `{0000010B-0000-0000-C000-000000000046}`
- **테스트:** Windows 전용입니다.
  - 경로를 인수로 받는 `create_shortcut_at(lnk, argv, workdir, icon)`로 분리하고 tmp에 바로가기를 만듭니다.
  - 같은 vtable의 `GetPath`(3), `GetArguments`(10), `GetWorkingDirectory`(8)로 읽는 `read_shortcut()`으로 왕복 확인합니다.
  - 수동: 탐색기에서 속성 확인, 작업 표시줄 고정

### FIX-08 · pynput 수식키 고착 임시책 · S (FEAT-06을 1.0 전에 못 할 때)
- **왜:**
  - Ctrl+Alt+Del이나 잠금 화면에서 Ctrl·Alt를 떼는 입력이 훅에 보이지 않아 pynput `HotKey` 내부 상태에 남습니다.
  - 그러면 잠금을 해제한 뒤 `a`/`w`/`f`/`q`(한글 ㅁ/ㅈ/ㄹ/ㅂ) 한 글자만 쳐도 캡처가 뜹니다. 검토 2번의 '왜 1'입니다.
- **완료 기준:**
  - 조합의 수식키가 실제로 눌려 있을 때만 `triggered`를 보냅니다. `GetAsyncKeyState`로 확인합니다: VK_CONTROL 0x11, VK_MENU 0x12, VK_SHIFT 0x10, VK_LWIN 0x5B, VK_RWIN 0x5C.
  - 다른 앱에 키가 전달되는 문제와 충돌 감지는 그대로입니다. FEAT-06에서 해결합니다.
- **손댈 곳:**
  - `HotkeyManager.restart`의 매핑 람다를 새 `_emit_if_mods_down(mode, combo)`로 바꿉니다.
  - 새 `_mods_of(combo)`, 새 `_key_down(vk)`
- **테스트:**
  - `_mods_of("<ctrl>+<alt>+a") == {"ctrl", "alt"}`
  - `_key_down`을 monkeypatch해서 False면 신호가 없고 True면 신호가 나가야 합니다.
  - 수동: Ctrl+Alt+Del → 취소 → 메모장에서 `a` 입력 → 캡처가 뜨지 않아야 합니다.

### REL-01 · GitHub Actions 첫 실행 · S–M
- **왜:** `.github/workflows/build.yml`은 작성만 했고 GitHub에서 한 번도 돌리지 않았습니다.
- **완료 기준:**
  - `main` 푸시에서 테스트, `installer/build.py`, 아티팩트 업로드가 모두 녹색이어야 합니다. 아티팩트는 `PinCapture-Setup-<버전>.exe`, `.sha256.txt`, `_배포안내.txt`입니다.
  - `APP_VERSION`과 같은 태그 `vX.Y.Z`를 붙이면 draft release가 생기고, 다른 태그는 실패하는지 확인합니다.
  - 태그 실행의 draft release에는 `.exe`와 `.sha256.txt`만 붙고, 본문은 `_배포안내.txt`(BOM 제거)입니다. 워크플로 아티팩트에는 세 파일이 모두 들어 있습니다.
  - 실패하면 원인을 고치고 `build.yml` 맨 위 `Status:` 주석을 갱신합니다.
  - 푸시와 태그는 소유자가 하거나 소유자가 요청할 때만 합니다(`docs/RELEASE.md` 5장).
- **알아 둘 것:**
  - Inno Setup은 6.3 이상이 필요합니다(`Languages\Korean.isl`이 6.3.0부터 함께 설치됩니다). CI는 `Korean.isl`이 없을 때만 choco로 6.7.1을 설치합니다.
  - GitHub가 2026-09-23에 러너의 Node 20 제거를 공지했습니다. 지금 액션 버전(`checkout@v4`, `setup-python@v5`, `upload-artifact@v4`, `download-artifact@v4`, `action-gh-release@v2`)은 그대로입니다. 각 액션의 릴리스를 확인한 뒤 Node 24 메이저로 올립니다.
- **손댈 곳:** `.github/workflows/build.yml`. 필요하면 `installer/build.py`의 ISCC 경로 탐색.
- **테스트:** CI 실행 자체가 테스트입니다. 추가로 아티팩트 설치 파일을 깨끗한 Windows나 VM에서 설치, 실행, 제거해 봅니다.

### REL-02 · 오너 결정 반영 · S (오너 답 대기)
- **왜:** 라이선스·게시자·저장소·후원 주소는 정해졌습니다. 코드 서명과 pynput 교체만 남아 있습니다.
- **완료 기준:** 아래 표대로 반영합니다.

  | 결정 | 반영할 곳 |
  |---|---|
  | 앱 코드 라이선스 | **확정: All rights reserved (MIT 아님).** `LICENSE`, README, 정보 창 |
  | 게시자 이름 | **확정: ChamomileGrey.** `installer/PinCapture.iss`의 `#define AppPublisher`, `installer/build.py`의 `PUBLISHER` (둘이 같아야 함) |
  | GitHub 소유자·저장소 이름 | **확정: ChamomileGrey/PinCapture** |
  | 코드 서명 여부 | 서명하지 않으면 `사용법.txt` 4절을 유지합니다. SmartScreen 경고가 뜨고, Smart App Control이 켜진 PC에는 설치할 수 없습니다 |
  | pynput 유지 또는 `RegisterHotKey` 교체 | FEAT-06 / FIX-08 |

- **손댈 곳:** 위 표
- **테스트:**
  - 결정한 뒤 `LICENSE` 파일이 있는지 확인하는 테스트를 추가합니다.
  - `build.py`가 `.iss`와 `PUBLISHER`가 다르면 실패하게 만들면 더 좋습니다.

---

## P1: 1.0 직후

### FEAT-01 · 지연 캡처 (3/5/10초) · M
- **왜:** 메뉴, 툴팁, 마우스 오버 상태는 Ctrl+Alt를 누르는 순간 닫혀서 찍을 수 없습니다.
- **완료 기준:**
  - 메인 창 캡처 버튼 줄에 '지연' 드롭다운(끔/3초/5초/10초)을, 트레이에 '지연 캡처' 하위 메뉴를 둡니다.
  - 선택값은 이번 실행 동안만 유지합니다. 재시작하면 꺼져서, 잊고 계속 지연되는 일을 막습니다. 버튼 글자로 상태를 표시합니다(예: "지연 5초").
  - 단축키를 포함한 모든 모드에 적용합니다.
  - 지연 중에는 `_capturing=True`를 유지합니다. 남은 시간은 트레이 툴팁에만 표시합니다. 화면에 라벨을 띄우면 캡처에 찍힙니다.
  - 지연 중에 다시 캡처를 요청하면(단축키, 버튼, 트레이) 지연을 취소합니다.
  - 영역·핀 모드는 지연이 끝난 뒤에 화면을 정지합니다(`RegionCaptureSession.start`).
- **손댈 곳:** `MainToolbar.capture`(지연 인수), 새 `_delay_timer`(1초 간격 `QTimer`), 새 `_cancel_delay`, `_build_ui`, `_build_tray`
- **테스트:** 지연을 ms 단위로 줄이는 내부 인수를 씁니다.
  - `capture("full")` 직후에는 기록 0건, 지연이 끝난 뒤에는 1건이어야 합니다.
  - 지연 중 두 번째 `capture`를 부르면 취소되어 `_capturing` False, 기록 0건이어야 합니다.

### FEAT-02 · 보관함 우클릭 메뉴 (탐색기에서 보기, 이름 바꾸기, 휴지통으로 삭제) · M
- **왜:**
  - '저장 폴더 열기'는 폴더만 열어서 파일을 다시 찾아야 합니다.
  - 이름 바꾸기와 삭제는 탐색기에서 따로 해야 합니다.
  - '목록에서 제거'는 파일을 지우지 않아 헷갈립니다.
- **완료 기준:**
  - 항목을 우클릭하면 다음 메뉴가 뜹니다.
    - 복사 / 다른 이름으로 저장… / (UI-01에서 정한 `b_pin_sel` 이름, 예: 핀으로 띄우기) / 탐색기에서 보기
    - 이름 바꾸기… (F2). 저장된 파일 1개를 선택했을 때만 켜집니다.
    - 휴지통으로 삭제… (Shift+Delete). 확인을 받은 뒤 `QFile.moveToTrash`를 씁니다. 영구 삭제는 하지 않습니다.
    - 목록에서 숨기기 (Delete)
  - 메모리 전용 항목에서는 파일 동작을 비활성화합니다.
  - 이름 바꾸기는 확장자를 유지하고, 금지 문자와 중복 이름을 거부하고, `entry.path`와 툴팁을 갱신합니다.
  - 탐색기에서 보기는 `SHOpenFolderAndSelectItems`를 씁니다. 여러 개를 한 번에 선택할 수 있고, `explorer /select,` 문자열의 따옴표 문제를 피할 수 있습니다. 실패하면 폴더를 엽니다.
- **손댈 곳:**
  - `_build_ui`: `listw.setContextMenuPolicy(CustomContextMenu)`, F2와 Shift+Delete 단축키
  - 새 `_history_menu`, `_reveal_selected`, `_rename_current`, `_trash_selected`, `_shell_select(paths)`
  - `_refresh_info`
- **테스트:** `test_history.py`에 추가합니다.
  - 메뉴 항목과 활성 상태: 메모리 항목이면 이름 바꾸기와 삭제가 비활성이어야 합니다.
  - `QInputDialog.getText`를 monkeypatch해 이름을 바꾸면 디스크 파일과 `entry.path`가 바뀌어야 합니다. `a:b`는 거부되어야 합니다.
  - `QFile.moveToTrash`와 `QMessageBox.question`을 monkeypatch해 삭제하면 항목이 사라져야 합니다. 실제 휴지통은 건드리지 않습니다.
  - `_shell_select`를 monkeypatch해 경로가 제대로 전달되는지 확인합니다.

### FEAT-03 · 보관함에서 드래그해서 내보내기 · S
- **왜:** 탐색기, 카카오톡, 메일, Word로 바로 끌어다 놓을 수 없습니다. 지금은 Ctrl+C로 복사해서 붙여넣는 방법뿐입니다.
- **완료 기준:**
  - 선택 항목을 목록 밖으로 끌면 파일로 놓입니다.
    - 저장된 파일은 그대로 씁니다.
    - 메모리 항목은 `~/.pincapture/clipboard/`에 PNG로 써서 씁니다.
  - 이미지만 받는 앱을 위해 첫 장의 이미지 데이터도 함께 싣습니다.
  - 목록 안에서 순서는 바꿀 수 없습니다(`DragOnly`).
  - 빈 곳에서 드래그해 여러 개 선택하는 동작과 Ctrl+C는 그대로 둡니다.
- **손댈 곳:**
  - `QListWidget`의 하위 클래스 `HistoryList`: `mimeData(items)`, `supportedDropActions`
  - `_build_ui`: `setDragEnabled(True)`, `setDragDropMode(DragOnly)`, `setDefaultDropAction(CopyAction)`
  - `_copy_selected`에서 파일 목록 `QMimeData`를 만드는 부분을 `_files_mime(entries)`로 빼서 복사와 드래그가 함께 씁니다.
- **테스트:**
  - `listw.mimeData([items])`의 URL이 모두 실제 파일이어야 합니다. 메모리 항목은 `CONFIG_DIR/clipboard`에 파일이 생겨야 합니다.
  - 기존 `test_keyboard_shortcuts`가 계속 통과해야 합니다.
  - 수동: 탐색기와 카카오톡에 드롭

### FEAT-04 · 캡처 차단 감지 확장 (한 모니터만, 창 단위, 로고형) · M
- **왜:** 지금은 모든 모니터가 완전한 검정일 때만 감지합니다(`screens_capture_blocked`). 다음 경우에는 검은 이미지나 가려진 이미지가 조용히 저장됩니다.
  - (a) 한 모니터만 검게 찍힘
  - (b) 창 하나에만 표시 보호(`SetWindowDisplayAffinity`)가 걸림. 화면 캡처에서 그 창이 검게 나오거나 빠집니다. PrintWindow 결과는 실기 확인이 필요합니다.
  - (c) 검정 대신 로고, 단색, 안내 문구를 그려 넣는 차단 방식
- **완료 기준:**
  - (a) 대상 모니터만 완전한 검정이면 캡처는 그대로 둡니다. 실제로 검은 화면일 수 있기 때문입니다. 대신 비모달 알림을 띄우고 영역 오버레이에 안내 문구를 표시합니다. 오버레이에 그린 글자는 결과 이미지에 들어가지 않습니다.
  - (b) 창 캡처 대상의 `GetWindowDisplayAffinity`가 0이 아니면 저장하지 않고 "이 창은 화면 캡처 금지가 설정돼 있어요"라고 안내합니다. `_capture_blocked`의 변형입니다.
  - (c) 두 조건이 모두 맞으면 알림을 띄우고 안내 대화상자로 연결합니다.
    - 자기 프로세스에 알려진 차단 모듈이 로드돼 있음(`GetModuleHandleW`). 확인된 이름은 `T_Prevent64.dll`뿐이고, 다른 이름은 실제 로그로 확인된 것만 추가합니다.
    - 결과가 거의 단색임. 축소본 픽셀의 98% 이상이 한 색이면 단색으로 봅니다.
  - UI-04 정보 창에 '감지된 캡처 방지 모듈'을 표시합니다.
  - 우회 코드는 넣지 않습니다.
- **손댈 곳:**
  - 새 함수: `is_near_uniform(img, ratio=0.98)`, `loaded_blocker_modules()`, `window_display_affinity(hwnd)`
  - `_run_full`, `RegionCaptureSession.start`, `SelectionOverlay.paintEvent`
  - `capture_active_window`: hwnd도 함께 돌려주도록
  - `_run_window`, `_capture_blocked(kind)`
- **테스트:** `test_capture_blocked.py`에 추가합니다.
  - offscreen에는 모니터가 1대뿐입니다. `screens_capture_blocked`와 `grab_screen_raw`를 monkeypatch해 '현재 모니터만 검정' 상황을 만들고, 기록 1건과 알림을 확인합니다.
  - `is_near_uniform` 표 테스트: 단색 위 작은 로고는 True, 그라데이션은 False.
  - `window_display_affinity`가 1을 돌려주게 monkeypatch하면 기록 0건이고 안내 문구가 변형이어야 합니다.
  - 기존 `test_genuinely_black_window_is_still_captured`(affinity 0)는 계속 통과해야 합니다.

### FEAT-05 · 단축키 편집기 (`QKeySequenceEdit`) · M
- **왜:**
  - 지금은 `<ctrl>+<alt>+a` 형식을 `QLineEdit`에 손으로 입력합니다. 일반 사용자에게 낯선 형식입니다.
  - 오타나 네 단축키끼리의 중복을 막지 못합니다.
- **완료 기준:**
  - 단축키 줄마다 `QKeySequenceEdit`를 씁니다. `setMaximumSequenceLength(1)`과 `setClearButtonEnabled(True)`를 지정하고, "Ctrl+Alt+A" 형식으로 표시합니다. 두 API는 PySide6 6.11에 있음을 확인했습니다.
  - 설정 파일에는 기존 pynput 문자열 형식 그대로 저장합니다. 하위 호환을 위해서이고, FEAT-06 이후에도 유지합니다.
  - 다음 입력은 거부합니다.
    - 수식키 없는 글자·숫자 키. F1–F24와 PrintScreen은 허용합니다.
    - 네 단축키 사이의 중복
  - FEAT-06 이후에는 등록에 실패한 줄에 사유를 표시합니다.
  - '기본값 복원' 버튼은 유지합니다.
  - PrintScreen 안내를 넣습니다: Windows 설정 → 접근성 → 키보드 → 'Print Screen 키로 화면 캡처 열기'를 꺼야 쓸 수 있어요.
- **손댈 곳:**
  - `SettingsDialog.__init__`(단축키 그룹), `_accept`, `_reset_hotkeys`
  - 새 `hotkey_to_keyseq(s)`, `keyseq_to_hotkey(seq)`
  - UI-02의 `format_hotkey`
- **테스트:**
  - 왕복 변환: `DEFAULTS["hotkeys"]` 전부, `<print_screen>`, `<ctrl>+<shift>+s`, `<f9>`
  - 중복이면 `_accept`가 `QMessageBox.warning`(monkeypatch)을 띄우고 창이 닫히지 않아야 합니다.
  - `QTest.keyClick(edit, Qt.Key_Z, Ctrl|Alt)`의 저장값이 `<ctrl>+<alt>+z`여야 합니다.
  - 수동: 한글 입력 상태에서도 영문 키로 기록되는지

### FEAT-06 · pynput을 Win32 `RegisterHotKey`로 교체 · L (오너 결정 필요)
- **왜:** 저수준 키보드 훅에는 다음 한계가 있습니다.
  - 수식키가 눌린 상태로 남습니다. FIX-08은 임시책입니다.
  - 키를 삼키지 않아 다른 앱에도 전달됩니다. 예를 들어 Ctrl+Alt+F를 누르면 Word에 각주가 들어갑니다.
  - 다른 프로그램과의 충돌을 감지할 수 없습니다.
  - 관리자 권한 창 위에서는 동작하지 않습니다(`사용법.txt` 8절).
  - pynput과 six를 빼면 LGPL 고지와 `.py` 수집 같은 배포 부담도 줄어듭니다.
- **완료 기준:**
  - 메인 창 HWND에 `RegisterHotKey`(`MOD_NOREPEAT`)로 등록하고, `MainToolbar.nativeEvent`에서 `WM_HOTKEY`(0x0312)를 처리합니다.
  - 오류 1409가 나면 설정 창과 알림에 단축키별로 "다른 프로그램이 사용 중"을 표시합니다.
  - 기존 `<ctrl>+<alt>+a` 형식과 `Ctrl+Alt+A` 형식을 둘 다 읽습니다.
  - `force_foreground`의 3단계(Alt `keybd_event` 주입)를 삭제합니다. `WM_HOTKEY`를 받은 프로세스는 전경 전환 권한을 얻으므로 필요 없습니다.
  - `restart_app`/`quit_app`에서 `hotkeys.stop()`을 먼저 부르는 순서를 유지합니다.
  - pynput 흔적을 모두 제거합니다.
    - `requirements*.txt`
    - `installer/PinCapture.spec`의 `module_collection_mode`
    - `installer/build.py` `MUST_HAVE`의 `_internal/pynput/...`
    - `THIRD_PARTY_NOTICES.txt`와 `licenses/`의 pynput·six
    - `_find_python_with_deps`, `_handle_missing_deps` 문구
    - `run_selftest`의 `hk._listener` 참조
    - `사용법.txt` 7·8절
    - FIX-08 코드
- **손댈 곳:**
  - `HotkeyManager` 전체 교체. 코드 초안은 검토 문서 2번에 있습니다.
  - `MainToolbar.__init__`, 새 `nativeEvent`, 새 `parse_hotkey`
  - 위에서 나열한 파일들
- **테스트:**
  - `parse_hotkey` 표 테스트: 구두점은 `VkKeyScanW`로 처리하고, 잘못된 형식은 `ValueError`를 내야 합니다.
  - 흔치 않은 조합(예: Ctrl+Alt+Shift+F24)을 두 번 등록해서 두 번째가 1409 사유로 실패하는지 확인한 뒤 해제합니다.
  - `MSG`를 직접 만들어 `toolbar.nativeEvent(b"windows_generic_MSG", addressof(msg))`를 부르면 `capture`가 호출되어야 합니다(monkeypatch).
  - 수동: 검토 문서 4절의 단축키 체크리스트(Word 각주, 잠금 해제 후 ㅁㅈㄹㅂ, 작업 관리자 위)

### FIX-09 · 설정 파일 검증과 버전 · M
- **왜:**
  - `load_config`는 JSON이 깨지면 기본값으로 시작하고, `main()`이 곧바로 `save_config(cfg)`로 파일을 덮어씁니다. 사용자 설정이 전부 사라집니다.
  - 타입 검사가 없습니다. `"hotkeys": ""`이면 시작할 때마다 `HotkeyManager.restart`의 `hotkeys.items()`에서 크래시합니다. `"jpg_quality": "high"`이면 설정 창을 열 때(`SettingsDialog.__init__`)나 JPG로 저장할 때(`_save_image`) `int(cfg["jpg_quality"])`에서 예외가 납니다.
  - `save_config`가 원자적이지 않습니다.
- **완료 기준:**
  - `DEFAULTS`에 `"config_version": 1`을 추가합니다.
  - 파싱에 실패하면 원본을 `config.bad-YYYYmmddHHMMSS.json`으로 옮기고(옮기기가 실패해도 계속 진행) 시작 후 한 번 안내합니다.
  - 새 `_validate_config(data)`는 `DEFAULTS`와 타입이 맞는 값만 받습니다.
    - `file_format`은 png 또는 jpg
    - `jpg_quality`는 50–100으로 자름
    - `hotkeys` 값은 문자열
    - 위치·크기는 정수 2개 또는 `None`
  - 모르는 키는 보존합니다. 새 버전의 설정을 옛 버전이 지우지 않게 하기 위해서입니다.
  - 나중의 마이그레이션을 위해 `_migrate(data)` 자리를 만들어 둡니다.
  - `save_config`는 `.tmp`에 쓴 뒤 `os.replace`로 바꿔 끼웁니다.
- **손댈 곳:** `DEFAULTS`, `load_config`, `save_config`, `main`, `docs/DEVELOPMENT.md`의 설정 설명
- **테스트:** 새 `tests/test_config.py`를 만들고 격리 홈의 `CONFIG_PATH`를 씁니다.
  - 깨진 JSON → 백업 파일이 생기고 기본값으로 시작
  - 잘못된 타입 → 그 키만 기본값
  - `jpg_quality: 500` → 100
  - 모르는 키는 저장 후에도 남아 있음
  - 저장 후 `.tmp` 파일이 남지 않음

### FIX-10 · 보관함 스캔 견고화 · S
- **왜:**
  - `_scan_existing_files`가 정렬 키에서 `f.stat()`을 부릅니다. 그래서 파일 하나만 실패해도(권한, 오프라인 OneDrive 파일) 기록 전체가 비게 됩니다.
  - 설정에서 저장 폴더를 바꿔도 다시 스캔하지 않습니다(`open_settings`).
  - '목록에서 제거'한 항목이 재시작하면 다시 나타납니다.
- **완료 기준:**
  - `os.scandir`로 읽고 파일마다 `try`로 감쌉니다.
  - `open_settings`에서 `save_dir`가 바뀌면 메모리 항목은 유지한 채 다시 스캔하고 `populate()`를 부릅니다. `SettingsDialog._accept`가 cfg를 직접 고치므로, 대화상자를 열기 전 값을 복사해 두고 비교합니다.
  - '목록에서 제거'를 '목록에서 숨기기'로 바꾸고, 숨긴 경로는 `cfg["hidden_paths"]`(최대 500개, 정규화한 경로)에 저장해 스캔에서 뺍니다.
  - 검토 14번이 제안한 파일명 패턴 필터는 넣지 않습니다. FEAT-02의 이름 바꾸기와 충돌합니다.
- **손댈 곳:** `_scan_existing_files`, `open_settings`, `_remove_selected`, `_refresh_info`, `DEFAULTS`(FIX-09 검증 대상에도 추가)
- **테스트:**
  - 한 파일의 stat이 예외를 던지게 monkeypatch해도 나머지 파일은 목록에 있어야 합니다.
  - 저장 폴더를 바꾸면 목록이 새 폴더 기준이어야 합니다.
  - 숨긴 뒤 같은 cfg로 새 `MainToolbar`를 만들면 그 항목이 없어야 합니다.
  - `test_history.py`의 '목록에서 제거' 단언을 고칩니다.

### UI-06 · Windows 다크 모드에서 창마다 색이 섞이는지 확인하고 정리 · S
- **왜:**
  - 메인 창은 스타일시트로 흰 배경과 고정 글자색(`BG`, `TEXT`)을 씁니다.
  - 설정, 메시지 박스, 메뉴는 Qt 기본 스타일입니다. Windows가 다크 모드면 이쪽만 어두운 팔레트로 그려질 수 있습니다.
  - 작성 시점에 실기로는 확인하지 않았습니다.
- **완료 기준:**
  - 다크 모드 PC에서 메인, 설정, 정보, 메뉴, 핀 메뉴를 확인합니다.
  - 그 뒤 둘 중 하나로 정리합니다. ①을 권장합니다.
    - ① 1.0은 밝은 테마로 고정: `QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Light)`. PySide6 6.11에 있음을 확인했습니다.
    - ② 색 상수를 팔레트 기반으로 바꿔 다크 모드를 지원합니다.
- **손댈 곳:** `main()`의 QApplication 생성 직후(새 `_apply_theme(app)`), `run_selftest`
- **테스트:**
  - offscreen에서는 `setColorScheme`을 불러도 값이 `Unknown`으로 남는 것을 확인했습니다. 그래서 `_apply_theme`이 호출되는지만 테스트합니다.
  - 색은 수동으로 확인합니다.

---

## P2: 1.1 이후

### FEAT-07 · 영역 선택 돋보기, 조절 핸들, 방향키 · L
- **왜:**
  - 마우스를 놓는 순간 확정되어서 2px만 빗나가도 처음부터 다시 그려야 합니다.
  - 픽셀 단위로 경계를 확인할 수 없습니다.
- **완료 기준:**
  - 그리는 중에는 커서 옆에 돋보기를 띄웁니다.
    - 정지 화면 `_frozen`의 약 15×15 물리 픽셀을 8배로 확대합니다.
    - 십자선, 좌표, `#RRGGBB`를 함께 표시합니다.
    - 화면 가장자리에서는 반대쪽으로 뒤집힙니다.
  - 설정 "영역을 놓은 뒤 조절하고 Enter로 확정"을 추가합니다. 지금의 빠른 흐름을 지키기 위해 기본값은 꺼짐입니다.
  - 이 설정이 켜져 있으면 놓은 뒤 조절 상태가 됩니다.
    - 핸들 8개로 크기 조절
    - 안쪽을 드래그해 이동
    - 방향키로 1 물리 px 이동, Shift+방향키는 10px
    - Alt+방향키로 크기 조절
    - Enter나 더블클릭으로 확정, Esc로 취소
  - 핀 모드도 같은 오버레이를 씁니다.
  - 돋보기와 핸들은 결과 이미지에 들어가지 않습니다.
- **손댈 곳:**
  - `SelectionOverlay`: 대기/그리기/조절 상태 추가, 새 `_hit_handle`, `_draw_magnifier`, `keyPressEvent`, `mouseDoubleClickEvent`, `paintEvent`
  - `_to_phys`의 역함수
  - `SettingsDialog`, `DEFAULTS`
- **테스트:** offscreen 오버레이에 `QTest.mousePress`/`mouseMove`/`mouseRelease`를 보냅니다.
  - 조절 모드에서 → 키 3번 + Enter → `selected`가 1번 나오고 영역 x가 3 물리 px 이동해야 합니다. 200% 시뮬레이션은 `run_selftest`의 `frozen2x` 방식을 씁니다.
  - 핸들을 드래그하면 크기가 바뀌어야 합니다.
  - 모서리에서도 돋보기 사각형이 위젯 안에 있어야 합니다.
  - `--selftest` 오버레이 스크린샷을 갱신합니다.

### FEAT-08 · 주석 편집기 (1.1의 대표 기능) · L
- **왜:**
  - 다른 캡처 도구와 비교해 가장 큰 공백입니다(검토 3절).
  - `사용법.txt` 9절도 '편집 없음'으로 안내합니다.
- **완료 기준 (MVP):**
  - `EditorWindow`를 보관함 버튼, 보관함 우클릭 '편집…', 핀 우클릭에서 엽니다.
  - 도구는 사각형, 화살표, 가리기입니다. 가리기는 단색으로 채웁니다. 모자이크는 고배율에서 읽히므로 쓰지 않습니다.
  - 색과 두께를 고를 수 있고 Ctrl+Z / Ctrl+Y를 지원합니다.
  - 결과는 새 파일 `<원본 이름>_편집.png`로 저장하고 기록 맨 위에 추가합니다. 원본은 덮어쓰지 않습니다.
  - 복사 버튼과, `b_pin_sel`과 같은 이름(UI-01)의 핀 버튼을 둡니다.
  - 좌표는 원본 해상도 기준이며 DPR을 고려합니다.
  - 다음 단계로 미룰 것:
    - 텍스트, 번호 스티커
    - '캡처 직후 바로 편집'. 하려면 `_finish`가 저장과 클립보드 복사를 먼저 하지 않도록 순서를 바꿔야 합니다.
- **손댈 곳:**
  - 새 `EditorWindow(QWidget)`. 편집 동작은 벡터 목록으로 들고 있다가 원본 사본에 다시 그립니다.
  - `_build_ui`(편집 버튼), FEAT-02 메뉴, `PinWindow.contextMenuEvent`
  - `STRINGS`, `사용법.txt` 2·9절
- **테스트:** 새 `tests/test_editor.py`
  - 동작을 코드로 추가(`add_op`)하면 렌더 결과의 해당 픽셀이 바뀌어야 합니다.
  - 실행 취소 후에는 원본과 픽셀이 같아야 합니다.
  - 저장하면 새 파일이 생기고 원본 파일의 해시는 그대로여야 합니다.
  - 가리기 영역은 단색이어야 합니다.

### FEAT-09 · 마우스로 창 골라 찍기 (hover pick) · L
- **왜:** 지금 창 캡처는 '현재 활성 창'만 찍습니다. 원하는 창을 먼저 클릭해야 하는데, FIX-05는 오작동만 막을 뿐 이 흐름은 그대로입니다.
- **완료 기준:**
  - 영역 오버레이에서 드래그하기 전에, 커서 아래 최상위 창의 테두리를 강조합니다.
  - 단순 클릭(4px 미만 이동, 지금은 무시됨)이면 그 창 영역을 정지 화면에서 잘라 캡처합니다.
  - 드래그는 지금처럼 영역 지정으로 동작합니다.
  - 창 목록은 오버레이를 띄우기 *전에* 스냅숏으로 만듭니다: `EnumWindows`(z 순서) + `_capturable`(FIX-05) + `DWMWA_EXTENDED_FRAME_BOUNDS`.
  - 100/125/150/200% 배율과, 배율이 섞인 다중 모니터에서도 위치가 맞아야 합니다.
- **손댈 곳:**
  - 새 `snapshot_windows()`
  - `RegionCaptureSession.start`
  - `SelectionOverlay.mouseMoveEvent`, `mouseReleaseEvent`, `paintEvent`
  - 물리 좌표 → 위젯 좌표 변환 함수
- **테스트:**
  - 가짜 창 목록(물리 좌표)을 오버레이에 주입합니다.
  - 마우스를 옮기면 강조 사각형이 변환된 좌표와 같아야 합니다.
  - 클릭하면 `selected` 이미지 크기가 창 크기와 같아야 합니다.
  - 200% 배율 시뮬레이션도 확인합니다.
  - 수동: 배율이 다른 모니터 2대

### FEAT-10 · 핀 다듬기 · S
- **왜:**
  - 핀을 여러 개 띄우면 하나씩 더블클릭해 닫아야 합니다.
  - 투명도를 조절할 수 없습니다.
  - 저장 대화상자가 홈 폴더에서 시작합니다.
- **완료 기준:**
  - 트레이와 톱니 메뉴에 '모든 핀 닫기'를 둡니다. 핀 수를 함께 표시하고 0개면 비활성화합니다.
  - Ctrl+휠로 투명도를 30–100% 사이에서 조절합니다(`setWindowOpacity`).
  - 핀과 보관함의 '다른 이름으로 저장'이 `save_dir`에서 시작합니다. 지금은 `PinWindow.contextMenuEvent`와 `_save_selected_as`가 `Path.home()`에서 시작합니다. 이를 위해 `PinWindow`에 저장 폴더를 넘깁니다.
  - FEAT-08 이후에는 핀 메뉴에 '편집…'을 추가합니다.
- **손댈 곳:** `PinWindow.wheelEvent`, `PinWindow.contextMenuEvent`, `_build_tray`, 새 `close_all_pins`
- **테스트:**
  - Ctrl 수식이 붙은 `QWheelEvent`를 보내면 `windowOpacity()`가 줄고, 0.3 아래로는 내려가지 않아야 합니다.
  - `close_all_pins()` 뒤에는 `_pins`가 비어 있어야 합니다.
  - `QFileDialog.getSaveFileName`을 monkeypatch해 저장 대화상자의 시작 경로 인수를 확인합니다.

### FEAT-11 · 영어 UI · M (UI-01 다음)
- **왜:** 외국인 사용자와 GitHub 방문자를 위해서입니다. UI-01로 문자열이 `STRINGS`에 모여 있으면 작업이 단순합니다.
- **완료 기준:**
  - 같은 키를 쓰는 `STRINGS_EN`을 만듭니다.
  - 언어 설정을 추가합니다: 자동(`QLocale.system()`) / 한국어 / English. 바꾼 언어는 재시작 후 적용되며, 그렇다고 안내합니다.
  - 설치 프로그램의 영어 메시지(`[Languages]`)와 영어 사용법은 따로 결정합니다.
- **손댈 곳:** `STRINGS`, `T`, `SettingsDialog`, `DEFAULTS`
- **테스트:**
  - 두 dict의 키 집합이 같아야 합니다.
  - 키마다 자리표시자(`{name}`) 집합이 같아야 합니다.

### FIX-11 · 시작 단계와 진단 정리 · S
- **왜:**
  - Qt import 가운데 `QtCore`만 `try` 안에 있습니다(`_handle_missing_deps`). `QtGui`, `QtNetwork`, `QtWidgets`는 밖에 있어서, EXE에서 그쪽 DLL이 빠지면 친절한 안내 대신 traceback 메시지 박스가 뜹니다.
  - `QtCore`를 두 번 import합니다.
  - 로그에 Qt 버전과 Windows 빌드가 없습니다.
- **완료 기준:**
  - 네 모듈의 import를 하나의 `try`로 합치고 중복을 없앱니다.
  - QApplication을 만든 직후 로그에 `qVersion()`과 `platform.version()`을 남깁니다.
  - (선택) `faulthandler.enable(file=로그)`. 단, Windows의 faulthandler는 프로그램이 스스로 처리한 예외(예: 주입된 DLL 안의 예외)도 "Windows fatal exception"으로 찍을 수 있어서 힌트로만 봅니다. 로그 읽는 법을 `docs/DEVELOPMENT.md`에 적어 둡니다.
- **손댈 곳:** 파일 상단 Qt import 블록, `_setup_logging`, `main`
- **테스트:** `test_process.py`에서 `PINCAP_NO_LOG` 없이, 격리 홈으로 `--quit`를 실행합니다. 로그 파일에 `APP_VERSION`과 Qt 버전이 있어야 합니다.

---

## 보류 / 제외

| 항목 | 결정 | 이유 |
|---|---|---|
| 화면 캡처 방지 우회 (DXGI, WGC, 훅 해제, 표시 속성 변경) | 영구 제외 | 지켜야 할 규칙입니다. 감지하고 안내만 합니다(FEAT-04) |
| 스크롤 캡처 | 제외 | 500줄이 넘고 스크롤 주입과 이어붙이기가 필요하며, 다른 도구에서도 불안정합니다. 브라우저의 전체 페이지 캡처를 안내합니다 |
| 모니터에 걸친 영역 선택 | 제외 | 비용에 비해 수요가 적습니다 |
| 파일 이름 패턴 설정 | 제외 | 대부분의 사용자가 바꾸지 않습니다 |
| 첫 실행 OneDrive 경고 | 제외 | `사용법.txt` 3절 한 줄로 충분합니다 |
| 업데이트 확인 등 인터넷 통신 | 제외 | `사용법.txt` 7절에서 "인터넷에 연결하지 않습니다"라고 약속했습니다. 업데이트는 새 설치 파일을 실행하는 방식입니다 |
| 실행 중 다른 버전 감지(`show <버전>`) | 보류 | 설치 프로그램이 `--quit`로 닫고 교체하므로 실사용에 문제가 없습니다 |
| onefile 빌드 | 제외 | 시작에 6–14초가 걸립니다(onedir은 약 3초) |
| 처음 닫을 때 '트레이로/종료' 묻기 | 제외 | 트레이 최소화는 표준 동작입니다(검토 5절). 대신 UI-03을 합니다 |
| 모자이크 가리기 | 제외 | 고배율에서 읽힙니다. 단색으로만 가립니다 |
| 코드 서명 | 오너 결정 | 서명이 없으면 SmartScreen 경고가 뜨고, Smart App Control이 켜진 PC에는 설치할 수 없습니다 |
| 앱 라이선스, 게시자, 저장소 이름 | 확정 (All rights reserved, ChamomileGrey, ChamomileGrey/PinCapture, ko-fi.com/chamomilegrey) | 코드·README·설치 정보에 반영됨. 코드 서명과 pynput 교체만 미정 |
| pynput 교체 | 오너 결정 | FEAT-06, 임시책은 FIX-08 |
