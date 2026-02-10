
import wx
import sqlite3
import weakref


class _ConfigTable:
    """
    This class represents a table in the sqlite database.

    This class mimicks some of the features of a dictionary so the saved
    entries are able to be accessed by using the attaribute name as a key.
    """

    def __init__(self, con, name):
        self._con = con
        self.name = name

    def __contains__(self, item):
        with self._con:
            cur = self._con.cursor()
            cur.execute(f'SELECT id FROM {self.name} WHERE key = "{item}";')
            if cur.fetchall():
                cur.close()
                return True

            cur.close()

        return False

    def __getitem__(self, item):
        with self._con:
            cur = self._con.cursor()
            cur.execute(f'SELECT value FROM {self.name} WHERE key = "{item}";')
            value = cur.fetchall()[0][0]
            cur.close()

        try:
            return eval(value)
        except:  # NOQA
            return value

    def __setitem__(self, key, value):
        value = str(value)

        if key not in self:
            with self._con:
                cur = self._con.cursor()
                cur.execute(f'INSERT INTO {self.name} (key, value) VALUES(?, ?);', (key, value))
                self._con.commit()
                cur.close()
        else:
            with self._con:
                cur = self._con.cursor()
                cur.execute(f'UPDATE {self.name} SET value = "{value}" WHERE key = "{key}";')

                self._con.commit()
                cur.close()

    def __delitem__(self, key):
        with self._con:
            cur = self._con.cursor()
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

        import threading

        self.lock = threading.Lock()

        self._config_file_path = ':memory:'
        self._con = None

    def set_path(self, path):
        self._config_file_path = path

    def open(self):
        if self._con is not None:
            raise RuntimeError('The config database is already open')

        self._con = sqlite3.connect(self._config_file_path, check_same_thread=False)

    def __contains__(self, item):
        if self._con is None:
            self.open()

        with self._con:
            cur = self._con.cursor()
            cur.execute('SELECT name FROM sqlite_master WHERE type="table";')
            tables = [row[0] for row in cur.fetchall()]
            cur.close()

        return item in tables

    def __getitem__(self, item):
        if item not in self:
            with self._con:
                cur = self._con.cursor()
                cur.execute(f'CREATE TABLE {item}('
                            'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                            'key TEXT UNIQUE NOT NULL, '
                            'value TEXT NOT NULL'
                            ');')
                self._con.commit()
                cur.close()

        return _ConfigTable(self._con, item)

    def close(self):
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

    def _save(cls):
        for key in dir(cls):
            if key.startswith('_'):
                continue

            value = getattr(cls, key)
            if callable(value):
                continue

            cls.__table__[key] = value

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
        name = name.replace('harness_designer_Config_', '')
        name = name.replace('_Config', '')
        return name

    @property
    def __table__(cls):
        return ConfigDB.__db__[cls.__table_name__]

    def __getitem__(cls, item):
        return getattr(cls, item)

    def __getattribute__(cls, item):
        if item.startswith('_'):
            return type.__getattribute__(cls, item)

        value = type.__getattribute__(cls, item)
        if callable(value):
            return value

        if item in cls.__table__:
            return cls.__table__[item]

        return value

    def __setitem__(cls, key, value):
        setattr(cls, key, value)

    def __setattr__(cls, key, value):
        type.__setattr__(cls, key, value)

        if not key.startswith('_'):
            cls.__table__[key] = value
            cls._process_change(key)

    def __delitem__(cls, key):
        delattr(cls, key)

    def __delattr__(cls, item):
        if item in cls.__table__:
            del cls.__table__[item]

        type.__delattr__(cls, item)

    @staticmethod
    def close():
        for cls in ConfigDB.__classes__:
            cls._save()

        ConfigDB.__db__.close()

    @staticmethod
    def set_path(path):
        ConfigDB.__db__.set_path(path)


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

    class editor3d(metaclass=ConfigDB):
        selected_color = [0.2, 1.0, 0.2, 0.35]

        class renderer(metaclass=ConfigDB):
            smooth_boots = True
            smooth_housings = True
            smooth_wires = True
            smooth_bundles = True
            smooth_seals = True
            smooth_cpa_locks = True
            smooth_tpa_locks = True
            smooth_terminals = True

    class camera(metaclass=ConfigDB):
        focal_target_visible = True
        focal_target_color = [1.0, 0.4, 0.4, 1.0]
        focal_target_radius = 0.25
        
    class floor(metaclass=ConfigDB):
        enable = True
        ground_height = 0.0
        reflections = True
        reflection_strength = 50.0
        distance = 1000
        primary_color = [0.2039, 0.2549, 0.2902, 0.8]
        secondary_color = [0.3058, 0.3843, 0.3804, 0.8]
        grid_size = 50
        show_grid = True

    class virtual_canvas(metaclass=ConfigDB):
        width = 1920
        height = 1080

    class movement(metaclass=ConfigDB):
        angle_detent = 10.0
        move_detent = 5.0

        angle_snap = -1
        move_snap = -1

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

    class debug(metaclass=ConfigDB):
        log_args = False
        call_duration = True
        bypass = True

    class headlight(metaclass=ConfigDB):
        turn_on = True
        cutoff = 8.0
        dissipate = 50.0
        color = [0.4, 0.4, 0.4, 0.8]

    class colors(metaclass=ConfigDB):
        custom_colors = ''
