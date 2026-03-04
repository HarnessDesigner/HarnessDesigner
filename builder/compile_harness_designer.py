import os

try:
    from . import utils
except ImportError:
    import utils


def run(rename_py):

    import harness_designer

    hd_path = os.path.dirname(harness_designer.__file__)

    cfiles = utils.iter_mod_path(hd_path)

    from Cython.Build import Cythonize

    Cythonize.main(['-3', '--build', f'--parallel={os.cpu_count()}', '--inplace', '--keep-going'] + cfiles)

    remove_py = not rename_py

    utils.cleanup_after_compile(hd_path, remove_py, rename_py)
