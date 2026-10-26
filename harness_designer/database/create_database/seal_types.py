# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import json
import os

from .. import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


if TYPE_CHECKING:
    from ... import splash_screen as _splash_screen
    from ..db_connectors import base as _connector_base


# Seal category codes -- what a placement session actually branches on
# (see add_handlers.editor_3d.seal), independent of whichever free-text
# `name` a given manufacturer's catalog happens to use for the same
# real-world seal category.
CATEGORY_SWS = 'SWS'
CATEGORY_MAT = 'MAT'
CATEGORY_PLUG = 'PLUG'
CATEGORY_ACC = 'ACC'

CATEGORIES = (CATEGORY_SWS, CATEGORY_MAT, CATEGORY_PLUG, CATEGORY_ACC)

# Fallback for get_seal_type_id's own auto-create path when a caller
# doesn't know the category of a name it's never seen before (e.g. a
# future catalog scrape introducing a new manufacturer type string) --
# ACC ("all other seals that don't fit into the categories above", per
# the user's own definition) is the correct default for "uncategorized"
# specifically because it's the one category snap-target logic never
# treats as cavity/terminal-relevant, so a wrongly-defaulted new type
# fails safe (excluded from snapping) rather than wrongly participating.
_DEFAULT_CATEGORY = CATEGORY_ACC


@_check_types.do
def add_records(con: "_connector_base.ConnectorBase",  # NOQA
                splash: "_splash_screen.Splash", data_path: str) -> None:  # NOQA

    """
    Add a records.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param splash: Value for ``splash``.
    :type splash: _splash_screen.Splash

    :param data_path: Value for ``data_path``.
    :type data_path: str
    """

    raise NotImplementedError


@_check_types.do
def add_seal_type(con: "_connector_base.ConnectorBase", name: str, category: str,
                  id: int | None = None, commit: bool = True) -> bytes | None:

    """
    Add a new row to ``seal_types``.

    :param con: Database connection wrapper.
    :type con: _connector_base.ConnectorBase

    :param name: Manufacturer-facing type name (unique).
    :type name: str

    :param category: One of :data:`CATEGORIES` -- what placement logic
        actually branches on, independent of *name*.
    :type category: str

    :param id: ``0`` from the catalog JSON stores the nil UUID
               (the "none" row that unassigned foreign keys
               default to) instead of a generated id; ``None`` generates one.
    :type id: int | None

    :param commit: Whether to commit immediately.
    :type commit: bool

    :returns: The new row's id, or ``None`` when ``commit`` is ``False``
        (the caller is batching, per :func:`add_records`).
    :rtype: bytes | None
    """

    if id is None:
        id_bytes = _id_generator.generate_global_row_id(con).bytes
    else:
        id_bytes = _id_generator.NIL_UUID.bytes

    con.execute(
        'INSERT INTO seal_types (id, name, category) '
        'VALUES (?, ?, ?);', (id_bytes, name, category)
        )

    _logger.database(f'seal type added "{name}" ({category})')

    if commit:
        con.commit()
        return id


@_check_types.do
def get_seal_type_id(con: "_connector_base.ConnectorBase", name: str | None,
                     category: str | None = None) -> bytes | None:

    """
    Resolve *name* to its ``seal_types`` row id, auto-creating the row
    if this is the first time *name* has been seen.

    :param con:
    :type con: _connector_base.ConnectorBase

    :param name: Type name to resolve. Falsy (unset) is a legitimate
                 state for a housing's own seal type (which may genuinely have
                 none) -- returns ``None`` (SQL NULL) in that case, never the old
                 nil-UUID sentinel row, which no longer exists (there is no
                 placeholder "None"/"Unknown" row in ``seal_types`` any more --
                 an actual seal part's own type, unlike a housing's, is required
                 and never reaches this branch with a falsy *name*).
    :type name: str | None

    :param category: Category for a newly-created row (see
                     :data:`CATEGORIES`). Only consulted when *name* doesn't already
                     exist; falls back to :data:`_DEFAULT_CATEGORY` (logged) when not
                     given, since most callers already know every name they'll ever
                     pass (seeded from ``seal_types.json`` before any part/housing
                     import runs) and only hit the auto-create path for a genuinely
                     new, not-yet-classified manufacturer string.
    :type category: str | None

    :returns: The row id, or ``None`` when *name* is falsy.
    :rtype: bytes | None
    """

    if not name:
        return None

    con.execute('SELECT id FROM seal_types WHERE name=?;', (name,))
    res = con.fetchall()

    if not res:
        if category is None:
            category = _DEFAULT_CATEGORY
            _logger.database(
                f'adding seal type ("{name}") with no category given -- '
                f'defaulting to {_DEFAULT_CATEGORY}, '
                f'needs a real classification later')
        else:
            _logger.database(f'adding seal type ("{name}", {category})')

        db_id = _id_generator.generate_global_row_id(con).bytes
        con.execute(
            'INSERT INTO seal_types (id, name, category) '
            'VALUES (?, ?, ?);',
            (db_id, name, category))

        con.commit()

        _logger.database(f'seal type added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'seal_types',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('category', no_null=True, default=f"'{_DEFAULT_CATEGORY}'"),
)
