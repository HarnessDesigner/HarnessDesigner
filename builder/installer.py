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
import tempfile

from . import prepare_installer_assets


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
        installer_bin = os.path.join(BUILD_DIR, 'dep_installer')
        if not os.path.isdir(app):
            errors.append(f'  missing dir : {app}')
        if not os.path.isfile(installer_bin):
            errors.append(f'  missing file: {installer_bin}')
    else:
        app = os.path.join(BUILD_DIR, 'harness_designer')
        if not os.path.isdir(app):
            errors.append(f'  missing dir : {app}')

        # Linux no longer uses a separate dep_installer process -- the main
        # app's own bootstrap.py shows the PySide6 license screen itself on
        # first launch instead (see builder/build.py's
        # build_dependency_installer(), which is a no-op on Linux).
        if not sys.platform.startswith('linux'):
            ext = '.exe' if sys.platform.startswith('win') else ''
            binary = os.path.join(BUILD_DIR, f'dep_installer{ext}')
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

    print('Converting icon PNG -> ICO ...')

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

    # Generate the multi-size ICO and the BMP assets the .iss needs at compile time.
    prepare_installer_assets.prepare_all()

    license_file = os.path.join(BASE_PATH, 'LICENSE')
    if not os.path.isfile(license_file):
        print(f'Error: LICENSE file not found at {license_file}')
        print('The Inno Setup script references it — add the file and re-run.')
        sys.exit(1)

    iss = os.path.join(INSTALLER_SCRIPTS_DIR, 'windows', 'harness_designer.iss')
    os.makedirs(os.path.join(DIST_DIR, 'windows'), exist_ok=True)

    print(f'Compiling {os.path.basename(iss)} ...')
    rc = subprocess.run(
        [iscc, f'/DAppVersion={version}', iss],
        check=False,
    ).returncode

    if rc != 0:
        print(f'Error: ISCC exited with code {rc}')
        sys.exit(rc)

    print(f'\nWindows installer:  {os.path.join(DIST_DIR, "windows")}')


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

    print('Running build_pkg.sh ...')
    rc = subprocess.run(cmd, check=False).returncode
    if rc != 0:
        print(f'Error: build_pkg.sh exited with code {rc}')
        sys.exit(rc)

    print(f'\nmacOS package:  {os.path.join(DIST_DIR, "macos")}')


# ── Linux ─────────────────────────────────────────────────────────────────────


def build_linux(version):
    """
    Bundle the compiled app into a self-contained .tar.gz for Linux.

    The archive mirrors the relative directory structure that install.sh
    expects (it computes REPO_ROOT as two levels above its own location).

    No separate dep_installer binary is bundled -- Linux has no install-time
    GUI step; the main app's own bootstrap.py shows the PySide6 license
    screen itself (in process, via builder/scripts/license_screen.py) the
    first time it finds PySide6 not importable at launch.

    Archive layout:

        harness_designer-{version}/
        ├── install.sh                          ← convenience root launcher
        ├── installer_scripts/
        │   └── linux/
        │       └── install.sh                  ← patched copy of original
        ├── builder/
        │   └── scripts/
        │       └── dist/
        │           └── harness_designer/       ← main app (PyInstaller onedir)
        └── harness_designer/
            └── image/
                └── icon_256x256.png
    """
    app_src = os.path.join(BUILD_DIR, 'harness_designer')
    install_sh_path = os.path.join(INSTALLER_SCRIPTS_DIR, 'linux', 'install.sh')

    machine = platform.machine().lower()
    stem = f'harness_designer-{version}'
    archive_name = f'harness_designer_{version}_linux_{machine}.tar.gz'
    archive_path = os.path.join(DIST_DIR, 'linux', archive_name)

    os.makedirs(os.path.dirname(archive_path), exist_ok=True)

    with open(install_sh_path, encoding='utf-8') as fh:
        install_sh_src = fh.read()

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

    print(f'Creating {archive_name} ...')

    with tarfile.open(archive_path, 'w:gz') as tar:
        # Root convenience launcher
        _add_text(tar, f'{stem}/install.sh', root_sh)

        # install.sh at the expected relative path
        _add_text(tar, f'{stem}/installer_scripts/linux/install.sh', install_sh_src)

        # Main application (PyInstaller onedir)
        print('   Adding main application ...')
        for fpath, arcname in _walk_dir(app_src, f'{stem}/builder/scripts/dist'):
            tar.add(fpath, arcname=arcname)

        # Application icon
        tar.add(
            ICON_PNG,
            arcname=f'{stem}/harness_designer/image/icon_256x256.png',
        )

    print(f'\nLinux archive:  {archive_path}')
    print()
    print('  To install:')
    print(f'    tar xzf {archive_name}')
    print(f'    sudo ./{stem}/install.sh')
    print(f'    # user-only:  ./{stem}/install.sh --user')


