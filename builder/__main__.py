# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
#
# Builds the PyInstaller onedir/onefile app bundle and the dependency
# installer from the harness_designer wheel installed by `pip install .`
# (see pyproject.toml / builder/_backend.py / builder/build_native_deps.py).
# Platform installer packaging is a separate subsequent step — see
# builder/installer.py.
#
# Usage:
#   python -m builder


def main():
    import sys

    base_import = list(sys.modules.keys())

    import os

    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # `python -m builder` prepends the current directory to sys.path (that's
    # how `-m` works, independent of PYTHONPATH) — when cwd is the repo root,
    # as it is in CI, that shadows the pip-installed harness_designer with
    # this repo's own uncompiled copy. `builder` itself is already fully
    # imported by this point (that's how -m got here — from_import below
    # resolves via the already-imported package's __path__, not sys.path),
    # so it's safe to strip every repo-root-referring entry from sys.path
    # now, before importing harness_designer.
    _norm = lambda p: os.path.normcase(os.path.normpath(p or os.getcwd()))
    _base_norm = _norm(base_path)
    sys.path[:] = [p for p in sys.path if _norm(p) != _base_norm]

    import harness_designer

    hd_path = os.path.dirname(harness_designer.__file__)

    # Hard safety check: harness_designer's parent dir must never be the repo
    # root. If it is, the sys.path stripping above failed silently — abort
    # loudly rather than letting PyInstaller bundle the wrong (uncompiled)
    # copy. Comparing dirname(hd_path) to base_path directly (rather than
    # os.path.commonpath()) avoids a ValueError when the repo and the Python
    # install live on different drives on Windows — commonpath() raises
    # "Paths don't have the same drive" instead of just returning a
    # non-matching result. normcase() guards against a false negative from
    # drive-letter/casing differences (Windows paths are case-insensitive).
    _hd_parent = os.path.normcase(os.path.dirname(os.path.abspath(hd_path)))
    _base_norm = os.path.normcase(os.path.abspath(base_path))
    if _hd_parent == _base_norm:
        raise RuntimeError(
            f'harness_designer resolved to {hd_path!r}, inside the repo '
            f'({base_path!r}) instead of the installed site-packages copy.'
        )

    os.chdir(base_path)

    from . import build

    build.build_installer(base_import)
    build.build_dependency_installer()


if __name__ == '__main__':
    main()
