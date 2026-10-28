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
; Shown on the wizard's License page with an "I accept" radio button. Inno shows
; it as plain text (or RTF), so keep the repo-root LICENSE plain text. The macOS
; and Linux installers read this same file; see build_pkg.sh and install.sh.
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

; Component installer — never auto-extracted by Inno; PrepareToInstall (see
; [Code] below) calls ExtractTemporaryFile on demand so it can run --phase
; pre BEFORE [Files] extraction begins. Once extracted it stays in {tmp} for
; the rest of Setup, so the later [Run] entry (--phase install) reuses the
; same extracted copy.
Source: "{#InstallerSrc}"; \
    DestDir: "{tmp}"; \
    Flags: dontcopy

[Icons]
Name: "{group}\{#AppName}";             Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}";   Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";     Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; dep_installer.exe (PySide6 license + install) and the xcopy step that
; follows it used to be declarative [Run] entries here, but that made it
; impossible to react to the user cancelling at the license screen -- a
; [Run] entry can't be inspected afterward. They're now Exec() calls from
; CurStepChanged(ssPostInstall) in [Code] below instead, at the same point
; in the install sequence (ssPostInstall is when [Run] entries fire anyway).
;
; Offer to launch the app from the Finish page, checked by default.
Filename: "{app}\{#AppExeName}"; \
    Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; dep_installer.exe pip-installs PySide6/GPU packages directly into {app},
; so Inno's uninstaller (which only tracks files it copied via [Files]) can't
; remove them on its own and leaves a non-empty, undeleted directory behind.
; No user data ever lives under {app}, so it's always safe to wipe it whole.
Type: filesandordirs; Name: "{app}"

[Code]
function GetDepInstallerParams(Param: String): String;
begin
  // Installs into a scratch temp folder, not {app} directly -- see the
  // [Run] section's comments for why. The xcopy step right after this one
  // moves the result into {app} for real.
  Result := '--phase install "' + ExpandConstant('{tmp}\deps') + '"';
  if IsTaskSelected('mysqlconnector') then
    Result := Result + ' --with-mysql';
end;

// ── Pre-install checks: dep_installer.exe --phase pre ──
// Runs right after "Install" is clicked, before [Files] extraction begins
// (Inno's dedicated hook for exactly this -- "run a check, optionally abort
// with a message, before anything is written"). Handles, in order: is the
// app currently running (Retry/Cancel), and is a previous installation
// already present (prompt + optional backup + removal via the real
// uninstaller -- see /NODATAPROMPT below). The PySide6/Qt license itself is
// NOT shown here -- see CurStepChanged(ssPostInstall) below, which shows it
// in the same dialog as the actual PySide6 install, not a separate one
// ahead of it. See builder/scripts/dep_installer.py.
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  DepInstallerPath: String;
begin
  Result := '';

  ExtractTemporaryFile('dep_installer.exe');
  DepInstallerPath := ExpandConstant('{tmp}\dep_installer.exe');

  if not Exec(DepInstallerPath, '--phase pre "' + ExpandConstant('{app}') + '"',
              '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
  begin
    Result := 'Failed to launch the PySide6 installer.';
    exit;
  end;

  if ResultCode = 3 then
    Result := 'Setup was cancelled.'
  else if ResultCode <> 0 then
    Result := 'The PySide6 installer reported an error (code ' +
      IntToStr(ResultCode) + ').';
end;

// ── Uninstall: optionally preserve the user's database/parts library/projects ──

var
  KeepUserData: Boolean;

// /NODATAPROMPT -- skip the keep-data prompt below and always keep the data,
// for scripted/silent uninstalls. Also what Phase A (PrepareToInstall, via
// dep_installer.exe --phase pre) passes when it runs this same uninstaller
// non-interactively to remove an old version during an upgrade -- an
// upgrade must never delete user data, prompt or no prompt.
function HasNoDataPromptSwitch(): Boolean;
var
  i: Integer;
begin
  Result := False;
  for i := 1 to ParamCount do
    if CompareText(ParamStr(i), '/NODATAPROMPT') = 0 then
    begin
      Result := True;
      exit;
    end;
end;

function InitializeUninstall(): Boolean;
begin
  if HasNoDataPromptSwitch() then
    KeepUserData := True
  else
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

// ── PySide6 license + install: dep_installer.exe --phase install ──
// Runs at ssPostInstall (the same point a declarative [Run] entry would
// have fired, right after [Files] extraction finishes) rather than as a
// [Run] entry, specifically so the result can be inspected: dep_installer
// shows the PySide6 license Accept/Cancel screen and, on Accept, the
// install progress -- one dialog, not two -- and Cancel here means the
// user declined after the new version's files were already copied, so
// this removes what was just installed rather than leaving a broken,
// PySide6-less app behind.
procedure RunDepInstallerPostFiles();
var
  ResultCode: Integer;
begin
  if not Exec(ExpandConstant('{tmp}\dep_installer.exe'), GetDepInstallerParams(''),
              '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
  begin
    MsgBox('Failed to launch the PySide6 installer.', mbCriticalError, MB_OK);
    DelTree(ExpandConstant('{app}'), True, True, True);
    Abort();
  end;

  if ResultCode = 3 then
  begin
    MsgBox('Setup was cancelled. The application has been removed.',
      mbInformation, MB_OK);
    DelTree(ExpandConstant('{app}'), True, True, True);
    Abort();
  end
  else if ResultCode <> 0 then
  begin
    MsgBox('The PySide6 installer reported an error (code ' +
      IntToStr(ResultCode) + ').', mbCriticalError, MB_OK);
    DelTree(ExpandConstant('{app}'), True, True, True);
    Abort();
  end;

  // pip's own --target install of PySide6/shiboken6/amdsmi/pynvml directly
  // into {app} was observed (2026-10-19) to leave those specific
  // directories with a broken ACL -- no BUILTIN\Users read access at all,
  // unlike every other file in {app}, which this installer's own [Files]
  // section placed and which all correctly inherit {app}'s normal
  // permissions. The cause was never fully root-caused (not an AV
  // quarantine -- Defender's logs were clean -- and not simply "pip ran
  // elevated", since NTFS inheritance doesn't depend on the creating
  // process's elevation). Rather than patch pip's behavior, sidestep it:
  // dep_installer.exe installs into a disposable {tmp}\deps scratch folder
  // instead (see GetDepInstallerParams), and this step copies the result
  // into {app} the same ordinary way every other file got there, which is
  // the one thing already proven to produce correct permissions. xcopy
  // does not copy source ACLs by default, so the copied files inherit
  // {app}'s ACL fresh, regardless of whatever pip left behind in
  // {tmp}\deps.
  if not Exec(ExpandConstant('{cmd}'),
              '/c xcopy "' + ExpandConstant('{tmp}\deps') + '" "' +
              ExpandConstant('{app}') + '\" /E /H /Y /I',
              '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    MsgBox('Failed to finish installing components.', mbCriticalError, MB_OK);
    Abort();
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    RunDepInstallerPostFiles();

  // ssDone fires after the above has finished, so this sees the final size
  // including everything pip installed into {app}.
  if CurStep = ssDone then
    RegWriteDWordValue(HKLM,
      'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1',
      'EstimatedSize', GetDirSizeBytes(ExpandConstant('{app}')) div 1024);
end;
