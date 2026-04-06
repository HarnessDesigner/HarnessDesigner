
def main():
    import sys

    base_import = list(sys.modules.keys())

    import os
    import shutil
    from builder import spawn

    build_installer = False
    installer_args = []

    for i, arg in enumerate(sys.argv[:]):

        if arg == '--installer':
            sys.argv.remove(arg)
            build_installer = True

        if arg == '--no-cython-wx':
            sys.argv.remove(arg)
            installer_args.append('--no-cython-wx')

        if arg == '--no-cython':
            sys.argv.remove(arg)
            installer_args.append('--no-cython')

        if arg == '--no-pyi-rename':
            sys.argv.remove(arg)
            installer_args.append('--no-pyi-rename')

    if sys.platform.startswith('win'):
        import ctypes
        import comtypes._safearray  # NOQA

        setattr(comtypes._safearray, 'VARIANT_BOOL', ctypes.c_short)  # NOQA

        import pyMSVC

        env = pyMSVC.setup_environment()
        print(env)
        print()

    from setuptools import setup

    p_cmd = (
        'cd libs/assimp&&'
        'cmake -G Ninja -DASSIMP_BUILD_TESTS=off -DASSIMP_INSTALL=off -S . -B build&&'
        'cd build&&'
        'ninja'
    )

    spawn.spawn(p_cmd)

    base_path = os.path.dirname(__file__)

    assimp_binary_path = os.path.join(base_path, 'libs/assimp/build/bin')
    assimp_path = os.path.join(base_path, 'libs/assimp/port/PyAssimp')
    assimp_lib_path = os.path.join(assimp_path, 'pyassimp')

    toml_path = os.path.join(assimp_path, 'pyproject.toml')

    if os.path.exists(toml_path):
        os.rename(toml_path, toml_path + '.bak')

    assimp_files = []
    for file in os.listdir(assimp_binary_path):
        src = os.path.join(assimp_binary_path, file)
        dst = os.path.join(assimp_lib_path, file)

        assimp_files.append(dst)
        shutil.copyfile(src, dst)

    os.environ['PATH'] += os.pathsep + assimp_binary_path

    os.chdir(assimp_path)
    setup(
        name='pyassimp',
        version='5.2.5',
        description='Python bindings for the Open Asset Import Library (ASSIMP)',
        url='https://github.com/assimp/assimp',
        author='ASSIMP developers',
        zip_safe=False,
        author_email='assimp-discussions@lists.sourceforge.net',
        maintainer='Séverin Lemaignan',
        maintainer_email='severin@guakamole.org',
        packages=['pyassimp'],
        include_package_data=True,
        package_data={
            'pyassimp': assimp_files,
            'share/pyassimp': ['README.rst'],
            'share/examples/pyassimp': ['scripts/' + f for f in
                                        os.listdir('scripts/')]
        },
        install_requires=['numpy==2.2.6']
    )

    os.chdir(base_path)

    from builder import build_pyx

    build_pyx.run('harness_designer')

    from setuptools import find_packages

    packages = ['harness_designer.' + pack for pack in find_packages("harness_designer")]
    packages.insert(0, 'harness_designer')

    setup(
        name="harness_designer",
        version="0.0.1",
        author='Kevin G. Schlosser',
        description="Wiring harness design software.",
        url="https://github.com/HarnessDesigner/HarnessDesigner",
        packages=packages,
        zip_safe=False,
        setup_requires=[
            "wheel==0.46.3",
            "wxPython==4.2.5",
            "pyinstaller==6.19.0",
            "pyMSVC@git+https://github.com/kdschlosser/python_msvc ; sys_platform=='win32'",
        ],
        install_requires=[
            "PyOpenGL==3.1.10",
            "PyOpenGL-accelerate==3.1.10",
            "PyMuPDF==1.26.7",
            "requests==2.32.5",
            "mysql-connector-python==9.5.0",
            "numpy==2.2.6",
            "pillow==12.1.0",
            "ezdxf==1.4.3",
            "scipy==1.17.0",
            "sympy==1.14.0",
            "wxPython==4.2.5",
            "opencv-python==4.12.0.88",
            "pyfqmr==0.5.0",
            "meshio==5.3.5",
            "ifcopenshell==0.8.4.post1",
            "build123d==0.10.0",
            "pyinstaller==6.19.0",
            "numpy==2.2.6",
            "keyring==25.7.0",
            "pyassimp"  # @ file:///" + os.path.join(base_path, 'libs/assimp/port/PyAssimp')
        ]
    )

    while base_path in sys.path:
        sys.path.remove(base_path)

    path = 'harness_designer'

    import harness_designer

    hd_path = os.path.dirname(harness_designer.__file__)

    def iter_harness_designer(p=''):
        if p:
            dpath = os.path.join(path, p)
        else:
            dpath = path

        for file_path in os.listdir(dpath):
            if file_path == '__pycache__':
                continue

            src_ = os.path.join(dpath, file_path)
            if os.path.isdir(src_):
                if p:
                    iter_harness_designer(os.path.join(p, file_path))
                else:
                    iter_harness_designer(file_path)

            elif (
                src_.endswith('.png') or
                src_.endswith('.pyi') or
                src_.endswith('.pyd') or
                src_.endswith('.so')
            ):
                if p:
                    dst_ = os.path.join(hd_path, p)
                else:
                    dst_ = os.path.join(hd_path)

                if not os.path.exists(dst_):
                    os.makedirs(dst_)

                dst_ = os.path.join(dst_, file_path)

                shutil.copyfile(src_, dst_)

    iter_harness_designer()

    if build_installer:

        from builder import build

        build.main(installer_args)

    if build_installer:
        from builder import build

        build.build_installer(base_import)


if __name__ == '__main__':
    main()
