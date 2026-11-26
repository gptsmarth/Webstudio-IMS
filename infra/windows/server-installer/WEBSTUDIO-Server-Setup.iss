; WEBSTUDIO Server Setup — Inno Setup script (M12C)
; Compile: scripts/release/build-server-setup.ps1 (stages Python + NSSM automatically)

#define MyAppName "WEBSTUDIO Server"
#define MyAppVersion "2.8.0"
#define MyAppBuild 10
#define MyAppPublisher "WEBSTUDIO"
#define MyAppURL "https://webstudio.local"
#define InstallRoot "D:\WEBSTUDIO-IMS"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={#InstallRoot}
DefaultGroupName=WEBSTUDIO
DisableProgramGroupPage=yes
UsePreviousTasks=no
OutputBaseFilename=WEBSTUDIO Server Setup
OutputDir=..\..\..\release\server
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=..\..\..\apps\desktop\public\assets\webstudio\icon.ico
UninstallDisplayIcon={app}\assets\webstudio\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "manualdatabase"; Description: "Use a PostgreSQL database I set up myself (skip automatic provisioning)"; Flags: unchecked; Check: NeedsDatabaseSetup

[Files]
Source: "..\..\..\apps\desktop\public\assets\webstudio\icon.ico"; DestDir: "{app}\assets\webstudio"; Flags: ignoreversion
Source: "..\..\..\VERSION.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\..\VERSION"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\..\apps\backend\pyproject.toml"; DestDir: "{app}\apps\backend"; Flags: ignoreversion
Source: "..\..\..\apps\backend\README.md"; DestDir: "{app}\apps\backend"; Flags: ignoreversion
Source: "..\..\..\apps\backend\src\*"; DestDir: "{app}\apps\backend\src"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc,.env*,*.key,*.pem"
Source: "..\..\..\database\migrations\*"; DestDir: "{app}\database\migrations"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc,.env*,*.key,*.pem"
Source: "..\..\..\config\env\.env.production.template"; DestDir: "{app}\config\env"; DestName: ".env.production.template"; Flags: ignoreversion
Source: "..\*.ps1"; DestDir: "{app}\infra\windows"; Flags: ignoreversion
Source: "server-install-post.ps1"; DestDir: "{app}\infra\windows\server-installer"; Flags: ignoreversion
Source: "invoke-server-post-install.ps1"; DestDir: "{app}\infra\windows\server-installer"; Flags: ignoreversion
Source: "postgres-setup.ps1"; DestDir: "{app}\infra\windows\server-installer"; Flags: ignoreversion
Source: "..\..\..\release\server\staging\runtime\python\*"; DestDir: "{app}\runtime\python"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\..\release\server\staging\tools\nssm\nssm.exe"; DestDir: "{app}\tools\nssm"; Flags: ignoreversion

[Icons]
Name: "{group}\WEBSTUDIO Server Logs"; Filename: "{app}\logs\webstudio-api.log"
Name: "{group}\Uninstall WEBSTUDIO Server"; Filename: "{uninstallexe}"

[Code]
const
  WebstudioServiceKey = 'SYSTEM\CurrentControlSet\Services\WEBSTUDIO Server';

function NeedsDatabaseSetup(): Boolean;
var
  Lines: TArrayOfString;
  I, Separator: Integer;
  Value: String;
begin
  Result := False;
  if RegKeyExists(HKLM, WebstudioServiceKey) then
    exit;

  Result := True;
  if LoadStringsFromFile(AddBackslash(WizardDirValue) + 'config\env\.env', Lines) then
    for I := 0 to GetArrayLength(Lines) - 1 do
    begin
      Separator := Pos('=', Lines[I]);
      if (Separator > 0) and
        (CompareText(Trim(Copy(Lines[I], 1, Separator - 1)), 'DATABASE_URL') = 0) then
      begin
        Value := Trim(Copy(Lines[I], Separator + 1, Length(Lines[I])));
        Result := (Value = '') or (Value = '""') or (Value = '''''') or
          (Pos(':CHANGE_ME@', Uppercase(Value)) > 0);
      end;
    end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  AppDirectory: String;
  InstallRoot: String;
  ResultCode: Integer;
begin
  Result := '';
  InstallRoot := ExpandConstant('{app}');
  if RegKeyExists(HKLM, WebstudioServiceKey) then
  begin
    if not RegQueryStringValue(HKLM, WebstudioServiceKey + '\Parameters',
      'AppDirectory', AppDirectory) or
      (CompareText(RemoveBackslashUnlessRoot(AppDirectory), InstallRoot + '\apps\backend') <> 0) then
      Result := 'An existing WEBSTUDIO Server uses a different installation folder. Upgrade it using its current installation folder.';
    if (Result = '') and not FileExists(InstallRoot + '\config\env\.env') then
      Result := 'Restore the existing WEBSTUDIO configuration file before upgrading this server.';
    if (Result = '') and
      (not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
        '-NoProfile -Command "$ErrorActionPreference = ''Stop''; $service = Get-Service ''WEBSTUDIO Server''; if ($service.Status -ne ''Stopped'') { Stop-Service -InputObject $service; $service.WaitForStatus(''Stopped'', [TimeSpan]::FromSeconds(30)) }"',
        '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0)) then
      Result := 'Could not stop the existing WEBSTUDIO Server service. Resolve the service issue before retrying.';
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Params: String;
  ResultCode: Integer;
begin
  if CurStep <> ssPostInstall then
    exit;
  WizardForm.StatusLabel.Caption := 'Configuring WEBSTUDIO Server service and database...';
  Params := ExpandConstant('-NoProfile -ExecutionPolicy Bypass -File "{app}\infra\windows\server-installer\invoke-server-post-install.ps1" -InstallRoot "{app}"');
  if NeedsDatabaseSetup() and WizardIsTaskSelected('manualdatabase') then
    Params := Params + ' -ManualDatabase';
  if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Params,
    '', SW_SHOW, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
    RaiseException(ExpandConstant('WEBSTUDIO Server setup did not finish. See {app}\logs\install-post.log before rerunning setup.'));
end;

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\infra\windows\uninstall-webstudio-service.ps1"" -InstallRoot ""{app}"""; Flags: runhidden waituntilterminated
