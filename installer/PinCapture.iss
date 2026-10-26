; 핀캡처 설치 프로그램 (Inno Setup 6)
; Created: 2026-10-22 by Claude Opus 5.5 via Claude Code
; Changelog:
;   v0.6.0 2026-10-22 Claude Opus 5.5 — 첫 버전: 사용자별 설치(관리자 권한 불필요), 시작 메뉴/바탕화면/
;                     자동 실행 바로가기, 설치·제거 전 실행 중인 앱 자동 종료(--quit → 실패 시 taskkill),
;                     관리자 권한 인스턴스 감지, 무인 업데이트 후 재실행, 제거 시 설정 삭제 선택
;   v0.7.0 2026-10-26 Grok 4.7 — 게시자 이름을 ChamomileGrey 로 (build.py PUBLISHER 와 같음). AppId 는 그대로
;
; 빌드는 installer\build.py 가 함 (AppVersion 을 /DAppVersion=x.y.z 로 넘김).
; 직접 컴파일: ISCC.exe /DAppVersion=0.6.0 PinCapture.iss   (먼저 build.py --no-setup 으로 build\dist 생성)

#ifndef AppVersion
  #error "AppVersion 이 없습니다. installer\build.py 로 빌드하거나 /DAppVersion=x.y.z 를 넘기세요."
#endif

#define AppName        "핀캡처"
#define AppNameEn      "PinCapture"
#define AppPublisher   "ChamomileGrey"
#define AppExe         "PinCapture.exe"
; pincapture.py 의 APP_USER_MODEL_ID / APP_MUTEX_NAME 과 같아야 함
#define AppUserModelID "pincapture.app"
#define AppMutex       "PinCaptureRunning"

