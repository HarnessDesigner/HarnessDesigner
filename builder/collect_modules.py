# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import importlib.util
import os
import logging


MODULE_NAMES = '''\
ipython_pygments_lexers
trianglesolver
typing_extensions
decorator
six
harness_designer
lib3mf
pyassimp
OpenGL_accelerate
OpenGL
numpy
PIL
pyparsing
packaging
kiwisolver
fontTools
cycler
svgelements
cadquery_ocp_proxy
mpmath
webcolors
isodate
lark
mdurl
pygments
traitlets
pure_eval
asttokens
executing
wcwidth
parso
colorama
anytree
ezdxf
jedi
matplotlib_inline
prompt_toolkit
stack_data
contourpy
scipy
sympy
shapely
markdown_it
cv2
pyfqmr
dateutil
ocp_gordon
rich
requests
meshio
svgwrite
svgpathtools
IPython
matplotlib
vtk
vtkmodules
cadquery_ocp
ocpsvg
build123d
pandas'''


def get_modules():

    res = []
    # Some modules (e.g. matplotlib) initialise loggers on import whose
    # underlying stream has been detached by PyInstaller's build harness,
    # producing spurious "ValueError: underlying buffer has been detached"
    # tracebacks.  Silence all logging for the duration of the probe imports.
    logging.disable(logging.CRITICAL)
    try:
        for name in MODULE_NAMES.split('\n'):
            try:
                mod = __import__(name)
            except ModuleNotFoundError:
                print('MODULE NOT FOUND:', name)
                continue

            if mod.__file__ is None:
                cmd = [f'--hidden-import={name}']
            elif '__init__' in mod.__file__:
                cmd = [f'--collect-all={name}']
            else:
                cmd = [f'--hidden-import={name}']

            res.extend(cmd)
    finally:
        logging.disable(logging.NOTSET)

    return res


def get_test_excludes():
    """
    Walk every package in MODULE_NAMES and return ``--exclude-module`` flags for
    every submodule whose dotted name contains a test component ('test', 'tests',
    '_test', '_tests', 'testing').

    PyInstaller has no wildcard support for --exclude-module, so this function
    enumerates them all via a pure file-system scan (no imports).  The generated
    flags cover both top-level test packages (e.g. pandas.tests) and every
    individual module inside them (e.g. pandas.tests.frame.test_api) so that
    explicit hidden-import requests from built-in hooks are also suppressed.
    """

    _TEST_COMPONENTS = frozenset(['test', 'tests', '_test', '_tests', 'testing'])

    excludes = set()

    def _add_all(dir_path, prefix):
        """Add every module and sub-package under an already-identified test dir."""
        try:
            entries = os.scandir(dir_path)
        except OSError:
            return

        for entry in entries:
            if entry.name.startswith('.'):
                continue

            if entry.is_dir(follow_symlinks=False):
                mod = prefix + entry.name
                excludes.add(mod)
                _add_all(entry.path, mod + '.')
            elif (
                entry.name.endswith('.py')
                and entry.name not in ('__init__.py', '__main__.py')
            ):
                excludes.add(prefix + entry.name[:-3])

    def _scan(dir_path, prefix):
        """Recurse into a package directory, stopping at test sub-directories."""
        try:
            entries = os.scandir(dir_path)
        except OSError:
            return

        for entry in entries:
            if entry.name.startswith('.') or not entry.is_dir(follow_symlinks=False):
                continue

            mod = prefix + entry.name

            if entry.name in _TEST_COMPONENTS:
                excludes.add(mod)
                _add_all(entry.path, mod + '.')
            elif os.path.isfile(os.path.join(entry.path, '__init__.py')):
                _scan(entry.path, mod + '.')

    for name in MODULE_NAMES.split('\n'):
        name = name.strip()
        if not name:
            continue

        try:
            spec = importlib.util.find_spec(name)
        except (ModuleNotFoundError, ValueError):
            continue

        if spec is None or not spec.submodule_search_locations:
            continue

        for pkg_dir in spec.submodule_search_locations:
            _scan(pkg_dir, name + '.')

    return [f'--exclude-module={n}' for n in sorted(excludes) if 'IPython' not in n]
