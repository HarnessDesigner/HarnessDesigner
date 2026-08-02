# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Strip dependency-closet cruft that _clean_dist() doesn't know is dead.

_clean_dist() (see build.py) removes what PyInstaller's own --collect-all
data collection always produces (stray .py source copies, __pycache__,
etc.) — that part is generic to any PyInstaller build. This module instead
removes things that are dead *for this specific app*, based on an actual
audit of a built dist folder: whole test suites dragged in by --collect-all
(numpy/scipy/pandas/matplotlib/sympy/IPython/stdlib all ship their own
tests/ dirs as package-internal data), source formats no interpreter ever
reads at runtime (Fortran/Cython/link-time files left over from how these
packages compile their own extensions), and a handful of specific
files/dirs confirmed unused by grepping harness_designer's own source
(pandas is only ever used for plain DataFrame/read_csv, never .style/
Styler; pyopencl only ever loads harness_designer's own bvh_kernel.cl,
never pyopencl.clrandom/clmath).

Deliberately does NOT touch *.dist-info/ (kept as-is, on request) or
anything under harness_designer/ itself (this module only prunes
third-party dependency payload).
"""

import os
import shutil

# Directories with these basenames (case-insensitive) are a package's own
# test suite, never imported by the running app. Removed wholesale,
# wherever they appear in the tree, at any depth.
_TEST_DIR_NAMES = frozenset(['test', 'tests', 'testing', 'test-examples'])

# Extensions that only ever matter at compile/link time for the packages
# in this bundle (numpy/scipy Fortran + f2py + Cython + MSVC import-lib
# leftovers from --collect-all's data collection, sympy's ANTLR grammar
# source, keyring's shell-completion scripts, pip's license-text
# snippets) — never read by any interpreter or the OS loader at runtime.
_BUILD_ARTIFACT_EXTS = frozenset([
    '.f90', '.f', '.f95',    # numpy Fortran sources
    '.pyf',                  # f2py signature files
    '.pxd',                  # Cython declarations (cimport-time only)
    '.lib',                  # MSVC import libs (link-time, not loaded like a .dll)
    '.g4',                   # sympy's ANTLR grammar source; already compiled
                              # into Python parser code at sympy's release time
    '.bash', '.zsh',         # keyring's shell-completion scripts
    '.apache', '.bsd',       # pip's vendored license-text snippets
])

# app_dir-relative paths confirmed dead by checking harness_designer's own
# source, or redundant with something else already bundled. Each is
# removed as a whole subtree if it's a directory, or as a single file.
_EXPLICIT_PATHS = [
    # Jinja2 templates for pandas' DataFrame.style HTML/LaTeX export.
    # harness_designer only ever uses plain pd.DataFrame/pd.read_csv
    # (see logger/log_handler.py, ui/log_viewer/viewer.py) -- Styler is
    # never imported, so these templates are never read.
    os.path.join('pandas', 'io', 'formats', 'templates'),

    # pyopencl's own bundled OpenCL headers for its special-function/
    # random-number submodules (clmath, clrandom's Philox/Threefry).
    # harness_designer's ray_tracing/renderer.py only ever compiles its
    # own bvh_kernel.cl and never imports clmath/clrandom, so pyopencl
    # never #includes any of these.
    os.path.join('pyopencl', 'cl'),

    # dateutil's own compressed fallback copy of the IANA tz database --
    # only consulted if the separate tzdata package isn't installed.
    # tzdata *is* bundled (see tzdata/zoneinfo/), so this is a redundant
    # second copy of the same data dateutil never falls back to.
    os.path.join('dateutil', 'zoneinfo', 'dateutil-zoneinfo.tar.gz'),

    # ensurepip's bundled pip/setuptools wheels -- only consulted by
    # ensurepip.bootstrap() when no pip is already importable. pip is
    # already bundled directly (see build_installer()'s --collect-all=pip),
    # so this fallback path never runs.
    os.path.join('ensurepip', '_bundled'),

    # Single stray files with no distinguishing extension (so they can't
    # go in _BUILD_ARTIFACT_EXTS without also catching LICENSE files,
    # which are kept deliberately -- see _clean_dist).
    os.path.join('IPython', 'core', 'profile', 'README_STARTUP'),
    os.path.join('ctypes', 'macholib', 'fetch_macholib'),
]


def prune_dist(app_dir):
    """Remove dependency payload that is never read at runtime.

    Run this after _clean_dist() in the same build step, against the same
    PyInstaller onedir/.app output directory.

    :param app_dir: Path to the PyInstaller onedir (or .app Contents)
        directory to prune in place.
    """
    n_files = 0
    n_dirs = 0

    # Explicit single-purpose removals first, before the generic sweeps --
    # cheaper to remove pandas/io/formats/templates as one rmtree than to
    # let the test-dir/extension sweeps rediscover its contents piecemeal.
    for rel_path in _EXPLICIT_PATHS:
        full_path = os.path.join(app_dir, rel_path)
        if os.path.isdir(full_path):
            shutil.rmtree(full_path, ignore_errors=True)
            n_dirs += 1
        elif os.path.isfile(full_path):
            try:
                os.remove(full_path)
                n_files += 1
            except OSError:
                pass

    # Whole test-suite directories, at any depth. topdown=True + pruning
    # dirs in place so os.walk never wastes time descending into a
    # subtree that's about to be deleted anyway.
    for root, dirs, _files in os.walk(app_dir, topdown=True):
        keep = []
        for dname in dirs:
            if dname.lower() in _TEST_DIR_NAMES:
                shutil.rmtree(os.path.join(root, dname), ignore_errors=True)
                n_dirs += 1
            else:
                keep.append(dname)
        dirs[:] = keep

    # Build/link-time-only files by extension, wherever they still exist.
    for root, _dirs, files in os.walk(app_dir):
        for fname in files:
            if os.path.splitext(fname)[1].lower() in _BUILD_ARTIFACT_EXTS:
                try:
                    os.remove(os.path.join(root, fname))
                    n_files += 1
                except OSError:
                    pass

    # Final bottom-up sweep for directories left empty by any of the
    # above (e.g. a package whose only content was its own tests/ dir).
    # *.dist-info is left alone throughout, same as _clean_dist.
    for root, dirs, files in os.walk(app_dir, topdown=False):
        for dname in dirs:
            if dname.endswith('.dist-info'):
                continue

            dir_path = os.path.join(root, dname)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    n_dirs += 1
            except OSError:
                pass

    print(f'prune_dist: removed {n_files} files and {n_dirs} directories')
