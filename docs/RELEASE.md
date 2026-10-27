# 배포 절차 (릴리스 체크리스트)

새 버전을 GitHub Release로 배포할 때 위에서부터 순서대로 따라 해요. 배포 여부와 시점은 소유자가 정해요.
명령은 저장소 루트에서 PowerShell로 실행해요. 아래 예시의 `X.Y.Z`는 새 버전으로 바꿔 읽으세요.

> **`installer/PinCapture.iss`의 `AppId`는 절대 바꾸지 마세요.** 바꾸면 업그레이드가 아니라 별개 프로그램으로 설치돼요. 다른 불변 조건은 `AGENTS.md` 6장에 있어요.

## 1. 버전 올리기

세 곳을 **함께** 바꿔요.

| 위치 | 바꿀 내용 |
|---|---|
| `pincapture.py`의 `APP_VERSION = "X.Y.Z"` | 큰따옴표, `=` 양쪽 공백 한 칸 형식을 그대로 유지해요. `build.py`와 CI가 정규식으로 읽어요 |
| `pincapture.py` 맨 위 이력 주석 | `#   vX.Y.Z YYYY-MM-DD  <도구> (<모델>) — 요약` 한 줄을 추가하고, `Modified:` 줄의 날짜와 모델을 갱신해요 |
| `CHANGELOG.md` | `[Unreleased]` 내용을 `## [X.Y.Z] - YYYY-MM-DD` 아래로 옮기고, 빈 `[Unreleased]`를 남겨요 |

함께 확인할 것:
- 동작이나 버튼 이름이 바뀌었으면 `installer/docs/사용법.txt`를 고쳐요(UTF-8 BOM + CRLF 유지. 확인 방법은 `AGENTS.md` 6장).
- 의존성이 바뀌었으면 `requirements*.txt`, `installer/docs/THIRD_PARTY_NOTICES.txt`, `installer/docs/licenses/`를 고쳐요.
- 화면 모양이 바뀌었으면 `docs/images/`를 다시 만들어요(`AGENTS.md` 9장).

## 2. 시험

```powershell
py -3.13 -m pytest -q
```

모두 통과해야 해요. 소유자 PC에서 `Windows fatal exception: access violation`이 한 번 찍히는 건 환경 잡음이에요(`AGENTS.md` 8장).

## 3. 로컬 빌드

```powershell
py -3.13 installer\build.py
```

`=== 1/5 icon`부터 `=== 5/5 Inno Setup`까지 진행되고, 아래 파일이 생겨요.

| 파일 | 용도 |
|---|---|
| `installer\output\PinCapture-Setup-X.Y.Z.exe` | 설치 파일 |
| `installer\output\PinCapture-Setup-X.Y.Z.sha256.txt` | SHA-256 |
| `installer\output\PinCapture-Setup-X.Y.Z_배포안내.txt` | 배포 페이지나 메시지에 붙일 안내문(SmartScreen 대처 포함) |

빌드가 멈추면 메시지로 원인을 찾아요.

| 메시지 | 원인 |
|---|---|
| `APP_VERSION not found in pincapture.py` | 버전 줄 형식이 바뀌었어요 |
| `bundle check failed: missing=[...] unexpected=[...]` | `PinCapture.spec`의 `DROP`과 `build.py`의 `MUST_HAVE`/`MUST_NOT`이 어긋났어요 |
| `cannot clean ...\installer\build: a file is in use` | `installer\build\dist`에서 실행한 `PinCapture.exe`가 떠 있거나, 그 폴더를 연 탐색기 창이 있어요. 닫고 다시 빌드해요 |
| `smoke test failed` | 빌드된 EXE의 `--selftest`(offscreen)가 실패했어요. 연기 시험은 `installer\build\smoke`를 임시 홈으로 쓰고, 그 안의 `config.json`이 `save_dir`을 같은 폴더로 가리켜요. 실제 `~/.pincapture`와 사진 폴더는 건드리지 않아요. 로그를 보려면 `PINCAP_NO_LOG`를 빼고 그 홈에서 EXE를 직접 실행해요. 로그를 남에게 보일 때는 경로의 사용자 이름을 가려요 |
| `Inno Setup 6 (ISCC.exe) not found` | Inno Setup 6을 설치해요. `.iss`의 한국어 메시지(`Korean.isl`)는 6.3 이상에 있어요 |

## 4. 깨끗한 Windows에서 수동 시험

Python이 없는 Windows 10/11 x64(VM, Windows 샌드박스, 다른 계정)에서 해요. 설치 파일은 브라우저로 받아서, 인터넷에서 받은 파일 표시(MOTW)가 붙은 상태로 시험해요.
단축키는 **반드시 실제 키보드로** 눌러요. pynput은 프로그램이 보낸 키 입력을 무시하므로 자동화할 수 없어요.

