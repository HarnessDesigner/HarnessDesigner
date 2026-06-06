# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from ..pjt_bases import PJTTableBase, PJTEntryBase


class BaseMixin:
    """Represent a base mixin in :mod:`harness_designer.database.project_db.mixins.base`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: PJTTableBase = None
    _db_id: int = None
    _obj = None

    @property
    def table(self):
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._table

    def _populate(self, tag):
        """Execute the populate operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param tag: Value for ``tag``.
        :type tag: UNKNOWN
        """
        PJTEntryBase._populate(self, tag)  # NOQA
