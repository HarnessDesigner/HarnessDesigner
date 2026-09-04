# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import json
import os

from .. import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


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
def add_records(con, splash, data_path):
    """Add a records.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param splash: Value for ``splash``.
    :type splash: UNKNOWN
    :param data_path: Value for ``data_path``.
    :type data_path: UNKNOWN
    """
    con.execute('SELECT 1 FROM seal_types LIMIT 1;')
    if con.fetchall():
        return

    json_path = os.path.join(data_path, 'seal_types.json')

    if os.path.exists(json_path):
        splash.SetText(f'Loading Seal Types file...')
        splash.flush()

        _logger.database(json_path)

        with open(json_path, 'r') as f:
            data = json.loads(f.read())

        if isinstance(data, dict):
            data = [value for value in data.values()]

        data_len = len(data)

        splash.SetText(f'Adding seal type to db [0 | {data_len}]...')
        splash.flush()

        for i, item in enumerate(data):
            splash.SetText(f'Adding seal type to db [{i + 1} | {data_len}]...')

            # seal_types.json is a pre-UUID-migration seed file and still
            # carries a leftover integer "id" per entry -- discard it so
            # every row gets a freshly generated UUID id instead of
            # colliding integers.
            item.pop('id', None)
            add_seal_type(con, commit=False, **item)

    con.commit()


@_check_types.do
def add_seal_type(con, name: str, category: str, commit: bool = True) -> bytes | None:
    """Add a new row to ``seal_types``.

    :param con: Database connection wrapper.
    :param name: Manufacturer-facing type name (unique).
    :param category: One of :data:`CATEGORIES` -- what placement logic
        actually branches on, independent of *name*.
    :param commit: Whether to commit immediately.
    :returns: The new row's id, or ``None`` when ``commit`` is ``False``
        (the caller is batching, per :func:`add_records`).
    """

    id = _id_generator.generate_global_row_id(con).bytes

    con.execute(
        'INSERT INTO seal_types (id, name, category) '
        'VALUES (?, ?, ?);', (id, name, category)
        )

    _logger.database(f'seal type added "{name}" ({category})')

    if commit:
        con.commit()
        return id


@_check_types.do
def get_seal_type_id(con, name: str | None, category: str | None = None) -> bytes | None:
    """Resolve *name* to its ``seal_types`` row id, auto-creating the row
    if this is the first time *name* has been seen.

    :param name: Type name to resolve. Falsy (unset) is a legitimate
        state for a housing's own seal type (which may genuinely have
        none) -- returns ``None`` (SQL NULL) in that case, never the old
        nil-UUID sentinel row, which no longer exists (there is no
        placeholder "None"/"Unknown" row in ``seal_types`` any more --
        an actual seal part's own type, unlike a housing's, is required
        and never reaches this branch with a falsy *name*).
    :param category: Category for a newly-created row (see
        :data:`CATEGORIES`). Only consulted when *name* doesn't already
        exist; falls back to :data:`_DEFAULT_CATEGORY` (logged) when not
        given, since most callers already know every name they'll ever
        pass (seeded from ``seal_types.json`` before any part/housing
        import runs) and only hit the auto-create path for a genuinely
        new, not-yet-classified manufacturer string.
    :returns: The row id, or ``None`` when *name* is falsy.
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
                f'defaulting to {_DEFAULT_CATEGORY}, needs a real classification later')
        else:
            _logger.database(f'adding seal type ("{name}", {category})')

        db_id = _id_generator.generate_global_row_id(con).bytes
        con.execute(
            'INSERT INTO seal_types (id, name, category) VALUES (?, ?, ?);',
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
