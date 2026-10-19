## FILES

#### __init__.py

Package init.

#### __main__.py

`main()` — lets `builder` run as `python -m builder ...`; `_norm()` is a small path-normalization helper.

#### _backend.py

The actual PEP 517 hook module (`build_wheel`/`build_sdist`/`get_requires_for_build_wheel`/`get_requires_for_build_sdist`). Supports `pip install . --config-settings cythonize=false` for a fast uncompiled dev build (ships plain `.py` for the auto-discovered modules; `bvh.pyx`/`culling.pyx` always compile, no fallback). `pyproject.toml` points `build-backend` here. This is the final stop in three build-system iterations — (1) install-then-mutate site-packages (original, fragile) → (2) `setup.py` + `setuptools.build_meta` via `pip install .` → (3) this fully custom PEP 517 backend — because setuptools was fragile and getting worse release over release, and the actual need (uniform compile flags across ~475 auto-discovered modules + 2 hand-written `.pyx` files) never needed setuptools' generality. `setup.py`/`MANIFEST.in` are gone entirely; `[build-system] requires` in `pyproject.toml` is Cython, numpy, wheel, packaging, pyMSVC (Windows only) — no setuptools, no pyinstaller.

#### build.py

`build_dependency_installer()`, `build_installer()` — the PyInstaller onedir build driver. `_clean_dist(app_dir)` strips stub `.py`/`.pyi`/`.pyc` files, dead/unreferenced resources, and empty directories from the onedir output after the post-build rename (HD→harness_designer), before installer packaging — it exists because the onedir output contained material that was getting compressed into the installer unnecessarily. Don't confuse this with `prune_dist.py`'s separate, more aggressive pass.

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

`build_windows`/`build_macos`/`build_linux` — per-platform installer packaging (Inno Setup on Windows via `_find_iscc`, codesigning on macOS, `.deb`/shell installer assembly on Linux); `_check_build_outputs()` validates the onedir build exists first.

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