# ── Linux (.deb) ─────────────────────────────────────────────────────────────

# platform.machine() -> Debian Architecture field. Add entries here as CI
# picks up more runner architectures.
_DEB_ARCH = {
    'x86_64': 'amd64',
    'aarch64': 'arm64',
}

# PySide6's bundled xcb platform plugin dlopen()s these rather than linking
# them directly, so PyInstaller's dependency walker never sees them -- same
# non-dev runtime packages apt-get installs on the CI runner (see
# .github/workflows/unix.yml), minus the -dev/build-only ones. Best-effort:
# not verified against a clean target VM.
_DEB_DEPENDS = [
    'libgl1',
    'libglu1-mesa',
    'libxcb-cursor0',
    'libxkbcommon-x11-0',
    'libxcb-icccm4',
    'libxcb-image0',
    'libxcb-keysyms1',
    'libxcb-randr0',
    'libxcb-render-util0',
    'libxcb-shape0',
    'libxcb-xinerama0',
    'libxcb-xfixes0',
    'libdbus-1-3',
    'ocl-icd-libopencl1',
]

# No separate dep_installer process on Linux -- the main binary's own
# bootstrap.py (see builder/scripts/bootstrap.py) shows the PySide6 license
# Accept/Cancel screen itself, in process, the first time it finds PySide6
# not importable, so this is a plain launcher again.
_LAUNCHER_SH = '''\
#!/bin/sh
set -e
exec "/opt/harness_designer/HD" "$@"
'''

# Debian policy forbids interactive/GUI work in maintainer scripts (preinst
# can run headless -- unattended-upgrades, CI, etc.), so this only does a
# plain-text check for the one thing dpkg itself can't: whether the app is
# currently running (dpkg's own file-replacement already handles "is this an
# upgrade" correctly and never touches a user's $HOME, so no separate
# already-installed check is needed here the way install.sh's raw `cp -r`
# needs one).
_PREINST_SH = '''\
#!/bin/sh
set -e

if command -v pgrep >/dev/null 2>&1; then
    while pgrep -x HD >/dev/null 2>&1; do
        if [ -t 0 ] && [ -t 1 ]; then
            printf 'Harness Designer is currently running. Close it, then press Enter to retry (Ctrl-C to cancel): '
            read -r _
        else
            echo 'Harness Designer is currently running and this is a non-interactive install -- aborting.' >&2
            exit 1
        fi
    done
fi

exit 0
'''

_DESKTOP_ENTRY = '''\
[Desktop Entry]
Version=1.0
Type=Application
Name=Harness Designer
GenericName=Electrical Harness Designer
Comment=Design and document electrical harnesses
Exec=harness_designer %F
Icon=harness_designer
Terminal=false
Categories=Engineering;Electronics;
MimeType=application/x-harness-designer;
StartupNotify=true
'''

_POSTINST_SH = '''\
#!/bin/sh
set -e

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi

exit 0
'''

_POSTRM_SH = '''\
#!/bin/sh
set -e

case "$1" in
    remove|purge)
        if command -v update-desktop-database >/dev/null 2>&1; then
            update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
        fi
        if command -v gtk-update-icon-cache >/dev/null 2>&1; then
            gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
        fi
        ;;
esac

exit 0
'''


