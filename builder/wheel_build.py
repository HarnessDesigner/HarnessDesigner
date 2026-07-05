# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
#
# Assembles the harness_designer wheel without setuptools: stage a build
# directory mirroring the final package layout, cythonize + compile the
# discovered modules into it, then hand the tree to wheel.wheelfile.WheelFile
# (which computes RECORD hashes and writes the archive for us).

import os
import shutil

from . import compiler, cython_build, msvc_env

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_PKG_NAME = 'harness_designer'
_IGNORE_DIRS = frozenset(['__pycache__'])


def _load_project_metadata():
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    with open(os.path.join(_REPO_ROOT, 'pyproject.toml'), 'rb') as f:
        data = tomllib.load(f)

    return data['project']


def _stage_assets(build_lib):
    """Copy __init__.py/__main__.py + every non-source asset into build_lib.

    Modules that get compiled (.py, excluding __init__/__main__) and
    hand-written extensions (.pyx) are skipped here — _compile_modules()
    places their compiled output instead. .pyi/.c are build-time-only
    artifacts, never shipped.
    """
    src_root = os.path.join(_REPO_ROOT, _PKG_NAME)

    for root, dirs, files in os.walk(src_root):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS]
        rel_dir = os.path.relpath(root, _REPO_ROOT)

        for name in files:
            stem, ext = os.path.splitext(name)
            is_module_source = ext == '.py' and stem not in ('__init__', '__main__')
            is_hand_written_ext = ext == '.pyx'
            if is_module_source or is_hand_written_ext or ext in ('.pyi', '.c'):
                continue

            src = os.path.join(root, name)
            dst = os.path.join(build_lib, rel_dir, name)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)


def _compile_modules(build_lib, cythonize_enabled):
    modules = cython_build.discover_modules(_PKG_NAME)

    if not cythonize_enabled:
        # Fast dev path: ship the auto-discovered .py files as-is. bvh/culling
        # have no plain-Python fallback, so they always compile regardless.
        plain_modules = [m for m in modules if not m[1].endswith('.pyx')]
        modules = [m for m in modules if m[1].endswith('.pyx')]

        for _, rel_path in plain_modules:
            dst = os.path.join(build_lib, rel_path)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(_REPO_ROOT, rel_path), dst)

    if not modules:
        return

    msvc_env.activate()

    os.chdir(_REPO_ROOT)
    build_dir = os.path.join(_REPO_ROOT, 'build', 'c')
    c_paths = cython_build.cythonize_to_c(modules, build_dir=build_dir)

    obj_dir = os.path.join(_REPO_ROOT, 'build', 'obj')

    import numpy
    include_dirs = [compiler.python_include_dir(), numpy.get_include()]
    ext_suffix = compiler.ext_suffix()

    jobs = []
    for dotted_name, rel_source in modules:
        rel_no_ext = os.path.splitext(rel_source)[0]
        output_path = os.path.join(build_lib, rel_no_ext + ext_suffix)
        jobs.append((dotted_name, c_paths[dotted_name], output_path, obj_dir, include_dirs))

    compiler.compile_all(jobs)


def _wheel_tag():
    import packaging.tags

    tag = next(iter(packaging.tags.sys_tags()))
    return f'{tag.interpreter}-{tag.abi}-{tag.platform}'


def _write_metadata(dist_info_dir, project):
    lines = [
        'Metadata-Version: 2.1',
        f'Name: {project["name"]}',
        f'Version: {project["version"]}',
    ]
    if project.get('description'):
        lines.append(f'Summary: {project["description"]}')
    if project.get('readme'):
        lines.append('Description-Content-Type: text/markdown')
    if project.get('requires-python'):
        lines.append(f'Requires-Python: {project["requires-python"]}')
    for author in project.get('authors', []):
        if author.get('name'):
            lines.append(f'Author: {author["name"]}')
    for url_name, url in project.get('urls', {}).items():
        lines.append(f'Project-URL: {url_name}, {url}')
    for dep in project.get('dependencies', []):
        lines.append(f'Requires-Dist: {dep}')

    body = ''
    readme = project.get('readme')
    if readme:
        readme_path = os.path.join(_REPO_ROOT, readme)
        if os.path.exists(readme_path):
            with open(readme_path, encoding='utf-8') as f:
                body = f.read()

    content = '\n'.join(lines) + '\n\n' + body
    with open(os.path.join(dist_info_dir, 'METADATA'), 'w', encoding='utf-8') as f:
        f.write(content)


def _write_wheel_file(dist_info_dir, tag):
    content = (
        'Wheel-Version: 1.0\n'
        'Generator: harness_designer_backend\n'
        'Root-Is-Purelib: false\n'
        f'Tag: {tag}\n'
    )
    with open(os.path.join(dist_info_dir, 'WHEEL'), 'w', encoding='utf-8') as f:
        f.write(content)


def build_wheel(wheel_directory, config_settings=None):
    config_settings = config_settings or {}
    cythonize_enabled = str(config_settings.get('cythonize', 'true')).lower() != 'false'

    project = _load_project_metadata()
    name = project['name']
    version = project['version']

    build_root = os.path.join(_REPO_ROOT, 'build', 'wheel')
    if os.path.exists(build_root):
        shutil.rmtree(build_root)
    os.makedirs(build_root)

    _stage_assets(build_root)
    _compile_modules(build_root, cythonize_enabled)

    dist_info_dir = os.path.join(build_root, f'{name}-{version}.dist-info')
    os.makedirs(dist_info_dir)
    _write_metadata(dist_info_dir, project)
    tag = _wheel_tag()
    _write_wheel_file(dist_info_dir, tag)

    wheel_name = f'{name}-{version}-{tag}.whl'
    wheel_path = os.path.join(wheel_directory, wheel_name)

    from wheel.wheelfile import WheelFile
    with WheelFile(wheel_path, 'w') as wf:
        wf.write_files(build_root)

    return wheel_name


def build_sdist(sdist_directory, config_settings=None):
    import subprocess
    import tarfile

    project = _load_project_metadata()
    prefix = f'{project["name"]}-{project["version"]}'

    try:
        result = subprocess.run(
            ['git', 'ls-files'], cwd=_REPO_ROOT, check=True,
            capture_output=True, text=True,
        )
        tracked = result.stdout.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        tracked = []
        for root, dirs, files in os.walk(_REPO_ROOT):
            dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__', 'build')]
            for name in files:
                tracked.append(
                    os.path.relpath(os.path.join(root, name), _REPO_ROOT)
                )

    sdist_name = f'{prefix}.tar.gz'
    sdist_path = os.path.join(sdist_directory, sdist_name)

    with tarfile.open(sdist_path, 'w:gz') as tar:
        for rel_path in tracked:
            tar.add(
                os.path.join(_REPO_ROOT, rel_path),
                arcname=os.path.join(prefix, rel_path),
            )

    return sdist_name
