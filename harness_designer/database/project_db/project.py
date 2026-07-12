# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable, TYPE_CHECKING

from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from .mixins import ColorMixin

if TYPE_CHECKING:
    from ...objects import project as _project_obj
    from ..global_db import model3d as _model3d


class ProjectsTable(PJTTableBase):
    """Represent a projects table in :mod:`harness_designer.database.project_db.project`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'projects'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import projects

        return projects.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import projects

        projects.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import projects

        projects.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["Project"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Project']
        """

        for db_id in PJTTableBase.__iter__(self):
            yield Project(self, db_id, db_id)

    def __getitem__(self, item) -> "Project":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Project`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return Project(self, item, item)
            raise IndexError(str(item))

        raise KeyError(item)

    def get_object_count(self, project_id) -> int:
        """Return the object count.

        UNKNOWN details are inferred from the callable name and signature.

        :param project_id: Identifier for the project.
        :type project_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        return self.select('object_count', id=project_id)[0][0]

    def set_object_count(self, project_id, value: int):
        """Set the object count.

        UNKNOWN details are inferred from the callable name and signature.

        :param project_id: Identifier for the project.
        :type project_id: UNKNOWN
        :param value: Value to store or process.
        :type value: int
        """
        self.update(project_id, object_count=value)

    def insert(self, name: str, description: str, creator: str, model_id: int | None, color_id: int) -> "Project":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param name: Name value.
        :type name: str
        :param description: Value for ``description``.
        :type description: str
        :param creator: Value for ``creator``.
        :type creator: str
        :param model_id: Value for ``model_id``.
        :type model_id: int
        :param color_id: Value for ``color_id``.
        :type color_id: int
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Project`
        """

        db_id = PJTTableBase.insert(self, name=name, description=description,
                                    creator=creator, model_id=model_id,
                                    color_id=color_id)

        return Project(self, db_id, db_id)


class Project(PJTEntryBase, ColorMixin):
    """Represent a project in :mod:`harness_designer.database.project_db.project`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: ProjectsTable = None

    def get_object(self) -> "_project_obj.Project":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_project_obj.Project`
        """
        return self._obj

    def set_object(self, obj: "_project_obj.Project"):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_project_obj.Project`
        """
        self._obj = obj

    @property
    def table(self) -> ProjectsTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`ProjectsTable`
        """
        return self._table

    _stored_name: str | DefaultStoredValueType = DefaultStoredValue

    @property
    def name(self) -> str:
        """Return the name.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        if self._stored_name is DefaultStoredValue:
            self._stored_name = self._table.select('name', id=self._db_id)[0][0]

        return self._stored_name

    @name.setter
    def name(self, value: str):
        """Set the name.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._stored_name = value
        self._table.update(self._db_id, name=value)

    _stored_description: str | DefaultStoredValueType = DefaultStoredValue

    @property
    def description(self) -> str:
        """Return the description.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        if self._stored_description is DefaultStoredValue:
            self._stored_description = self._table.select('description', id=self._db_id)[0][0]

        return self._stored_description

    @description.setter
    def description(self, value: str):
        """Set the description.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._stored_description = value
        self._table.update(self._db_id, description=value)

    _stored_creator: str | DefaultStoredValueType = DefaultStoredValue

    @property
    def creator(self) -> str:
        """Return the creator.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        if self._stored_creator is DefaultStoredValue:
            self._stored_creator = self._table.select('creator', id=self._db_id)[0][0]

        return self._stored_creator

    @creator.setter
    def creator(self, value: str):
        """Set the creator.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._stored_creator = value
        self._table.update(self._db_id, creator=value)

    _stored_model_id: int | None | DefaultStoredValueType = DefaultStoredValue

    @property
    def model_id(self) -> int:
        if self._stored_model_id is DefaultStoredValue:
            self._stored_model_id = self._table.select('model_id', id=self._db_id)[0][0]

        return self._stored_model_id

    @model_id.setter
    def model_id(self, value: int):
        self._stored_model_id = value
        self._stored_model = DefaultStoredValue

        self._table.update(self._db_id, model_id=value)

    _stored_model: "_model3d.Model3D | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    def model(self) -> "_model3d.Model3D":
        if self._stored_model is DefaultStoredValue:
            model_id = self.model_id
            if model_id is None:
                self._stored_model = None
            else:
                self._stored_model = self.table.db.global_db.models3d_table[model_id]

        return self._stored_model