def _control_file(pkg_version, arch):
    depends = ', '.join(_DEB_DEPENDS)
    return (
        'Package: harness-designer\n'
        f'Version: {pkg_version}\n'
        'Section: electronics\n'
        'Priority: optional\n'
        f'Architecture: {arch}\n'
        f'Depends: {depends}\n'
        'Maintainer: Kevin G. Schlosser <kevin.g.schlosser@gmail.com>\n'
        'Description: design and document electrical wire harnesses\n'
        ' Harness Designer is a desktop application for designing and\n'
        ' documenting electrical wire harnesses.\n'
        ' .\n'
        ' NOTE: on first launch, Harness Designer itself installs the\n'
        ' PySide6 (Qt) runtime and a few platform-specific components,\n'
        ' after showing its license -- this requires network access the\n'
        ' first time the application runs.\n'
    )


def _write_text(path, text, mode):
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.chmod(path, mode)


def build_deb(version):
    """
    Package the compiled app as a real, installable .deb (Debian/Ubuntu).

    This is in addition to build_linux()'s .tar.gz, which install.sh (and
    Fedora/RHEL/Arch users) still rely on -- see its docstring for why a
    plain zip-of-tar.gz CI artifact gets flagged as malware by some
    browsers/SmartScreen, which a real .deb (a standardized, recognized
    container format) does not.
    """
    app_src = os.path.join(BUILD_DIR, 'harness_designer')

    machine = platform.machine().lower()
    arch = _DEB_ARCH.get(machine)
    if arch is None:
        print(f'Error: no Debian architecture mapping for machine {machine!r}')
        print(f'  Add it to _DEB_ARCH in {__file__}')
        sys.exit(1)

    pkg_version = f'{version}-1'
    deb_name = f'harness-designer_{pkg_version}_{arch}.deb'
    out_dir = os.path.join(DIST_DIR, 'linux_deb')
    deb_path = os.path.join(out_dir, deb_name)
    os.makedirs(out_dir, exist_ok=True)

    staging = tempfile.mkdtemp(prefix='harness_designer_deb_')
    try:
        debian_dir = os.path.join(staging, 'DEBIAN')
        app_dir = os.path.join(staging, 'opt', 'harness_designer')
        bin_dir = os.path.join(staging, 'usr', 'bin')
        desktop_dir = os.path.join(staging, 'usr', 'share', 'applications')
        icon_dir = os.path.join(
            staging, 'usr', 'share', 'icons', 'hicolor', '256x256', 'apps',
        )

        for d in (debian_dir, app_dir, bin_dir, desktop_dir, icon_dir):
            os.makedirs(d, exist_ok=True)

        print('   Copying application files ...')
        shutil.copytree(app_src, app_dir, dirs_exist_ok=True)

        os.chmod(os.path.join(app_dir, 'HD'), 0o755)

        icon_dst = os.path.join(icon_dir, 'harness_designer.png')
        shutil.copy2(ICON_PNG, icon_dst)
        os.chmod(icon_dst, 0o644)

        _write_text(os.path.join(bin_dir, 'harness_designer'), _LAUNCHER_SH, 0o755)
        _write_text(
            os.path.join(desktop_dir, 'harness_designer.desktop'),
            _DESKTOP_ENTRY,
            0o644,
        )
        _write_text(
            os.path.join(debian_dir, 'control'),
            _control_file(pkg_version, arch),
            0o644,
        )
        _write_text(os.path.join(debian_dir, 'preinst'), _PREINST_SH, 0o755)
        _write_text(os.path.join(debian_dir, 'postinst'), _POSTINST_SH, 0o755)
        _write_text(os.path.join(debian_dir, 'postrm'), _POSTRM_SH, 0o755)

        print(f'Building {deb_name} ...')
        rc = subprocess.run(
            ['dpkg-deb', '--root-owner-group', '--build', staging, deb_path],
            check=False,
        ).returncode
        if rc != 0:
            print(f'Error: dpkg-deb exited with code {rc}')
            sys.exit(rc)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    print(f'\nLinux .deb:  {deb_path}')
    print(f'  To install:  sudo apt install ./{deb_name}')


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
        build_deb(version)
    else:
        print(f'Error: unsupported platform: {sys.platform!r}')
        sys.exit(1)


if __name__ == '__main__':
    main()
