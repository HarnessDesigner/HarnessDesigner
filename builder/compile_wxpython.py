import os

try:
    from . import utils_
except ImportError:
    import utils_


def run():
    import wx

    wx_path = os.path.dirname(wx.__file__)

    cfiles = utils_.iter_mod_path(wx_path)

    from Cython.Build import Cythonize

    try:
        Cythonize.main(['-3', '--build', f'--parallel={os.cpu_count()}', '--inplace', '--keep-going'] + cfiles)
    except RuntimeError:
        pass
    else:
        utils_.cleanup_after_compile(wx_path, False)
