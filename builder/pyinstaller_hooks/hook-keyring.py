# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
#
# Overrides PyInstaller's own hook-keyring.py (wired in via
# --additional-hooks-dir in builder/build.py, which takes precedence over
# PyInstaller's bundled hooks). keyring's runtime backend discovery
# (keyring.backend.get_all_keyring(), via importlib.metadata entry points)
# needs its dist-info metadata present in the frozen app -- same reason
# PyInstaller's own hook collects it with copy_metadata('keyring').
#
# copy_metadata() raises on macOS CI:
#   RuntimeError: Cannot collect metadata from path PosixPath(...), which
#   is of unsupported type <class 'pathlib.PosixPath'>.
# from its own `if not isinstance(src_path, Path): raise ...` check, even
# though PosixPath is a Path subclass -- filed with PyInstaller upstream,
# unresolved as of this writing. keyring's dist._path is a perfectly usable
# path on disk regardless; this hook copies it directly, skipping
# PyInstaller's type check entirely.
import importlib.metadata
import os

_dist = importlib.metadata.distribution('keyring')
_src = str(_dist._path)
datas = [(_src, os.path.basename(_src))]
