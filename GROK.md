# GROK.md

Grok 운영자는 **[`AGENTS.md`](AGENTS.md)를 먼저 읽으세요.** 이 파일은 요약이고, 규칙의 원본은 `AGENTS.md`예요.

가장 중요한 규칙 5가지:
1. `pincapture.py`는 저장소 루트의 단일 파일로 유지해요. 소유자의 바로가기가 이 파일을 바로 실행하니, 깨진 상태로 두지 마세요.
2. 작업을 끝내기 전에 `py -3.13 -m pytest -q`를 통과시키고, 버그를 고치면 테스트를 함께 추가해요. `pincapture.py`를 따로 실행할 때는 `tests/_isolation.py`의 `isolated_env()`로 홈과 저장 폴더를 격리해요(`AGENTS.md` 9장).
3. `AGENTS.md` 6장의 불변 조건(Inno `AppId`, AppUserModelID·뮤텍스 동기화, `exit(0)` 종료, onedir, BOM+CRLF, 캡처 방지 우회 금지)은 깨지 않아요.
4. 개인정보는 쓰지 않아요. `archive/`는 커밋하지 않고, 소유자 이메일·사용자 이름·실제 경로 대신 `C:\Users\<사용자>`를 써요.
5. 라이선스는 All rights reserved(MIT 아님), 게시자는 ChamomileGrey, 저장소는 ChamomileGrey/PinCapture, 후원은 https://ko-fi.com/chamomilegrey 로 정해져 있어요. 코드 서명과 pynput 교체만 소유자에게 물어요(`AGENTS.md` 7장).

첫 작업 제안: [`docs/ROADMAP.md`](docs/ROADMAP.md)의 작업 순서를 보되, 0.7.0·0.8.0·0.9.0에 이미 있는 기능은 다시 만들지 않아요. 0.9.0은 핀 위 표시, 스포이트, 자예요.
