
import wx
import sqlite3
import weakref
import threading

import os
from . import utils as _utils

CONNECTOR_SQLITE = 0


_lock = threading.RLock()

DEBUG_CONFIG = False


def DEBUG(*args):
    if DEBUG_CONFIG:
        args = ' '.join(str(item) for item in args)
        print(args)


class _ConfigTable:
    """
    This class represents a table in the sqlite database.

    This class mimicks some of the features of a dictionary so the saved
    entries are able to be accessed by using the attribute name as a key.
    """

    def __init__(self, con, name):
        self._con = con
        self.name = name

    def __contains__(self, item):
        with _lock:
            with self._con:
                cur = self._con.cursor()
                cur.execute(f'SELECT id FROM {self.name} WHERE key = "{item}";')
                DEBUG('__contains__.SELECT:', self.name, item)
                if cur.fetchall():
                    cur.close()
                    return True

                cur.close()

            return False

    def __getitem__(self, item):
        with _lock:
            with self._con:
                cur = self._con.cursor()

                cur.execute(f'SELECT value FROM {self.name} WHERE key = "{item}";')
                value = cur.fetchall()[0][0]

                DEBUG('__getitem__.SELECT:', self.name, item, value)
                cur.close()

            try:
                return eval(value)
            except:  # NOQA
                return value

    def __setitem__(self, key, value):
        value = str(value)

        if key not in self:
            with _lock:
                with self._con:
                    cur = self._con.cursor()
                    DEBUG('__setitem__.INSERT:', self.name, key, value)

                    cur.execute(f'INSERT INTO {self.name} (key, value) VALUES(?, ?);', (key, value))
                    self._con.commit()
                    cur.close()
        else:
            with _lock:
                with self._con:
                    cur = self._con.cursor()
                    DEBUG('__setitem__.UPDATE:', self.name, key, value)
                    cur.execute(f'UPDATE {self.name} SET value = "{value}" WHERE key = "{key}";')

                    self._con.commit()
                    cur.close()

    def __delitem__(self, key):
        with _lock:
            with self._con:
                cur = self._con.cursor()
                DEBUG('__delitem__.DELETE:', self.name, key)

                cur.execute(f'DELETE FROM {self.name} WHERE key = "{key}"')
                self._con.commit()
                cur.close()


class _ConfigDB:
    """
    This class handles the actual connection to the sqlite database.

    Handles what table in the database is to be accessed. The tables are
    not cached because most of the information that is stored only gets loaded
    when the application starts and data gets saved to the database if a value
    gets modified and also when the application exits.
    """

    def __init__(self):
        self._con = None
        self.save_all = False

    def open(self):
        if self._con is not None:
            raise RuntimeError('The config database is already open')

        path = os.path.join(_utils.get_appdata(), 'config.db')

        self.save_all = not os.path.exists(path)
        self._con = sqlite3.connect(path, check_same_thread=False)

    def __contains__(self, item):
        with _lock:
            with self._con:
                cur = self._con.cursor()
                cur.execute('SELECT name FROM sqlite_master WHERE type="table";')
                tables = [row[0] for row in cur.fetchall()]
                cur.close()

            ret = item in tables
            DEBUG('__contains__.table.SELECT:', item, ret)

            return ret

    def __getitem__(self, item):
        with _lock:
            if item not in self:
                with self._con:
                    cur = self._con.cursor()
                    DEBUG('__getitem__.table.CREATE:', item)

                    cur.execute(f'CREATE TABLE {item}('
                                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                                'key TEXT UNIQUE NOT NULL, '
                                'value TEXT NOT NULL'
                                ');')
                    self._con.commit()
                    cur.close()

            return _ConfigTable(self._con, item)

    def close(self):
        with _lock:
            self._con.close()


