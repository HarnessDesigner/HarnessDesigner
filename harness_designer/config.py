# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Persistent application configuration backed by SQLite tables."""

import sqlite3
import weakref
import threading
import os

from . import utils as _utils


CONNECTOR_SQLITE = 0

_lock = threading.RLock()

DEBUG_CONFIG = False


def DEBUG(*args):
    """Print config debug output when :data:`DEBUG_CONFIG` is enabled.

    :param args: Values to print.
    :type args: tuple
    """
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
        """Initialise a table wrapper.

        :param con: Open SQLite connection.
        :type con: sqlite3.Connection
        :param name: Table name.
        :type name: str
        """
        self._con = con
        self.name = name

    def __contains__(self, item):
        """Return whether a key exists in the table.

        :param item: Setting key.
        :type item: str
        :returns: ``True`` when the key exists.
        :rtype: bool
        """
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
        """Fetch and deserialize a stored value.

        :param item: Setting key.
        :type item: str
        :returns: Stored value.
        :rtype: UNKNOWN
        """
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
        """Insert or update a stored value.

        :param key: Setting key.
        :type key: str
        :param value: Value to persist.
        :type value: UNKNOWN
        """
        value = str(value)

        if key not in self:
            with _lock:
                with self._con:
                    cur = self._con.cursor()
                    DEBUG('__setitem__.INSERT:', self.name, key, value)

                    try:
                        cur.execute(f'INSERT INTO {self.name} (key, value) VALUES(?, ?);', (key, value))
                    except sqlite3.IntegrityError:
                        DEBUG('__setitem__.UPDATE:', self.name, key, value)
                        cur.execute(f'UPDATE {self.name} SET value = "{value}" WHERE key = "{key}";')

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
        """Delete a stored key from the table.

        :param key: Setting key.
        :type key: str
        """
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
        """Initialise the backing database wrapper.

        """
        self._con = None
        self.save_all = False

    def open(self):
        """Open the configuration database file.

        :raises RuntimeError: If the database is already open.
        """
        if self._con is not None:
            raise RuntimeError('The config database is already open')

        path = os.path.join(_utils.get_appdata(), 'config.db')

        self.save_all = not os.path.exists(path)
        self._con = sqlite3.connect(path, check_same_thread=False)

    def __contains__(self, item):
        """Return whether a table exists in the database.

        :param item: Table name.
        :type item: str
        :returns: ``True`` when the table exists.
        :rtype: bool
        """
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
        """Return a table wrapper, creating the table on demand.

        :param item: Table name.
        :type item: str
        :returns: Table wrapper for the requested table.
        :rtype: _ConfigTable
        """
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
        """Close the configuration database connection.

        """
        with _lock:
            self._con.close()


