import os
import sys


def get_appdata():
    user_profile = os.path.expanduser('~')

    if sys.platform.startswith('win'):
        app_data = os.path.join('appdata', 'roaming', 'HarnessMaker')
    else:
        app_data = '.HarnessMaker'

    app_data = os.path.join(user_profile, app_data)
    if not os.path.exists(app_data):
        os.mkdir(app_data)

    return app_data

