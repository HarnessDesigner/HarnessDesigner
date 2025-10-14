from . import Signal


class SIGNAL_BUNDLE_SELECTED(Signal):

    def __init__(self, *, db_obj):
        super().__init__(id=id, db_obj=db_obj)


class SIGNAL_BUNDLE_P1_MOVED(Signal):

    def __init__(self, *, id: int, x: float | int, y: float | int,
                 z: float | int | None):
        super().__init__(id=id, x=x, y=y, z=z)


class SIGNAL_BUNDLE_P2_MOVED(Signal):

    def __init__(self, *, id: int, x: float | int, y: float | int,
                 z: float | int | None):
        super().__init__(id=id, x=x, y=y, z=z)


class SIGNAL_BUNDLE_LOADED(Signal):

    def __init__(self, *, db_obj):
        super().__init__(db_obj=db_obj)


class SIGNAL_BUNDLE_REMOVED(Signal):

    def __init__(self, *, id: int):
        super().__init__(id=id)


class SIGNAL_BUNDLE_LAYOUT_NEW(Signal):

    def __init__(self, *, id: int, x: float | int, y: float | int,
                 z: float | int | None):
        super().__init__(id=id, x=x, y=y, z=z)


class SIGNAL_BUNDLE_LAYOUT_ADDED(Signal):

    def __init__(self, *, id: int, layout_id: int):
        super().__init__(id=id, layout_id=layout_id)


class SIGNAL_BUNDLE_LAYOUT_MOVED(Signal):

    def __init__(self, *, id: int, x: float | int, y: float | int,
                 z: float | int | None):
        super().__init__(id=id, x=x, y=y, z=z)


class SIGNAL_BUNDLE_LAYOUT_LOADED(Signal):

    def __init__(self, *, db_obj):
        super().__init__(db_obj=db_obj)


class SIGNAL_BUNDLE_LAYOUT_REMOVED(Signal):

    def __init__(self, *, id: int):
        super().__init__(id=id)


class SIGNAL_BUNDLE_LAYOUT_SELECTED(Signal):

    def __init__(self, *, db_obj):
        super().__init__(db_obj=db_obj)
