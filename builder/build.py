import sys
import os
import argparse  # NOQA

BASE_PATH = os.path.abspath(os.path.dirname(__file__))
sys.path.append(BASE_PATH)


def main(args):
    parser = argparse.ArgumentParser("-")

    parser.add_argument(
        '--no-cython-wx',
        dest='no_cython_wx',
        help='do not compile wxPython using Cython.',
        default=False,
        action='store_true')

    parser.add_argument(
        '--no-cython',
        dest='no_cython',
        help='do not compile Harness Designer using Cython.',
        default=False,
        action='store_true')

    parser.add_argument(
        '--no-pyi-rename',
        dest='no_pyi_rename',
        help='do not rename the py files to pyi.',
        default=False,
        action='store_true')

    args = parser.parse_args(args)

    cython_wx = not args.no_cython_wx
    cython = not args.no_cython
    pyi_rename = not args.no_pyi_rename

    if cython_wx:
        import compile_wxpython

        compile_wxpython.run()

    if cython:
        import compile_harness_designer

        compile_harness_designer.run(pyi_rename)


def build_installer():
    import collect_stdlib
    import collect_modules

    std_lib = collect_stdlib.get_modules()
    modules = collect_modules.get_modules()

    manifest_path = os.path.join(BASE_PATH, 'harness_designer.MANIFEST')

    manifest = (
        '<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">\n'
        '<dependency>\n'
        '    <dependentAssembly>\n'
        '       <assemblyIdentity type="win32" name="HarnessDesigner.product.HarnessDesigner" version="0.0.1.1" language="*" />\n'
        '       <supportedOS id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}" />\n'
        '     </dependentAssembly>\n'
        '</dependency>\n'
        '</assembly>\n'
    )

    # with open(manifest_path, 'w') as f:
    #     f.write(manifest)

    import PyInstaller.__main__
    script = 'builder/run.py'

    args = []
    args += std_lib
    args += modules

    if sys.platform.startswith('win'):
        args.extend(['--icon=harness_designer/image/icon_256x256.png'])
        args.extend(['--name=harness_designer'])
        # args.extend(['--version-file=builder/version_info.txt'])
        # args.extend(['--manifest=builder/harness_designer.MANIFEST'])
        #
        # '--win-private-assemblies'
        # '--win-no-prefer-redirects'
    elif sys.platform.startswith('darwin'):
        args.extend(['--icon=harness_designer/image/icon_256x256.png'])
    else:
        pass

    # '--windowed'
    args += ['--collect-all=harness_designer', '--noconfirm', script]

    PyInstaller.__main__.run(args)


if __name__ == '__main__':

    if sys.platform.startswith('win'):
        import ctypes
        import comtypes._safearray  # NOQA

        setattr(comtypes._safearray, 'VARIANT_BOOL', ctypes.c_short)  # NOQA

        import pyMSVC

        environment = pyMSVC.setup_environment()
        print(environment)
        print()

    main(sys.argv[1:])
