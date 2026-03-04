import os
import sys
import shutil

'c:\python3.11.14\python.exe setup.py build --installer --no-cython-wx --no-cython'


def main():
    from builder import spawn

    build_installer = False
    installer_args = []

    is_build = False

    for i, arg in enumerate(sys.argv[:]):
        if arg == 'build':
            is_build = True

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

    if is_build:
        os.environ['PATH'] += os.pathsep + os.path.dirname(__file__)

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

    data_files = []

    for file in os.listdir('libs/assimp/build/bin'):
        src = f'libs/assimp/build/bin/{file}'
        dst = f'harness_designer/{file}'
        shutil.copyfile(src=src, dst=dst)
        data_files.append(os.path.abspath(dst))

    images_path = 'harness_designer/image'

    def iter_images(p):
        found_files = []
        directories = []

        for image_path in os.listdir(p):
            f = os.path.join(p, image_path)
            if os.path.isdir(f):
                directories.extend(iter_images(f))
            elif f.endswith('.png'):
                found_files.append(f)

        directories.append([p, found_files])

        return directories

    image_data = iter_images(images_path)
    package_data = {'harness_designer': data_files}
    package_data.update({key: value for key, value in image_data})

    base_path = os.path.dirname(__file__)

    setup(
        name="harness_designer",
        version="0.0.1",
        author='Kevin G. Schlosser',
        description="Wiring harness design software.",
        license="GPL",
        keywords="",
        url="https://github.com/HarnessDesigner/HarnessDesigner",
        packages=['harness_designer'],
        include_package_data=True,
        package_data=package_data,
        setup_requires=[
            "wheel==0.46.3",
            "pyMSVC@git+https://github.com/kdschlosser/python_msvc;sys_platform=='win32'",
            "pyinstaller==6.19.0"
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
            "pyassimp @ file:///" + os.path.join(base_path, 'libs/assimp/port/PyAssimp')
        ]
    )

    if build_installer:
        from builder import build

        build.main(installer_args)


if __name__ == '__main__':
    main()



