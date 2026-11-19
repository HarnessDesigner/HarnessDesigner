# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Applies the Qt-level settings: display scaling and pen/touch handling
(``Config.graphics`` / ``Config.interface``, read before the Qt application
object exists), and the application font, style, colour scheme, pointer
behaviour, toolbars, dock options and Qt logging rules (applied at startup and
again whenever Preferences or Debug Settings is closed with OK or Apply).

The system's own values (the font, style, wheel lines, drag distance and
time, double click interval) are remembered the first time they are about to
be changed, so setting one back to "system default" restores it.
"""

from typing import Any
from typing import TYPE_CHECKING

import os
import sys

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from . import config as _config
from . import check_types as _check_types


if TYPE_CHECKING:
    from . import ui as _ui


Config = _config.Config

# (label, value) pairs for the Preferences drop downs.
HIGH_DPI_CHOICES: list[tuple[str, str]] = [
    ('Qt default', 'default'),
    ('Round', 'round'),
    ('Round, prefer floor', 'round_prefer_floor'),
    ('Ceil', 'ceil'),
    ('Floor', 'floor'),
    ('Exact (pass through)', 'pass_through')
]

COLOR_SCHEME_CHOICES: list[tuple[str, str]] = [
    ('System', 'system'),
    ('Light', 'light'),
    ('Dark', 'dark')
]

TOOLBAR_STYLE_CHOICES: list[tuple[str, str]] = [
    ('Icons only', 'icon'),
    ('Text only', 'text'),
    ('Text beside icons', 'text_beside'),
    ('Text under icons', 'text_under')
]

WINDOWS_DARK_MODE_CHOICES: list[tuple[str, str]] = [
    ('Default', 'default'),
    ('Off', 'off'),
    ('Window frames only', 'frames')
]

WINDOWS_FONT_ENGINE_CHOICES: list[tuple[str, str]] = [
    ('Default', 'default'),
    ('DirectWrite', 'directwrite'),
    ('FreeType', 'freetype'),
    ('GDI (native)', 'native')
]

_Rounding = QtCore.Qt.HighDpiScaleFactorRoundingPolicy

_ROUNDING: dict[str, QtCore.Qt.HighDpiScaleFactorRoundingPolicy] = {
    'round': _Rounding.Round,
    'round_prefer_floor': _Rounding.RoundPreferFloor,
    'ceil': _Rounding.Ceil,
    'floor': _Rounding.Floor,
    'pass_through': _Rounding.PassThrough
}

_ColorScheme = QtCore.Qt.ColorScheme

_COLOR_SCHEMES: dict[str, QtCore.Qt.ColorScheme] = {
    'system': _ColorScheme.Unknown,
    'light': _ColorScheme.Light,
    'dark': _ColorScheme.Dark
}

_ToolButtonStyle = QtCore.Qt.ToolButtonStyle

_TOOLBAR_STYLES: dict[str, QtCore.Qt.ToolButtonStyle] = {
    'icon': _ToolButtonStyle.ToolButtonIconOnly,
    'text': _ToolButtonStyle.ToolButtonTextOnly,
    'text_beside': _ToolButtonStyle.ToolButtonTextBesideIcon,
    'text_under': _ToolButtonStyle.ToolButtonTextUnderIcon
}

# What the Windows platform plugin is told, by setting value.
_WINDOWS_DARK_MODE: dict[str, str] = {
    'off': 'darkmode=0',
    'frames': 'darkmode=1'
}

# The system's values, captured before the first change.
_os_defaults: dict[str, Any] = {}


@_check_types.do
def apply_before_application() -> None:
    """
    Settings Qt reads while it creates the application object; call it
    before ``QApplication(...)``. A value already set in the environment
    (``QT_SCALE_FACTOR``, ``QT_QPA_PLATFORM``) is left alone.
    """

    graphics = Config.graphics
    interface = Config.interface

    if graphics.high_dpi_policy != 'default':
        QtGui.QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            _ROUNDING[graphics.high_dpi_policy])

    if graphics.scale_factor > 0.0:
        os.environ.setdefault('QT_SCALE_FACTOR', str(graphics.scale_factor))

    attributes = QtCore.Qt.ApplicationAttribute

    QtCore.QCoreApplication.setAttribute(
        attributes.AA_CompressTabletEvents, interface.compress_tablet_events)

    QtCore.QCoreApplication.setAttribute(
        attributes.AA_SynthesizeMouseForUnhandledTouchEvents,
        interface.touch_to_mouse)

    if sys.platform != 'win32':
        return

    # The plugin's options go in QT_QPA_PLATFORM separated by colons
    # ('windows:darkmode=1:fontengine=freetype'); commas are an error.
    options: list[str] = []

    if interface.windows_dark_mode != 'default':
        options.append(_WINDOWS_DARK_MODE[interface.windows_dark_mode])

    if interface.windows_font_engine != 'default':
        options.append(f'fontengine={interface.windows_font_engine}')

    if options:
        os.environ.setdefault('QT_QPA_PLATFORM', ':'.join(['windows'] + options))


@_check_types.do
def _remember_defaults(app: QtWidgets.QApplication) -> None:
    """Keep the system's values the first time, so 'default' can restore them."""
    if _os_defaults:
        return

    _os_defaults['font'] = QtGui.QFont(app.font())
    _os_defaults['style'] = app.style().name()
    _os_defaults['wheel_scroll_lines'] = app.wheelScrollLines()
    _os_defaults['drag_distance'] = app.startDragDistance()
    _os_defaults['drag_time'] = app.startDragTime()
    _os_defaults['double_click_interval'] = app.doubleClickInterval()


