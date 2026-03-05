import os
import shutil


IGNORE_PATH = [
    '__pycache__'
]


def iter_mod_path(p):
    res = []

    for f in os.listdir(p):
        if f in IGNORE_PATH:
            continue

        file_path = os.path.join(p, f)
        if os.path.isdir(file_path):
            res.extend(iter_mod_path(file_path))
        else:
            c = file_path[:2] + 'c'

            if os.path.exists(c):
                os.remove(c)

            if not f.endswith('.py'):
                continue

            if '__init__' in f or '__main__' in f:
                continue

            res.append(file_path)

    return res


def cleanup_after_compile(p, remove_py=False, rename_py=False):
    res = []

    for f in os.listdir(p):
        if f in IGNORE_PATH:
            continue

        file_path = os.path.join(p, f)
        if os.path.isdir(file_path):

            if f == 'build':
                shutil.rmtree(file_path)
            else:
                cleanup_after_compile(file_path, remove_py, rename_py)
        else:
            if '__init__' in f or '__main__' in f:
                continue

            if f.endswith('.py'):

                c = file_path[:-2] + 'c'

                if os.path.exists(c):
                    os.remove(c)
                else:
                    continue

                if remove_py or rename_py:
                    for compiled_file in os.listdir(p):
                        if (
                            not compiled_file.endswith('.so') and
                            not compiled_file.endswith('.pyd')
                        ):
                            continue

                        if not compiled_file.startswith(f[:-2]):
                            continue

                        if remove_py:
                            os.remove(file_path)
                        elif rename_py:
                            os.rename(file_path, file_path + 'i')

    return res
