#!/usr/bin/env python3
# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
#
# Creates a platform-specific installer for Harness Designer from the compiled
# build outputs produced by:  python -m builder
#
# Usage:
#   python installer.py [--version X.Y.Z] [--sign]
#
#   --version   Override the version string (default: from harness_designer/__version__.py).
#   --sign      (macOS only) Codesign and notarize the .pkg.

import argparse
import importlib.util
import io
import os
import platform
import shutil
import subprocess
import sys
import tarfile


BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
INSTALLER_SCRIPTS_DIR = os.path.join(BASE_PATH, 'installer_scripts')
BUILD_DIR = os.path.join(BASE_PATH, 'builder', 'scripts', 'dist')
DIST_DIR = os.path.join(BASE_PATH, 'dist')
ICON_PNG = os.path.join(BASE_PATH, 'harness_designer', 'image', 'icon_256x256.png')

print('BASE_PATH:', BASE_PATH)

# ── Utilities ─────────────────────────────────────────────────────────────────


def _read_version():
    """Read the version string from harness_designer/__version__.py."""
    path = os.path.join(BASE_PATH, 'harness_designer', '__version__.py')
    spec = importlib.util.spec_from_file_location('__version__', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.string


def _check_build_outputs():
    """Abort with a clear message if any expected build output is missing."""
    errors = []

    if sys.platform.startswith('darwin'):
        app = os.path.join(BUILD_DIR, 'harness_designer.app')
        installer_bin = os.path.join(
            BUILD_DIR, 'installer.app', 'Contents', 'MacOS', 'installer'
        )
        if not os.path.isdir(app):
            errors.append(f'  missing dir : {app}')
        if not os.path.isfile(installer_bin):
            errors.append(f'  missing file: {installer_bin}')
    else:
        app = os.path.join(BUILD_DIR, 'harness_designer')
        if not os.path.isdir(app):
            errors.append(f'  missing dir : {app}')

        installer_dir = os.path.join(BUILD_DIR, 'installer')
        if not os.path.isdir(installer_dir):
            errors.append(f'  missing dir : {installer_dir}')
        else:
            ext = '.exe' if sys.platform.startswith('win') else ''
            binary = os.path.join(installer_dir, f'installer{ext}')
            if not os.path.isfile(binary):
                errors.append(f'  missing file: {binary}')

    if not os.path.isfile(ICON_PNG):
        errors.append(f'  missing file: {ICON_PNG}')

    if errors:
        print('Error: required build outputs are missing:')
        for e in errors:
            print(e)
        print()
        print('Run the builder first:  python -m builder')
        sys.exit(1)


# ── Windows ───────────────────────────────────────────────────────────────────


def _find_iscc():
    """Locate the Inno Setup compiler (ISCC.exe)."""
    iscc = shutil.which('iscc')
    if iscc:
        return iscc
    for candidate in (
        r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
        r'C:\Program Files\Inno Setup 6\ISCC.exe',
    ):
        if os.path.isfile(candidate):
            return candidate
    return None


def _ensure_icon_ico():
    """Convert icon_256x256.png to icon_256x256.ico; return the .ico path."""
    ico = os.path.join(BASE_PATH, 'harness_designer', 'image', 'icon_256x256.ico')
    if os.path.isfile(ico):
        return ico

    print('→ Converting icon PNG → ICO ...')

    from PIL import Image
    img = Image.open(ICON_PNG)
    img.save(
        ico,
        format='ICO',
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    return ico


def build_windows(version):
    """Compile installer_scripts/windows/harness_designer.iss into a setup .exe."""
    iscc = _find_iscc()
    if not iscc:
        print('Error: Inno Setup compiler (ISCC.exe) not found.')
        print('Download: https://jrsoftware.org/isinfo.php')
        sys.exit(1)

    _ensure_icon_ico()

    license_file = os.path.join(BASE_PATH, 'LICENSE')
    if not os.path.isfile(license_file):
        print(f'Error: LICENSE file not found at {license_file}')
        print('The Inno Setup script references it — add the file and re-run.')
        sys.exit(1)

    iss = os.path.join(INSTALLER_SCRIPTS_DIR, 'windows', 'harness_designer.iss')
    os.makedirs(os.path.join(DIST_DIR, 'windows'), exist_ok=True)

    print(f'→ Compiling {os.path.basename(iss)} ...')
    rc = subprocess.run(
        [iscc, f'/DAppVersion={version}', iss],
        check=False,
    ).returncode

    if rc != 0:
        print(f'Error: ISCC exited with code {rc}')
        sys.exit(rc)

    print(f'\n✓ Windows installer:  {os.path.join(DIST_DIR, "windows")}')


# ── macOS ─────────────────────────────────────────────────────────────────────


def build_macos(version, sign):
    """Run installer_scripts/macos/build_pkg.sh to produce a signed .pkg."""
    script = os.path.join(INSTALLER_SCRIPTS_DIR, 'macos', 'build_pkg.sh')
    if not os.path.isfile(script):
        print(f'Error: macOS build script not found: {script}')
        sys.exit(1)

    os.chmod(script, 0o755)

    cmd = [script, '--version', version]
    if sign:
        cmd.append('--sign')

    print('→ Running build_pkg.sh ...')
    rc = subprocess.run(cmd, check=False).returncode
    if rc != 0:
        print(f'Error: build_pkg.sh exited with code {rc}')
        sys.exit(rc)

    print(f'\n✓ macOS package:  {os.path.join(DIST_DIR, "macos")}')


# ── Linux ─────────────────────────────────────────────────────────────────────


def build_linux(version):
    """
    Bundle the compiled app into a self-contained .tar.gz for Linux.

    The archive mirrors the relative directory structure that install.sh
    expects (it computes REPO_ROOT as two levels above its own location).

    The archived copy of install.sh is patched so that INSTALLER_SRC points
    to the executable inside the PyInstaller onedir rather than the directory
    itself (build_dependency_installer() defaults to --onedir, not --onefile,
    and the original install.sh tries to `cp` the path as a plain file).

    Archive layout:

        harness_designer-{version}/
        ├── install.sh                          ← convenience root launcher
        ├── installer_scripts/
        │   └── linux/
        │       └── install.sh                  ← patched copy of original
        ├── builder/
        │   └── scripts/
        │       └── dist/
        │           ├── harness_designer/       ← main app (PyInstaller onedir)
        │           └── installer/              ← dep installer (PyInstaller onedir)
        │               └── installer           ← dep installer binary
        └── harness_designer/
            └── image/
                └── icon_256x256.png
    """
    app_src = os.path.join(BUILD_DIR, 'harness_designer')
    installer_src = os.path.join(BUILD_DIR, 'installer')
    install_sh_path = os.path.join(INSTALLER_SCRIPTS_DIR, 'linux', 'install.sh')

    machine = platform.machine().lower()
    stem = f'harness_designer-{version}'
    archive_name = f'harness_designer_{version}_linux_{machine}.tar.gz'
    archive_path = os.path.join(DIST_DIR, 'linux', archive_name)

    os.makedirs(os.path.dirname(archive_path), exist_ok=True)

    # ── Patch install.sh ──────────────────────────────────────────────────────
    # The original sets INSTALLER_SRC="$BUILD_DIR/installer" (the onedir).
    # We change it to point at the binary inside the directory.

    with open(install_sh_path, encoding='utf-8') as fh:
        install_sh_src = fh.read()

    patched_sh = install_sh_src.replace(
        'INSTALLER_SRC="$BUILD_DIR/installer"',
        'INSTALLER_SRC="$BUILD_DIR/installer/installer"',
        1,
    )

    # Root-level convenience launcher so users run ./install.sh from the
    # extracted directory instead of the longer installer_scripts/linux/ path.
    root_sh = '''\
#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/installer_scripts/linux/install.sh" "$@"
'''

    def _add_text(tar, arcname, text, mode=0o755):
        data = text.encode('utf-8')
        ti = tarfile.TarInfo(name=arcname)
        ti.size = len(data)
        ti.mode = mode
        tar.addfile(ti, io.BytesIO(data))

    def _walk_dir(src_dir, arc_prefix):
        """Yield (abs_path, arcname) for every file under src_dir."""
        parent = os.path.dirname(src_dir)
        for dirpath, _, filenames in os.walk(src_dir):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                rel = os.path.relpath(fpath, parent).replace(os.sep, '/')
                yield fpath, f'{arc_prefix}/{rel}'

    print(f'→ Creating {archive_name} ...')

    with tarfile.open(archive_path, 'w:gz') as tar:
        # Root convenience launcher
        _add_text(tar, f'{stem}/install.sh', root_sh)

        # Patched install.sh at the expected relative path
        _add_text(tar, f'{stem}/installer_scripts/linux/install.sh', patched_sh)

        # Main application (PyInstaller onedir)
        print('   Adding main application ...')
        for fpath, arcname in _walk_dir(app_src, f'{stem}/builder/scripts/dist'):
            tar.add(fpath, arcname=arcname)

        # Dependency installer (PyInstaller onedir)
        print('   Adding dependency installer ...')
        for fpath, arcname in _walk_dir(installer_src, f'{stem}/builder/scripts/dist'):
            tar.add(fpath, arcname=arcname)

        # Application icon
        tar.add(
            ICON_PNG,
            arcname=f'{stem}/harness_designer/image/icon_256x256.png',
        )

    print(f'\n✓ Linux archive:  {archive_path}')
    print()
    print('  To install:')
    print(f'    tar xzf {archive_name}')
    print(f'    sudo ./{stem}/install.sh')
    print(f'    # user-only:  ./{stem}/install.sh --user')


# ── Entry point ───────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description='Build a platform-specific installer for Harness Designer.',
        epilog='Prerequisite:  python -m builder',
    )
    parser.add_argument(
        '--version',
        metavar='X.Y.Z',
        default=None,
        help='Version string (default: from harness_designer/__version__.py)',
    )
    parser.add_argument(
        '--sign',
        action='store_true',
        help='(macOS only) Codesign and notarize the .pkg',
    )
    args = parser.parse_args()

    version = args.version or _read_version()

    print('Harness Designer — Installer Builder')
    print(f'Platform : {sys.platform} ({platform.machine()})')
    print(f'Version  : {version}')
    print()

    _check_build_outputs()

    if sys.platform.startswith('win'):
        build_windows(version)
    elif sys.platform.startswith('darwin'):
        build_macos(version, args.sign)
    elif sys.platform.startswith('linux'):
        build_linux(version)
    else:
        print(f'Error: unsupported platform: {sys.platform!r}')
        sys.exit(1)


if __name__ == '__main__':
    main()
