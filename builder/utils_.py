# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os
import shutil
import traceback


IGNORE_PATH = [
    '__pycache__'
]


def iter_mod_path(p, ignore_files=()):
    res = []

    for f in os.listdir(p):
        if f in IGNORE_PATH:
            continue
        if f in ignore_files:
            continue

        file_path = os.path.join(p, f)
        if os.path.isdir(file_path):
            res.extend(iter_mod_path(file_path, ignore_files))
        else:
            c = file_path[:-2] + 'c'

            if os.path.exists(c):
                os.remove(c)

            if not f.endswith('.py'):
                continue

            if '__init__' in f or '__main__' in f:
                continue

            res.append(file_path)

    return res


def cleanup_after_compile(p):
    res = []

    pyd_files = []
    c_files = []
    py_files = []
    pyx_files = []

    for f in os.listdir(p):
        if f.endswith('.py'):
            py_files.append(f)
        elif f.endswith('.c'):
            c_files.append(f)
        elif f.endswith('.pyx'):
            pyx_files.append(f)
        elif f.endswith('.pyd') or f.endswith('.so'):
            pyd_files.append(f)

    for f in os.listdir(p):
        if f in IGNORE_PATH:
            continue

        file_path = os.path.join(p, f)

        if os.path.isdir(file_path):

            if f == 'build':
                shutil.rmtree(file_path)
            else:
                cleanup_after_compile(file_path)
        else:
            if '__init__' in f or '__main__' in f:
                continue

            if f.endswith('.py'):
                filename = os.path.splitext(f)[0]
                for pyd in pyd_files:
                    # we specifically check filenames this way because some
                    # files might have matching names up to a point. we don't
                    # want to be removing the wrong file.
                    if pyd.startswith(filename + '.cp311') or pyd.startswith(filename + '.cpython'):
                        try:
                            os.remove(file_path)
                        except:  # NOQA
                            traceback.print_exc()
                        break

                for c in c_files:
                    if c.startswith(filename):
                        try:
                            os.remove(os.path.join(p, c))
                        except:  # NOQA
                            traceback.print_exc()

                        break

                for pyx in pyx_files:
                    if pyx.startswith(filename):
                        try:
                            os.remove(os.path.join(p, pyx))
                        except:  # NOQA
                            traceback.print_exc()

                        break

    return res
