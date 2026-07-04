# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
#
# Pure file-discovery + Cython transpile — no setuptools involved. Every
# discovered module compiles with identical flags (see builder/compiler.py),
# so there's no per-module metadata to track here beyond a name and a path.

import os

_IGNORE_DIRS = frozenset(['__pycache__'])
_SKIP_STEMS = frozenset(['__init__', '__main__'])

# Hand-written Cython extensions that ship as .pyx source rather than being
# auto-discovered from plain .py files.
_HAND_WRITTEN_EXTENSIONS = (
    'ray_tracing/bvh.pyx',
    'gl/canvas3d/culling.pyx',
)


def _iter_py_files(pkg_root):
    for entry in sorted(os.listdir(pkg_root)):
        if entry in _IGNORE_DIRS:
            continue

        path = os.path.join(pkg_root, entry)
        if os.path.isdir(path):
            yield from _iter_py_files(path)
            continue

        stem, ext = os.path.splitext(entry)
        if ext == '.py' and stem not in _SKIP_STEMS:
            yield path


def _dotted_name(pkg_name, pkg_root, file_path):
    rel = os.path.relpath(file_path, pkg_root)
    stem = os.path.splitext(rel)[0]
    parts = stem.split(os.sep)
    return '.'.join([pkg_name] + parts)


def discover_modules(pkg_name):
    """Return (dotted_name, relative_source_path) pairs to cythonize.

    Paths are relative to the current directory (expected to be the repo
    root) — Cython's cythonize(build_dir=...) silently has no effect on
    absolute source paths, so callers must chdir to the repo root before
    passing these to cythonize_to_c().
    """
    pkg_root = pkg_name

    modules = [
        (_dotted_name(pkg_name, pkg_root, path), path)
        for path in _iter_py_files(pkg_root)
    ]

    for rel_path in _HAND_WRITTEN_EXTENSIONS:
        parts = rel_path.split('/')
        path = os.path.join(pkg_root, *parts)
        name = '.'.join([pkg_name] + parts)[:-len('.pyx')]
        modules.append((name, path))

    return modules


def cythonize_to_c(modules, build_dir, nthreads=None):
    """Transpile every (dotted_name, relative_source_path) pair to a .c file.

    Returns {dotted_name: generated_c_path}. Must be called with cwd at the
    repo root (see discover_modules docstring). Uses build_dir (instead of
    --inplace) so generated .c files land in a build staging area instead of
    next to the .py/.pyx sources in the repo tree — that staging area is then
    walked below to find what cythonize actually produced, rather than
    predicting the output path ourselves from the source path.
    """
    from Cython.Build import cythonize

    cythonize(
        [path for _, path in modules],
        build_dir=build_dir,
        compiler_directives={'language_level': '3'},
        nthreads=nthreads or os.cpu_count(),
    )

    generated = {}
    for root, _dirs, files in os.walk(build_dir):
        for fname in files:
            if not fname.endswith('.c'):
                continue

            c_path = os.path.join(root, fname)
            rel = os.path.relpath(c_path, build_dir)
            stem = os.path.splitext(rel)[0]
            generated['.'.join(stem.split(os.sep))] = c_path

    c_paths = {}
    for dotted_name, _source_path in modules:
        if dotted_name not in generated:
            raise RuntimeError(
                f'cythonize did not produce a .c file for {dotted_name!r} '
                f'under {build_dir!r}'
            )
        c_paths[dotted_name] = generated[dotted_name]

    return c_paths
