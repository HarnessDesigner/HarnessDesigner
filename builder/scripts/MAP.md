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