class ConfigDB(type):
    """Metaclass that persists class attributes to configuration tables."""
    __db__ = _ConfigDB()
    __classes__ = []
    __callbacks__ = {}

    def __init__(cls, name, bases, dct):
        """Register a configuration class with the metaclass registry.

        :param name: Class name.
        :type name: str
        :param bases: Base classes.
        :type bases: tuple[type, ...]
        :param dct: Class namespace.
        :type dct: dict
        """
        super().__init__(name, bases, dct)
        ConfigDB.__classes__.append(cls)
        ConfigDB.__callbacks__[cls] = {}

    def bind(cls, callback, setting_name):
        """Bind a callback to a persisted setting name.

        :param callback: Bound method notified when the setting changes.
        :type callback: collections.abc.Callable
        :param setting_name: Setting name to observe.
        :type setting_name: str
        """
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
        """Remove a dead callback weak reference.

        :param ref: Weak reference to remove.
        :type ref: weakref.ReferenceType
        """
        for refs in ConfigDB.__callbacks__[cls].values():
            if ref in refs:
                refs.remove(ref)
                return

    def _load(cls):
        """Load persisted values back onto the configuration class.

        """
        for key in dir(cls):
            if key.startswith('_'):
                continue

            if cls.__table_name__ in ConfigDB.__db__:
                if key in cls.__table__:
                    type.__setattr__(cls, key, cls.__table__[key])

    def _save(cls):
        """Persist current class attributes to the database.

        """
        for key in dir(cls):
            if key.startswith('_'):
                continue

            value = getattr(cls, key)

            if callable(value):
                continue

            cls.__table__[key] = value
            DEBUG('_save:', cls.__name__, cls.__table_name__, key, repr(value), '\n\n')

    def _process_change(cls, setting_name):
        """Notify callbacks that a setting changed.

        :param setting_name: Changed setting name.
        :type setting_name: str
        """
        if setting_name in ConfigDB.__callbacks__[cls]:
            for ref in ConfigDB.__callbacks__[cls][setting_name][:]:
                cb = ref()
                if cb is None:
                    ConfigDB.__callbacks__[cls][setting_name].remove(ref)
                else:
                    cb(cls, setting_name)

    @property
    def __table_name__(cls):
        """Return the SQLite table name for this configuration class.

        :returns: Derived table name.
        :rtype: str
        """
        name = f'{cls.__module__.split(".", 1)[-1]}_{cls.__qualname__}'
        name = name.replace(".", "_")
        name = name.replace('harness_designer_config_Config_', '')
        name = name.replace('_Config', '')
        return name

    @property
    def __table__(cls):
        """Return the table wrapper for this configuration class.

        :returns: Backing table wrapper.
        :rtype: _ConfigTable
        """
        return ConfigDB.__db__[cls.__table_name__]

    def __getitem__(cls, item):
        """Return a configuration attribute by key.

        :param item: Setting name.
        :type item: str
        :returns: Stored attribute value.
        :rtype: UNKNOWN
        """
        DEBUG('__getitem__:', cls.__table_name__, cls.__name__, item)
        value = getattr(cls, item)

        return value

    def __getattribute__(cls, item):
        """Fetch an attribute, falling back to persisted table values.

        :param item: Attribute name.
        :type item: str
        :returns: Attribute value.
        :rtype: UNKNOWN
        :raises AttributeError: If the attribute is not defined anywhere.
        """
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
        """Assign a configuration attribute by key.

        :param key: Setting name.
        :type key: str
        :param value: Value to store.
        :type value: UNKNOWN
        """
        DEBUG('__setitem__:', cls.__table_name__, cls.__name__, key, repr(value))

        setattr(cls, key, value)

    def __setattr__(cls, key, value):
        """Assign and persist a configuration attribute.

        :param key: Attribute name.
        :type key: str
        :param value: Value to store.
        :type value: UNKNOWN
        """
        if key.startswith('_'):
            type.__setattr__(cls, key, value)

        else:
            DEBUG('__setattr__:', cls.__table_name__, cls.__name__, key, repr(value), '\n')
            type.__setattr__(cls, key, value)

            cls.__table__[key] = value
            cls._process_change(key)

    def __delitem__(cls, key):
        """Delete a configuration attribute by key.

        :param key: Setting name.
        :type key: str
        """
        delattr(cls, key)

    def __delattr__(cls, item):
        """Delete a configuration attribute and its persisted value.

        :param item: Attribute name.
        :type item: str
        """
        if item in cls.__table__:
            del cls.__table__[item]

        type.__delattr__(cls, item)

    @staticmethod
    def open():
        """Open the config database and load all registered classes.

        """
        ConfigDB.__db__.open()

        for cls in ConfigDB.__classes__:
            cls._load()

    @staticmethod
    def close():
        """Save all registered configuration classes and close the database.

        """
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
    """Root container for persisted application settings."""

    class ray_trace(metaclass=ConfigDB):
        """Ray-tracing renderer defaults and quality presets."""

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
            """Background colour and gradient settings for ray tracing."""
            color1 = [0.18, 0.20, 0.22]
            color2 = [0.18, 0.20, 0.22]

            enable_gradient = True

        class environment_map(metaclass=ConfigDB):
            """Environment-map settings for ray tracing."""
            enable = True
            generate = True
            path = ''

        class shadows(metaclass=ConfigDB):
            """Shadow settings for ray tracing."""
            enable = True
            softness = 1.0

        class ambient_occlusion(metaclass=ConfigDB):
            """Ambient occlusion settings for ray tracing."""
            enable = False
            samples = 8.0
            radius = 0.5

        class lighting(metaclass=ConfigDB):
            """Light source defaults for ray tracing."""
            ambient_intensity = 0.2
            lights = [
                {
                    'position': [0.0, 0.0, 0.0],
                    'intensity': 1.0,
                    'color': [1.0, 1.0, 1.0],
                }
            ]

    class editor2d(metaclass=ConfigDB):
        """2D editor interaction and canvas settings."""

        class virtual_canvas(metaclass=ConfigDB):
            """Virtual canvas size for 2D editing."""
            width = 1920
            height = 1080

        class angle(metaclass=ConfigDB):
            """Angle snapping settings for the 2D editor."""
            lock = False
            lock_increment = 90.0

        class grid(metaclass=ConfigDB):
            """Grid display and snapping settings for the 2D editor."""
            enabled = True
            size = 8000
            snap = False

        class zoom(metaclass=ConfigDB):
            """2D editor zoom control bindings."""
            mouse = MOUSE_WHEEL  # | MOUSE_REVERSE_WHEEL_AXIS
            in_key = 43
            out_key = 45
            sensitivity = 5.0

        class pan(metaclass=ConfigDB):
            """2D editor pan control bindings."""
            mouse = MOUSE_LEFT
            up_key = 16777235
            down_key = 16777237
            left_key = 16777234
            right_key = 16777236
            sensitivity = 0.4

        class reset(metaclass=ConfigDB):
            """2D editor reset-view bindings."""
            key = 16777232
            mouse = MOUSE_NONE

        class canvas(metaclass=ConfigDB):
            """Export or render canvas size for the 2D editor."""
            width = 3840
            height = 2160

    class editor3d(metaclass=ConfigDB):
        """3D editor rendering and navigation settings."""
        background_color = [0.20, 0.20, 0.20, 1.0]
        selected_color = [0.2, 0.6, 0.2, 0.35]

        class lighting(metaclass=ConfigDB):
            """Default 3D scene lighting values."""
            position = [100.0, 100.0, 100.0]
            ambient = [0.4, 0.4, 0.4, 1.0]
            diffuse = [0.8, 0.8, 0.8, 1.0]
            specular = [1.0, 1.0, 1.0, 1.0]

        class renderer(metaclass=ConfigDB):
            """3D renderer smoothing toggles for supported object types."""
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
            """Focal target marker settings in the 3D editor."""
            enable = True
            color = [1.0, 0.4, 0.4, 1.0]
            radius = 0.25

        class rotation_rings(metaclass=ConfigDB):
            """Rotation ring gizmo settings in the 3D editor."""
            # Ring diameter as a multiple of the object's AABB space diagonal
            # (the largest distance between two corners of the bounding box)
            diameter_scale = 1.1
            # Grab handle diameter as a fraction of the ring diameter
            handle_diameter_scale = 0.08
            # Ring tube diameter as a fraction of the ring diameter
            tube_diameter_scale = 0.01
            # Ring/handle colors as scalar RGBA (0.0 - 1.0)
            x_color = [0.782, 0.135, 0.135, 0.8]
            y_color = [0.135, 0.684, 0.135, 0.8]
            z_color = [0.175, 0.331, 0.822, 0.8]
            # Enable snapping of ring-drag rotation to snap_angle increments
            snap_enable = False
            # Drag snap increment in degrees. Must have at most 2 decimal
            # places and divide the 360 degree range evenly (15, 22.5,
            # 0.45, ...) — invalid values disable snapping
            snap_angle = 15.0
            # Half-width in degrees of the detent at 0 — the dragged angle
            # sticks at exactly 0.0 until the cursor moves past this
            detent_width = 1.0

        class floor(metaclass=ConfigDB):
            """Floor plane, grid, and reflection settings for the 3D editor."""
            enable = True
            ground_height = 0.0
            size = 2000
            enable_floor_lock = True

            class grid(metaclass=ConfigDB):
                """Floor grid appearance settings."""
                primary_color = [0.2039, 0.2549, 0.2902, 0.8]
                secondary_color = [0.2925, 0.3430, 0.3430, 0.8]

                primary_line_color = [0.87, 0.88, 0.92, 1.0]
                secondary_line_color = [0.57, 0.59, 0.65, 1.0]
                primary_line_width = 0.8
                secondary_line_width = 0.25

                secondary_lines_per_tile = 4

                secondary_line_pattern = 0x0B2664D0
                # 0000 1011 0010 0110 0110 0100 1101 0000
                secondary_line_shift = False

                size = 80
                enable = True

            class reflections(metaclass=ConfigDB):
                """Floor reflection settings in the 3D editor."""
                enable = True
                strength = 50.0

        class virtual_canvas(metaclass=ConfigDB):
            """Virtual canvas size for 3D rendering output."""
            width = 1920
            height = 1080

        class keyboard_settings(metaclass=ConfigDB):
            """Keyboard speed scaling settings for the 3D editor."""
            max_speed_factor = 10.0
            speed_factor_increment = 0.1
            start_speed_factor = 1.0

        class rotate(metaclass=ConfigDB):
            """3D rotate control bindings."""
            mouse = MOUSE_MIDDLE
            up_key = ord('w')
            down_key = ord('s')
            left_key = ord('a')
            right_key = ord('d')
            sensitivity = 0.4

        class pan_tilt(metaclass=ConfigDB):
            """3D pan/tilt control bindings."""
            mouse = MOUSE_LEFT
            up_key = ord('o')
            down_key = ord('l')
            left_key = ord('k')
            right_key = ord(';')
            sensitivity = 0.2

        class truck_pedestal(metaclass=ConfigDB):
            """3D truck and pedestal movement bindings."""
            mouse = MOUSE_RIGHT
            up_key = ord('8')
            down_key = ord('2')
            left_key = ord('4')
            right_key = ord('6')
            sensitivity = 0.2
            speed = 1.0

        class walk(metaclass=ConfigDB):
            """3D walking/navigation bindings."""
            mouse = MOUSE_WHEEL | MOUSE_SWAP_AXIS
            forward_key = 16777235
            backward_key = 16777237
            left_key = 16777234
            right_key = 16777236
            sensitivity = 1.0
            speed = 5.0

        class zoom(metaclass=ConfigDB):
            """3D zoom control bindings."""
            mouse = MOUSE_NONE  # | MOUSE_REVERSE_WHEEL_AXIS
            in_key = 43
            out_key = 45
            sensitivity = 5.0

        class reset(metaclass=ConfigDB):
            """3D editor reset-view bindings."""
            key = 16777232
            mouse = MOUSE_NONE

        class headlight(metaclass=ConfigDB):
            """Headlight settings for the 3D editor camera."""
            enable = True
            cutoff = 8.0
            dissipate = 50.0
            color = [0.6, 0.6, 0.4, 0.8]

        class axis_overlay(metaclass=ConfigDB):
            """Axis overlay visibility and placement settings."""
            is_visible = True
            size = (150, 150)
            position = (830, 245)

    class logging(metaclass=ConfigDB):
        """Logging destinations and verbosity settings."""
        save_path = os.path.join(_utils.get_appdata(), 'log')
        num_archives = 10
        num_logfiles = 10
        max_logfile_size = 10485760
        log_notice = True
        log_warning = True
        log_debug = False
        log_traceback = True
        log_error = True
        log_wx_error = True
        log_database = False
        log_file_transfers = True

    class debug:
        """Debug feature toggles used throughout the application."""
        class functions(metaclass=ConfigDB):
            """Function-call debug logging settings."""
            log_args = False
            log_duration = False

        class rendering3d(metaclass=ConfigDB):
            """3D debug rendering overlays and colours."""
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
        """Colour customisation settings."""
        custom_colors = ''

        class add_object(metaclass=ConfigDB):
            """Highlight colours used while adding objects."""
            preview_color = [0.5, 0.85, 1.0, 0.45]

            terminal_highlight = [1.0, 0.8, 0.0, 0.6]
            housing_highlight = [1.0, 0.0, 0.8, 0.6]

            transition_highlight = [0.8, 1.0, 0.0, 0.6]
            bundle_highlight = [0.8, 0.0, 1.0, 0.6]

            wire_highlight = [0.0, 1.0, 0.8, 0.6]
            cavity_highlight = [0.0, 0.8, 1.0, 0.6]

            splice_highlight = [0.0, 0.8, 1.0, 0.6]

    class resources(metaclass=ConfigDB):
        model_watchdog_timeout = 120

    class database(metaclass=ConfigDB):
        """Database backend selection and connection defaults."""
        connector = CONNECTOR_SQLITE
        monitor_duration = 60

        class maintenance(metaclass=ConfigDB):
            """Database maintenance batch settings."""
            point_batch_size = 50

        class sqlite(metaclass=ConfigDB):
            """SQLite backend settings."""
            database_path = os.path.join(_utils.get_appdata(), 'harness_designer.db')

        class mysql(metaclass=ConfigDB):
            """MySQL backend connection settings."""
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
                """Window geometry for the MySQL settings dialog."""
                size = (950, 950)
                pos = (0, 0)

    class mainframe(metaclass=ConfigDB):
        """Main window geometry and docking layout settings."""
        theme = 'Dark'
        position = ()
        size = ()

        ui_perspective = (
            'layout2'
            '|name=editor_3d;caption=3D Editor;state=2816;dir=5;layer=0;row=0;pos=0;prop=100000;bestw=20;besth=20;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1'
            '|name=editor_2d;caption=Schematic Editor;state=14684156;dir=2;layer=0;row=2;pos=0;prop=100000;bestw=20;besth=20;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=803;floaty=323;floatw=45;floath=59'
            '|name=editor_db;caption=Database Editor;state=14700540;dir=3;layer=0;row=0;pos=0;prop=100000;bestw=20;besth=20;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1'
            '|name=editor_obj;caption=Object Editor;state=14684156;dir=4;layer=0;row=0;pos=0;prop=100000;bestw=20;besth=20;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1'
            '|name=editor_assembly;caption=Assembly Editor;state=14684156;dir=3;layer=0;row=0;pos=1;prop=100000;bestw=20;besth=20;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=1786;floaty=727;floatw=45;floath=59'
            '|name=object_browser;caption=Object Browser;state=14684156;dir=2;layer=0;row=0;pos=0;prop=100000;bestw=20;besth=20;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=1811;floaty=226;floatw=45;floath=59'
            '|name=log_viewer;caption=Log Viewer;state=14684158;dir=3;layer=0;row=0;pos=2;prop=100000;bestw=20;besth=20;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=1760;floaty=764;floatw=45;floath=59'
            '|name=general_toolbar;caption=;state=2106108;dir=1;layer=10;row=0;pos=0;prop=100000;bestw=228;besth=45;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1'
            '|name=editor_toolbar;caption=;state=2106108;dir=1;layer=10;row=0;pos=1006;prop=100000;bestw=658;besth=45;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1'
            '|name=note_toolbar;caption=;state=2106108;dir=1;layer=10;row=0;pos=862;prop=100000;bestw=142;besth=45;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1'
            '|name=object_toolbar;caption=;state=2106108;dir=1;layer=10;row=0;pos=460;prop=100000;bestw=400;besth=45;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1'
            '|name=settings3d_toolbar;caption=;state=2106108;dir=1;layer=10;row=0;pos=230;prop=100000;bestw=228;besth=45;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1'
            '|dock_size(5,0,0)=22'
            '|dock_size(2,0,0)=198'
            '|dock_size(3,0,0)=283'
            '|dock_size(4,0,0)=271'
            '|dock_size(1,10,0)=47'
            '|dock_size(2,0,2)=662|')

    class project(metaclass=ConfigDB):
        """Project-level defaults such as recent locations."""
        last_project = None
        model_dir = _utils.get_documents()


Config.open()