class ConfigDB(type):
    __db__ = _ConfigDB()
    __classes__ = []
    __callbacks__ = {}

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        ConfigDB.__classes__.append(cls)
        ConfigDB.__callbacks__[cls] = {}

    def bind(cls, callback, setting_name):
        if setting_name not in ConfigDB.__callbacks__[cls]:
            ConfigDB.__callbacks__[cls][setting_name] = []

        for ref in ConfigDB.__callbacks__[cls][setting_name][:]:
            cb = ref()
            if cb is None:
                ConfigDB.__callbacks__[cls][setting_name].remove(cb)
            elif callback == cb:
                break
        else:
            ref = weakref.WeakMethod(weakref, cls._remove_ref)
            ConfigDB.__callbacks__[cls][setting_name].append(ref)

    def _remove_ref(cls, ref):
        for refs in ConfigDB.__callbacks__[cls].values():
            if ref in refs:
                refs.remove(ref)
                return

    def _load(cls):
        for key in dir(cls):
            if key.startswith('_'):
                continue

            if cls.__table_name__ in ConfigDB.__db__:
                if key in cls.__table__:
                    type.__setattr__(cls, key, cls.__table__[key])

    def _save(cls):
        for key in dir(cls):
            if key.startswith('_'):
                continue

            value = getattr(cls, key)

            if callable(value):
                continue

            cls.__table__[key] = value
            DEBUG('_save:', cls.__name__, cls.__table_name__, key, repr(value), '\n\n')

    def _process_change(cls, setting_name):
        if setting_name in ConfigDB.__callbacks__[cls]:
            for ref in ConfigDB.__callbacks__[cls][setting_name][:]:
                cb = ref()
                if cb is None:
                    ConfigDB.__callbacks__[cls][setting_name].remove(ref)
                else:
                    cb(cls, setting_name)

    @property
    def __table_name__(cls):
        name = f'{cls.__module__.split(".", 1)[-1]}_{cls.__qualname__}'
        name = name.replace(".", "_")
        name = name.replace('harness_designer_config_Config_', '')
        name = name.replace('_Config', '')
        return name

    @property
    def __table__(cls):
        return ConfigDB.__db__[cls.__table_name__]

    def __getitem__(cls, item):
        DEBUG('__getitem__:', cls.__table_name__, cls.__name__, item)
        value = getattr(cls, item)

        return value

    def __getattribute__(cls, item):
        if item.startswith('_'):
            return type.__getattribute__(cls, item)

        try:
            value = type.__getattribute__(cls, item)
            DEBUG('type.__getattribute__:', cls.__table_name__, cls.__name__, item, repr(value), '\n')
            return value
        except AttributeError:
            pass

        if item in cls.__table__:
            value = cls.__table__[item]
            DEBUG('__getattribute__:', cls.__table_name__, cls.__name__, item, repr(value), '\n')

            return value

        raise AttributeError(item)

    def __setitem__(cls, key, value):
        DEBUG('__setitem__:', cls.__table_name__, cls.__name__, key, repr(value))

        setattr(cls, key, value)

    def __setattr__(cls, key, value):
        if key.startswith('_'):
            type.__setattr__(cls, key, value)

        else:
            DEBUG('__setattr__:', cls.__table_name__, cls.__name__, key, repr(value), '\n')
            type.__setattr__(cls, key, value)

            cls.__table__[key] = value
            cls._process_change(key)

    def __delitem__(cls, key):
        delattr(cls, key)

    def __delattr__(cls, item):
        if item in cls.__table__:
            del cls.__table__[item]

        type.__delattr__(cls, item)

    @staticmethod
    def open():
        ConfigDB.__db__.open()

        for cls in ConfigDB.__classes__:
            cls._load()

    @staticmethod
    def close():
        for cls in ConfigDB.__classes__:
            cls._save()

        ConfigDB.__db__.close()


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