@_check_types.do
def apply_application(app: QtWidgets.QApplication) -> None:
    """Font, style, colour scheme, pointer behaviour and Qt logging rules."""
    _remember_defaults(app)

    interface = Config.interface

    style = interface.style
    if not style:
        style = _os_defaults['style']

    if app.style().name().lower() != style.lower():
        app.setStyle(style)

    app.styleHints().setColorScheme(_COLOR_SCHEMES[interface.color_scheme])

    font = QtGui.QFont(_os_defaults['font'])

    if interface.font_family:
        font.setFamily(interface.font_family)

    if interface.font_size > 0:
        font.setPointSize(interface.font_size)

    if font != app.font():
        app.setFont(font)

    wheel = interface.wheel_scroll_lines
    if wheel <= 0:
        wheel = _os_defaults['wheel_scroll_lines']

    app.setWheelScrollLines(wheel)

    distance = interface.drag_distance
    if distance <= 0:
        distance = _os_defaults['drag_distance']

    app.setStartDragDistance(distance)

    drag_time = interface.drag_time
    if drag_time <= 0:
        drag_time = _os_defaults['drag_time']

    app.setStartDragTime(drag_time)

    interval = interface.double_click_interval
    if interval <= 0:
        interval = _os_defaults['double_click_interval']

    app.setDoubleClickInterval(interval)

    apply_logging_rules()


@_check_types.do
def apply_logging_rules() -> None:
    """Hand ``Config.debug.qt.logging_rules`` to Qt (rules may be separated
    by ';' as well as by line breaks)."""
    rules = Config.debug.qt.logging_rules.replace(';', '\n')

    QtCore.QLoggingCategory.setFilterRules(rules)


@_check_types.do
def dock_options() -> QtWidgets.QMainWindow.DockOption:
    """The main window's dock options from ``Config.interface``."""
    options = QtWidgets.QMainWindow.DockOption

    flags = options.AllowTabbedDocks | options.AllowNestedDocks

    if Config.interface.dock_animated:
        flags |= options.AnimatedDocks

    if Config.interface.dock_vertical_tabs:
        flags |= options.VerticalTabs

    if Config.interface.dock_grouped_dragging:
        flags |= options.GroupedDragging

    return flags


@_check_types.do
def apply_mainframe(mainframe: "_ui.MainFrame") -> None:
    """Dock options, and icon size and button style of the main window's
    toolbars (not the toolbars inside panels)."""
    interface = Config.interface

    mainframe.setDockOptions(dock_options())

    size = QtCore.QSize(interface.toolbar_icon_size, interface.toolbar_icon_size)
    style = _TOOLBAR_STYLES[interface.toolbar_button_style]

    toolbars = mainframe.findChildren(
        QtWidgets.QToolBar, options=QtCore.Qt.FindChildOption.FindDirectChildrenOnly)

    for toolbar in toolbars:
        toolbar.setIconSize(size)
        toolbar.setToolButtonStyle(style)


@_check_types.do
def apply_live(mainframe: "_ui.MainFrame") -> None:
    """Everything that can be applied to the running application."""
    apply_application(QtWidgets.QApplication.instance())
    apply_mainframe(mainframe)
