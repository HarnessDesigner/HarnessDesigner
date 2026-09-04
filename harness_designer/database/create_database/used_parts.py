# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Schema for the ``used_parts`` table.

Tracks accessory parts (TPA lock, CPA lock, cover, terminal) that have
previously been used together with a given housing, so the UI can offer
them back to the user the next time that housing is placed. One row per
housing/accessory pairing that has actually been used -- this is a global
history table, not a per-project instance table.
"""

from . import housings as _housings
from . import tpa_locks as _tpa_locks
from . import cpa_locks as _cpa_locks
from . import covers as _covers
from . import terminals as _terminals

from .. import db_connectors as _con


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'used_parts',
    id_field,
    _con.UUIDField('housing_id', default="X'00000000000000000000000000000000'", no_null=True,
                  references=_con.SQLFieldReference(_housings.table,
                                                    _housings.id_field,
                                                    on_delete=_con.REFERENCE_NO_ACTION,
                                                    on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('tpa_lock_id', default='NULL',
                  references=_con.SQLFieldReference(_tpa_locks.table,
                                                    _tpa_locks.id_field,
                                                    on_delete=_con.REFERENCE_NO_ACTION,
                                                    on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('cpa_lock_id', default='NULL',
                  references=_con.SQLFieldReference(_cpa_locks.table,
                                                    _cpa_locks.id_field,
                                                    on_delete=_con.REFERENCE_NO_ACTION,
                                                    on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('cover_id', default='NULL',
                  references=_con.SQLFieldReference(_covers.table,
                                                    _covers.id_field,
                                                    on_delete=_con.REFERENCE_NO_ACTION,
                                                    on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('terminal_id', default='NULL',
                  references=_con.SQLFieldReference(_terminals.table,
                                                    _terminals.id_field,
                                                    on_delete=_con.REFERENCE_NO_ACTION,
                                                    on_update=_con.REFERENCE_NO_ACTION))
)
