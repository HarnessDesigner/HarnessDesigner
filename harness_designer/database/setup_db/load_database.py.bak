import math
import json
import zipfile
import io
import uuid
import os
import sys
import sqlite3
import time
import requests

from PIL import Image


BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


splash = None


if __name__ == '__main__':

    class Splash:

        @staticmethod
        def SetText(_):
            pass


    splash = Splash

    user_profile = os.path.expanduser('~')

    if sys.platform.startswith('win'):
        app_data = os.path.join('appdata', 'roaming', 'HarnessDesigner')
    else:
        app_data = '.HarnessDesigner'

    app_data = os.path.join(user_profile, app_data)

    if not os.path.exists(app_data):
        os.mkdir(app_data)

    con_ = sqlite3.connect(os.path.join(app_data, 'harness_designer.db'))
    cur_ = con_.cursor()

    _settings(con_, cur_, app_data)

    funcs = [
        _boots,
        _terminals,
        _covers,
        _seals,
        _transitions,
        _bundle_covers,
        _housings,
        _splices,
        _wires,
        _wire_markers,
        _tpa_locks,
        _cpa_locks,
    ]

    for func in funcs:
        try:
            func(con_, cur_)
        except:  # NOQA
            import traceback
            traceback.print_exc()

    cur_.close()
    con_.close()
