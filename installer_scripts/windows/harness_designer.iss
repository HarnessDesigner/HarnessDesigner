; Harness Designer — Inno Setup installer script
; © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
;
; Prerequisites:
;   - Build the app:        python -m builder (produces builder\scripts\dist\harness_designer\)
;   - Build the installer:  build_dependency_installer() (produces builder\scripts\dist\installer\)
;   - Convert icon:         harness_designer\image\icon_256x256.png → icon_256x256.ico
;                           (use ImageMagick: magick icon_256x256.png icon_256x256.ico)
;   - Inno Setup 6+:        https://jrsoftware.org/isinfo.php
;
; To compile: open this file in the Inno Setup IDE and press F9, or run:
;   iscc harness_designer.iss

#define AppName      "Harness Designer"
#define AppVersion   "1.0.0"
#define AppPublisher "Kevin G. Schlosser"
#define AppURL       "https://github.com/HarnessDesigner/HarnessDesigner"
#define AppExeName   "harness_designer.exe"

; Generate a fresh GUID via Tools > Generate GUID in the Inno Setup IDE.
; Never reuse this GUID for a different application.
#define AppId "{{REPLACE-WITH-GENERATED-GUID}"

; Source paths relative to this .iss file (installer_scripts/windows/)
#define AppSrcDir    "..\..\builder\scripts\dist\harness_designer"
#define InstallerSrc "..\..\builder\scripts\dist\installer\installer.exe"
#define IconFile     "..\..\harness_designer\image\icon_256x256.ico"
#define LicenseFile  "..\..\LICENSE"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\HarnessDesigner
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile={#LicenseFile}
OutputDir=..\..\dist\windows
OutputBaseFilename=harness_designer_setup_{#AppVersion}
SetupIconFile={#IconFile}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
MinVersion=10.0
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; \
    Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Main application — all files from the PyInstaller onedir build
Source: "{#AppSrcDir}\*"; \
    DestDir: "{app}"; \
    Flags: recursesubdirs createallsubdirs ignoreversion

; Dependency installer — extracted to temp, runs during setup, then deleted
Source: "{#InstallerSrc}"; \
    DestDir: "{tmp}"; \
    Flags: deleteafterinstall

[Icons]
Name: "{group}\{#AppName}";             Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}";   Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";     Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Run the dependency installer after files are copied.
; Passes the lib\ directory inside the install folder as the target.
; The installer GUI lets the user choose optional components (e.g. MySQL support).
Filename: "{tmp}\installer.exe"; \
    Parameters: """{app}"""; \
    StatusMsg: "Installing required components..."; \
    Flags: waituntilterminated
