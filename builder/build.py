

def main(args):
    import argparse

    try:
        from . import spawn
    except ImportError:
        import spawn

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
        try:
            from . import compile_wxpython
        except ImportError:
            import compile_wxpython

        compile_wxpython.run()

    if cython:
        try:
            from . import compile_harness_designer
        except ImportError:
            import compile_harness_designer

        compile_harness_designer.run(pyi_rename)


def build_installer(base_import):
    import sys
    import os

    try:
        from . import collect_stdlib
        from . import collect_modules
    except ImportError:
        import collect_stdlib
        import collect_modules

    base_path = os.path.abspath(os.path.dirname(__file__))

    std_lib = collect_stdlib.get_modules()
    modules = collect_modules.get_modules()
    #
    # manifest_path = os.path.join(base_path, 'harness_designer.MANIFEST')
    #
    # manifest = (
    #     '<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">\n'
    #     '<dependency>\n'
    #     '    <dependentAssembly>\n'
    #     '       <assemblyIdentity type="win32" name="HarnessDesigner.product.HarnessDesigner" version="0.0.1.1" language="*" />\n'
    #     '       <supportedOS id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}" />\n'
    #     '     </dependentAssembly>\n'
    #     '</dependency>\n'
    #     '</assembly>\n'
    # )

    # with open(manifest_path, 'w') as f:
    #     f.write(manifest)

    script = 'run.py'

    args = []
    args += std_lib
    args += modules

    if sys.platform.startswith('win'):
        args.extend(['--icon=../../harness_designer/image/icon_256x256.png'])
        args.extend(['--name=harness_designer'])
        # args.extend(['--version-file=builder/version_info.txt'])
        # args.extend(['--manifest=builder/harness_designer.MANIFEST'])
        #
        # '--win-private-assemblies'
        # '--win-no-prefer-redirects'
    elif sys.platform.startswith('darwin'):
        args.extend(['--icon=../../harness_designer/image/icon_256x256.png'])
    else:
        pass

    args += ['--collect-all=harness_designer', '--noconfirm', '--clean', '--windowed', f'{script}']

    full_imports = set(list(sys.modules.keys()))
    base_import = set(base_import)

    for item in sorted(list(full_imports.difference(base_import))):
        del sys.modules[item]

    cwd = os.getcwd()

    os.chdir(os.path.join(base_path, 'scripts'))

    import gc

    gc.collect()

    import PyInstaller.__main__

    PyInstaller.__main__.run(args)

    os.chdir(cwd)


if __name__ == '__main__':
    import sys

    if sys.platform.startswith('win'):
        import ctypes
        import comtypes._safearray  # NOQA

        setattr(comtypes._safearray, 'VARIANT_BOOL', ctypes.c_short)  # NOQA

        import pyMSVC

        environment = pyMSVC.setup_environment()
        print(environment)
        print()

    main(sys.argv[1:])
