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
WizardImageFile={#AssetsDir}\wizard_panel.bmp
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
; Main application
Source: "{#AppSrcDir}\*"; \
    DestDir: "{app}"; \
    Flags: recursesubdirs createallsubdirs ignoreversion

; Component installer — runs after main files are in place, deleted from temp afterwards
Source: "{#InstallerSrc}"; \
    DestDir: "{tmp}"; \
    Flags: deleteafterinstall

; Wizard header banner — extracted to temp on demand, never written to {app}
Source: "{#AssetsDir}\installer_header.bmp"; \
    DestDir: "{tmp}"; \
    Flags: dontcopy deleteafterinstall

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

[Code]

{ ── Windows API ────────────────────────────────────────────────────────────── }

function SendMessage(hWnd: HWND; Msg: Cardinal; wParam: Integer; lParam: Integer): Integer;
  external 'SendMessageW@user32.dll stdcall';

{ ── Constants ───────────────────────────────────────────────────────────────── }

const
  WM_VSCROLL = $0115;
  SB_BOTTOM  = 7;

{ ── Header banner ───────────────────────────────────────────────────────────── }

procedure InitializeWizard();
begin
  { Extract the pre-built BMP from the installer archive to the temp directory }
  ExtractTemporaryFile('installer_header.bmp');

  { Expand WizardBitmapImage2 (the wizard small image, top-right on inner pages)
    to span the full header width.  PageNameLabel and PageDescriptionLabel were
    created after WizardBitmapImage2, so they have a higher z-order and render
    on top of the banner automatically. }
  WizardForm.WizardBitmapImage2.Left    := 0;
  WizardForm.WizardBitmapImage2.Top     := 0;
  WizardForm.WizardBitmapImage2.Width   := WizardForm.ClientWidth;
  WizardForm.WizardBitmapImage2.Stretch := True;
  WizardForm.WizardBitmapImage2.Bitmap.LoadFromFile(
    ExpandConstant('{tmp}\installer_header.bmp'));

  { Make the header text legible against the dark cable-photo banner }
  WizardForm.PageNameLabel.Font.Color        := clWhite;
  WizardForm.PageDescriptionLabel.Font.Color := $00DDDDDD;
end;
