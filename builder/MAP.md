## FILES

#### __init__.py

Package init.

#### __main__.py

`main()` — lets `builder` run as `python -m builder ...`; `_norm()` is a small path-normalization helper.

#### _backend.py

The actual PEP 517 hook module (`build_wheel`/`build_sdist`/`get_requires_for_build_wheel`/`get_requires_for_build_sdist`). Supports `pip install . --config-settings cythonize=false` for a fast uncompiled dev build (ships plain `.py` for the auto-discovered modules; `bvh.pyx`/`culling.pyx` always compile, no fallback). `pyproject.toml` points `build-backend` here. This is the final stop in three build-system iterations — (1) install-then-mutate site-packages (original, fragile) → (2) `setup.py` + `setuptools.build_meta` via `pip install .` → (3) this fully custom PEP 517 backend — because setuptools was fragile and getting worse release over release, and the actual need (uniform compile flags across ~475 auto-discovered modules + 2 hand-written `.pyx` files) never needed setuptools' generality. `setup.py`/`MANIFEST.in` are gone entirely; `[build-system] requires` in `pyproject.toml` is Cython, numpy, wheel, packaging, pyMSVC (Windows only) — no setuptools, no pyinstaller.

#### build.py

`build_dependency_installer()`, `build_installer()` — the PyInstaller onedir build driver. `_clean_dist(app_dir)` strips stub `.py`/`.pyi`/`.pyc` files, dead/unreferenced resources, and empty directories from the onedir output after the post-build rename (HD→harness_designer), before installer packaging — it exists because the onedir output contained material that was getting compressed into the installer unnecessarily. Don't confuse this with `prune_dist.py`'s separate, more aggressive pass. `build_dependency_installer()` is a no-op on Linux (prints a message and returns) — Linux has no separate installer process any more, see `builder/scripts/bootstrap.py`; on Windows/macOS it also now bundles `harness_designer/licenses/{LGPLv3,GPLv3,Qt-Commercial-Reference}.txt` into `dep_installer`'s `--onefile` payload via `--add-data`, for its new `--phase pre` license screen.

#### build_native_deps.py

Builds `assimp` from source (CMake/Ninja against the `libs/assimp` submodule), pip-installs PyAssimp's bindings from that submodule path with `--no-build-isolation`, then manually copies the built assimp shared libraries into wherever pip installed pyassimp. This is a known stopgap: upstream pyassimp doesn't publish to PyPI and isn't cleanly separated from assimp; the plan is to package/publish a custom pyassimp to PyPI using the same PEP-517-backend playbook as this directory. The only reason setuptools is still installed anywhere in this project's CI is that upstream `libs/assimp/port/PyAssimp/setup.py` is genuinely `distutils`-dependent (works today only because setuptools ≥60.x vendors distutils via a shim). Once PyAssimp ships its own build, expect setuptools to be removable from CI and this file's CMake/Ninja vendoring step to collapse to a plain `pip install`.

#### collect_modules.py

`get_modules()` resolves which third-party distributions' import names need bundling into the PyInstaller build (`_distribution_to_import_names`, `_walk_distributions`, `_resolve_import_names`); `get_test_excludes()` keeps test trees out of the frozen app.

#### collect_stdlib.py

`get_modules()` — the stdlib-module counterpart to `collect_modules.py`, resolving which stdlib modules need bundling.

#### compiler.py

Per-platform compile/link. POSIX flags come from `sysconfig.get_config_var`; Windows is a hardcoded flag list (no sysconfig equivalent) validated against real captured compile/link command lines from CI on all three platforms. Compilation is parallelized across `os.cpu_count()` threads via `ThreadPoolExecutor` calling `spawn.py`. If the build breaks, this file's recipes are the most likely fragile point (hand-maintained, not setuptools-maintained) — check against a fresh captured CI log before assuming flags are still correct, especially after a Python version bump or a Windows Python installer layout change.

#### cython_build.py

