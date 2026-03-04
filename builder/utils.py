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


def cleanup_after_compile(p, rename_pyi=True):
    res = []

    for f in os.listdir(p):
        if f in IGNORE_PATH:
            continue

        file_path = os.path.join(p, f)
        if os.path.isdir(file_path):
            res.extend(iter_mod_path(file_path))
        else:
            if '__init__' in f or '__main__' in f:
                continue

            if f.endswith('.py'):
                c = file_path[:2] + 'c'

                if os.path.exists(c):
                    os.remove(c)
                
    return res
