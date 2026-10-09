# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ..bases import (TableBase, EntryBase,
                     DefaultStoredValue as _DefaultStoredValue,
                     DefaultStoredValueType as _DefaultStoredValueType)
from .... import check_types as _check_types
from ... import id_generator as _id_generator


if TYPE_CHECKING:
    from .. import bases as _glb_bases


DefaultStoredValue = _DefaultStoredValue
DefaultStoredValueType = _DefaultStoredValueType

# A NOT NULL foreign key column that has no real value stored (a lookup the
# part's source data never supplied) holds this all-zero id instead of NULL,
# and there is no row for it in the referenced table. Mixins return None for
# it rather than trying to build an entry for a row that doesn't exist.
NIL_ID: bytes = _id_generator.NIL_UUID.bytes


class BaseMixin:
    """Represent a base mixin in :mod:`harness_designer.database.global_db.mixins.base`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: TableBase = None
    _db_id: int | bytes | None = None

    @property
    @_check_types.do
    def table(self) -> "_glb_bases.TableBase":
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._table

    @_check_types.do
    def _populate(self, tag: str) -> None:
        """Execute the populate operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param tag: Value for ``tag``.
        :type tag: UNKNOWN
        """
        EntryBase._populate(self, tag)  # NOQA
