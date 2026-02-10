from typing import TYPE_CHECKING

import wx
import wxOpenGL
from wxOpenGL import config as _config
import os
from . import utils as _utils


if TYPE_CHECKING:
    from .ui import splash as _splash

splash: "_splash.Splash" = None

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


class Config(metaclass=_config.ConfigDB):

    editor3d = wxOpenGL.Config

    selected_color = [0.78, 0.2, 1.0, 1.0]

    class axis_overlay(metaclass=_config.ConfigDB):
        is_visible = True
        size = (150, 150)
        position = (830, 245)

    class modeling(metaclass=_config.ConfigDB):
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

    class database(metaclass=_config.ConfigDB):
        connector = CONNECTOR_SQLITE

        class sqlite(metaclass=_config.ConfigDB):
            database_path = os.path.join(_utils.get_appdata(), 'harness_designer.db')

        class mysql(metaclass=_config.ConfigDB):
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

            database_name = 'harness_designer'
            recent_projects = []
            recent_users = []

            class settings_dialog(metaclass=_config.ConfigDB):
                size = (950, 950)
                pos = (0, 0)

    class mainframe(metaclass=_config.ConfigDB):
        position = ()
        size = ()

        ui_perspective = (
            'layout2|'
            'name=editor_toolbar;caption=;state=2108156;dir=1;layer=10;row=0;pos=0;prop=100000;bestw=408;besth=42;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1|'
            'name=editors;caption=;state=2944;dir=5;layer=0;row=0;pos=0;prop=100000;bestw=20;besth=20;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1|'
            'name=db_editor;caption=DB Editor;state=12603388;dir=3;layer=0;row=0;pos=0;prop=100000;bestw=20;besth=20;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1|'
            'name=obj_selected;caption=Selected Object;state=12587004;dir=2;layer=0;row=0;pos=0;prop=100000;bestw=20;besth=20;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1|'
            'name=editor2d_toolbar;caption=;state=2108156;dir=3;layer=10;row=0;pos=0;prop=100000;bestw=10;besth=5;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1|'
            'dock_size(1,10,0)=44|'
            'dock_size(5,0,0)=22|'
            'dock_size(3,0,0)=171|'
            'dock_size(2,0,0)=254|'
            'dock_size(3,10,0)=10|'
        )

    class project(metaclass=_config.ConfigDB):
        recent_projects = []


class App(wx.App):
    def OnInit(self):
        global splash

        from .ui import splash as _splsh

        splash = _splsh.Splash(None)
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
