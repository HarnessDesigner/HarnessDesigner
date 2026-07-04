# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os
from . import utils_


def run(hd_path):

    cfiles = utils_.iter_mod_path(hd_path)

    from Cython.Build import Cythonize

    Cythonize.main(['-3', '--build', f'--parallel={os.cpu_count()}', '--inplace', '--keep-going'] + cfiles)

    utils_.cleanup_after_compile(hd_path)
