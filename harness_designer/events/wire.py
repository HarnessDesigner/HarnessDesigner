from . import Signal


class SIGNAL_WIRE_SELECTED(Signal):

    def __init__(self, *, db_obj):
        super().__init__(id=id, db_obj=db_obj)


class SIGNAL_WIRE_P1_MOVED(Signal):

    def __init__(self, *, id: int, x: float | int, y: float | int,
                 z: float | int | None):
        super().__init__(id=id, x=x, y=y, z=z)


class SIGNAL_WIRE_P1_CHANGED(Signal):
    
    def __init__(self, *, id: int, x: float | int, y: float | int,
                 z: float | int | None):
        super().__init__(id=id, x=x, y=y, z=z)


class SIGNAL_WIRE_P2_MOVED(Signal):

    def __init__(self, *, id: int, x: float | int, y: float | int,
                 z: float | int | None):
        super().__init__(id=id, x=x, y=y, z=z)


class SIGNAL_WIRE_REMOVED(Signal):

    def __init__(self, *, id: int):
        super().__init__(id=id)


class SIGNAL_WIRE_ADDED(Signal):

    def __init__(self, *, id: int, wire_id: int):
        super().__init__(id=id, wire_id=wire_id)


class SIGNAL_WIRE_NEW(Signal):

    def __init__(self, *, id: int, x1: int | float, y1: int | float, z1: int | float | None,
                 x2: int | float, y2: int | float, z2: int | float | None):
        super().__init__(id=id, x1=x1, y1=y1, z1=z1, x2=x2, y2=y2, z2=z2)


class SIGNAL_WIRE_LOADED(Signal):

    def __init__(self, *, db_obj):
        super().__init__(db_obj=db_obj)


class SIGNAL_WIRE_LAYOUT_NEW(Signal):

    def __init__(self, *, id: int, x: float | int, y: float | int,
                 z: float | int | None):
        super().__init__(id=id, x=x, y=y, z=z)


class SIGNAL_WIRE_LAYOUT_ADDED(Signal):

    def __init__(self, *, id: int, layout_id: int):
        super().__init__(id=id, layout_id=layout_id)


class SIGNAL_WIRE_LAYOUT_MOVED(Signal):

    def __init__(self, *, id: int, x: float | int, y: float | int, z: float | int | None):
        super().__init__(id=id, x=x, y=y, z=z)


class SIGNAL_WIRE_LAYOUT_LOADED(Signal):

    def __init__(self, *, db_obj):
        super().__init__(db_obj=db_obj)


class SIGNAL_WIRE_LAYOUT_REMOVED(Signal):

    def __init__(self, *, id: int):
        super().__init__(id=id)


class SIGNAL_WIRE_LAYOUT_SELECTED(Signal):

    def __init__(self, *, db_obj):
        super().__init__(db_obj=db_obj)
