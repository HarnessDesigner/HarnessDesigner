import os
import utils


def run():
    import wx

    wx_path = os.path.dirname(wx.__file__)

    cfiles = utils.iter_mod_path(wx_path)

    from Cython.Build import Cythonize

    Cythonize.main(['-3', '--build', f'--parallel={os.cpu_count()}', '--inplace', '--keep-going'] + cfiles)

    utils.cleanup_after_compile(wx_path)