class Config(metaclass=ConfigDB):

    class ray_trace(metaclass=ConfigDB):

        enable_reflections = True
        enable_depth_of_field = True
        resolutions = [
            {'label': '640x360 (360p LD) (16:9)', 'width': 640, 'height': 360},
            {'label': '480x360 (360p LD) (4:3)', 'width': 480, 'height': 360},
            {'label': '720x480 (480p SD) (16:9)', 'width': 720, 'height': 480},
            {'label': '640x480 (480p SD) (4:3)', 'width': 640, 'height': 480},
            {'label': '1280x544 (UW 720p HD) (21:9)', 'width': 1280, 'height': 544},
            {'label': '1280x720 (720p HD) (16:9)', 'width': 1280, 'height': 720},
            {'label': '960x720 (720p HD) (4:3)', 'width': 960, 'height': 720},
            {'label': '1920x816 (UW 1080p) (FHD 21:9)', 'width': 1920, 'height': 816},
            {'label': '1920x1080 (1080p) (FHD 16:9)', 'width': 1920, 'height': 1080},
            {'label': '1440x1080 (1080i) (FHD  4:3)', 'width': 1440, 'height': 1080},
            {'label': '2048x870 (UW 2K) (21:9)', 'width': 2048, 'height': 870},
            {'label': '2048x1152 (2K) (16:9)', 'width': 2048, 'height': 1152},
            {'label': '1536x1152 (2K) (4:3)', 'width': 1536, 'height': 1152},
            {'label': '2880x1226 (UW 3K UHD) (21:9)', 'width': 2880, 'height': 1226},
            {'label': '2880x1620 (3K UHD) (16:9)', 'width': 2880, 'height': 1620},
            {'label': '2160x1620 (3K UHD) (4:3)', 'width': 2160, 'height': 1620},
            {'label': '3072x1306 (UW 3K) (21:9)', 'width': 3072, 'height': 1306},
            {'label': '3072x1728 (3K) (16:9)', 'width': 3072, 'height': 1728},
            {'label': '2304x1728 (3K) (4:3)', 'width': 2304, 'height': 1728},
            {'label': '3840x1634 (UW 4K UHD) (21:9)', 'width': 3840, 'height': 1634},
            {'label': '3840x2160 (4K UHD) (16:9)', 'width': 3840, 'height': 2160},
            {'label': '2880x2160 (4K UHD) (4:3)', 'width': 2880, 'height': 2160},
            {'label': '4096x1742 (UW 4K) (21:9)', 'width': 4096, 'height': 1742},
            {'label': '4096x2304 (4K) (16:9)', 'width': 4096, 'height': 2304},
            {'label': '3072x2304 (4K) (4:3)', 'width': 3072, 'height': 2304},
            {'label': '5120x2178 (UW 5K) (21:9)', 'width': 5120, 'height': 2178},
            {'label': '5120x2880 (5K) (16:9)', 'width': 5120, 'height': 2880},
            {'label': '3840x2880 (5K) (4:3)', 'width': 3840, 'height': 2880},
            {'label': '6144x2614 (UW 6K) (21:9)', 'width': 6144, 'height': 2614},
            {'label': '6144x3456 (6K) (16:9)', 'width': 6144, 'height': 3456},
            {'label': '4608x3456 (6K) (4:3)', 'width': 4608, 'height': 3456},
            {'label': '7680x3268 (UW 8K UHD) (21:9)', 'width': 7680, 'height': 3268},
            {'label': '7680x4320 (8K UHD) (16:9)', 'width': 7680, 'height': 4320},
            {'label': '5760x3456 (8K UHD) (4:3)', 'width': 5760, 'height': 3456},
            {'label': '8192x3486 (UW 8K) (21:9)', 'width': 8192, 'height': 3486},
            {'label': '8192x4608 (8K) (16:9)', 'width': 8192, 'height': 4608},
            {'label': '6144x4608 (8K) (4:3)', 'width': 6144, 'height': 4608},
            {'label': '15360x6480 (UW 16K) (21:9)', 'width': 15360, 'height': 6480},
            {'label': '15360x8640 (16K) (16:9)', 'width': 15360, 'height': 8640},
            {'label': '32768x13824 (UW 32K) (21:9)', 'width': 32768, 'height': 13824},
            {'label': '30720x17280 (32K) (16:9)', 'width': 30720, 'height': 17280}
        ]

        default_resolution = '7680x3268 (UW 8K UHD) (21:9)'

        class background:
            color1 = [0.18, 0.20, 0.22]
            color2 = [0.18, 0.20, 0.22]

            enable_gradient = True

        class environment_map(metaclass=ConfigDB):
            enable = True
            generate = True
            path = ''

        class shadows(metaclass=ConfigDB):
            enable = True
            softness = 1.0

        class ambient_occlusion(metaclass=ConfigDB):
            enable = False
            samples = 8.0
            radius = 0.5

        class lighting(metaclass=ConfigDB):
            ambient_intensity = 0.2
            lights = [
                {
                    'position': [0.0, 0.0, 0.0],
                    'intensity': 1.0,
                    'color': [1.0, 1.0, 1.0],
                }
            ]

    class editor2d(metaclass=ConfigDB):

        class virtual_canvas(metaclass=ConfigDB):
            width = 1920
            height = 1080

        class angle(metaclass=ConfigDB):
            lock = False
            lock_increment = 90.0

        class grid(metaclass=ConfigDB):
            enabled = True
            size = 8000
            snap = False

        class zoom(metaclass=ConfigDB):
            mouse = MOUSE_WHEEL  # | MOUSE_REVERSE_WHEEL_AXIS
            in_key = wx.WXK_ADD
            out_key = wx.WXK_SUBTRACT
            sensitivity = 5.0

        class pan(metaclass=ConfigDB):
            mouse = MOUSE_LEFT
            up_key = wx.WXK_UP
            down_key = wx.WXK_DOWN
            left_key = wx.WXK_LEFT
            right_key = wx.WXK_RIGHT
            sensitivity = 0.4

        class reset(metaclass=ConfigDB):
            key = wx.WXK_HOME
            mouse = MOUSE_NONE

        class canvas(metaclass=ConfigDB):
            width = 3840
            height = 2160

    class editor3d(metaclass=ConfigDB):
        background_color = [0.20, 0.20, 0.20, 1.0]
        selected_color = [0.2, 0.6, 0.2, 0.35]

        class lighting(metaclass=ConfigDB):
            position = [100.0, 100.0, 100.0]
            ambient = [0.4, 0.4, 0.4, 1.0]
            diffuse = [0.8, 0.8, 0.8, 1.0]
            specular = [1.0, 1.0, 1.0, 1.0]

        class renderer(metaclass=ConfigDB):
            smooth_covers = True
            smooth_boots = True
            smooth_housings = True
            smooth_wires = True
            smooth_bundles = True
            smooth_seals = True
            smooth_cpa_locks = True
            smooth_tpa_locks = True
            smooth_terminals = True

        class focal_target(metaclass=ConfigDB):
            enable = True
            color = [1.0, 0.4, 0.4, 1.0]
            radius = 0.25

        class floor(metaclass=ConfigDB):
            enable = True
            ground_height = 0.0
            distance = 1000
            enable_floor_lock = True

            class grid(metaclass=ConfigDB):
                primary_color = [0.2039, 0.2549, 0.2902, 0.8]
                secondary_color = [0.2925, 0.3430, 0.3430, 0.8]
                size = 50
                enable = True

            class reflections(metaclass=ConfigDB):
                enable = True
                strength = 50.0

        class virtual_canvas(metaclass=ConfigDB):
            width = 1920
            height = 1080

        class keyboard_settings(metaclass=ConfigDB):
            max_speed_factor = 10.0
            speed_factor_increment = 0.1
            start_speed_factor = 1.0

        class rotate(metaclass=ConfigDB):
            mouse = MOUSE_MIDDLE
            up_key = ord('w')
            down_key = ord('s')
            left_key = ord('a')
            right_key = ord('d')
            sensitivity = 0.4

        class pan_tilt(metaclass=ConfigDB):
            mouse = MOUSE_LEFT
            up_key = ord('o')
            down_key = ord('l')
            left_key = ord('k')
            right_key = ord(';')
            sensitivity = 0.2

        class truck_pedestal(metaclass=ConfigDB):
            mouse = MOUSE_RIGHT
            up_key = ord('8')
            down_key = ord('2')
            left_key = ord('4')
            right_key = ord('6')
            sensitivity = 0.2
            speed = 1.0

        class walk(metaclass=ConfigDB):
            mouse = MOUSE_WHEEL | MOUSE_SWAP_AXIS
            forward_key = wx.WXK_UP
            backward_key = wx.WXK_DOWN
            left_key = wx.WXK_LEFT
            right_key = wx.WXK_RIGHT
            sensitivity = 1.0
            speed = 5.0

        class zoom(metaclass=ConfigDB):
            mouse = MOUSE_NONE  # | MOUSE_REVERSE_WHEEL_AXIS
            in_key = wx.WXK_ADD
            out_key = wx.WXK_SUBTRACT
            sensitivity = 5.0

        class reset(metaclass=ConfigDB):
            key = wx.WXK_HOME
            mouse = MOUSE_NONE

        class headlight(metaclass=ConfigDB):
            enable = True
            cutoff = 8.0
            dissipate = 50.0
            color = [0.6, 0.6, 0.4, 0.8]

        class axis_overlay(metaclass=ConfigDB):
            is_visible = True
            size = (150, 150)
            position = (830, 245)

    class logging(metaclass=ConfigDB):
        save_path = os.path.join(_utils.get_appdata(), 'log')
        num_archives = 10
        num_logfiles = 10
        max_logfile_size = 10485760
        log_notice = True
        log_warning = True
        log_debug = True
        log_traceback = True
        log_error = True
        log_wx_error = True
        log_database = False
        log_file_transfers = True

    class debug:
        class functions(metaclass=ConfigDB):
            log_args = False
            log_duration = True

        class rendering3d(metaclass=ConfigDB):
            draw_obb = False
            draw_aabb = False
            draw_normals = False
            draw_edges = False
            draw_vertices = False
            draw_faces = True
            edge_color_dark = [0.7, 0.7, 0.7]  # For dark materials
            edge_color_light = [0.0, 0.0, 0.0]  # For light materials
            edge_luminance_threshold = 0.5  # Brightness cutoff
            vertices_color = [1.0, 0.0, 0.0]
            normals_color = [1.0, 1.0, 1.0]

    class colors(metaclass=ConfigDB):
        custom_colors = ''

    class database(metaclass=ConfigDB):
        connector = CONNECTOR_SQLITE
        monitor_duration = 60

        class sqlite(metaclass=ConfigDB):
            database_path = os.path.join(_utils.get_appdata(), 'harness_designer.db')

        class mysql(metaclass=ConfigDB):
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

            class settings_dialog(metaclass=ConfigDB):
                size = (950, 950)
                pos = (0, 0)

    class mainframe(metaclass=ConfigDB):
        position = ()
        size = ()

        ui_perspective = None  # (
        #     'layout2|'
        #     'name=editor_3d;caption=3D Editor;state=2816;dir=5;layer=0;row=0;pos=0;prop=100000;bestw=20;besth=20;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1|'
        #     'name=editor_2d;caption=Schematic Editor;state=12587004;dir=4;layer=0;row=0;pos=0;prop=100000;bestw=20;besth=20;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1|'
        #     'name=editor_db;caption=Database Editor;state=12587004;dir=3;layer=0;row=1;pos=0;prop=100000;bestw=20;besth=20;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=763;floaty=870;floatw=45;floath=59|'
        #     'name=editor_obj;caption=Object Editor;state=12587004;dir=2;layer=0;row=2;pos=0;prop=100000;bestw=20;besth=20;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=1845;floaty=372;floatw=45;floath=59|'
        #     'name=editor_assembly;caption=Assembly Editor;state=12603388;dir=2;layer=0;row=2;pos=1;prop=100000;bestw=20;besth=20;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=1648;floaty=270;floatw=45;floath=59|'
        #     'name=general_toolbar;caption=;state=2106108;dir=2;layer=10;row=0;pos=273;prop=100000;bestw=45;besth=228;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=1828;floaty=402;floatw=-1;floath=-1|'
        #     'name=editor_toolbar;caption=;state=2106108;dir=1;layer=10;row=0;pos=0;prop=100000;bestw=658;besth=45;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=187;floaty=63;floatw=674;floath=84|'
        #     'name=note_toolbar;caption=;state=2106108;dir=2;layer=10;row=0;pos=0;prop=100000;bestw=45;besth=271;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=1877;floaty=124;floatw=-1;floath=-1|'
        #     'name=object_toolbar;caption=;state=2106108;dir=1;layer=10;row=0;pos=660;prop=100000;bestw=400;besth=45;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=857;floaty=128;floatw=-1;floath=-1|'
        #     'name=settings3d_toolbar;caption=;state=2106108;dir=2;layer=10;row=0;pos=503;prop=100000;bestw=45;besth=142;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=1832;floaty=639;floatw=-1;floath=-1|'
        #     'dock_size(5,0,0)=22|'
        #     'dock_size(4,0,0)=565|'
        #     'dock_size(2,10,0)=47|'
        #     'dock_size(1,10,0)=47|'
        #     'dock_size(2,0,2)=247|'
        #     'dock_size(3,0,1)=258|'
        # )

    class project(metaclass=ConfigDB):
        last_project = None
        model_dir = _utils.get_documents()


Config.open()
