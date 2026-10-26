# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from .. import db_connectors as _con
from . import ip_supps as _ip_supps
from . import ip_fluids as _ip_fluids
from . import ip_solids as _ip_solids
from ... import check_types as _check_types
from .. import id_generator as _id_generator


if TYPE_CHECKING:
    from ... import splash_screen as _splash_screen
    from ..db_connectors import base as _connector_base

# Positional index -> ip_solids.name / ip_fluids.name, matching the order
# each was seeded in (see ip_solids.py/ip_fluids.py add_records) -- this
# table's own data below still refers to solids/fluids by that original
# sequential position, not by name directly.
_SOLID_NAMES_BY_INDEX = ('0', '1', '2', '3', '4', '5', '6', 'X')
_FLUID_NAMES_BY_INDEX = ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '6K', '9K', 'X')


@_check_types.do
def add_records(con: "_connector_base.ConnectorBase",
                splash: "_splash_screen.Splash", _: str | None = None) -> None:

    """
    Add a records.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param splash: Value for ``splash``.
    :type splash: _splash_screen.Splash

    :param _: Value for ``_``.
    :type _: str | None
    """

    raise NotImplementedError


@_check_types.do
def get_ip_rating_id(con: "_connector_base.ConnectorBase",  # NOQA
                     ip_rating: str) -> bytes:  # NOQA

    """
    Return the ip rating ID.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param ip_rating: Value for ``ip_rating``.
    :type ip_rating: str

    :returns: Return value. UNKNOWN details.
    :rtype: bytes
    """

    if ip_rating is None:
        return _id_generator.NIL_UUID.bytes

    ip_rating = ip_rating.upper().replace('-', '').replace(' ', '')

    con.execute('SELECT id FROM ip_ratings WHERE name=?;', (ip_rating,))
    rows = con.fetchall()
    if rows:
        return rows[0][0]

    con.execute('SELECT id FROM ip_ratings WHERE name=?;', ('IPXX',))
    rows = con.fetchall()
    if rows:
        return rows[0][0]

    return _id_generator.NIL_UUID.bytes


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'ip_ratings',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    # No schema-level default: previously defaulted to the seeded "Unknown"
    # row (id 7/12 under the old sequential scheme), but a fixed integer
    # can't name a dynamically-generated UUID. Callers that relied on the
    # implicit default now need to resolve the Unknown row's real id
    # explicitly before inserting.
    _con.UUIDField('solid_id', no_null=True,
                   references=_con.SQLFieldReference(_ip_solids.table, _ip_solids.id_field)),
    _con.UUIDField('fluid_id', no_null=True,
                   references=_con.SQLFieldReference(_ip_fluids.table, _ip_fluids.id_field)),
    _con.UUIDField('supp_id', default='NULL',
                   references=_con.SQLFieldReference(_ip_supps.table, _ip_supps.id_field))
)
