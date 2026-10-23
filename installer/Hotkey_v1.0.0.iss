; HotKey 1.0.0 installer
; Build the application first:
;   .\.venv\Scripts\pyinstaller.exe --noconfirm HotKey.spec
; Then compile:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\Hotkey_v1.0.0.iss

#define MyAppName "HotKey"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Surile"
#define MyAppURL "http://www.github.com/qiuxile/hotkey"
#define MyAppExeName "HotKey.exe"

[Setup]
AppId={{B7F4E6E4-3C2A-4D8B-9A61-8F2C1D7E5A93}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright=Copyright (C) 2026 {#MyAppPublisher}
DefaultDirName={autopf}\HotKey
DefaultGroupName=HotKey
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=Hotkey_v1.0.0_Setup
SetupIconFile=..\assets\hotkey.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} {#MyAppVersion} installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoVersion=1.0.0.0
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "..\dist\HotKey\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\HotKey"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\HotKey"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch HotKey"; Flags: nowait postinstall skipifsilent
