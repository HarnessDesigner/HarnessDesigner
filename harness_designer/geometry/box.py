from . import point as _point
from . import line as _line
from . import rect as _rect
from ..wrappers.decimal import Decimal as _decimal


class Box:

    def __init__(self, p1: _point, length: _decimal | None = None,
                 width: _decimal | None = None, height: _decimal | None = None,
                 p2: _point.Point | None = None, p3: _point.Point | None = None,
                 p4: _point.Point | None = None, p5: _point.Point | None = None,
                 p6: _point.Point | None = None, p7: _point.Point | None = None,
                 p8: _point.Point | None = None):

        if width is None and height is None:
            if None in (p2, p3, p4, p5, p6, p7, p8):
                raise ValueError('Width and height must be supplied or all points must be supplied')
        else:
            rect = _rect.Rect(p1, width=width, height=height)

            p2_1 = rect.p2
            p3_1 = rect.p3
            p4_1 = rect.p4

            rect = _rect.Rect(p1, width=width, height=length, x_angle=_decimal(90.00))
            p2_2 = rect.p2
            p2_3 = rect.p3
            p2_4 = rect.p4

            rect = _rect.Rect(p1, width=width, height=length, x_angle=_decimal(90.00), y_angle=_decimal(90.0))
            p2_3 = rect.p2
            p3_3 = rect.p3
            p4_3 = rect.p4





