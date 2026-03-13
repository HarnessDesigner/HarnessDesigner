
from typing import TYPE_CHECKING

import wx

from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base3d as _base3d
from ...shapes import sphere as _sphere
from ...gl import materials as _materials
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire_layout as _pjt_wire_layout
    from .. import wire_layout as _wire_layout


Config = _config.Config.editor3d


class WireLayout(_base3d.Base3D):
    _parent: "_wire_layout.WireLayout" = None
    db_obj: "_pjt_wire_layout.PJTWireLayout"

    def __init__(self, parent: "_wire_layout.WireLayout",
                 db_obj: "_pjt_wire_layout.PJTWireLayout"):

        wires = db_obj.attached_wires
        if wires:
            diameter = wires[0].part.od_mm
            color = wires[0].part.color.ui
        else:
            raise RuntimeError('sanity check')

        material = _materials.Plastic(color)

        scale = _point.Point(diameter, diameter, diameter)
        vbo = _sphere.create_vbo()
        angle = _angle.Angle()
        position = db_obj.position3d

        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position, scale, material)

    def _sync_from_bundle_layout_point(self, point: _point.Point):
        """Callback to sync wire layout point position from bundle layout point.

        This is called when the bundle layout point moves. Wire layout points
        share coordinates with bundle layout points but do NOT share the same
        Point instances.
        """
        if self._is_deleted:
            return

        # Update our center to match the bundle layout point
        delta = point - self._position
        self._position += delta

    def bind_to_bundle_layout_point(self, bundle_layout_point: _point.Point):
        """Register callback to bundle layout point for synchronization.

        When a wire is bundled, wire layouts register callbacks to the relevant
        bundle layout Points so wires follow bundle movement.
        """
        if self._bundle_layout_point_id is not None:
            # Already bound, unbind first
            self.unbind_from_bundle_layout_point()

        # Store the db_id for tracking (not a strong reference)
        self._bundle_layout_point_id = bundle_layout_point.db_id

        # Bind our sync callback to the bundle layout point
        bundle_layout_point.bind(self._sync_from_bundle_layout_point)

        # Initial sync
        self._sync_from_bundle_layout_point(bundle_layout_point)

    def unbind_from_bundle_layout_point(self):
        """Unbind from bundle layout point.

        When a wire is unbundled, wire layouts unbind themselves from the
        bundle layout Points.
        """
        if self._bundle_layout_point_id is None:
            return

        # Use db_id-based lookup to get the point without holding strong reference
        # The PointMeta cache will return the same instance if it still exists
        try:
            bundle_layout_point = _point.Point(0.0, 0.0, 0.0,
                                               db_id=self._bundle_layout_point_id)

            bundle_layout_point.unbind(self._sync_from_bundle_layout_point)

        except:  # NOQA
            # Point may have been garbage collected
            pass

        self._bundle_layout_point_id = None

    def delete(self):
        """Override delete to clean up bundle bindings."""
        self.unbind_from_bundle_layout_point()
        super().delete()

    def get_context_menu(self):
        return WireLayoutMenu(self.mainframe.editor3d.editor, self)


class WireLayoutMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        item = self.Append(wx.ID_ANY, 'Add Splice')
        canvas.Bind(wx.EVT_MENU, self.on_add_splice, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Trace Circuit')
        canvas.Bind(wx.EVT_MENU, self.on_trace_circuit, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Select')
        canvas.Bind(wx.EVT_MENU, self.on_select, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Delete')
        canvas.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

    def on_add_splice(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_trace_circuit(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_select(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()
