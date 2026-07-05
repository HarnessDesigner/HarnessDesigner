# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
#
# Resolves PyInstaller --collect-all/--hidden-import flags automatically
# from harness_designer's own installed dependency metadata, instead of a
# hand-maintained list of import names. A hand-maintained list is prone to
# exactly the bug that motivated this rewrite: a PyPI distribution name
# (what's in pyproject.toml, e.g. "cadquery-ocp") is frequently *not* the
# same as its actual import name (e.g. "OCP") — get it wrong, or simply
# forget to add a newly-introduced dependency, and PyInstaller silently
# fails to bundle it, surfacing only as a runtime ModuleNotFoundError in
# the frozen app.
#
# Uses only the stdlib (importlib.metadata) plus `packaging` (already a
# build-time dependency of this project, for its own wheel-tag computation
# in builder/wheel_build.py) — no setuptools anywhere in this path.

import functools
import importlib.metadata
import importlib.util
import logging
import os

from packaging.requirements import Requirement


def _distribution_to_import_names():
    """{distribution_name: [import_name, ...]} for every installed package.

    importlib.metadata.packages_distributions() gives the reverse mapping
    (import name -> distributions that provide it); this inverts it once.
    A single distribution can provide more than one import name (e.g.
    PyYAML provides both `yaml` and the compiled `_yaml` helper) — this
    catches those correctly rather than assuming a 1:1 mapping.
    """
    forward = {}
    for import_name, dist_names in importlib.metadata.packages_distributions().items():
        for dist_name in dist_names:
            forward.setdefault(dist_name, []).append(import_name)
    return forward


def _walk_distributions(name, seen):
    """Recursively resolve every distribution name in name's dependency
    graph.

    Only follows requirements whose environment marker applies to the
    current platform (e.g. skips an `apple_smi; sys_platform == "darwin"`
    dependency when not running on macOS) and that are actually installed
    here — anything not installed (a platform-conditional dependency for a
    different OS, or an extras-gated dependency nothing requested) is
    skipped silently, not treated as an error.
    """
    key = name.lower()
    if key in seen:
        return
    seen.add(key)

    try:
        requires = importlib.metadata.requires(name) or []
    except importlib.metadata.PackageNotFoundError:
        return

    for req_str in requires:
        req = Requirement(req_str)
        if req.marker is not None and not req.marker.evaluate():
            continue
        _walk_distributions(req.name, seen)


@functools.cache
def _resolve_import_names():
    """Every import name reachable from harness_designer's own installed
    dependency graph.

    Walking from harness_designer itself (rather than re-parsing
    pyproject.toml separately) pulls in every dependency declared there
    automatically, plus everything those depend on in turn — harness_designer's
    own installed METADATA already records exactly that dependency list, via
    the Requires-Dist lines builder/wheel_build.py writes from pyproject.toml
    at build time.
    """
    distributions = set()
    _walk_distributions('harness_designer', distributions)

    dist_to_import = _distribution_to_import_names()

    import_names = set()
    for dist_name in distributions:
        matches = dist_to_import.get(dist_name)
        if matches:
            import_names.update(matches)
        else:
            # packages_distributions() isn't always complete — some
            # installed packages lack top_level.txt and the RECORD-based
            # fallback doesn't always fill the gap either (confirmed: idna
            # has a proper idna/__init__.py yet doesn't show up in the
            # mapping in at least one environment tested against). Falling
            # back to the distribution name itself, normalized, catches the
            # common case where the import name matches the distribution
            # name outright. If this guess is wrong, get_modules() reports
            # it in the "not importable" list below rather than it vanishing
            # without a trace the way a hand-maintained list's gaps would.
            import_names.add(dist_name.lower().replace('-', '_'))

    return import_names


def get_modules():
    import_names = _resolve_import_names()

    res = []
    existing = []
    missing = []

    # Some modules (e.g. matplotlib) initialise loggers on import whose
    # underlying stream has been detached by PyInstaller's build harness,
    # producing spurious "ValueError: underlying buffer has been detached"
    # tracebacks.  Silence all logging for the duration of the probe imports.
    logging.disable(logging.CRITICAL)
    try:
        for name in sorted(import_names):
            try:
                mod = __import__(name)
            except ModuleNotFoundError:
                missing.append(name)
                continue

            existing.append(name)

            if mod.__file__ is None:
                cmd = [f'--hidden-import={name}']
            elif '__init__' in mod.__file__:
                cmd = [f'--collect-all={name}']
            else:
                cmd = [f'--hidden-import={name}']

            res.extend(cmd)
    finally:
        logging.disable(logging.NOTSET)

    print(f'Resolved {len(import_names)} import name(s) from the installed dependency graph:')
    for name in sorted(import_names):
        print(f'  {name}')

    print(f'{len(existing)} of those actually importable in this environment:')
    for name in existing:
        print(f'  {name}')

    if missing:
        print(
            f'{len(missing)} resolved name(s) not importable here '
            '(expected for platform-conditional dependencies not installed on this OS):'
        )
        for name in missing:
            print(f'  {name}')

    return res


def get_test_excludes():
    """
    Walk every resolved import name and return ``--exclude-module`` flags for
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

    for name in sorted(_resolve_import_names()):
        try:
            spec = importlib.util.find_spec(name)
        except (ModuleNotFoundError, ValueError):
            continue

        if spec is None or not spec.submodule_search_locations:
            continue

        for pkg_dir in spec.submodule_search_locations:
            _scan(pkg_dir, name + '.')

    return [f'--exclude-module={n}' for n in sorted(excludes) if 'IPython' not in n]
