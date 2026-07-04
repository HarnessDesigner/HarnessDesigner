# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
#
# Builds the PyInstaller onedir/onefile app bundle and the dependency
# installer from the harness_designer wheel installed by `pip install .`
# (see setup.py / builder/build_native_deps.py). Platform installer packaging
# is a separate subsequent step — see builder/installer.py.
#
# Usage:
#   python -m builder


def main():
    import sys

    base_import = list(sys.modules.keys())

    import os

    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    import harness_designer

    hd_path = os.path.dirname(harness_designer.__file__)

    # Hard safety check: this script needs the repo root importable (for
    # `builder` itself, via PYTHONPATH), which risks `harness_designer` also
    # resolving to this repo's copy instead of the pip-installed one in
    # site-packages. Abort loudly rather than letting PyInstaller bundle the
    # wrong (uncompiled) copy.
    _hd_abs = os.path.abspath(hd_path)
    _base_abs = os.path.abspath(base_path)
    if os.path.commonpath([_hd_abs, _base_abs]) == _base_abs:
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