| # | 항목 | 확인할 것 |
|---|---|---|
| 1 | 설치 | `_배포안내.txt`의 순서대로 브라우저 경고와 SmartScreen("추가 정보" → "실행")을 통과해요. UAC 창 없이 `%LOCALAPPDATA%\Programs\PinCapture`에 설치돼요. 마지막 화면의 "핀캡처 실행"으로 앱이 떠요 |
| 2 | 바로가기 | 시작 메뉴에 `핀캡처`와 `핀캡처 사용법`이 있어요. 선택한 경우 바탕화면 바로가기가 있어요. `.lnk` 속성에서 대상은 `PinCapture.exe`, 시작 위치는 설치 폴더예요. 작업 표시줄에 고정 → 종료 → 고정 아이콘으로 다시 실행돼요 |
| 3 | 트레이로 시작 | 자동 실행을 선택하고 로그오프 후 로그온(또는 재부팅)해요. 창 없이 트레이 아이콘만 떠요. `%USERPROFILE%\.pincapture\pincapture.log` 시작 줄에 새 버전과 `(exe)`가 찍혀요 |
| 4 | 단축키(실제 키보드) | `Ctrl+Alt+A`, `Ctrl+Alt+W`, `Ctrl+Alt+F`, `Ctrl+Alt+Q`가 창이 숨겨진 상태에서도 동작해요. 설정 창의 단축키 그룹 제목에 "(현재 사용 불가)"가 없어요 |
| 5 | 캡처 모드 | 영역: 드래그, 크기 표시, Esc·우클릭 취소. 창: 일부 가려진 창도 온전히 찍혀요. 전체: 마우스가 있는 모니터. 핀: 드래그 이동, 휠 크기 조절, 우클릭 메뉴, 더블클릭·Esc 닫기. 파일이 `사진\PinCapture`에 저장되고 `Ctrl+V`로 붙여 넣어져요. 트레이 메뉴와 창 버튼으로도 한 번씩 해 봐요 |
| 6 | 화면 배율 | 가능하면 125%·150%와 다중 모니터에서 영역 캡처 크기가 실제 픽셀과 맞는지 확인해요 |
| 7 | 실행 중 업그레이드(핀을 연 채로) | 이전 버전을 설치·실행하고 핀 2~3개를 띄운 다음 창을 트레이로 숨겨요. 새 설치 파일을 실행하면 "실행 중이라 설치할 수 없습니다" 없이 앱이 자동으로 닫혀요. 작업 관리자에 `PinCapture.exe`가 남지 않고, 설치 후 설정이 그대로예요. `PinCapture-Setup-X.Y.Z.exe /SILENT`로도 한 번 해 보고, 끝나면 앱이 트레이로 다시 떠요 |
| 8 | 관리자 권한 인스턴스 | 핀캡처를 관리자 권한으로 실행한 채 설치 파일을 실행하면, 그 창에서 직접 종료하라는 안내가 나와요 |
| 9 | 제거 | 시작 메뉴 `핀캡처` 우클릭 → 제거. 실행 중인 앱이 닫혀요. 바로가기(설정 창으로 만든 것 포함)가 사라지고, `~/.pincapture` 삭제를 물어요(기본값은 "아니요"). 저장한 캡처는 남아 있어요 |
| 10 | 글자·표·수식 | 핀 우클릭 **글자 복사**에 글자, 표 (엑셀), 표 (Markdown), 수식이 있어요. 글자는 한 문단의 줄바꿈이 이어지고 문단은 남아요. 표 (엑셀)은 엑셀에 칸으로 붙여 넣어져요. 메인 창 글자 복사 아이콘의 왼쪽 클릭은 글자, 우클릭은 같은 목록이에요. 수식은 모델 파일을 넣기 전에는 안내만 나와요. 사용법대로 넣은 뒤에는 LaTeX가 복사돼요. 새 단축키는 없어요 |

결과는 릴리스 메모나 PR에 짧게 남겨요. 실패한 항목이 있으면 배포하지 않아요.

## 5. 태그 붙이고 푸시하기

변경을 `main`에 푸시해서 CI가 초록색인지 먼저 확인한 다음 태그를 붙여요.

```powershell
git tag vX.Y.Z
git push origin vX.Y.Z
```

CI가 태그 `vX.Y.Z`와 `APP_VERSION`이 같은지 검사해요. 다르면 실패해요.

## 6. CI 초안 릴리스 확인

GitHub → Actions → `build` 실행이 끝나면 아래를 확인해요.

- 실행 요약의 Artifacts에 `PinCapture-setup`이 있어요.
- Releases에 **초안(Draft)** 릴리스가 생기고, `installer/output/*`(설치 파일, `.sha256.txt`, `_배포안내.txt`)가 첨부돼 있어요.

