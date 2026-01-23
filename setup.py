import os
import sys


if __name__ == '__main__':
    def iter_remove(p):
        for file in os.listdir(p):
            file = os.path.join(p, file)

            if os.path.isdir(file):
                iter_remove(file)
            elif file.endswith('.c') or file.endswith('.pyd'):
                os.remove(file)
                print(file)


    iter_remove('harness_designer')

    raise RuntimeError

    if sys.platform.startswith('win'):
        import pyMSVC

        environment = pyMSVC.setup_environment()
        print(environment)

    from Cython.Build import Cythonize

    def iter_file(p):
        res = []
        for file in os.listdir(p):

            if file.endswith('bak'):
                continue

            file = os.path.join(p, file)

            if os.path.isdir(file):
                res.extend(iter_file(file))
            elif file.endswith('.py') and '__init__' not in file:
                res.append(file)

        return res

    files = iter_file('harness_designer')
    for item in files:
        print(item)
    print()

    Cythonize.main(['-3', '--build', '--parallel=16', '--inplace'] + files)
