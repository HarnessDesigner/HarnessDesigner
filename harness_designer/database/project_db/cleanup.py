# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
project_db/cleanup.py
=====================
Deferred orphan-point cleanup for the project database.

WHY DEFERRED?
-------------
During editing, drag-and-drop operations repoint objects from one Point to
another.  A point that appears temporarily unreferenced between two related
operations should not be deleted prematurely.  Running an orphan check after
every single operation is also expensive at precisely the moment the user is
actively interacting with the UI.

Cleanup runs at three moments:

1. **Idle time** — ``ProjectCleanup.process_chunk()`` called from EVT_IDLE
   in small batches while the user is not interacting.
2. **Application exit** — full pass in ``MainFrame.on_close``.
3. **On user request** — full pass from a Tools menu action.

HOW THE CANDIDATE REDUCTION WORKS
-----------------------------------
A batch of candidate point IDs is passed through each project table in turn
using ``PJTTableBase.find_unreferenced_ids(candidate_ids, suffix)``.

That method builds a single query for its table that returns only the IDs
NOT found in any of the table's point reference columns.  The surviving set
is passed to the next table.  Each table call can only shrink the set.

If the set empties before all tables have been checked the loop exits early.
IDs that survive all table checks are confirmed orphans and are deleted.

No hardcoded column lists are needed — ``find_unreferenced_ids`` discovers
relevant columns at runtime from the cached ``field_names`` on each table,
filtered by the naming convention suffix (``'_point3d_id'`` /
``'_point2d_id'``).  New tables added to the schema are covered automatically.

CURSOR DESIGN (chunked idle pass)
----------------------------------
The cursor is the highest point ID processed in the previous batch, not a
row offset.  ``SELECT id FROM pjt_points3d WHERE id > ? ORDER BY id LIMIT ?``
is safe against deletions mid-scan.
"""

from typing import TYPE_CHECKING

from ... import config as _config

if TYPE_CHECKING:
    from . import pjt_bases as _pjt_bases
    from ...objects import project as _project


Config = _config.Config


# ══════════════════════════════════════════════════════════════════════════════
# ProjectCleanup — chunked idle-time cleanup
# ══════════════════════════════════════════════════════════════════════════════

class ProjectCleanup:
    """
    Per-project orphan-point cleanup manager.

    Created in ``Project.__init__`` immediately after ``ptables.load()``.
    Discarded automatically when the project closes.

    The idle handler calls ``process_chunk()`` which processes BATCH_SIZE
    point IDs per call.  Returns True while work remains, False when the
    full pass is complete.

    Example usage with a zero-interval QTimer::

        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(0)
        self._idle_timer.timeout.connect(self._on_idle)
        self._idle_timer.start()

        def _on_idle(self):
            if self.project is None:
                return
            if not self.project.cleanup.process_chunk():
                self._idle_timer.stop()
    """

    def __init__(self, project: "_project.Project"):
        self.project = project
        self._cursor_3d = 0
        self._cursor_2d = 0
        self._phase = '3d'

        self._tables_3d = [table for table in project.ptables.tables if table.has_points3d]
        self._tables_2d = [table for table in project.ptables.tables if table.has_points3d]

    def process_chunk(self) -> bool:
        """
        Process one batch of BATCH_SIZE point IDs.

        Returns True if more work remains, False when the full pass is
        complete and cursors have been reset for the next idle cycle.
        """

        if self._phase == '3d':
            self._cursor_3d = self._process_batch(
                'pjt_points3d', self._tables_3d, self._cursor_3d)

            if self._cursor_3d == 0:
                self._phase = '2d'

            return True

        if self._phase == '2d':
            self._cursor_2d = self._process_batch(
                'pjt_points2d', self._tables_2d, self._cursor_2d)

            if self._cursor_2d == 0:
                self._phase = '3d'

        return False

    def _process_batch(self, table_name: str, tables: list["_pjt_bases.PJTTableBase"],
                       cursor: int) -> bool:
        """
        Fetch the next BATCH_SIZE IDs after the cursor, find orphans,
        delete them.  Returns True when the end of the table is reached.
        """
        con = self.project.connector

        # Compare cursor against the actual highest ID in the table.
        # len(rows) < BATCH_SIZE cannot reliably signal end-of-table
        # because deleted rows leave gaps in the ID sequence — there
        # may be rows with higher IDs even when fewer than BATCH_SIZE
        # rows were returned for this range.
        con.execute(f'SELECT MAX(id) FROM {table_name} WHERE project_id = ?;',
                    (self.project.project_id,))

        result = con.fetchone()
        max_id = result[0] if result and result[0] is not None else 0

        rows = ()
        new_cursor = cursor

        while not rows and new_cursor < max_id:
            con.execute(f'SELECT id FROM {table_name} '
                        f'WHERE project_id = ? AND id > ? ORDER BY id LIMIT ?;',
                        (self.project.project_id, cursor,
                         Config.database.maintenance.point_batch_size))

            rows = con.fetchall()

            if rows:
                new_cursor = rows[-1][0]

        if not rows:
            return 0

        db_ids = [row[0] for row in rows]

        if '3d' in table_name:
            for table in tables:
                db_ids = table.find_unreferenced_point3d_ids(db_ids)

                if not db_ids:
                    break
        else:
            for table in tables:
                db_ids = table.find_unreferenced_point2d_ids(db_ids)

                if not db_ids:
                    break

        if db_ids:
            self._delete_batch(table_name, db_ids)

        if new_cursor >= max_id:
            return 0

        return new_cursor

    def _delete_batch(self, table_name: str, orphan_ids: list[int]):
        """
        Delete a set of orphaned point IDs from *table_name* in one query.

        The project_id filter ensures we only delete points belonging to the
        currently open project, protecting other projects' points in a shared
        database.
        """
        con = self.project.connector

        placeholders = ','.join('?' * len(orphan_ids))
        con.execute(f'DELETE FROM {table_name} WHERE project_id = ? AND id IN ({placeholders});',
                    [self.project.project_id, *orphan_ids])

        con.commit()
