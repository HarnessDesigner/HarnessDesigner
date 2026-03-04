
import os

try:
    from . import utils
except ImportError:
    import utils


def run(hd_path):
    pyx_path = os.path.join(hd_path, 'gl/canvas3d/culling.pyx')
    import numpy


    with open(pyx_path, 'r') as f:

        data = f.read()

    data = data.split('\n')

    data[0] = f'# distutils: include_dirs = {numpy.get_include()}'
    data = '\n'.join(data)
    with open(pyx_path, 'w') as f:
        f.write(data)

    from Cython.Build import Cythonize

    Cythonize.main(['-3', '--build', f'--parallel={os.cpu_count()}', '--inplace', pyx_path])

    # utils.cleanup_after_compile(hd_path)
