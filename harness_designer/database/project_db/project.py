
from typing import Iterable as _Iterable

from . import PJTEntryBase, PJTTableBase


class ProjectsTable(PJTTableBase):
    __table_name__ = 'projects'

    def __iter__(self) -> _Iterable["Project"]:

        for db_id in PJTTableBase.__iter__(self):
            yield Project(self, db_id, db_id)

    def __getitem__(self, item) -> "Project":
        if isinstance(item, int):
            if item in self:
                return Project(self, item, None)
            raise IndexError(str(item))

        raise KeyError(item)

    def get_object_count(self, project_id) -> int:
        return self.select('object_count', id=project_id)[0][0]

    def set_object_count(self, project_id, value: int):
        self.update(project_id, object_count=value)

    def insert(self, name: str, description: str, creator: str) -> "Project":

        db_id = PJTTableBase.insert(self, name=name, description=description, creator=creator)

        return Project(self, db_id, db_id)


class Project(PJTEntryBase):
    _table: ProjectsTable = None

    @property
    def table(self) -> ProjectsTable:
        return self._table

    @property
    def name(self) -> str:
        return self._table.select('name', id=self._db_id)[0][0]

    @name.setter
    def name(self, value: str):
        self._table.update(self._db_id, name=value)

    @property
    def description(self) -> str:
        return self._table.select('description', id=self._db_id)[0][0]

    @description.setter
    def description(self, value: str):
        self._table.update(self._db_id, description=value)

    @property
    def creator(self) -> str:
        return self._table.select('creator', id=self._db_id)[0][0]

    @creator.setter
    def creator(self, value: str):
        self._table.update(self._db_id, creator=value)
