from typing import TYPE_CHECKING
import weakref


from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal
from . import base3d as _base3d
from ... import gl_materials as _gl_materials
from ...shapes import cylinder as _cylinder
from ... import Config

if TYPE_CHECKING:
    from ...database.project_db import pjt_bundle as _pjt_bundle
    from .. import bundle as _bundle


Config = Config.editor3d


def _build_model(p1: _point.Point, p2: _point.Point, diameter: _decimal):
    line = _line.Line(p1, p2)
    wire_length = line.length()

    wire_radius = diameter / _decimal(2.0)
    return _cylinder.create(float(wire_radius), float(wire_length))


class Bundle(_base3d.Base3D):
    _parent: "_bundle.Bundle" = None

    def __init__(self, parent: "_bundle.Bundle",
                 db_obj: "_pjt_bundle.PJTBundle"):

        _base3d.Base3D.__init__(self, parent)
        self._db_obj: "_pjt_bundle.PJTBundle" = db_obj

        self._part = db_obj.part

        self._color = self._part.color.ui
        self._diameter: _decimal = None
        self._is_dragging = False

        self._material = _gl_materials.Rubber(self._color.rgba_scalar)

        start_layout = db_obj.start_layout
        stop_layout = db_obj.stop_layout

        self._is_start_clickable = start_layout is None
        self._is_stop_clickable = stop_layout is None

        self._p1 = db_obj.start_point3d.point
        self._p2 = db_obj.stop_point3d.point

        self._model = None
        self._hit_test_rect = None

        # Track wires in this bundle using weak references
        # Wires hold strong references to bundles; bundles use weak refs to wires
        self._wires = []  # List of weak references to Wire objects

        self._p1.bind(self._build)
        self._p2.bind(self._build)

        self._build()

    @property
    def is_dragging(self) -> bool:
        return self._is_dragging

    @is_dragging.setter
    def is_dragging(self, value: bool):
        if value != self._is_dragging:
            self._is_dragging = value

            if value:
                # this is the agnostic for a bundle. Instead of rendering the bundle
                # over and over again which can get a bit expensive the larger the diameter
                # of the bundle instead we swap out the rendering of the cylinder
                # for rendering a line that is the same color.
                # it's not going to look as pretty but it will be a lot faster to render.

                # TODO: set dragging mode for wires if the end of the bundle is being dragged.

                self._triangles = _base3d.LineRenderer(self._p1, self._p2, self._diameter,
                                                       self._color.rgba_scalar)
            else:
                self._build()
        else:
            self._is_dragging = value

    def _build(self, _=None):
        if self._is_dragging:
            return

        if self._diameter is None:
            layers = self._db_obj.concentric.layers

            if layers:
                self._diameter = layers[-1].diameter
            else:
                self._diameter = self._part.min_size

        vertices, faces = _build_model(self._p1, self._p2, self._diameter)

        tris, nrmls, count = self._get_triangles(vertices, faces)
        angle = _angle.Angle.from_points(self._p1, self._p2)

        tris @= angle
        nrmls @= angle
        tris += self._p1

        p1, p2 = self._compute_rect(tris)

        self._position = ((p2 - p1) / _decimal(2.0)) + p1

        self._bb = [self._compute_bb(p1, p2)]
        self._rect = [[p1, p2]]

        if self._is_selected:
            self._material.x_ray_color = Config.selected_color
            self._material.x_ray = True
        else:
            self._material.x_ray = False

        self._triangles = [_base3d.TriangleRenderer([[tris, nrmls, count]], self._material)]

    def _get_triangles(self, vertices, faces):
        if Config.modeling.smooth_bundles:
            return self._compute_smoothed_vertex_normals(vertices, faces)
        else:
            return self._compute_vertex_normals(vertices, faces)

    def set_diameter(self, parent_layout, value: _decimal):
        # TODO: set transition branch diameter
        #       finish code to cascade bundle diameter
        #       through layouts from one end of the bundle to the other stopping
        #       at a boot, the end of the bundle or a transition branch
        self._diameter = value
        self._build()

        if parent_layout.position.db_id == self._p1.db_id:
            for layout in self.editor3d.mainframe.project.bundle_layouts:
                if layout.obj3d.position.db_id == self._p2.db_id:
                    layout.obj3d.set_diameter(self, value)
                    break
            else:
                for transition in self.editor3d.mainframe.project.transitions:
                    index = transition.obj3d.get_branch_index(self._p2)

        else:
            for layout in self.editor3d.mainframe.project.bundle_layouts:
                if layout.obj3d.position.db_id == self._p1.db_id:
                    layout.obj3d.set_diameter(self, value)
                    break
    
    def add_wire(self, wire):
        # Store weak reference to the wire
        wire_ref = weakref.ref(wire, self._on_wire_deleted)
        self._wires.append(wire_ref)
        
        # Hide the wire when it's bundled
        if wire.is_visible:
            wire.is_visible = False

            self._build()
    
    def remove_wire(self, wire):
        # Remove the weak reference
        for ref in self._wires[:]:
            w = ref()
            if w is None:
                self._wires.remove(ref)
            elif w == wire:
                self._wires.remove(ref)
                # Make the wire visible again
                wire.is_visible = True
                break

        self._build()
    
    def _on_wire_deleted(self, ref):
        """Callback when a wire is garbage collected."""
        if ref in self._wires:
            self._wires.remove(ref)

            self._build()
    
    @property
    def wires(self):
        """Get all wires in this bundle (that still exist)."""
        for ref in self._wires[:]:
            wire = ref()
            if wire is None:
                self._wires.remove(ref)
            else:
                yield wire
    
    @property
    def wire_count(self) -> int:
        """Return the number of wires in this bundle."""
        count = 0
        for ref in self._wires[:]:
            if ref() is None:
                self._wires.remove(ref)
            else:
                count += 1

        return count

    def delete(self):
        """Override delete to restore wire visibility."""
        # Restore visibility of all wires before deleting
        for ref in self._wires[:]:
            wire = ref()
            if wire is not None:
                wire.is_visible = True

        self._wires.clear()
        super().delete()

