from typing import TYPE_CHECKING

import wx
import math

from ..wrappers.decimal import Decimal as _decimal
from ..geometry import point as _point
from ..geometry import line as _line
from ..geometry import angle as _angle

if TYPE_CHECKING:
    from ..database.project_db import pjt_wire as _pjt_wire
    from ..database.project_db import pjt_bundle_layer as _pjt_bundle_layer
    from ..database.project_db import pjt_bundle as _pjt_bundle


class Layer:

    def __init__(self, db_obj: "_pjt_bundle_layer.PJTBundleLayer"):
        self._db_obj = db_obj
        self.bounding_boxes = []
        self.selected = None

    @property
    def id(self) -> int:
        return self._db_obj.layer_id

    @property
    def wires(self) -> list["_pjt_wire.PJTWire"]:
        return self._db_obj.wires

    @property
    def bundle(self) -> "_pjt_bundle.PJTBundle":
        return self._db_obj.bundle

    @staticmethod
    def _rotate_point(origin: _point.Point, point: _point.Point, angle: _decimal) -> _point.Point:
        """
        This is a 2d function and it only deals with the x and y axis.
        """
        ox, oy = origin.x, origin.y
        px, py = point.x, point.y

        cos = _decimal(math.cos(angle))
        sin = _decimal(math.sin(angle))

        x = px - ox
        y = py - oy

        qx = ox + (cos * x) - (sin * y)
        qy = oy + (sin * x) + (cos * y)
        return _point.Point(qx, qy)

    def set_selected(self, wire: "_pjt_wire.PJTWire"):
        self.selected = wire

    def get_selected(self) -> "_pjt_wire.PJTWire":
        return self.selected

    def hit_test(self, p: _point.Point) -> "_pjt_wire.PJTWire":
        for (p1, p2), wire in self.bounding_boxes:
            if p1 <= p <= p2:
                return wire

    def draw(self, gcdc: wx.GCDC, gc: wx.GraphicsContext):

        wires = self.wires
        gcdc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), 1))

        del self.bounding_boxes[:]

        for wire in wires:
            center = wire.layer_view_point.point
            part = wire.part
            is_filler = wire.is_filler_wire
            wire_color = part.color.ui
            wire_diamater = part.od_mm

            core_dia = part.conductor_dia_mm
            num_cores = part.num_conductors
            is_shielded = part.shielded
            symbol = part.core_material.symbol

            core_dia += _decimal(1.0)
            wire_diamater += _decimal(1.0)
            cr = core_dia / _decimal(2.0)
            core_offset = _point.Point(cr, cr)

            wire_r = wire_diamater / _decimal(2.0)
            wire_offset = _point.Point(wire_r, wire_r)
            wire_point = center - wire_offset

            self.bounding_boxes.append(((wire_point, center + wire_offset), wire))

            if symbol.startswith('Sn'):
                color = 'Tin'
            elif symbol.startswith('Cu'):
                color = 'Copper'
            elif symbol.startswith('Al'):
                color = 'Aluminum'
            elif symbol.startswith('Ti'):
                color = 'Titanium'
            elif symbol.startswith('Zn'):
                color = 'Zinc'
            elif symbol.startswith('Au'):
                color = 'Gold'
            elif symbol.startswith('Ag'):
                color = 'Silver'
            elif symbol.startswith('Ni'):
                color = 'Nickel'
            else:
                color = 'Tin'

            color = part._table.db.colors_table[color]
            core_color = color.ui
            gcdc.SetBrush(wx.Brush(wire_color))

            gc.DrawEllipse(float(wire_point.x), float(wire_point.y), float(wire_diamater), float(wire_diamater))

            if num_cores == 1:
                cp = center - core_offset

                gcdc.SetBrush(wx.Brush(core_color))
                if not is_filler:
                    gc.DrawEllipse(float(cp.x), float(cp.y), float(core_dia), float(core_dia))

            elif num_cores == 2:
                cond_dia = wire_diamater / _decimal(2.0)
                r = cond_dia /_decimal(2.0)

                p1 = _point.Point(cond_dia, _decimal(0.0)) + center
                p2 = self._rotate_point(center, p1, _decimal(180.0))

                offset = _point.Point(r, r)

                c1p = p1 - offset
                c1cp = p1 - core_offset

                c2p = p2 - offset
                c2cp = p2 - core_offset

                gc.DrawEllipse(float(c1p.x), float(c1p.y), float(cond_dia), float(cond_dia))
                gc.DrawEllipse(float(c2p.x), float(c2p.y), float(cond_dia), float(cond_dia))
                gcdc.SetBrush(wx.Brush(core_color))

                if not is_filler:
                    gc.DrawEllipse(float(c1cp.x), float(c1cp.y), float(core_dia), float(core_dia))
                    gc.DrawEllipse(float(c2cp.x), float(c2cp.y), float(core_dia), float(core_dia))

            elif num_cores == 3:
                cond_dia = wire_diamater * _decimal(46.296296)
                r = cond_dia / _decimal(2.0)

                diam = _decimal(1.16) * cond_dia
                pr = diam / _decimal(2.0)

                p1 = self._rotate_point(center, _point.Point(pr, _decimal(0.0)) + center, _decimal(30.0))
                p2 = self._rotate_point(center, p1, _decimal(120.0))
                p3 = self._rotate_point(center, p2, _decimal(120.0))

                offset = _point.Point(r, r)

                c1p = p1 - offset
                c1cp = p1 - core_offset

                c2p = p2 - offset
                c2cp = p2 - core_offset

                c3p = p3 - offset
                c3cp = p3 - core_offset

                gc.DrawEllipse(float(c1p.x), float(c1p.y), float(cond_dia), float(cond_dia))
                gc.DrawEllipse(float(c2p.x), float(c2p.y), float(cond_dia), float(cond_dia))
                gc.DrawEllipse(float(c3p.x), float(c3p.y), float(cond_dia), float(cond_dia))
                gcdc.SetBrush(wx.Brush(core_color))

                if not is_filler:
                    gc.DrawEllipse(float(c1cp.x), float(c1cp.y), float(core_dia), float(core_dia))
                    gc.DrawEllipse(float(c2cp.x), float(c2cp.y), float(core_dia), float(core_dia))
                    gc.DrawEllipse(float(c3cp.x), float(c3cp.y), float(core_dia), float(core_dia))

            elif num_cores == 4:
                cond_dia = wire_diamater * _decimal(0.413223)
                r = cond_dia / _decimal(2.0)

                diam = _decimal(1.42) * cond_dia
                pr = diam / _decimal(2.0)

                p1 = _point.Point(pr, _decimal(0.0)) + center
                p2 = self._rotate_point(center, p1, _decimal(90.0))
                p3 = self._rotate_point(center, p2, _decimal(90.0))
                p4 = self._rotate_point(center, p3, _decimal(90.0))

                offset = _point.Point(r, r)

                c1p = p1 - offset
                c1cp = p1 - core_offset

                c2p = p2 - offset
                c2cp = p2 - core_offset

                c3p = p3 - offset
                c3cp = p3 - core_offset

                c4p = p4 - offset
                c4cp = p4 - core_offset

                gc.DrawEllipse(float(c1p.x), float(c1p.y), float(cond_dia), float(cond_dia))
                gc.DrawEllipse(float(c2p.x), float(c2p.y), float(cond_dia), float(cond_dia))
                gc.DrawEllipse(float(c3p.x), float(c3p.y), float(cond_dia), float(cond_dia))
                gc.DrawEllipse(float(c4p.x), float(c4p.y), float(cond_dia), float(cond_dia))

                gcdc.SetBrush(wx.Brush(core_color))

                if not is_filler:
                    gc.DrawEllipse(float(c1cp.x), float(c1cp.y), float(core_dia), float(core_dia))
                    gc.DrawEllipse(float(c2cp.x), float(c2cp.y), float(core_dia), float(core_dia))
                    gc.DrawEllipse(float(c3cp.x), float(c3cp.y), float(core_dia), float(core_dia))
                    gc.DrawEllipse(float(c4cp.x), float(c4cp.y), float(core_dia), float(core_dia))

            else:
                raise RuntimeError('sanity check')
