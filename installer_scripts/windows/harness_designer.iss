; Harness Designer — Inno Setup installer script
; © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
;
; Prerequisites (run in order before compiling):
;   1. python -m builder.prepare_installer_assets
;        Produces installer_scripts\windows\assets\:
;          harness_designer.ico, installer_header.bmp, wizard_panel.bmp
;   2. Build the main app and dependency installer:
;        build_installer(base_import)          → builder\scripts\dist\harness_designer\
;        build_dependency_installer()          → builder\scripts\dist\installer.exe
;   3. Inno Setup 6+: https://jrsoftware.org/isinfo.php
;
; To compile:
;   iscc installer_scripts\windows\harness_designer.iss
;   (or open in the Inno Setup IDE and press F9)

#define AppName      "Harness Designer"
#define AppVersion   "1.0.0"
#define AppPublisher "Kevin G. Schlosser"
#define AppURL       "https://github.com/HarnessDesigner/HarnessDesigner"
#define AppExeName   "HD.exe"

; Generate a fresh GUID via Tools > Generate GUID in the Inno Setup IDE.
; Never reuse this GUID for a different application.
#define AppId "{{55225F52-09E5-41B4-8DFA-4CCDB1114743}"

; Source paths relative to the repository root (two levels up from this file)
#define AppSrcDir    "..\..\builder\scripts\dist\harness_designer"
#define InstallerSrc "..\..\builder\scripts\dist\dep_installer.exe"
#define AssetsDir    "assets"
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
SetupIconFile={#AssetsDir}\harness_designer.ico
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

; Component installer — runs after main files are in place, deleted from temp afterwards
Source: "{#InstallerSrc}"; \
    DestDir: "{tmp}"; \
    Flags: deleteafterinstall

[Icons]
Name: "{group}\{#AppName}";             Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}";   Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";     Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Launch the component installer after the main application files are in place.
; installer.exe opens its own window (license → components → install log) and
; must be closed by the user before InnoSetup continues to the Finish page.
Filename: "{tmp}\dep_installer.exe"; \
    Parameters: """{app}"""; \
    StatusMsg: "Installing required components (PySide6)..."; \
    Flags: waituntilterminated
