## FILES

#### bootstrap.py

`install(package, import_name=None)` / `run()` — installs a missing dependency at runtime if it isn't importable (`_is_importable`), resolving the frozen app's own bundled Python (`_python_exe`, `_lib_dir`). `run()` calls `_run_pyside6_install_ui()` when PySide6 isn't importable — on Linux this is the *only* place PySide6 ever gets installed (no separate install-time step there any more, see `builder/installer.py`'s `build_deb()`/`build_linux()` and `installer_scripts/linux/install.sh`). `_run_pyside6_install_ui()` shows `license_screen.py`'s PySide6 Accept/Cancel screen, and on Accept, **in the same Tk root/window** (not a second dialog), swaps it for an indeterminate progress bar and runs `install('PySide6')` in a background thread; Cancel exits the app before anything is installed. Same pattern as `dep_installer.py`'s `--phase install`.

#### dep_installer.py

Windows/macOS only (built by `builder/build.py`'s `build_dependency_installer()`, which is a no-op on Linux). `main()` dispatches on `--phase`: `--phase pre <app_dir>` runs *before* any new files are copied — a running-process check (Retry/Cancel) and an already-installed check (prompt + optional backup via a `tkinter.filedialog` destination picker, zipped with stdlib `zipfile`, then removal of the old install — the real Inno uninstaller with `/NODATAPROMPT` on Windows, `shutil.rmtree` on macOS). It deliberately does **not** show the PySide6 license — that's `--phase install <target_dir>` (default): the license Accept/Cancel screen (`license_screen.build_license_screen`) first, then **the same window** swaps to the `_install_all`/`_build_progress_screen` pip-install progress UI on Accept. One dialog for the whole PySide6 install, not two — license-then-install in the same invocation; the pre-copy checks are a separate, earlier invocation since they must run before `[Files]`/the payload copy, which the license/install step cannot (see `installer_scripts/windows/harness_designer.iss`'s `CurStepChanged(ssPostInstall)` and macOS's `postinstall`, which both now also handle Cancel **after** files are already copied by removing them). Cancel at any point exits 3 (`EXIT_CANCELLED`), distinct from argparse's own usage-error exit 2. Window title is always `PySide6 Installation`.

#### license_screen.py

Shared by `dep_installer.py` (Windows/macOS) and `bootstrap.py` (Linux) so the PySide6/Qt license Accept/Cancel screen reads the same everywhere. `license_text(licenses_dir)` builds the combined LGPLv3/GPLv3/commercial-reference notice (mirrors `harness_designer/ui/dialogs/about_dialog.py`'s `_qt_license_text()`, kept independent since this module must not import the `harness_designer` package); `build_license_screen(root, licenses_dir, on_accept, on_cancel)` builds the Tk frame; `resolve_licenses_dir(bundled_subdir='')` locates the bundled `.txt` files — at the `sys._MEIPASS` root for `dep_installer`'s own `--add-data` bundling, under `harness_designer/licenses` for the main app's `--collect-all` bundling (pass `bundled_subdir='harness_designer/licenses'`).

#### rthook_pip_distlib.py

A PyInstaller runtime hook — `_FileSystemFinder`/`_Resource`/`_patched_finder` patch `pip`'s vendored `distlib` resource-finder so it can find its data files inside the frozen app's layout instead of a normal installed package's. This is the file behind the "new file callout" rule referenced throughout MEMORY.md: it was created locally but never `git add`-ed, which caused a real CI failure when the user committed and pushed without realizing it had been left out. Any new file created by an editing tool must be staged with `git add <path>` immediately after creation, not as a follow-up at the end of a session.

#### run.py

The frozen app's real entry point / excepthook (`_excepthook`) — what actually launches `harness_designer.app.App` inside the PyInstaller onedir build.

## DESIGN NOTES

Lasting rules and design notes moved here from the repo-root `MEMORY.md` on 2026-11-01 and trimmed the
same day: bug-fix narratives were dropped (git history has them), keeping only what still constrains
the code. Point-in-time -- verify claims against the current code before relying on them.



#### run.py makes the faulthandler crash log in the main process only (user, 2026-10-23)
`_enable_native_crash_log()` runs only when `_is_main_process()`; workers get no faulthandler log (a native crash in the model/image worker leaves no traceback of its own). Before, every `spawn`ed worker enabled it and each opened its own `crash_*.log`, which a killed run leaves behind empty. Gotcha: `multiprocessing.parent_process()` is still `None` while a spawned child imports the main module (it is set later, in `_bootstrap`), so the test is `current_process().name == 'MainProcess'` (source runs: spawn sets the name before re-running the file) plus `not multiprocessing.spawn.is_forking(sys.argv)` (frozen workers still say `MainProcess` but carry `--multiprocessing-fork`). Verified with a real two-worker spawn; the frozen path is untested.

#### Installer: dep_installer installs into a temp folder, then xcopy into {app} (found and fixed 2026-10-19)
Fresh Windows installs hit `ImportError: cannot import name QtWidgets` in `utils/ui_utils.py` on first launch: the directories written by `dep_installer.exe` (`pip install --target {app} --force-reinstall`: `PySide6\`, `shiboken6\`, and the then-runtime-installed `amdsmi\`, `nvidia_ml_py-*.dist-info\`) came out with an unreadable ACL (owner `BUILTIN\Administrators`, no DACL readable, no `BUILTIN\Users` access), while everything copied by Inno Setup's `[Files]` (e.g. `numpy\`) was fine. Not an AV action; "runs elevated" alone does not explain it and the exact mechanism inside pip's install path was never root-caused (an unchased lead: pip spawns subprocesses, which is why `bootstrap.py`/`dep_installer.py` swap `sys.executable` to the bundled `python.exe`).
**Fix (user's idea): route around it.** `dep_installer.exe` installs into a disposable `{tmp}\deps` (`GetDepInstallerParams` in `installer_scripts/windows/harness_designer.iss`) and a `[Run]` step `xcopy "{tmp}\deps" "{app}\" /E /H /Y /I` copies it in the ordinary way, so the files inherit `{app}`'s ACL (xcopy does not copy source ACLs). `dep_installer.py` itself just takes a `target_dir`. Confirmed fixed by the user.
**GPU packages:** `nvapi` and `pyamd_adl` (ctypes wrappers that only `dlopen` the driver on first use) replaced `nvidia-ml-py`/`amdsmi` and are ordinary BUNDLED dependencies, not runtime-installed. `apple_smi` (macOS) is the only GPU-monitoring package excluded from the bundle and installed by `dep_installer.py`, because compiled extensions that probe for the driver eagerly at import fail on a CI machine with no GPU driver. The user went back and forth on this twice; do not revert it to the runtime-install pattern. `dep_installer.py`'s `REQUIRED_PACKAGES`, `builder/build.py`'s exclude list / `_RUNTIME_ONLY_PREFIXES`, `builder/collect_modules.py`'s `_EXCLUDED_DISTRIBUTIONS` and the CI workflows (`windows.yml`, `unix.yml`) still named the old packages when this was written, so check them against the final state above.
