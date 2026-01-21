import wx

import os

from .ui import splash as _splash
from . import config as _config
from . import utils as _utils


splash: _splash.Splash = None

CONNECTOR_SQLITE = 1
CONNECTOR_MYSQL = 2

MOUSE_NONE = 0x00000000
MOUSE_LEFT = 0x00000001
MOUSE_MIDDLE = 0x00000002
MOUSE_RIGHT = 0x00000004
MOUSE_AUX1 = 0x00000008
MOUSE_AUX2 = 0x00000010
MOUSE_WHEEL = 0x00000020

MOUSE_REVERSE_X_AXIS = 0x80000000
MOUSE_REVERSE_Y_AXIS = 0x40000000
MOUSE_REVERSE_WHEEL_AXIS = 0x20000000
MOUSE_SWAP_AXIS = 0x10000000


class Config(metaclass=_config.Config):

    class editor3d(metaclass=_config.Config):
        ground_height = 0.0
        eye_height = 10.0
        selected_color = [0.3, 0.3, 1.0, 0.45]
        angle_lock_color = [0.3, 0.8, 0.3, 0.45]

        class modeling:
            smooth_wires = True
            smooth_housings = False
            smooth_bundles = True
            smooth_transitions = True
            smooth_terminals = True
            smooth_cpa_locks = False
            smooth_tpa_locks = False
            smooth_boots = True
            smooth_covers = False
            smooth_splices = False
            smooth_markers = True
            smooth_seals = False

        class virtual_canvas(metaclass=_config.Config):
            width = 0
            height = 0

        class movement(metaclass=_config.Config):
            angle_detent = 10.0
            move_detent = 5.0

            angle_snap = -1
            move_snap = -1

        class keyboard_settings(metaclass=_config.Config):
            max_speed_factor = 10.0
            speed_factor_increment = 0.1
            start_speed_factor = 1.0

        class rotate(metaclass=_config.Config):
            mouse = MOUSE_MIDDLE
            up_key = ord('w')
            down_key = ord('s')
            left_key = ord('a')
            right_key = ord('d')
            sensitivity = 0.4

        class pan_tilt(metaclass=_config.Config):
            mouse = MOUSE_LEFT
            up_key = ord('o')
            down_key = ord('l')
            left_key = ord('k')
            right_key = ord(';')
            sensitivity = 0.2

        class truck_pedistal(metaclass=_config.Config):
            mouse = MOUSE_RIGHT
            up_key = ord('8')
            down_key = ord('2')
            left_key = ord('4')
            right_key = ord('6')
            sensitivity = 0.2
            speed = 1.0

        class walk(metaclass=_config.Config):
            mouse = MOUSE_WHEEL | MOUSE_SWAP_AXIS
            forward_key = wx.WXK_UP
            backward_key = wx.WXK_DOWN
            left_key = wx.WXK_LEFT
            right_key = wx.WXK_RIGHT
            sensitivity = 1.0
            speed = 1.0

        class zoom(metaclass=_config.Config):
            mouse = MOUSE_NONE  # | MOUSE_REVERSE_WHEEL_AXIS
            in_key = wx.WXK_ADD
            out_key = wx.WXK_SUBTRACT
            sensitivity = 1.0

        class reset(metaclass=_config.Config):
            key = wx.WXK_HOME
            mouse = MOUSE_NONE

    class database(metaclass=_config.Config):
        connector = CONNECTOR_SQLITE

        class sqlite(metaclass=_config.Config):
            database_path = os.path.join(_utils.get_appdata(), 'harness_designer.db')

        class mysql(metaclass=_config.Config):
            host = 'local_host'
            port = 3306
            compress = False
            oci_config_file = ''
            oci_config_profile = 'DEFAULT'
            kerberos_auth_mode = 'SSPI'
            force_ipv6 = False
            ssl_verify_identity = False
            ssl_verify_cert = False
            ssl_key = ''  # path to ssl key file
            ssl_disabled = False
            ssl_cert = ''  # path to ssl certificate file
            ssl_ca = ''  # path to ssl certificate authority file
            tls_versions = ['TLSv1.2', 'TLSv1.3']
            buffered = False
            write_timeout = None
            read_timeout = None
            connection_timeout = None
            client_flags = None
            sql_mode = []
            auth_plugin = ''
            openid_token_file = ''  # Path to the file containing the OpenID JWT formatted identity token.

            database_name = 'harness_maker'
            recent_projects = []
            recent_users = []

            class settings_dialog(metaclass=_config.Config):
                size = (950, 950)
                pos = (0, 0)


class App(wx.App):
    def OnInit(self):
        global splash

        splash = _splash.Splash(None)
        splash.Show()
        return True

    def OnExit(self):
        Config.close()

        return wx.App.OnExit(self)


_app = None


def __main__():
    global _app
    _app = App()
    _app.MainLoop()
