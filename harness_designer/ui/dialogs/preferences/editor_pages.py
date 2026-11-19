# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The Preferences pages of the three editors (3D, Pegboard, Schematic):
colours, lighting, floor, shading, tools and sizes.

The editors read most of these when they draw, so a change shows on the next
repaint of the view; the pages do not push anything to the canvases
themselves.
"""

from typing import TYPE_CHECKING

from PySide6 import QtWidgets

from . import fields as _fields
from . import page_base as _page_base
from .... import check_types as _check_types


if TYPE_CHECKING:
    from .... import ui as _ui


_WORLD = 100000.0


@_check_types.do
def _lighting(editor: str) -> list[_fields.Field]:
    path = f'{editor}.lighting'

    return [
        _fields.vector(path, 'position', 'Light position', -_WORLD, _WORLD, 10.0),
        _fields.color(path, 'ambient', 'Ambient'),
        _fields.color(path, 'diffuse', 'Diffuse'),
        _fields.color(path, 'specular', 'Specular')
    ]


@_check_types.do
def _smooth(editor: str, kinds: list[str]) -> list[_fields.Field]:
    """One 'smooth shading' tick box per object kind (``smooth_<kind>``)."""
    return [
        _fields.boolean(f'{editor}.renderer', f'smooth_{kind}',
                        kind.replace('_', ' ').title())
        for kind in kinds
    ]


@_check_types.do
def _reflections(editor: str) -> list[_fields.Field]:
    """The floor reflection settings. Only the 3D editor stores them: in the
    Pegboard and Schematic editors ``floor.reflections`` is an unsaved
    placeholder class (see ``config.py``), so they have no such group."""
    path = f'{editor}.floor.reflections'

    return [
        _fields.boolean(path, 'enable', 'Reflections'),
        _fields.real(path, 'strength', 'Strength', 0.0, 100.0, 1.0, 1)
    ]


class EditorPage(_page_base.PreferencesPage):
    """A page made only of groups of fields: ``groups`` is
    ``[(title, [field, ...]), ...]``."""

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None, mainframe: "_ui.MainFrame",
                 groups: list[tuple[str, list[_fields.Field]]]):
        super().__init__(parent, mainframe)

        for title, fields in groups:
            self.add_group(title, fields)

        self.finish()


@_check_types.do
def editor_3d_page(parent: QtWidgets.QWidget | None, mainframe: "_ui.MainFrame") -> EditorPage:
    editor = 'editor_3d'
    grid = f'{editor}.floor.grid'
    rotation = f'{editor}.rotation_handler'

    return EditorPage(parent, mainframe, [
        ('Colors', [
            _fields.color(editor, 'background_color', 'Background'),
            _fields.color(editor, 'selected_color', 'Selection')
        ]),
        ('Lighting', _lighting(editor)),
        ('Headlight', [
            _fields.boolean(f'{editor}.headlight', 'enable', 'Headlight'),
            _fields.real(f'{editor}.headlight', 'cutoff', 'Cutoff', 0.0, 180.0, 0.5, 1),
            _fields.real(f'{editor}.headlight', 'dissipate', 'Dissipate', 0.0, 1000.0, 1.0, 1),
            _fields.color(f'{editor}.headlight', 'color', 'Colour')
        ]),
        ('Focal target', [
            _fields.boolean(f'{editor}.focal_target', 'enable', 'Show focal target'),
            _fields.color(f'{editor}.focal_target', 'color', 'Colour'),
            _fields.real(f'{editor}.focal_target', 'radius', 'Radius', 0.01, 100.0, 0.1, 2)
        ]),
        ('Floor', [
            _fields.boolean(f'{editor}.floor', 'enable', 'Show floor'),
            _fields.real(f'{editor}.floor', 'ground_height', 'Ground height',
                         -_WORLD, _WORLD, 1.0, 2),
            _fields.integer(f'{editor}.floor', 'size', 'Floor size', 1, 10000000),
            _fields.boolean(f'{editor}.floor', 'enable_floor_lock', 'Floor lock')
        ]),
        ('Floor grid', [
            _fields.boolean(grid, 'enable', 'Show grid'),
            _fields.integer(grid, 'size', 'Grid size', 1, 100000),
            _fields.color(grid, 'primary_color', 'Primary tile'),
            _fields.color(grid, 'secondary_color', 'Secondary tile'),
            _fields.color(grid, 'primary_line_color', 'Primary line'),
            _fields.color(grid, 'secondary_line_color', 'Secondary line'),
            _fields.real(grid, 'primary_line_width', 'Primary line width', 0.0, 20.0, 0.05, 2),
            _fields.real(grid, 'secondary_line_width', 'Secondary line width', 0.0, 20.0, 0.05, 2),
            _fields.integer(grid, 'secondary_lines_per_tile', 'Secondary lines per tile', 0, 100),
            _fields.boolean(grid, 'secondary_line_shift', 'Shift secondary lines')
        ]),
        ('Floor reflections', _reflections(editor)),
        ('Smooth shading', _smooth(editor, [
            'covers', 'boots', 'housings', 'wires', 'bundles', 'seals',
            'cpa_locks', 'tpa_locks', 'terminals', 'notes', 'transitions',
            'splices', 'wire_markers'])),
        ('Rotation gizmo', [
            _fields.real(rotation, 'diameter_scale', 'Diameter scale', 0.1, 20.0, 0.1, 2),
            _fields.real(rotation, 'tube_diameter_scale', 'Tube diameter scale', 0.001, 1.0, 0.005, 4),
            _fields.color(rotation, 'x_color', 'X ring'),
            _fields.color(rotation, 'y_color', 'Y ring'),
            _fields.color(rotation, 'z_color', 'Z ring'),
            _fields.color(rotation, 'outer_ring_color', 'Outer ring'),
            _fields.boolean(rotation, 'snap_enable', 'Snap to angle'),
            _fields.real(rotation, 'snap_angle', 'Snap angle', 0.1, 180.0, 1.0, 1)
        ])
    ])


@_check_types.do
def editor_pegboard_page(parent: QtWidgets.QWidget | None, mainframe: "_ui.MainFrame") -> EditorPage:
    editor = 'editor_pegboard'
    floor = f'{editor}.floor'
    rotation = f'{editor}.rotation_handler'
    rope = f'{editor}.rope_pull'
    table = f'{editor}.table'

    return EditorPage(parent, mainframe, [
        ('Colors', [
            _fields.color(editor, 'background_color', 'Background'),
            _fields.color(editor, 'selected_color', 'Selection'),
            _fields.color(editor, 'wire_highlight_color', 'Wire highlight')
        ]),
        ('Lighting', _lighting(editor)),
        ('Floor', [
            _fields.boolean(floor, 'enable', 'Show floor'),
            _fields.real(floor, 'ground_height', 'Ground height', -_WORLD, _WORLD, 1.0, 2),
            _fields.boolean(floor, 'enable_floor_lock', 'Floor lock'),
            _fields.boolean(floor, 'snap', 'Snap to grid'),
            _fields.real(floor, 'target_dot_pixel_spacing', 'Dot spacing (pixels)', 2.0, 1000.0, 1.0, 1),
            _fields.color(floor, 'dot_color', 'Dot colour')
        ]),
        ('Smooth shading', _smooth(editor, [
            'boots', 'housings', 'wires', 'bundles', 'seals', 'terminals',
            'notes', 'transitions', 'splices', 'wire_markers'])),
        ('Rotation gizmo', [
            _fields.real(rotation, 'diameter_scale', 'Diameter scale', 0.1, 20.0, 0.1, 2),
            _fields.real(rotation, 'tube_diameter_scale', 'Tube diameter scale', 0.001, 1.0, 0.005, 4),
            _fields.color(rotation, 'y_color', 'Ring'),
            _fields.color(rotation, 'outer_ring_color', 'Outer ring'),
            _fields.real(rotation, 'ring_height', 'Ring height', 0.0, 10000.0, 1.0, 1)
        ]),
        ('Rope pull', [
            _fields.boolean(rope, 'enabled', 'Enabled'),
            _fields.boolean(rope, 'trace', 'Trace every solver decision to the log'),
            _fields.real(rope, 'zigzag_length_factor', 'Zigzag length factor', 0.0, 100.0, 0.1, 2),
            _fields.real(rope, 'threshold_factor', 'Threshold factor', 0.0, 100.0, 0.1, 2)
        ]),
        ('Wire table', [
            _fields.real(table, 'default_width', 'Default width', 10.0, 10000.0, 10.0, 1),
            _fields.real(table, 'default_height', 'Default height', 10.0, 10000.0, 10.0, 1),
            _fields.real(table, 'base_font_size', 'Base font size', 1.0, 200.0, 0.5, 1),
            _fields.integer(table, 'min_font_px', 'Smallest font (pixels)', 1, 200),
            _fields.integer(table, 'max_font_px', 'Largest font (pixels)', 1, 400)
        ])
    ])


@_check_types.do
def editor_schematic_page(parent: QtWidgets.QWidget | None, mainframe: "_ui.MainFrame") -> EditorPage:
    editor = 'editor_schematic'
    floor = f'{editor}.floor'
    rotation = f'{editor}.rotation_handler'
    layout = f'{editor}.layout'
    colors = f'{editor}.colors'
    sizes = f'{editor}.object_sizes'

    return EditorPage(parent, mainframe, [
        ('Colors', [
            _fields.color(editor, 'background_color', 'Background'),
            _fields.color(editor, 'selected_color', 'Selection'),
            _fields.color(colors, 'housing', 'Housing'),
            _fields.color(colors, 'housing_outline', 'Housing outline'),
            _fields.color(colors, 'label', 'Label'),
            _fields.color(colors, 'splice', 'Splice'),
            _fields.color(colors, 'wire_junction', 'Wire junction'),
            _fields.color(colors, 'free_terminal', 'Free terminal')
        ]),
        ('Lighting', _lighting(editor)),
        ('Layout', [
            _fields.real(layout, 'housing_spacing', 'Housing spacing', 0.0, 1000.0, 1.0, 1),
            _fields.real(layout, 'routing_grid', 'Routing grid', 0.1, 1000.0, 0.5, 2),
            _fields.real(layout, 'wire_spacing', 'Wire spacing', 0.0, 1000.0, 0.5, 2),
            _fields.real(layout, 'terminal_stub_length', 'Terminal stub length', 0.0, 1000.0, 0.5, 2)
        ]),
        ('Floor', [
            _fields.boolean(floor, 'enable', 'Show floor'),
            _fields.real(floor, 'ground_height', 'Ground height', -_WORLD, _WORLD, 1.0, 2),
            _fields.boolean(floor, 'enable_floor_lock', 'Floor lock'),
            _fields.boolean(floor, 'snap', 'Snap to grid'),
            _fields.real(floor, 'target_dot_pixel_spacing', 'Dot spacing (pixels)', 2.0, 1000.0, 1.0, 1),
            _fields.color(floor, 'dot_color', 'Dot colour')
        ]),
        ('Smooth shading', _smooth(editor, [
            'housings', 'wires', 'terminals', 'notes', 'transitions',
            'splices', 'wire_markers'])),
        ('Rotation gizmo', [
            _fields.real(rotation, 'diameter_scale', 'Diameter scale', 0.1, 20.0, 0.1, 2),
            _fields.real(rotation, 'tube_diameter_scale', 'Tube diameter scale', 0.001, 1.0, 0.005, 4),
            _fields.color(rotation, 'y_color', 'Ring'),
            _fields.color(rotation, 'outer_ring_color', 'Outer ring'),
            _fields.real(rotation, 'ring_height', 'Ring height', 0.0, 10000.0, 1.0, 1),
            _fields.real(rotation, 'snap_angle', 'Snap angle', 0.1, 180.0, 1.0, 1)
        ]),
        ('Object sizes', [
            _fields.real(f'{sizes}.terminal', 'name_font_size', 'Terminal name font size', 0.1, 100.0, 0.1, 2),
            _fields.real(f'{sizes}.free_terminal', 'diameter', 'Free terminal diameter', 0.1, 100.0, 0.1, 2),
            _fields.real(f'{sizes}.splice', 'diameter', 'Splice diameter', 0.1, 100.0, 0.1, 2),
            _fields.real(f'{sizes}.wire', 'diameter', 'Wire diameter', 0.1, 100.0, 0.1, 2),
            _fields.real(f'{sizes}.cavity', 'name_font_size', 'Cavity name font size', 0.1, 100.0, 0.1, 2),
            _fields.real(f'{sizes}.cavity', 'padding', 'Cavity padding', 0.0, 100.0, 0.05, 2),
            _fields.real(f'{sizes}.housing', 'width', 'Housing width', 1.0, 1000.0, 1.0, 1),
            _fields.real(f'{sizes}.housing', 'font_size', 'Housing font size', 0.1, 100.0, 0.1, 2)
        ])
    ])
