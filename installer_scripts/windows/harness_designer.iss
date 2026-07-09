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

Name: "mysqlconnector"; \
    Description: "MySQL Connector/Python (required for shared multi-seat installations using a MySQL database)"; \
    GroupDescription: "Optional Components:"; \
    Flags: unchecked

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
; installer.exe opens its own window (progress bar only — component choice is
; now made via the mysqlconnector task above) and must finish before InnoSetup
; continues to the Finish page.
Filename: "{tmp}\dep_installer.exe"; \
    Parameters: "{code:GetDepInstallerParams}"; \
    StatusMsg: "Installing required components (PySide6)..."; \
    Flags: waituntilterminated

[UninstallDelete]
; dep_installer.exe pip-installs PySide6/GPU packages directly into {app},
; so Inno's uninstaller (which only tracks files it copied via [Files]) can't
; remove them on its own and leaves a non-empty, undeleted directory behind.
; No user data ever lives under {app}, so it's always safe to wipe it whole.
Type: filesandordirs; Name: "{app}"

[Code]
function GetDepInstallerParams(Param: String): String;
begin
  Result := '"' + ExpandConstant('{app}') + '"';
  if IsTaskSelected('mysqlconnector') then
    Result := Result + ' --with-mysql';
end;

// ── Uninstall: optionally preserve the user's database/parts library/projects ──

var
  KeepUserData: Boolean;

function InitializeUninstall(): Boolean;
begin
  KeepUserData := (MsgBox(
    'Do you want to keep your Harness Designer database, parts library, ' +
    'downloaded CAD/model files, and saved projects?' + #13#10 + #13#10 +
    'Choose Yes to keep this data (recommended) in case you reinstall later, ' +
    'or No to permanently delete it now.',
    mbConfirmation, MB_YESNO or MB_DEFBUTTON1) = IDYES);
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and not KeepUserData then
    DelTree(ExpandConstant('{userappdata}\HarnessDesigner'), True, True, True);
end;

// ── Install: reflect the real on-disk footprint (main app + pip-installed
// components) in Add/Remove Programs, instead of Inno's [Files]-only estimate ──

function GetDirSizeBytes(Path: String): Int64;
var
  FindRec: TFindRec;
  Size: Int64;
  FullPath: String;
begin
  Size := 0;
  if FindFirst(Path + '\*', FindRec) then
  begin
    try
      repeat
        if (FindRec.Name <> '.') and (FindRec.Name <> '..') then
        begin
          FullPath := Path + '\' + FindRec.Name;
          if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
            Size := Size + GetDirSizeBytes(FullPath)
          else
            Size := Size + (Int64(FindRec.SizeHigh) shl 32) + FindRec.SizeLow;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
  Result := Size;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  // ssDone fires after the [Run] entries (dep_installer.exe) have finished,
  // so this sees the final size including everything pip installed into {app}.
  if CurStep = ssDone then
    RegWriteDWordValue(HKLM,
      'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1',
      'EstimatedSize', GetDirSizeBytes(ExpandConstant('{app}')) div 1024);
end;
