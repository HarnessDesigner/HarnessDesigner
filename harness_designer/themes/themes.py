# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os


BASE_PATH = os.path.dirname(__file__)


def get_themes():
    return [file for file in os.listdir(BASE_PATH)
            if os.path.isdir(os.path.join(BASE_PATH, file))]


def load_theme(theme_name):
    file_name = os.path.join(BASE_PATH, theme_name, theme_name + '.qss')
    if not os.path.exists(file_name):
        return

    with open(file_name, 'r') as f:
        theme = f.read()

    icon_path = os.path.join(BASE_PATH, theme_name, 'icons')
    icon_path = icon_path.replace('\\', '/')

    theme = theme.replace(':/qss_icons/dark/rc', icon_path)

    import harness_designer as hd

    hd._app.setStyleSheet(theme)
