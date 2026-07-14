; Inno Setup script for Dracula Adventure (Windows installer).
; Compiled in CI by iscc; PyInstaller must have produced dist\dracula.exe and
; dist\dracula-gui.exe first. Override the version from CI with:
;     iscc /DMyAppVersion=1.2.3 installer\windows\dracula.iss

#define MyAppName "Dracula Adventure"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "Gerwout van der Veen"
#define MyAppURL "https://github.com/gerwout/dracula-adventure"

[Setup]
; A stable AppId keeps upgrades/uninstall consistent across releases — do not change it.
AppId={{AFE31851-C05A-48B3-BDB8-10BE449533CC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\Dracula Adventure
DefaultGroupName=Dracula Adventure
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
UninstallDisplayIcon={app}\dracula-gui.exe
OutputDir=..\..\dist\installer
OutputBaseFilename=dracula-adventure-{#MyAppVersion}-setup
SetupIconFile=..\..\icon\vampire.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
; Per-machine install; requires admin (default). Both exes are self-contained.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\dist\dracula-gui.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\dracula.exe";     DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\README.md";            DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "..\..\LICENSE";              DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Dracula Adventure";              Filename: "{app}\dracula-gui.exe"
Name: "{group}\Dracula Adventure (terminal)";   Filename: "{app}\dracula.exe"
Name: "{group}\{cm:UninstallProgram,Dracula Adventure}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Dracula Adventure";        Filename: "{app}\dracula-gui.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\dracula-gui.exe"; Description: "{cm:LaunchProgram,Dracula Adventure}"; Flags: nowait postinstall skipifsilent
