
from . import projects as _projects
from . import bundle_covers as _bundle_covers
from . import transition_branches as _transition_branches

from .. import db_connectors as _con


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

# def pjt_concentrics(con, cur):
#     cur.execute('CREATE TABLE pjt_concentrics('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'bundle_id INTEGER DEFAULT NULL, '
#                 'transition_branch_id INTEGER DEFAULT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (bundle_id) REFERENCES pjt_bundles(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (transition_branch_id) REFERENCES pjt_transition_branches(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()
