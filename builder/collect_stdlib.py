# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os
import sys


def get_modules():

    for item in sys.path:
        if item.endswith('Lib'):
            python_stdlib = item

            break
    else:
        python_stdlib = os.path.dirname(os.__file__)
        print('PYTHON_STDLIB:', python_stdlib)

        # raise RuntimeError('error locating the python standard library')

    std_lib = []

    for item in os.listdir(python_stdlib):
        if item.endswith('.py'):
            if item in ('__hello__.py', 'turtle.py'):
                continue

            std_lib.append(f'--hidden-import={item[:-3]}')
        else:
            if item in (
                '__pycache__', 'unittest', 'test',
                '__phello__', 'turtledemo', 'site-packages',
                # These are excluded from the bundle in build.py.  Skipping
                # them here prevents --collect-all from triggering their
                # PyInstaller hooks, which would otherwise declare dozens of
                # hidden imports that then fail with ERROR "not found" because
                # the module itself is excluded.
                'idlelib',      # Python IDLE IDE
                'lib2to3',      # Python 2→3 converter
                'venv',         # virtual-env support (unused in frozen app)
                'tkinter',      # Tk GUI toolkit (app uses PySide6)
            ):
                continue

            path = os.path.join(python_stdlib, item)

            if os.path.isdir(path):
                std_lib.append(f'--collect-all={item}')

    return std_lib

