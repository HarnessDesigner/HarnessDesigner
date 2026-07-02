# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
#
# Runtime hook for the dependency installer frozen app.
#
# pip/_vendor/distlib/scripts.py runs finder('pip._vendor.distlib').iterator('')
# at MODULE LEVEL (line ~66) to load script templates.  distlib.resources.finder()
# resolves the resource finder by matching the module's loader TYPE against a
# registry.  PyInstaller's FrozenImporter is not in that registry, so finder()
# raises DistlibException before pip can do anything useful.
#
# This hook runs before installer.py is executed.  It replaces finder() with a
# version that falls back to a plain file-system walk when the loader type is
# unrecognised, which is always the case inside a frozen app.

import os
import sys

if getattr(sys, 'frozen', False):
    try:
        # Import resources.py here — it does NOT call finder() at module level,
        # so this import is safe.  Importing it also guarantees that
        # pip._vendor.distlib is in sys.modules, giving us __file__.
        import pip._vendor.distlib as _distlib_pkg
        import pip._vendor.distlib.resources as _res

        _distlib_base = os.path.dirname(_distlib_pkg.__file__)
        _orig_finder = _res.finder

        class _Resource:
            """Minimal duck-type resource object (name + lazy bytes)."""
            __slots__ = ('name', '_path')

            def __init__(self, name, path):
                self.name = name
                self._path = path

            @property
            def bytes(self):
                try:
                    with open(self._path, 'rb') as f:
                        return f.read()
                except OSError:
                    return b''

        class _FileSystemFinder:
            def __init__(self, base):
                self._base = base

            def iterator(self, rel=''):
                target = os.path.join(self._base, rel) if rel else self._base
                try:
                    for name in sorted(os.listdir(target)):
                        yield _Resource(name, os.path.join(target, name))
                except OSError:
                    return

            def find(self, rel):
                path = os.path.join(self._base, rel)
                return _Resource(os.path.basename(path), path) if os.path.exists(path) else None

        def _patched_finder(package):
            try:
                return _orig_finder(package)
            except Exception:
                if package == 'pip._vendor.distlib':
                    return _FileSystemFinder(_distlib_base)
                # Generic fallback for any other unrecognised package
                try:
                    mod = sys.modules.get(package)
                    if mod is None:
                        import importlib
                        mod = importlib.import_module(package)
                    paths = getattr(mod, '__path__', None)
                    base = paths[0] if paths else os.path.dirname(mod.__file__)
                except Exception:
                    base = ''
                return _FileSystemFinder(base)

        _res.finder = _patched_finder

    except Exception:
        pass
