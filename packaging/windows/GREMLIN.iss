#define MyAppName "GREMLIN AI Research Orchestrator"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Adrian Lipa / Intention Lab"
#define MyAppExeName "gremlin-control-center.exe"

[Setup]
AppId={{F39F4C32-A5C5-4C74-AB31-A1981432C9EF}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\GREMLIN
DefaultGroupName=GREMLIN
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
OutputDir=..\..\dist\installer
OutputBaseFilename=GREMLIN-Setup-{#MyAppVersion}-x64
UninstallDisplayIcon={app}\{#MyAppExeName}
ChangesEnvironment=no

[Files]
Source: "..\..\dist\windows\runtime\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\dist\windows\control-center\gremlin-control-center.exe"; DestDir: "{app}"; DestName: "gremlin-control-center.exe"; Flags: ignoreversion
Source: "..\..\dist\windows\resources\*"; DestDir: "{app}\resources"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\GREMLIN Control Center"; Filename: "{app}\gremlin-control-center.exe"
Name: "{userdesktop}\GREMLIN"; Filename: "{app}\gremlin-control-center.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\gremlinctl.exe"; Parameters: "init --json"; WorkingDir: "{app}"; Flags: runhidden waituntilterminated; StatusMsg: "Initializing GREMLIN user configuration..."
Filename: "{app}\gremlin-control-center.exe"; Description: "Launch GREMLIN Control Center"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Program files are removed by the uninstaller. User configuration/state intentionally remains.
Type: filesandordirs; Name: "{app}"
