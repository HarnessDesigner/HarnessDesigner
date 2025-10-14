from . import Signal


class SIGNAL_CONNECTOR_SELECTED(Signal):

    def __init__(self, *, db_obj):
        super().__init__(id=id, db_obj=db_obj)


class SIGNAL_CONNECTOR_MOVED(Signal):

    def __init__(self, *, id: int, x: float | int, y: float | int,
                 z: float | int | None):
        super().__init__(id=id, x=x, y=y, z=z)


class SIGNAL_CONNECTOR_ANGLE_CHANGED(Signal):

    def __init__(self, *, id: int, x_angle: float, y_angle: float,
                 z_angle: float | None):
        super().__init__(id=id, x_angle=x_angle, y_angle=y_angle, z_angle=z_angle)


class SIGNAL_CONNECTOR_NEW(Signal):

    def __init__(self, *, id: int, x: float | int, y: float | int, z: float | int | None):
        super().__init__(id=id, x=x, y=y, z=z)


class SIGNAL_CONNECTOR_ADDED(Signal):

    def __init__(self, *, id: int, connector_id: int):
        super().__init__(id=id, connector_id=connector_id)


class SIGNAL_CONNECTOR_LOADED(Signal):

    def __init__(self, *, db_obj):
        super().__init__(db_obj=db_obj)
