; WEBSTUDIO Server Setup — Inno Setup script (M12C)
; Compile: scripts/release/build-server-setup.ps1

#define MyAppName "WEBSTUDIO Server"
#define MyAppVersion "0.1.0"
#define MyAppBuild 1
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
OutputBaseFilename=WEBSTUDIO Server Setup
OutputDir=..\..\..\release\server
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=..\..\..\apps\desktop\public\assets\webstudio\icon.ico
UninstallDisplayIcon={#InstallRoot}\assets\webstudio\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\..\..\apps\desktop\public\assets\webstudio\icon.ico"; DestDir: "{#InstallRoot}\assets\webstudio"; Flags: ignoreversion
Source: "..\..\..\apps\backend\*"; DestDir: "{#InstallRoot}\apps\backend"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc,.pytest_cache\*"
Source: "..\..\..\database\*"; DestDir: "{#InstallRoot}\database"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\..\config\env\.env.production.template"; DestDir: "{#InstallRoot}\config\env"; DestName: ".env.production.template"; Flags: ignoreversion
Source: "..\*.ps1"; DestDir: "{#InstallRoot}\infra\windows"; Flags: ignoreversion
Source: "server-install-post.ps1"; DestDir: "{#InstallRoot}\infra\windows\server-installer"; Flags: ignoreversion
Source: "payload\*"; DestDir: "{#InstallRoot}\payload"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Icons]
Name: "{group}\WEBSTUDIO Server Logs"; Filename: "{#InstallRoot}\logs\webstudio-api.log"
Name: "{group}\Uninstall WEBSTUDIO Server"; Filename: "{uninstallexe}"

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{#InstallRoot}\infra\windows\server-installer\server-install-post.ps1"" -InstallRoot ""{#InstallRoot}"""; Flags: runhidden waituntilterminated; StatusMsg: "Configuring WEBSTUDIO Server service and database..."

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  if not RegKeyExists(HKLM, 'SYSTEM\CurrentControlSet\Services\postgresql-x64-16') then
  begin
    if FileExists(ExpandConstant('{src}\payload\postgresql-installer.exe')) then
    begin
      if MsgBox('PostgreSQL 16 was not detected. Install PostgreSQL now?', mbConfirmation, MB_YESNO) = IDYES then
      begin
        Exec(ExpandConstant('{src}\payload\postgresql-installer.exe'), '--mode unattended --superpassword postgres --servicename postgresql-x64-16', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
      end
      else
      begin
        MsgBox('PostgreSQL is required. Install PostgreSQL 16 manually, then re-run this installer.', mbError, MB_OK);
        Result := False;
        exit;
      end;
    end
    else
    begin
      MsgBox('PostgreSQL 16 service not found. Place postgresql-installer.exe in infra/windows/server-installer/payload/ or install PostgreSQL manually.', mbInformation, MB_OK);
    end;
  end;
  Result := True;
end;

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{#InstallRoot}\infra\windows\uninstall-webstudio-service.ps1"" -InstallRoot ""{#InstallRoot}"""; Flags: runhidden waituntilterminated
