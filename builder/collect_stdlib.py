import os
import sys


def get_modules():

    for item in sys.path:
        if item.endswith('Lib'):
            python_stdlib = item

            break
    else:
        raise RuntimeError('error locating the python standard library')

    std_lib = []

    for item in os.listdir(python_stdlib):
        if item.endswith('.py'):
            if item in ('__hello__.py', 'turtle.py'):
                continue

            std_lib.append(f'--hidden-import={item[:-3]}')
        else:
            if item in (
                '__pycache__', 'unittest', 'test',
                '__phello__', 'turtledemo', 'site-packages'
            ):
                continue

            path = os.path.join(python_stdlib, item)

            if os.path.isdir(path):
                std_lib.append(f'--collect-all={item}')

    return std_lib

