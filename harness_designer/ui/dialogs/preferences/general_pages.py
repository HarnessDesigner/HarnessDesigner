# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The Preferences pages that are not tied to one editor: Graphics,
Appearance, Project, Logging, Models & Resources, Database, Bundles,
Placement Colors and Ray Tracing.

A setting marked ``restart=True`` is read once when the application starts;
its label gets a ``*`` and the dialog says so after OK.
"""

from typing import TYPE_CHECKING

import sys

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from . import fields as _fields
from . import input_pages as _input_pages
from . import page_base as _page_base
from .. import render_setings as _render_settings
from ....gl import info as _gl_info
from ....gl import surface_format as _surface_format
from .... import config as _config
from .... import qt_settings as _qt_settings
from .... import themes as _themes
from .... import check_types as _check_types


if TYPE_CHECKING:
    from .... import ui as _ui
    from ....gl.canvas_base import canvas_window_base as _canvas_window_base


_RESTART_NOTE = (
    'Settings marked * are read when the application starts; restart '
    'Harness Designer for a change to them to take effect.')

# When the driver does not report a limit.
_DEFAULT_MAX_TEXTURE_SIZE = 8192


class GraphicsPage(_page_base.PreferencesPage):
    """OpenGL surface settings and the virtual canvas sizes."""

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None, mainframe: "_ui.MainFrame"):
        super().__init__(parent, mainframe)

        info = _gl_info.get()

        max_samples = info['Max Samples']
        if not max_samples:
            max_samples = 0

        max_texture = info['Texture Capabilities']['Max Texture Size']
        if not max_texture:
            max_texture = _DEFAULT_MAX_TEXTURE_SIZE

        samples: list[tuple[str, int]] = [('Off', 0)]
        for count in (2, 4, 8, 16):
            if count <= max_samples:
                samples.append((f'{count}x', count))

        self.add_note(_RESTART_NOTE)

        self.add_group('Window surface', [
            _fields.boolean('graphics', 'vsync', 'VSync', restart=True),
            _fields.choice('graphics', 'msaa_samples', 'Anti-aliasing (MSAA)',
                           samples, restart=True),
            _fields.choice('graphics', 'buffering', 'Buffering',
                           _surface_format.BUFFERING_CHOICES, restart=True)
        ])

        self.add_group('Render target', [
            _fields.choice('graphics', 'texture_format', 'Texture format',
                           _surface_format.TEXTURE_FORMAT_CHOICES, restart=True),
            _fields.boolean('graphics', 'srgb', 'sRGB framebuffer (experimental, replaces the format)',
                            restart=True),
            _fields.choice('graphics', 'update_behavior', 'Between frames',
                           _surface_format.UPDATE_BEHAVIOR_CHOICES, restart=True)
        ])

        self.add_group('Display scaling', [
            _fields.choice('graphics', 'high_dpi_policy', 'Fractional scale rounding',
                           _qt_settings.HIGH_DPI_CHOICES, restart=True),
            _fields.real('graphics', 'scale_factor', 'Extra scale factor', 0.0, 4.0,
                         0.05, 2, restart=True, special='Automatic')
        ])

        self.add_note(
            'Virtual canvas size: the fixed size, in pixels, each editor '
            'renders at (the window shows a crop of it, so make it at least '
            'as large as the biggest window you use). Bigger canvases cost '
            'GPU memory and fill time. Applies at once.')

        self._canvas_fields: dict[str, tuple[_fields.Field, _fields.Field]] = {}

        for editor, title in _input_pages.EDITORS:
            width = _fields.integer(
                f'{editor}.virtual_canvas', 'width', 'Width', 256, max_texture)

            height = _fields.integer(
                f'{editor}.virtual_canvas', 'height', 'Height', 256, max_texture)

            self._canvas_fields[editor] = (width, height)
            self.add_group(f'{title} editor virtual canvas', [width, height])

        self.finish()

    @_check_types.do
    def apply(self) -> list[str]:
        restart = super().apply()

        for editor, (width, height) in self._canvas_fields.items():
            if not (width.changed or height.changed):
                continue

            canvas = _fields.section(f'{editor}.virtual_canvas')
            self._editor_canvas(editor).set_virtual_size(
                canvas['width'], canvas['height'])

        return restart

    @_check_types.do
    def _editor_canvas(self, editor: str) -> "_canvas_window_base.CanvasWindowBase":
        """The canvas widget of the editor whose ``Config`` section is *editor*."""
        if editor == 'editor_3d':
            return self.mainframe.editor3d.editor

        if editor == 'editor_pegboard':
            return self.mainframe.editor_pegboard.editor

        return self.mainframe.editor2d.editor


class _InterfacePage(_page_base.PreferencesPage):
    """A page whose ``Config.interface`` settings are applied to the running
    application (``qt_settings.apply_live``) when any of them changed."""

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None, mainframe: "_ui.MainFrame"):
        super().__init__(parent, mainframe)

        self._live_fields: list[_fields.Field] = []

    @_check_types.do
    def add_live_group(self, title: str, fields: list[_fields.Field]) -> _page_base.FieldGroup:
        self._live_fields.extend(fields)

        return self.add_group(title, fields)

    @_check_types.do
    def apply(self) -> list[str]:
        restart = super().apply()

        if any(field.changed for field in self._live_fields):
            _qt_settings.apply_live(self.mainframe)

        return restart


class AppearancePage(_InterfacePage):
    """Theme, fonts, widget style, toolbars and docks of the main window."""

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None, mainframe: "_ui.MainFrame"):
        super().__init__(parent, mainframe)

        positions = QtWidgets.QTabWidget.TabPosition
        shapes = QtWidgets.QTabWidget.TabShape

        self._theme = _fields.choice(
            'mainframe', 'theme', 'Theme',
            [(name, name) for name in sorted(_themes.get_themes())])

        self._tab_location = _fields.choice(
            'mainframe', 'tab_location', 'Dock tab position', [
                ('Top', positions.North.value),
                ('Bottom', positions.South.value),
                ('Left', positions.West.value),
                ('Right', positions.East.value)])

        self._tab_shape = _fields.choice(
            'mainframe', 'tab_shape', 'Dock tab shape', [
                ('Rounded', shapes.Rounded.value),
                ('Triangular', shapes.Triangular.value)])

        self.add_group('Window', [self._theme, self._tab_location, self._tab_shape])

        fonts: list[tuple[str, str]] = [('System default', '')]
        fonts.extend((family, family) for family in QtGui.QFontDatabase.families())

        styles: list[tuple[str, str]] = [('System default', '')]
        styles.extend((name, name) for name in QtWidgets.QStyleFactory.keys())

        self.add_live_group('Font and style', [
            _fields.choice('interface', 'font_family', 'Font', fonts),
            _fields.integer('interface', 'font_size', 'Font size (points)', 0, 72,
                            special='System default'),
            _fields.choice('interface', 'style', 'Widget style', styles),
            _fields.choice('interface', 'color_scheme', 'Colour scheme',
                           _qt_settings.COLOR_SCHEME_CHOICES)
        ])

        self.add_note(
            "The theme's style sheet decides most of how the widgets look; "
            'the widget style and colour scheme only show where it does not. '
            'Widgets that set their own font keep it.')

        self.add_live_group('Toolbars', [
            _fields.integer('interface', 'toolbar_icon_size', 'Icon size (pixels)', 16, 64),
            _fields.choice('interface', 'toolbar_button_style', 'Button style',
                           _qt_settings.TOOLBAR_STYLE_CHOICES)
        ])

        self.add_note(
            'Buttons that are placed on a toolbar as a widget, such as the '
            'snap buttons, keep their own icon size.')

        self.add_live_group('Docks', [
            _fields.boolean('interface', 'dock_animated', 'Animate docking'),
            _fields.boolean('interface', 'dock_vertical_tabs', 'Vertical tabs'),
            _fields.boolean('interface', 'dock_grouped_dragging',
                            'Drag a group of tabbed docks together')
        ])

        if sys.platform == 'win32':
            self.add_group('Windows', [
                _fields.choice('interface', 'windows_dark_mode', 'Dark window frames',
                               _qt_settings.WINDOWS_DARK_MODE_CHOICES, restart=True),
                _fields.choice('interface', 'windows_font_engine', 'Font engine',
                               _qt_settings.WINDOWS_FONT_ENGINE_CHOICES, restart=True)
            ])

            self.add_note(_RESTART_NOTE)

        self.finish()

    @_check_types.do
    def apply(self) -> list[str]:
        restart = super().apply()

        mainframe_config = _config.Config.mainframe

        if self._theme.changed:
            _themes.load_theme(mainframe_config.theme)

        if self._tab_location.changed:
            self.mainframe.setTabPosition(
                QtCore.Qt.DockWidgetArea.AllDockWidgetAreas,
                QtWidgets.QTabWidget.TabPosition(mainframe_config.tab_location))

        if self._tab_shape.changed:
            self.mainframe.setTabShape(
                QtWidgets.QTabWidget.TabShape(mainframe_config.tab_shape))

        return restart


class PointerPage(_InterfacePage):
    """Mouse wheel, drag and double click behaviour, and pen and touch."""

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None, mainframe: "_ui.MainFrame"):
        super().__init__(parent, mainframe)

        self.add_live_group('Mouse', [
            _fields.integer('interface', 'wheel_scroll_lines', 'Wheel scroll lines', 0, 20,
                            special='System default'),
            _fields.integer('interface', 'drag_distance', 'Drag distance (pixels)', 0, 100,
                            special='System default'),
            _fields.integer('interface', 'drag_time', 'Drag time (milliseconds)', 0, 2000,
                            special='System default'),
            _fields.integer('interface', 'double_click_interval',
                            'Double click interval (milliseconds)', 0, 2000,
                            special='System default')
        ])

        self.add_note(
            'Drag distance and time are how far and how long a button must be '
            'held before a click counts as a drag.')

        self.add_group('Pen and touch', [
            _fields.boolean('interface', 'compress_tablet_events',
                            'Merge pen events that arrive in a burst', restart=True),
            _fields.boolean('interface', 'touch_to_mouse',
                            'Treat unhandled touch as mouse input', restart=True)
        ])

        self.add_note(_RESTART_NOTE)
        self.finish()


class _RayTracingItem(QtWidgets.QWidget):
    """Hosts the ray tracing settings panel the View > Ray Tracing dialog
    also uses; its ``apply()`` writes ``Config.ray_trace``."""

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None):
        super().__init__(parent)

        self._panel = _render_settings.RenderSettingsPanel(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._panel)

    @_check_types.do
    def apply(self) -> list[str]:
        self._panel.apply()

        return []


class RayTracingPage(_page_base.PreferencesPage):

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None, mainframe: "_ui.MainFrame"):
        super().__init__(parent, mainframe)

        self.add_item(_RayTracingItem(self))
        self.finish()


class _SimplePage(_page_base.PreferencesPage):
    """A page that is only groups of fields: ``groups`` is
    ``[(title, [field, ...]), ...]``."""

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None, mainframe: "_ui.MainFrame",
                 groups: list[tuple[str, list[_fields.Field]]], restart_note: bool = False):
        super().__init__(parent, mainframe)

        if restart_note:
            self.add_note(_RESTART_NOTE)

        for title, fields in groups:
            self.add_group(title, fields)

        self.finish()


@_check_types.do
def project_page(parent: QtWidgets.QWidget | None, mainframe: "_ui.MainFrame") -> _SimplePage:
    return _SimplePage(parent, mainframe, [
        ('Project', [
            _fields.folder('project', 'model_dir', 'Model folder')
        ])
    ])


@_check_types.do
def logging_page(parent: QtWidgets.QWidget | None, mainframe: "_ui.MainFrame") -> _SimplePage:
    return _SimplePage(parent, mainframe, [
        ('Log files', [
            _fields.folder('logging', 'save_path', 'Log folder', restart=True),
            _fields.integer('logging', 'num_logfiles', 'Log files kept', 1, 1000),
            _fields.integer('logging', 'num_archives', 'Archives kept', 0, 1000),
            _fields.integer('logging', 'max_logfile_size', 'Largest log file (bytes)',
                            1024, 2147483647)
        ]),
        ('What is logged', [
            _fields.boolean('logging', 'log_notice', 'Notices'),
            _fields.boolean('logging', 'log_warning', 'Warnings'),
            _fields.boolean('logging', 'log_error', 'Errors'),
            _fields.boolean('logging', 'log_traceback', 'Tracebacks'),
            _fields.boolean('logging', 'log_debug', 'Debug messages'),
            _fields.boolean('logging', 'log_database', 'Database activity'),
            _fields.boolean('logging', 'log_file_transfers', 'File transfers')
        ])
    ], restart_note=True)


@_check_types.do
def resources_page(parent: QtWidgets.QWidget | None, mainframe: "_ui.MainFrame") -> _SimplePage:
    return _SimplePage(parent, mainframe, [
        ('Worker processes', [
            _fields.integer('resources', 'model_watchdog_timeout',
                            'Model processing watchdog (seconds)', 1, 86400),
            _fields.real('resources', 'heartbeat_interval',
                         'Heartbeat interval (seconds)', 0.5, 600.0, 0.5, 1)
        ]),
        ('Model import', [
            _fields.integer('model_processing', 'max_triangle_count',
                            'Re-tessellate above (triangles)', 1000, 100000000),
            _fields.real('model_processing', 'loose_lin_deflection',
                         'Coarse linear deflection', 0.0001, 100.0, 0.01, 4),
            _fields.boolean('model_processing', 'loose_is_relative',
                            'Coarse deflection is relative'),
            _fields.real('model_processing', 'loose_ang_deflection',
                         'Coarse angular deflection', 0.001, 6.3, 0.05)
        ])
    ])


@_check_types.do
def database_page(parent: QtWidgets.QWidget | None, mainframe: "_ui.MainFrame") -> _SimplePage:
    return _SimplePage(parent, mainframe, [
        ('Database', [
            _fields.file('database.sqlite', 'database_path', 'SQLite database file',
                         restart=True),
            _fields.integer('database', 'monitor_duration', 'Monitor duration',
                            1, 86400),
            _fields.integer('database.maintenance', 'point_batch_size',
                            'Point maintenance batch size', 1, 100000)
        ])
    ], restart_note=True)


@_check_types.do
def bundles_page(parent: QtWidgets.QWidget | None, mainframe: "_ui.MainFrame") -> _SimplePage:
    return _SimplePage(parent, mainframe, [
        ('Bundle diameter', [
            _fields.real('bundle', 'unorganized_pack_fudge_factor',
                         'Unorganized packing factor', 1.0, 5.0, 0.05, 2)
        ]),
        ('Wire guards', [
            _fields.real('bundle.routing', 'guard_distance_min_mm',
                         'Minimum distance (mm)', 0.0, 1000.0, 1.0, 1),
            _fields.real('bundle.routing', 'guard_distance_diameter_multiple',
                         'Distance (times bundle diameter)', 0.0, 20.0, 0.1, 2)
        ])
    ])


@_check_types.do
def placement_colors_page(parent: QtWidgets.QWidget | None,
                          mainframe: "_ui.MainFrame") -> _SimplePage:
    names = [
        ('preview_color', 'Placement preview'),
        ('terminal_highlight', 'Terminal highlight'),
        ('housing_highlight', 'Housing highlight'),
        ('transition_highlight', 'Transition highlight'),
        ('bundle_highlight', 'Bundle highlight'),
        ('wire_highlight', 'Wire highlight'),
        ('cavity_highlight', 'Cavity highlight'),
        ('splice_highlight', 'Splice highlight'),
        ('snap_capable_highlight', 'Snap target highlight'),
        ('seal_size_mismatch_highlight', 'Seal size mismatch highlight')
    ]

    return _SimplePage(parent, mainframe, [
        ('Adding objects', [
            _fields.color('colors.add_object', name, label)
            for name, label in names
        ])
    ])
