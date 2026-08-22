# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Persistent application configuration backed by SQLite tables."""
import inspect
import binascii
import sqlite3
import weakref
import threading
import os

from . import utils as _utils
from . import check_types as _check_types


CONNECTOR_SQLITE = 0

_lock = threading.RLock()

DEBUG_CONFIG = False


@_check_types.do
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

    @_check_types.do
    def __init__(self, con, name):
        """Initialise a table wrapper.

        :param con: Open SQLite connection.
        :type con: sqlite3.Connection
        :param name: Table name.
        :type name: str
        """
        self._con = con
        self.name = name

    @_check_types.do
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
                cur.execute(f'SELECT id FROM [{self.name}] WHERE key = "{item}";')
                DEBUG('__contains__.SELECT:', self.name, item)
                if cur.fetchall():
                    cur.close()
                    return True

                cur.close()

            return False

    @_check_types.do
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

                cur.execute(f'SELECT value, decode FROM [{self.name}] WHERE key = "{item}";')
                value, decode = cur.fetchall()[0]

                DEBUG('__getitem__.SELECT:', self.name, item, value)
                cur.close()

            if decode:
                value = binascii.unhexlify(value)
                value = value.decode('utf-8')

            try:
                return eval(value)
            except:  # NOQA
                return value

    @_check_types.do
    def __setitem__(self, key, value):
        """Insert or update a stored value.

        :param key: Setting key.
        :type key: str
        :param value: Value to persist.
        :type value: UNKNOWN
        """
        value = str(value)

        if '"' in value or "'" in value:
            decode = True
            value = value.encode('utf-8')
            value = binascii.hexlify(value).decode('utf-8')
        else:
            decode = False

        if key not in self:
            with _lock:
                with self._con:
                    cur = self._con.cursor()
                    DEBUG('__setitem__.INSERT:', self.name, key, value)

                    try:
                        cur.execute(f'INSERT INTO [{self.name}] (key, value, decode) VALUES(?, ?, ?);', (key, value, int(decode)))
                    except sqlite3.IntegrityError:
                        DEBUG('__setitem__.UPDATE:', self.name, key, value, decode)
                        cur.execute(f'UPDATE [{self.name}] SET value = ?, decode = ? WHERE key = ?;', (value, int(decode), key))

                    self._con.commit()
                    cur.close()
        else:
            with _lock:
                with self._con:
                    cur = self._con.cursor()
                    DEBUG('__setitem__.UPDATE:', self.name, key, value)
                    cur.execute(f'UPDATE [{self.name}] SET value = ?, decode = ? WHERE key = ?;', (value, int(decode), key))

                    self._con.commit()
                    cur.close()

    @_check_types.do
    def __delitem__(self, key):
        """Delete a stored key from the table.

        :param key: Setting key.
        :type key: str
        """
        with _lock:
            with self._con:
                cur = self._con.cursor()
                DEBUG('__delitem__.DELETE:', self.name, key)

                cur.execute(f'DELETE FROM [{self.name}] WHERE key = "{key}"')
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

    @_check_types.do
    def __init__(self):
        """Initialise the backing database wrapper.

        """
        self._con = None

    @_check_types.do
    def open(self):
        """Open the configuration database file.

        :raises RuntimeError: If the database is already open.
        """
        if self._con is not None:
            raise RuntimeError('The config database is already open')

        path = os.path.join(_utils.get_appdata(), 'config.db')

        save_all = not os.path.exists(path)
        self._con = sqlite3.connect(path, check_same_thread=False)
        return save_all

    @_check_types.do
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
                cur.execute('SELECT [name] FROM sqlite_master WHERE type="table";')
                tables = [row[0] for row in cur.fetchall()]
                cur.close()

            ret = item in tables
            DEBUG('__contains__.table.SELECT:', item, ret)

            return ret

    @_check_types.do
    def __setitem__(self, key, value):
        with _lock:
            if key not in self:
                with self._con:
                    cur = self._con.cursor()
                    DEBUG('__getitem__.table.CREATE:', key)

                    cur.execute(f'CREATE TABLE [{key}]('
                                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                                'key TEXT UNIQUE NOT NULL, '
                                'value TEXT NOT NULL, '
                                'decode INT NOT NULL'
                                ');')
                    self._con.commit()
                    cur.close()

    @_check_types.do
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

                    cur.execute(f'CREATE TABLE [{item}]('
                                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                                'key TEXT UNIQUE NOT NULL, '
                                'value TEXT NOT NULL, '
                                'decode INT NOT NULL'
                                ');')
                    self._con.commit()
                    cur.close()

            return _ConfigTable(self._con, item)

    @_check_types.do
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

    @_check_types.do
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

    @_check_types.do
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

    @_check_types.do
    def _remove_ref(cls, ref):
        """Remove a dead callback weak reference.

        :param ref: Weak reference to remove.
        :type ref: weakref.ReferenceType
        """
        for refs in ConfigDB.__callbacks__[cls].values():
            if ref in refs:
                refs.remove(ref)
                return

    @_check_types.do
    def _load(cls, save_all):
        """Load persisted values back onto the configuration class.

        """
        for key in dir(cls):
            if key.startswith('_'):
                continue

            if save_all and cls.__table_name__ not in ConfigDB.__db__:
                ConfigDB.__db__[cls.__table_name__] = None

            if cls.__table_name__ in ConfigDB.__db__:
                if key in cls.__table__:
                    type.__setattr__(cls, key, cls.__table__[key])

                elif save_all:
                    value = getattr(cls, key)
                    if type(value) is not ConfigDB and not inspect.isclass(value):
                        cls.__table__[key] = value

    @_check_types.do
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

    @_check_types.do
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
    @_check_types.do
    def __table_name__(cls):
        """Return the SQLite table name for this configuration class.

        :returns: Derived table name.
        :rtype: str
        """
        name = cls.__qualname__
        name = name.replace('Config.', '')
        return name

    @property
    @_check_types.do
    def __table__(cls):
        """Return the table wrapper for this configuration class.

        :returns: Backing table wrapper.
        :rtype: _ConfigTable
        """
        return ConfigDB.__db__[cls.__table_name__]

    @_check_types.do
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

    @_check_types.do
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

    @_check_types.do
    def __setitem__(cls, key, value):
        """Assign a configuration attribute by key.

        :param key: Setting name.
        :type key: str
        :param value: Value to store.
        :type value: UNKNOWN
        """
        DEBUG('__setitem__:', cls.__table_name__, cls.__name__, key, repr(value))

        setattr(cls, key, value)

    @_check_types.do
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

    @_check_types.do
    def __delitem__(cls, key):
        """Delete a configuration attribute by key.

        :param key: Setting name.
        :type key: str
        """
        delattr(cls, key)

    @_check_types.do
    def __delattr__(cls, item):
        """Delete a configuration attribute and its persisted value.

        :param item: Attribute name.
        :type item: str
        """
        if item in cls.__table__:
            del cls.__table__[item]

        type.__delattr__(cls, item)

    @staticmethod
    @_check_types.do
    def open():
        """Open the config database and load all registered classes.

        """
        save_all = ConfigDB.__db__.open()

        for cls in ConfigDB.__classes__:
            cls._load(save_all)

    @staticmethod
    @_check_types.do
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

    class editor_schematic(metaclass=ConfigDB):
        # Selection highlight material color -- mirrors
        # Config.editor_3d.selected_color's role exactly.
        background_color = [0.20, 0.20, 0.20, 1.0]
        selected_color = [0.2, 0.6, 0.2, 0.25]

        class lighting(metaclass=ConfigDB):
            position = [100.0, 100.0, 100.0]
            ambient = [0.4, 0.4, 0.4, 1.0]
            diffuse = [0.8, 0.8, 0.8, 1.0]
            specular = [1.0, 1.0, 1.0, 1.0]

        class renderer(metaclass=ConfigDB):
            smooth_housings = False
            smooth_wires = True
            smooth_terminals = False
            smooth_notes = False
            smooth_transitions = True
            smooth_splices = True
            smooth_wire_markers = True

        class drag_handler(metaclass=ConfigDB):
            mode = ''

        class rotation_handler(metaclass=ConfigDB):
            # Ring diameter as a multiple of the object's AABB space diagonal
            # (the largest distance between two corners of the bounding box)
            diameter_scale = 1.1
            # Grab handle diameter as a fraction of the ring diameter
            handle_diameter_scale = 0.08
            # Ring tube diameter as a fraction of the ring diameter
            tube_diameter_scale = 0.01
            # Ring/handle colors as scalar RGBA (0.0 - 1.0)
            y_color = [0.135, 0.684, 0.135, 0.8]
            # Enable snapping of ring-drag rotation to snap_angle increments
            snap_enable = True
            # Drag snap increment in degrees. Must have at most 2 decimal
            # places and divide the 360 degree range evenly (15, 22.5,
            # 0.45, ...) — invalid values disable snapping
            snap_angle = 90.0
            # Half-width in degrees of the detent at 0 — the dragged angle
            # sticks at exactly 0.0 until the cursor moves past this
            detent_width = 1.0

        class virtual_canvas(metaclass=ConfigDB):
            width = 1920
            height = 1080

        class floor(metaclass=ConfigDB):
            enable = True
            ground_height = 0.0
            enable_floor_lock = True

            snap = False

            target_dot_pixel_spacing = 40.0
            dot_color = [0.45, 0.45, 0.45, 1.0]

            manual_snap_spacing = None

            class reflections:
                enable = False
                strength = 50.0

        class keyboard_settings(metaclass=ConfigDB):
            max_speed_factor = 10.0
            speed_factor_increment = 0.1
            start_speed_factor = 1.0

        class input(metaclass=ConfigDB):
            class rotate:
                mouse = None
                up_key = None
                down_key = None
                left_key = None
                right_key = None
                sensitivity = None

            class pan_tilt:
                mouse = None
                up_key = None
                down_key = None
                left_key = None
                right_key = None
                sensitivity = None

            class truck_pedestal(metaclass=ConfigDB):
                mouse = MOUSE_LEFT | MOUSE_REVERSE_X_AXIS | MOUSE_REVERSE_Y_AXIS
                up_key = ord('8')
                down_key = ord('2')
                left_key = ord('4')
                right_key = ord('6')
                sensitivity = 0.2
                speed = 1.0

            class walk:
                mouse = None
                forward_key = None
                backward_key = None
                left_key = None
                right_key = None
                sensitivity = None
                speed = None

            class dolly(metaclass=ConfigDB):
                mouse = None
                in_key = None
                out_key = None
                sensitivity = None

            class zoom:
                mouse = MOUSE_WHEEL  # | MOUSE_REVERSE_WHEEL_AXIS
                in_key = 16777235
                out_key = 16777237
                sensitivity = 2.0

            class reset(metaclass=ConfigDB):
                key = 16777232
                mouse = MOUSE_NONE

        class colors(metaclass=ConfigDB):
            """Part colours for the 2D schematic editor."""

            housing = [0.55, 0.75, 0.95, 1.0]
            housing_outline = [0.15, 0.25, 0.45, 1.0]
            # Selection highlight -- mirrors Config.editor_pegboard.selected_color's role.
            selected = [0.2, 0.6, 0.2, 0.25]
            label = [0.1, 0.1, 0.1, 1.0]
            splice = [0.0, 0.0, 0.0, 1.0]

        class object_sizes(metaclass=ConfigDB):
            # Shared padding (mm) used throughout the cavity/terminal
            # pin-edge layout: how far the cavity name sits outside the
            # housing's pin edge, how far the terminal's "(" bracket sits
            # outside it (the two land at the same X for this reason --
            # not because one is aligned to the other, they're both
            # independently pin_edge - pin_edge_padding), and how far the
            # terminal's own name is inset from its cavity's AABB on all
            # 4 sides. One shared value for now (confirmed with the user
            # 2026-08-20) -- split into separate per-purpose values later
            # if that turns out to be needed.
            pin_edge_padding = 3.0

            class terminal(metaclass=ConfigDB):
                # Maximum -- a housing's own cavity_height (see
                # objects_schematic/housing.py's Housing.__init__) is
                # always derived from this value, but an individual
                # terminal may render smaller than this to fit its own
                # name inside that computed slot height.
                name_font_size = 3.0

            class splice(metaclass=ConfigDB):
                """Fixed splice sizing for the 2D schematic editor -- a
                splice renders as the same shared sphere mesh
                objects_3d/splice.py's Splice uses (schematic2d's shader
                already does the full 3D lighting/transform before
                projecting to 2D, so there's no need for a flat-only mesh
                here)."""
                diameter = 2.0  # mm

            class wire(metaclass=ConfigDB):
                """Fixed diameter (mm) for both the 2D wire itself and its
                own WireLayout drag handle -- objects_schematic/wire.py's
                Wire and objects_schematic/wire_layout.py's WireLayout both
                read this SAME value (never two separate sizes), regardless
                of the wire part's real od_mm."""
                diameter = 1.0

            class cavity(metaclass=ConfigDB):
                """Cavity sizing for the 2D schematic editor. Cavities are
                never individually drawn as boxes -- only their own name
                label. The cavity slot height itself is no longer a fixed
                config value -- see ``objects_schematic/housing.py``'s
                ``Housing.__init__``, which derives it from
                ``Config.object_sizes.terminal.name_font_size`` (the
                driving/tallest label in a slot) instead."""
                name_font_size = 1.5

                # mm around text when it drives box sizing (corner label
                # inset from the housing's own edges, and how far
                # Housing.get_cavity_aabb's far edge stops short of the
                # housing's own far edge to leave room for that label).
                padding = 0.75

            class housing(metaclass=ConfigDB):
                """Fixed housing rectangle sizing for the 2D schematic editor
                -- width is constant regardless of cavity count or terminal-
                name length; height is ``num_pins * Config.editor2d.cavity.height``.
                """
                width = 50.0  # mm
                font_size = 3.0  # housing's own name/part number/manufacturer block

    class editor_pegboard(metaclass=ConfigDB):

        # Selection highlight material color -- mirrors
        # Config.editor_3d.selected_color's role exactly.
        background_color = [0.20, 0.20, 0.20, 1.0]
        selected_color = [0.2, 0.6, 0.2, 0.25]

        class lighting(metaclass=ConfigDB):
            position = [100.0, 100.0, 100.0]
            ambient = [0.4, 0.4, 0.4, 1.0]
            diffuse = [0.8, 0.8, 0.8, 1.0]
            specular = [1.0, 1.0, 1.0, 1.0]

        class renderer(metaclass=ConfigDB):
            smooth_boots = True
            smooth_housings = True
            smooth_wires = True
            smooth_bundles = True
            smooth_seals = True
            smooth_terminals = True
            smooth_notes = False
            smooth_transitions = True
            smooth_splices = True
            smooth_wire_markers = True

        class drag_handler(metaclass=ConfigDB):
            mode = ''

        class rotation_handler(metaclass=ConfigDB):
            # Ring diameter as a multiple of the object's AABB space diagonal
            # (the largest distance between two corners of the bounding box)
            diameter_scale = 1.1
            # Grab handle diameter as a fraction of the ring diameter
            handle_diameter_scale = 0.08
            # Ring tube diameter as a fraction of the ring diameter
            tube_diameter_scale = 0.01
            # Ring/handle colors as scalar RGBA (0.0 - 1.0)
            y_color = [0.135, 0.684, 0.135, 0.8]
            # Enable snapping of ring-drag rotation to snap_angle increments
            snap_enable = False
            # Drag snap increment in degrees. Must have at most 2 decimal
            # places and divide the 360 degree range evenly (15, 22.5,
            # 0.45, ...) — invalid values disable snapping
            snap_angle = 15.0
            # Half-width in degrees of the detent at 0 — the dragged angle
            # sticks at exactly 0.0 until the cursor moves past this
            detent_width = 1.0

        class virtual_canvas(metaclass=ConfigDB):
            width = 1920
            height = 1080

        class floor(metaclass=ConfigDB):
            enable = True
            ground_height = 0.0
            enable_floor_lock = True

            snap = False

            target_dot_pixel_spacing = 40.0
            dot_color = [0.45, 0.45, 0.45, 1.0]

            manual_snap_spacing = None

            class reflections:
                enable = False
                strength = 50.0

        class keyboard_settings(metaclass=ConfigDB):
            max_speed_factor = 10.0
            speed_factor_increment = 0.1
            start_speed_factor = 1.0

        class input(metaclass=ConfigDB):

            class rotate:
                mouse = None
                up_key = None
                down_key = None
                left_key = None
                right_key = None
                sensitivity = None

            class pan_tilt:
                mouse = None
                up_key = None
                down_key = None
                left_key = None
                right_key = None
                sensitivity = None

            class truck_pedestal(metaclass=ConfigDB):
                mouse = MOUSE_LEFT | MOUSE_REVERSE_X_AXIS | MOUSE_REVERSE_Y_AXIS
                up_key = ord('8')
                down_key = ord('2')
                left_key = ord('4')
                right_key = ord('6')
                sensitivity = 0.2
                speed = 1.0

            class walk:
                mouse = None
                forward_key = None
                backward_key = None
                left_key = None
                right_key = None
                sensitivity = None
                speed = None

            class dolly(metaclass=ConfigDB):
                mouse = None
                in_key = None
                out_key = None
                sensitivity = None

            class zoom:
                mouse = MOUSE_WHEEL  # | MOUSE_REVERSE_WHEEL_AXIS
                in_key = 16777235
                out_key = 16777237
                sensitivity = 2.0

            class reset(metaclass=ConfigDB):
                key = 16777232
                mouse = MOUSE_NONE

        class table(metaclass=ConfigDB):
            """Excel-like wire-table overlay settings."""
            default_width = 200.0    # world units
            default_height = 120.0   # world units
            base_font_size = 10.0    # world units, scaled by zoom at render time
            min_font_px = 6
            max_font_px = 48

    class editor_3d(metaclass=ConfigDB):
        background_color = [0.20, 0.20, 0.20, 1.0]
        selected_color = [0.2, 0.6, 0.2, 0.25]

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
            smooth_notes = False
            smooth_transitions = True
            smooth_splices = True
            smooth_wire_markers = True

        class focal_target(metaclass=ConfigDB):
            enable = True
            color = [1.0, 0.4, 0.4, 1.0]
            radius = 0.25

        class drag_handler(metaclass=ConfigDB):
            mode = ''

        class rotation_handler(metaclass=ConfigDB):
            # Ring diameter as a multiple of the object's AABB space diagonal
            # (the largest distance between two corners of the bounding box)
            diameter_scale = 1.1
            # Grab handle diameter as a fraction of the ring diameter
            handle_diameter_scale = 0.08
            # Ring tube diameter as a fraction of the ring diameter
            tube_diameter_scale = 0.01
            # Ring/handle colors as scalar RGBA (0.0 - 1.0)
            y_color = [0.135, 0.684, 0.135, 0.8]
            # Enable snapping of ring-drag rotation to snap_angle increments
            snap_enable = False
            # Drag snap increment in degrees. Must have at most 2 decimal
            # places and divide the 360 degree range evenly (15, 22.5,
            # 0.45, ...) — invalid values disable snapping
            snap_angle = 15.0
            # Half-width in degrees of the detent at 0 — the dragged angle
            # sticks at exactly 0.0 until the cursor moves past this
            detent_width = 1.0

        class virtual_canvas(metaclass=ConfigDB):
            width = 1920
            height = 1080

        class floor(metaclass=ConfigDB):
            enable = True
            ground_height = 0.0
            size = 2000
            enable_floor_lock = True

            class grid(metaclass=ConfigDB):
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
                enable = True
                strength = 50.0

        class keyboard_settings(metaclass=ConfigDB):
            max_speed_factor = 10.0
            speed_factor_increment = 0.1
            start_speed_factor = 1.0

        class input(metaclass=ConfigDB):

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
                forward_key = 16777235
                backward_key = 16777237
                left_key = 16777234
                right_key = 16777236
                sensitivity = 1.0
                speed = 5.0

            class dolly:
                mouse = MOUSE_WHEEL
                in_key = None
                out_key = None
                sensitivity = 3.0

            class zoom(metaclass=ConfigDB):
                mouse = MOUSE_NONE  # | MOUSE_REVERSE_WHEEL_AXIS
                in_key = 43
                out_key = 45
                sensitivity = 5.0

            class reset(metaclass=ConfigDB):
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
            size = None
            position = None

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
        log_database = False
        log_file_transfers = True

    class debug(metaclass=ConfigDB):
        """Debug feature toggles used throughout the application."""
        class functions(metaclass=ConfigDB):
            """Function-call debug logging settings."""
            log_args = False
            log_duration = False

        class database(metaclass=ConfigDB):
            """SQL query profiling toggle.

            When enabled, ``SQLConnector`` accumulates per-statement call
            counts and timing (keyed by normalized SQL text, literals
            stripped) instead of doing nothing extra per query. Read it back
            with ``connector.dump_query_profile()``.
            """
            profile_queries = False

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

        # Child-process liveness heartbeat (image_process.py/model_process.py).
        # Each worker pings the parent this often while idle, then waits the
        # same span for a reply; no reply and it self-terminates immediately,
        # no retries -- daemon=True only cleans up children on a clean
        # interpreter shutdown (a hard crash skips that entirely), so without
        # this a dead parent would leave it orphaned. The parent thread just
        # forwards messages to the main thread -- no real work of its own --
        # so a live parent should never take anywhere near this long to
        # answer a ping.
        heartbeat_interval = 5.0

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
        position = None
        size = None

        tab_location = 2

        # QtWidgets.QTabWidget.TabShape.Rounded
        # QtWidgets.QTabWidget.TabShape.Triangular
        tab_shape = 0
        ui_perspective = (
            b'\x00\x00\x00\xFF\x00\x00\x00\x00\xFD\x00\x00\x00\x01\x00\x00\x00'
            b'\x01\x00\x00\x06\x47\x00\x00\x02\xF2\xFC\x02\x00\x00\x00\x02\xFC'
            b'\x00\x00\x00\x58\x00\x00\x02\x2E\x00\x00\x01\x21\x00\x08\x00\x15'
            b'\xFC\x01\x00\x00\x00\x02\xFC\x00\x00\x00\x4A\x00\x00\x04\x7F\x00'
            b'\x00\x00\x47\x01\x00\x00\x17\xFA\x00\x00\x00\x00\x02\x00\x00\x00'
            b'\x03\xFB\x00\x00\x00\x12\x00\x65\x00\x64\x00\x69\x00\x74\x00\x6F'
            b'\x00\x72\x00\x5F\x00\x33\x00\x64\x01\x00\x00\x00\x00\xFF\xFF\xFF'
            b'\xFF\x00\x00\x00\x16\x00\xFF\xFF\xFF\xFB\x00\x00\x00\x12\x00\x65'
            b'\x00\x64\x00\x69\x00\x74\x00\x6F\x00\x72\x00\x5F\x00\x32\x00\x64'
            b'\x01\x00\x00\x00\x00\xFF\xFF\xFF\xFF\x00\x00\x00\x16\x00\xFF\xFF'
            b'\xFF\xFB\x00\x00\x00\x1E\x00\x65\x00\x64\x00\x69\x00\x74\x00\x6F'
            b'\x00\x72\x00\x5F\x00\x70\x00\x65\x00\x67\x00\x62\x00\x6F\x00\x61'
            b'\x00\x72\x00\x64\x01\x00\x00\x00\x00\xFF\xFF\xFF\xFF\x00\x00\x00'
            b'\x16\x00\xFF\xFF\xFF\xFC\x00\x00\x04\xD2\x00\x00\x01\xBF\x00\x00'
            b'\x00\xEA\x00\x08\x00\x17\xFA\x00\x00\x00\x00\x02\x00\x00\x00\x05'
            b'\xFB\x00\x00\x00\x14\x00\x65\x00\x64\x00\x69\x00\x74\x00\x6F\x00'
            b'\x72\x00\x5F\x00\x6F\x00\x62\x00\x6A\x01\x00\x00\x00\x00\xFF\xFF'
            b'\xFF\xFF\x00\x00\x00\x28\x00\xFF\xFF\xFF\xFB\x00\x00\x00\x1C\x00'
            b'\x6F\x00\x62\x00\x6A\x00\x65\x00\x63\x00\x74\x00\x5F\x00\x62\x00'
            b'\x72\x00\x6F\x00\x77\x00\x73\x00\x65\x00\x72\x01\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\xFF\x00\x00\x00\x74\x00\xFF\xFF\xFF\xFB\x00\x00\x00'
            b'\x1C\x00\x65\x00\x64\x00\x69\x00\x74\x00\x6F\x00\x72\x00\x5F\x00'
            b'\x63\x00\x69\x00\x72\x00\x63\x00\x75\x00\x69\x00\x74\x01\x00\x00'
            b'\x00\x00\xFF\xFF\xFF\xFF\x00\x00\x01\x21\x00\x08\x00\x15\xFB\x00'
            b'\x00\x00\x1E\x00\x65\x00\x64\x00\x69\x00\x74\x00\x6F\x00\x72\x00'
            b'\x5F\x00\x61\x00\x73\x00\x73\x00\x65\x00\x6D\x00\x62\x00\x6C\x00'
            b'\x79\x01\x00\x00\x00\x00\xFF\xFF\xFF\xFF\x00\x00\x00\x16\x00\xFF'
            b'\xFF\xFF\xFB\x00\x00\x00\x14\x00\x6C\x00\x6F\x00\x67\x00\x5F\x00'
            b'\x76\x00\x69\x00\x65\x00\x77\x00\x65\x00\x72\x01\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\xFF\x00\x00\x00\x62\x00\xFF\xFF\xFF\xFB\x00\x00\x00'
            b'\x12\x00\x65\x00\x64\x00\x69\x00\x74\x00\x6F\x00\x72\x00\x5F\x00'
            b'\x64\x00\x62\x01\x00\x00\x02\x8F\x00\x00\x00\xBB\x00\x00\x00\x86'
            b'\x00\xFF\xFF\xFF\x00\x00\x00\x00\x00\x00\x02\xF2\x00\x00\x00\x04'
            b'\x00\x00\x00\x04\x00\x00\x00\x08\x00\x00\x00\x08\xFC\x00\x00\x00'
            b'\x03\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x24\x00\x73\x00'
            b'\x65\x00\x74\x00\x74\x00\x69\x00\x6E\x00\x67\x00\x73\x00\x33\x00'
            b'\x64\x00\x5F\x00\x74\x00\x6F\x00\x6F\x00\x6C\x00\x62\x00\x61\x00'
            b'\x72\x03\x00\x00\x00\x00\xFF\xFF\xFF\xFF\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x20\x00\x70\x00\x65\x00\x67\x00\x62\x00\x6F'
            b'\x00\x61\x00\x72\x00\x64\x00\x5F\x00\x74\x00\x6F\x00\x6F\x00\x6C'
            b'\x00\x62\x00\x61\x00\x72\x03\x00\x00\x01\x81\x00\x00\x01\x71\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00'
            b'\x00\x00\x1E\x00\x67\x00\x65\x00\x6E\x00\x65\x00\x72\x00\x61\x00'
            b'\x6C\x00\x5F\x00\x74\x00\x6F\x00\x6F\x00\x6C\x00\x62\x00\x61\x00'
            b'\x72\x03\x00\x00\x00\x00\xFF\xFF\xFF\xFF\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00\x1C\x00\x65'
            b'\x00\x64\x00\x69\x00\x74\x00\x6F\x00\x72\x00\x5F\x00\x74\x00\x6F'
            b'\x00\x6F\x00\x6C\x00\x62\x00\x61\x00\x72\x01\x00\x00\x00\x00\xFF'
            b'\xFF\xFF\xFF\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x18\x00'
            b'\x6E\x00\x6F\x00\x74\x00\x65\x00\x5F\x00\x74\x00\x6F\x00\x6F\x00'
            b'\x6C\x00\x62\x00\x61\x00\x72\x01\x00\x00\x01\xFC\xFF\xFF\xFF\xFF'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1C\x00\x6F\x00\x62'
            b'\x00\x6A\x00\x65\x00\x63\x00\x74\x00\x5F\x00\x74\x00\x6F\x00\x6F'
            b'\x00\x6C\x00\x62\x00\x61\x00\x72\x01\x00\x00\x02\x87\xFF\xFF\xFF'
            b'\xFF\x00\x00\x00\x00\x00\x00\x00\x00')

    class project(metaclass=ConfigDB):
        """Project-level defaults such as recent locations."""
        last_project = None
        model_dir = _utils.get_documents()


Config.open()
