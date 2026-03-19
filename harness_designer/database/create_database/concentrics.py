
from . import projects as _projects
from . import bundle_covers as _bundle_covers
from . import transition_branches as _transition_branches

from .. import db_connectors as _con
from ... import logger as _logger


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_concentrics',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('bundle_id', no_null=True,
                  references=_con.SQLFieldReference(_bundle_covers.pjt_table,
                                                    _bundle_covers.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),

    _con.IntField('transition_branch_id', no_null=True,
                  references=_con.SQLFieldReference(_transition_branches.pjt_table,
                                                    _transition_branches.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('notes', default='""', no_null=True)
)