[Setup]
; AppId 는 절대 바꾸지 말 것 — 바꾸면 업그레이드가 아니라 별개 프로그램으로 설치됨
AppId={{6F1C2B8E-3D4A-4E9B-9A7C-2E5D1F0B8C41}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppNameEn}
VersionInfoDescription={#AppName} 설치 프로그램
; 사용자별 설치: 관리자 권한(UAC) 없이 %LOCALAPPDATA%\Programs\PinCapture 에 설치
PrivilegesRequired=lowest
DefaultDirName={autopf}\{#AppNameEn}
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=output
OutputBaseFilename=PinCapture-Setup-{#AppVersion}
SetupIconFile=build\pincapture.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=no
; 실행 중인 앱은 [Code] 에서 --quit 으로 직접 닫음 (재시작 관리자 대신)
CloseApplications=no
RestartApplications=no
SetupMutex=PinCaptureSetupMutex

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 작업:"
Name: "autostart"; Description: "Windows 시작 시 자동 실행 (트레이에서 대기)"; GroupDescription: "추가 작업:"

[InstallDelete]
; 업그레이드 때 이전 버전의 런타임 폴더를 비우고 새로 설치 (이전 설치가 있을 때만)
Type: filesandordirs; Name: "{app}\_internal"; Check: IsUpgrade

[Files]
Source: "build\dist\PinCapture\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "docs\사용법.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "docs\THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "docs\licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion

[Icons]
; AppUserModelID 를 앱 창과 맞춰야 작업 표시줄 고정·그룹이 핀캡처 아이콘으로 됨
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; AppUserModelID: "{#AppUserModelID}"
Name: "{autoprograms}\{#AppName} 사용법"; Filename: "{app}\사용법.txt"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; AppUserModelID: "{#AppUserModelID}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExe}"; Parameters: "--tray"; WorkingDir: "{app}"; AppUserModelID: "{#AppUserModelID}"; Tasks: autostart

[Run]
Filename: "{app}\{#AppExe}"; Description: "핀캡처 실행"; Flags: nowait postinstall skipifsilent
Filename: "{app}\사용법.txt"; Description: "사용법 보기"; Flags: shellexec postinstall skipifsilent unchecked
; 무인(/SILENT) 업데이트로 실행 중이던 앱을 닫았다면 트레이로 다시 실행
Filename: "{app}\{#AppExe}"; Parameters: "--tray"; Flags: nowait skipifnotsilent; Check: WasAppRunning

[UninstallDelete]
; 앱 설정 창의 '바로가기 만들기' 버튼으로 만든 바로가기도 같은 이름이라 함께 정리
Type: files; Name: "{autodesktop}\{#AppName}.lnk"
Type: files; Name: "{userstartup}\{#AppName}.lnk"
Type: files; Name: "{autoprograms}\{#AppName}.lnk"
; 런타임이 만든 캐시 등. {app} 통째 삭제는 하지 않음 (사용자가 엉뚱한 폴더를 골랐을 때를 대비)
Type: filesandordirs; Name: "{app}\_internal"
Type: dirifempty; Name: "{app}"

[Code]
const
  SYNCHRONIZE = $00100000;
  ERROR_ACCESS_DENIED = 5;

var
  AppWasRunning: Boolean;
  AppRunningElevated: Boolean;

function OpenMutexW(DesiredAccess: Cardinal; InheritHandle: Integer; Name: String): THandle;
  external 'OpenMutexW@kernel32.dll stdcall';
function CloseHandle(Handle: THandle): Integer;
  external 'CloseHandle@kernel32.dll stdcall';

{ 핀캡처가 이 세션에서 실행 중인지. 관리자 권한으로 실행된 인스턴스의 뮤텍스는 열 수 없어서(접근 거부)
  그것도 '실행 중'으로 본다 (아니면 사용 중인 파일을 덮어쓰다 설치가 깨짐). }
function IsAppRunning(): Boolean;
var
  H: THandle;
begin
  AppRunningElevated := False;
  H := OpenMutexW(SYNCHRONIZE, 0, '{#AppMutex}');
  if H <> 0 then
  begin
    CloseHandle(H);
    Result := True;
  end
  else
  begin
    AppRunningElevated := (DLLGetLastError = ERROR_ACCESS_DENIED);
    Result := AppRunningElevated;
  end;
end;

function IsUpgrade(): Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\{#AppExe}'));
end;

function WasAppRunning(): Boolean;
begin
  Result := AppWasRunning;
end;

{ 실행 중인 핀캡처를 닫는다: --quit 요청 → 최대 10초 대기 → 그래도 남아 있으면 taskkill. }
function CloseRunningApp(const ExePath: String): Boolean;
var
  ResultCode, I: Integer;
begin
  Result := True;
  if not IsAppRunning() then
    Exit;
  if AppRunningElevated then
  begin
    { 관리자 권한 인스턴스는 일반 권한 설치 프로그램이 닫을 수 없음 }
    Log('PinCapture is running elevated; cannot close it');
    Result := False;
    Exit;
  end;
  Log('PinCapture is running; sending --quit');
  if FileExists(ExePath) then
    Exec(ExePath, '--quit', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  for I := 1 to 25 do
  begin
    if not IsAppRunning() then
      Exit;
    Sleep(200);
  end;
  Log('PinCapture still running after --quit; forcing taskkill');
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM {#AppExe}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  for I := 1 to 15 do
  begin
    if not IsAppRunning() then
      Exit;
    Sleep(200);
  end;
  Result := not IsAppRunning();
end;

function CloseFailedMessage(const Action: String): String;
begin
  Result := '핀캡처가 실행 중이라 ' + Action + '할 수 없습니다.' + #13#10 +
            '작업 표시줄 오른쪽 트레이의 핀캡처 아이콘을 우클릭해 [종료]한 뒤 다시 시도해 주세요.';
  if AppRunningElevated then
    Result := Result + #13#10#13#10 + '(핀캡처를 관리자 권한으로 실행 중이면 그 창에서 직접 종료해야 합니다.)';
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  AppWasRunning := IsAppRunning();
  if not CloseRunningApp(ExpandConstant('{app}\{#AppExe}')) then
    Result := CloseFailedMessage('설치');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  { '제거하시겠습니까?' 확인 다음 단계에서 앱을 닫는다 (확인에서 '아니요'를 누르면 앱은 그대로) }
  if CurUninstallStep = usAppMutexCheck then
  begin
    if not CloseRunningApp(ExpandConstant('{app}\{#AppExe}')) then
    begin
      SuppressibleMsgBox(CloseFailedMessage('제거'), mbError, MB_OK, IDOK);
      Abort;
    end;
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{%USERPROFILE}\.pincapture');
    if DirExists(DataDir) then
      if SuppressibleMsgBox('핀캡처 설정과 기록 파일도 삭제할까요?' + #13#10 + DataDir + #13#10#13#10 +
                            '저장해 둔 캡처 이미지는 삭제하지 않습니다.',
                            mbConfirmation, MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES then
        DelTree(DataDir, True, True, True);
  end;
end;
