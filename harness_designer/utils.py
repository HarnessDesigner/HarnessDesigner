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


def remap(value, old_min, old_max, new_min, new_max):
    old_range = old_max - old_min
    new_range = new_max - new_min
    new_value = (((value - old_min) * new_range) / old_range) + new_min
    return new_value