Pure file discovery (`discover_modules()` — walks for plain `.py` modules to cythonize, no `setuptools.Extension`) + `cythonize_to_c()`. `cythonize_to_c()` silently no-ops for absolute source paths — `Cython.Build.cythonize` warns and writes the `.c` next to the source instead of into `build_dir` if given an absolute path; paths must be relative to cwd, and cwd must be the repo root, for the `build_dir` redirect to actually work (`discover_modules()` returns repo-root-relative paths specifically because of this). Also owns `_HAND_WRITTEN_EXTENSIONS` (every hand-written `.pyx` that isn't auto-discovered — **registering a new one here is not automatic and easy to forget**: `discover_modules()` only auto-walks plain `.py` files, so an unregistered hand-written `.pyx` is invisible to the packaged wheel build, and `wheel_build.py`'s `_stage_assets` even explicitly skips copying `.pyx` sources as plain assets. `wire_routing/astar.pyx` was found missing from this list on 2026-09-30 — since the locally-compiled `.pyd` is gitignored, every from-scratch/CI wheel build had been silently shipping with no compiled `astar` extension at all, falling back to the slow pure-Python reference in production. Whenever a new `.pyx` is written, add it to `_HAND_WRITTEN_EXTENSIONS` in the same change, not as a follow-up) and `_SKIP_STEMS` (files that stay plain Python even under a full build, e.g. `__init__.py`/`__main__.py`).

#### installer.py