## 7. 게시

1. 초안 릴리스를 편집해요. 제목은 `핀캡처 X.Y.Z`로 해요.
2. 본문에 **CI가 만든** `_배포안내.txt` 내용 전체와 `CHANGELOG.md`의 해당 버전 항목을 붙여요.
   - PyInstaller 빌드는 바이트 단위로 재현되지 않아서, 로컬 빌드의 SHA-256은 CI 설치 파일과 달라요. 반드시 첨부된 파일 기준 값을 써요.
   - 첨부 파일을 받아서 직접 확인해요: `Get-FileHash .\PinCapture-Setup-X.Y.Z.exe -Algorithm SHA256`
3. 가능하면 설치 파일을 VirusTotal로 검사해요. 오탐이 나오면 게시 전에 백신사에 신고해요.
4. "Publish release"를 눌러요. 이미 게시한 태그나 릴리스는 지우지 말고, 문제가 있으면 다음 패치 버전으로 고쳐요.

## 8. CI 첫 실행 디버깅

`.github/workflows/build.yml`은 처음 푸시에서 빠졌다가 0.7.0에서 다시 넣었어요. Inno Setup 단계가 `choco` 종료 코드 3010(재부팅 요청)을 실패로 보지 않고, `Korean.isl`이 있는지도 확인해요. 첫 실행은 태그 없이 PR이나 `main` 푸시로 초록색을 확인한 다음 태그를 붙여요.

- 다시 실행: Actions → 해당 실행 → "Re-run jobs"
- 수동 실행: Actions → `build` → "Run workflow"(`workflow_dispatch`, 워크플로 파일이 기본 브랜치에 있어야 보여요)
- 브랜치에서 시험: 브랜치를 푸시하고 PR을 열면 `pull_request`로 돌아요(이때는 릴리스를 만들지 않아요).

| 단계 | 실패할 수 있는 이유 | 할 일 |
|---|---|---|
| `Install dependencies` | 고정 버전 휠을 받지 못함 | pip 로그에서 패키지 이름을 확인해요. 버전은 소유자 승인 없이 바꾸지 않아요 |
| `Tests` | 러너 환경 차이(offscreen, 키보드 훅, 시간 제한) | 실패한 테스트 이름과 출력을 확인해요. 로컬 `py -3.13 -m pytest -q`와 비교해요 |
| `Tests` | 로그는 `N passed`인데 단계 종료 코드가 1 | Qt가 파이썬 종료 중에 죽는 경우예요. 예외 문장이 없을 수 있어요. `tests/conftest.py`가 요약 뒤에 pytest 코드로 `os._exit` 해요. 그 코드가 있는데도 실패하면 실패한 테스트 이름을 봐요 |
| `Tag must match APP_VERSION` | 태그와 `APP_VERSION`이 다름 | 잘못 붙인 태그는 `git push --delete origin vX.Y.Z`와 `git tag -d vX.Y.Z`로 지우고(아직 게시 전일 때만) 다시 붙여요 |
| `Ensure Inno Setup 6` | `choco install innosetup` 실패, 또는 다른 경로에 설치됨, 또는 `Korean.isl` 없음 | 로그의 `ISCC:` 경로를 확인해요. `build.py`의 `find_iscc()`는 `%ProgramFiles(x86)%\Inno Setup 6` 등 정해진 경로와 `PATH`만 봐요. 종료 코드 3010은 워크플로가 성공으로 바꿔요 |
| `Build installer` | 번들 검사, 연기 시험, `compiler:Languages\Korean.isl` 없음, BOM이 빠진 `.iss` | 3장 표를 보세요. 한국어 메시지 파일이 없다는 오류면 러너의 Inno Setup 버전을 확인해요 |
| `Build installer` | `UnicodeEncodeError` (`cp1252`) while printing `_배포안내.txt` | 설치는 끝났고 마지막 출력만 실패한 경우예요. `installer/build.py`의 `configure_stdio()`와 워크플로의 `PYTHONIOENCODING=utf-8`이 그 출력을 UTF-8로 바꿔요 |
| `upload-artifact` | `installer/output/`가 비어 있음 | 앞 단계 로그를 확인해요 |
| `Draft release` | 권한 부족(403) | 저장소 Settings → Actions → General → Workflow permissions에서 쓰기 권한을 확인해요(워크플로에는 `contents: write`가 있어요) |
| 릴리스 첨부 파일 이름 | 한글이 들어간 `_배포안내.txt` 이름이 GitHub에서 바뀔 수 있음 | 본문에 내용을 붙였으면 그 첨부 파일은 지워도 돼요 |

첫 실행이 초록색이 되면 이 장 첫 문장의 "첫 실행" 안내를 지나간 기록으로 다듬어요.
