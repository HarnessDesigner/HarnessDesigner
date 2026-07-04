# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os

try:
    from . import utils_
except ImportError:
    import utils_


def run(hd_path):
    bvh_path = os.path.join(hd_path, 'ray_tracing/bvh.pyx')
    culling_path = os.path.join(hd_path, 'gl/canvas3d/culling.pyx')
    files = [bvh_path, culling_path]

    import numpy

    for path in files:
        with open(path, 'r') as f:

            data = f.read()

        data = data.split('\n')

        data[0] = (
            f'# distutils: include_dirs = {numpy.get_include()}\n'
            '# distutils: define_macros = NPY_NO_DEPRECATED_API=NPY_1_7_API_VERSION'
        )
        data = '\n'.join(data)

        with open(path, 'w') as f:
            f.write(data)

    from Cython.Build import Cythonize

    for file in files:
        Cythonize.main(['-3', '--build', '--inplace', file])

    # utils_.cleanup_after_compile(hd_path)