`build_windows`/`build_macos`/`build_linux`/`build_deb` — per-platform installer packaging (Inno Setup on Windows via `_find_iscc`, codesigning on macOS, `.deb`/shell installer assembly on Linux); `_check_build_outputs()` validates the onedir build exists first (skips requiring a `dep_installer` binary on Linux, which doesn't build one). `build_deb()`'s `_PREINST_SH` is a plain-text (no GUI, Debian-policy-compliant) check that the app isn't currently running, run before `dpkg` unpacks the new files; `_LAUNCHER_SH` is a plain `exec` launcher (PySide6 installs itself from inside the main app now, see `builder/scripts/bootstrap.py`, not a separate first-launch wrapper).

#### msvc_env.py

Wraps `pyMSVC.setup_environment()` — populates `INCLUDE`/`LIB` so `cl.exe`/`link.exe` auto-search the right paths; `compiler.py` deliberately does not re-specify MSVC/Windows-SDK paths itself.

#### prepare_installer_assets.py

`build_ico`/`build_header_bmp`/`build_wizard_panel_bmp`/`prepare_all` — generates the installer's icon/banner image assets from source art.

#### prune_dist.py

`prune_dist(app_dir)` / `is_protected_path` — a second, more aggressive dist-pruning pass distinct from `build.py`'s `_clean_dist`.

#### spawn.py

`spawn(cmd)` — the actual subprocess invocation `compiler.py` farms out across threads; confirmed thread-safe.

#### version_info.txt

Static Windows version-resource data consumed by the PyInstaller build (not Python source).

#### wheel_build.py

Orchestration: reads `[project]` from `pyproject.toml` (`tomllib`/`tomli`), stages a build dir (copies `__init__.py`/`__main__.py` + non-source assets, replacing `MANIFEST.in`'s old job), cythonizes + compiles, hand-writes `METADATA`/`WHEEL`, hands the staged tree to `wheel.wheelfile.WheelFile.write_files()` (auto-computes `RECORD` with sha256 hashes).

## FOLDERS

#### scripts/

Small standalone scripts bundled *into* the frozen app (not build-time tooling) — see `scripts/MAP.md`.

## DESIGN NOTES

Lasting rules and design notes moved here from the repo-root `MEMORY.md` on 2026-11-01 and trimmed the
same day: bug-fix narratives were dropped (git history has them), keeping only what still constrains
the code. Point-in-time -- verify claims against the current code before relying on them.



#### Build system: custom PEP 517 backend, no setuptools
The build went through three iterations (install-then-mutate site-packages; `setup.py` + `setuptools.build_meta`; final: a fully custom PEP 517 backend) because setuptools is fragile and the real need (uniform flags across ~475 auto-discovered `.py` modules + 2 hand-written `.pyx`) doesn't need its generality. `pyproject.toml`: `build-backend = "builder._backend"`, `backend-path = ["."]`, `[build-system] requires` = Cython, numpy, wheel, packaging, pyMSVC (Windows only). CI only calls `pip install .`.
- `compiler.py`: per-platform compile/link. POSIX flags come from `sysconfig.get_config_var`; Windows is a hardcoded list (`/c /nologo /O2 /W3 /GL /DNDEBUG /MD` to compile; `/DLL /INCREMENTAL:NO /LTCG /LIBPATH:<py>\libs /EXPORT:PyInit_<name> /IMPLIB:<redirected>` to link), validated against captured CI command lines on all three platforms. MSVC/SDK paths come from `INCLUDE`/`LIB` set by `pyMSVC.setup_environment()` (via `msvc_env.py`). Compiles are parallel (`ThreadPoolExecutor` over `spawn.py`; thread-safe).
- `cython_build.py`: file discovery (`discover_modules()`) + `cythonize_to_c()`. **Gotcha:** `Cython.Build.cythonize(paths, build_dir=...)` silently ignores `build_dir` for absolute source paths (warns, writes `.c` beside the source), so paths must be repo-root-relative with cwd at the repo root.
- `wheel_build.py`: reads `[project]` via `tomllib`/`tomli`, stages a build dir (`__init__.py`/`__main__.py` + non-source assets, replacing `MANIFEST.in`), cythonizes + compiles, hand-writes `METADATA`/`WHEEL`, and lets `wheel.wheelfile.WheelFile.write_files()` compute RECORD.
- `_backend.py`: the hooks (`build_wheel`/`build_sdist`/`get_requires_for_build_*`). `pip install . --config-settings cythonize=false` gives a fast uncompiled dev build (plain `.py`; `bvh.pyx` and the culling `.pyx` always compile, no fallback).
- If the build breaks, `compiler.py`'s hand-maintained recipes are the likeliest fragile point: compare with a fresh captured CI log, especially after a Python version bump or a Windows Python installer layout change.

#### PyAssimp PyPI initiative (plan)
Upstream pyassimp does not publish to PyPI. Stopgap: `builder/build_native_deps.py` builds assimp from the `libs/assimp` submodule with CMake/Ninja, pip-installs the bindings from that path with `--no-build-isolation` and copies the shared libraries next to them. setuptools is still in CI only because upstream `port/PyAssimp/setup.py` does `from distutils.core import setup` (works via setuptools' vendored distutils shim). Plan: the user publishes their own pyassimp with a custom PEP 517 backend following `builder/_backend.py`/`wheel_build.py`; then remove setuptools from all three CI workflows' "Install build tools" step and expect `build_native_deps.py` to shrink to a plain `pip install`.

#### PyInstaller `--collect-all`/`collect_submodules` silently drops a subtree on ANY import-time exception (found 2026-10-19; pyinstaller/pyinstaller#9495, filed-and-closed-not-planned)
The installed app was missing most of `harness_designer/ui/` (toolbar, docks, system_menu...) with only a bare `ImportError: cannot import name 'toolbar'`. Cause: the app is almost entirely compiled `.pyd` (everything but `__init__.py`/`__main__.py`, see `cython_build.py`'s `_SKIP_STEMS`), and modulegraph cannot see inside a `.pyd`, so `--collect-all=harness_designer` is the ONLY thing that discovers the internal import graph. `collect_submodules()` really `__import__`s every subpackage; on ANY `Exception` (not just `ImportError`) the default `on_error='warn once'` logs one warning for the whole build, then ignores all later failures, and a failed subpackage is dropped whole with its children. So any import-time bug anywhere under `harness_designer` can silently remove an unrelated subpackage with no build-time signal. The trigger this time was the `claude` -> `claude_ai` rename leaving broken imports in `ui/editor_script/`, `scraping/` and `claude_ai/`. The robust rule: every subpackage must be importable standalone.
Pre-flight check to run (with the build env's Python) before packaging; it reports every broken subpackage with its traceback in one pass, unlike PyInstaller:
```python
import sys, pkgutil, traceback
import harness_designer
fails = []
for info in pkgutil.walk_packages(harness_designer.__path__, 'harness_designer.',
                                   onerror=lambda n: fails.append((n, sys.exc_info()))):
    pass
for name, exc in fails:
    traceback.print_exception(*exc, limit=3)
```
`builder/` has no such check yet; adding it to `build.py` as a fail-loud pre-flight step is still open.
