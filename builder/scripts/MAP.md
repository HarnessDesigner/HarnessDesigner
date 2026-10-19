## FILES

#### bootstrap.py

`install(package, import_name=None)` / `run()` — installs a missing dependency at runtime if it isn't importable (`_is_importable`), resolving the frozen app's own bundled Python (`_python_exe`, `_lib_dir`).

#### dep_installer.py

`_install_all(target_dir, packages, on_status, on_progress)` plus a small Tk-based (`_build_progress_screen`) progress UI — the user-facing dependency-install flow that `bootstrap.py`'s mechanism feeds into.

#### rthook_pip_distlib.py

A PyInstaller runtime hook — `_FileSystemFinder`/`_Resource`/`_patched_finder` patch `pip`'s vendored `distlib` resource-finder so it can find its data files inside the frozen app's layout instead of a normal installed package's. This is the file behind the "new file callout" rule referenced throughout MEMORY.md: it was created locally but never `git add`-ed, which caused a real CI failure when the user committed and pushed without realizing it had been left out. Any new file created by an editing tool must be staged with `git add <path>` immediately after creation, not as a follow-up at the end of a session.

#### run.py

The frozen app's real entry point / excepthook (`_excepthook`) — what actually launches `harness_designer.app.App` inside the PyInstaller onedir build.
