from . import Signal


class SIGNAL_PROJECT_LOAD(Signal):

    def __init__(self, *, project_id: int):
        super().__init__(project_id=project_id)


class SIGNAL_PROJECT_SAVE(Signal):

    def __init__(self, *, project_id: int):
        super().__init__(project_id=project_id)


class SIGNAL_PROJECT_CLOSE(Signal):

    def __init__(self, *, project_id: int):
        super().__init__(project_id=project_id)


class SIGNAL_PROJECT_LOADED(Signal):

    def __init__(self, *, project_id: int, sql_con):
        super().__init__(project_id=project_id, sql_con=sql_con)
