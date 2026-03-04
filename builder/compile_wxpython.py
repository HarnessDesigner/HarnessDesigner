import os

try:
    from . import utils
except ImportError:
    import utils


def run():
    import wx

    wx_path = os.path.dirname(wx.__file__)

    cfiles = utils.iter_mod_path(wx_path)

    from Cython.Build import Cythonize

    try:
        Cythonize.main(['-3', '--build', f'--parallel={os.cpu_count()}', '--inplace', '--keep-going'] + cfiles)
    except RuntimeError:
        pass
    else:
        utils.cleanup_after_compile(wx_path, False)
