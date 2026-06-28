# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np
from PySide6 import QtWidgets, QtCore, QtGui

from . import dialog_base as _dialog_base
from ..widgets import choice_ctrl as _choice_ctrl
from ...exporter import exporter as _exporter

if TYPE_CHECKING:
    from ... import ui as _ui


# Object collections on project that may carry 3D models.
_OBJECT_COLLECTIONS = [
    'boots', 'covers', 'housings', 'seals',
    'splices', 'terminals', 'transitions',
]

# Ordered list displayed in the format dropdown.
_FORMAT_LIST = [
    (_exporter.EXPORT_TYPE_BREP,    _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_BREP]),
    (_exporter.EXPORT_TYPE_IGES,    _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_IGES]),
    (_exporter.EXPORT_TYPE_VRML,    _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_VRML]),
    (_exporter.EXPORT_TYPE_OBJ,     _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_OBJ]),
    (_exporter.EXPORT_TYPE_COLLADA, _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_COLLADA]),
    (_exporter.EXPORT_TYPE_FBX,     _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_FBX]),
    (_exporter.EXPORT_TYPE_GLTF,    _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_GLTF]),
    (_exporter.EXPORT_TYPE_PLY,     _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_PLY]),
    (_exporter.EXPORT_TYPE_STL,     _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_STL]),
    (_exporter.EXPORT_TYPE_3DS,     _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_3DS]),
    (_exporter.EXPORT_TYPE_X3D,     _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_X3D]),
    (_exporter.EXPORT_TYPE_3MF,     _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_3MF]),
    (_exporter.EXPORT_TYPE_STEP,    _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_STEP]),
    (_exporter.EXPORT_TYPE_DIRECTX, _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_DIRECTX]),
    (_exporter.EXPORT_TYPE_OPENGEX, _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_OPENGEX]),
    (_exporter.EXPORT_TYPE_ASSBIN,  _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_ASSBIN]),
    (_exporter.EXPORT_TYPE_ASSXML,  _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_ASSXML]),
    (_exporter.EXPORT_TYPE_ASSJSON, _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_ASSJSON]),
    (_exporter.EXPORT_TYPE_PBRT,    _exporter.FORMAT_NAMES[_exporter.EXPORT_TYPE_PBRT]),
]
_FORMAT_TYPES = [fmt for fmt, _ in _FORMAT_LIST]
_FORMAT_DISPLAY_NAMES = [name for _, name in _FORMAT_LIST]


def _wx_to_qt_filter(wx_wildcard: str) -> str:
    """Convert 'Desc|*.ext;*.ext2|' (wx) to 'Desc (*.ext *.ext2)' (Qt)."""
    parts = [p for p in wx_wildcard.rstrip('|').split('|') if p]
    if len(parts) >= 2:
        exts = parts[1].replace(';', ' ')
        return f'{parts[0]} ({exts})'
    return wx_wildcard


def _obj_label(obj) -> str:
    try:
        return f'{type(obj).__name__} [{obj.db_obj.part.part_number}]'
    except AttributeError:
        try:
            return f'{type(obj).__name__} [id:{obj.db_obj.db_id}]'
        except AttributeError:
            return type(obj).__name__


# ---------------------------------------------------------------------------
# File-picker row widget
# ---------------------------------------------------------------------------

class _FilePickerRow(QtWidgets.QWidget):

    def __init__(self, parent):
        super().__init__(parent)

        self._qt_filter = 'All Files (*)'

        lbl = QtWidgets.QLabel('Output File:', self)
        lbl.setFixedWidth(80)

        self._edit = QtWidgets.QLineEdit(self)
        self._edit.setPlaceholderText('Select output file path...')

        self._browse_btn = QtWidgets.QPushButton('Browse...', self)
        self._browse_btn.setFixedWidth(80)
        self._browse_btn.clicked.connect(self._on_browse)

        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(lbl)
        row.addWidget(self._edit, 1)
        row.addWidget(self._browse_btn)

    def set_filter(self, qt_filter: str):
        self._qt_filter = qt_filter

    def _on_browse(self):
        start = self._edit.text().strip() or ''
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save Export', start, self._qt_filter)
        if path:
            self._edit.setText(path)

    def get_path(self) -> str:
        return self._edit.text().strip()


# ---------------------------------------------------------------------------
# Background export worker
# ---------------------------------------------------------------------------

class _ExportWorker(QtCore.QThread):
    log_appended = QtCore.Signal(str)
    step_started = QtCore.Signal(str, int)   # (description, total_steps)
    step_progressed = QtCore.Signal(int)     # current step value
    export_finished = QtCore.Signal(bool, str)  # (success, error_message)

    def __init__(self, verts: np.ndarray, normals: np.ndarray,
                 path: str, export_type: int):
        super().__init__()
        self._verts = verts
        self._normals = normals
        self._path = path
        self._export_type = export_type
        self._current_total = 0

    def _progress_cb(self, current: int, total: int, phase: str):
        if total < 0:
            # File-write phase — log only, bar stays at max
            self.log_appended.emit(f'  {phase}...')
            return
        if current == 0:
            self._current_total = total
            self.step_started.emit(phase, total)
        self.step_progressed.emit(current)

    def run(self):
        try:
            n_verts = len(self._verts)
            n_tris = n_verts // 3
            export_type = self._export_type

            if export_type in _exporter.OCP_FORMAT_STRINGS:
                fmt = _exporter.OCP_FORMAT_STRINGS[export_type]
                self.log_appended.emit(
                    f'Building OCP triangulation  '
                    f'({n_verts:,} vertices, {n_tris:,} triangles)...')
                _exporter.export_ocp(
                    self._verts, self._normals,
                    self._path, fmt,
                    progress_cb=self._progress_cb)

            elif export_type in _exporter.ASSIMP_FORMAT_IDS:
                file_type = _exporter.ASSIMP_FORMAT_IDS[export_type]
                self.log_appended.emit(
                    f'Building Assimp scene ({file_type.upper()})  '
                    f'({n_verts:,} vertices, {n_tris:,} triangles)...')
                _exporter.export_assimp(
                    self._verts, self._normals,
                    self._path, file_type,
                    progress_cb=self._progress_cb)

            else:
                raise ValueError(f'Unknown export type: {export_type}')

            self.log_appended.emit(f'Export complete → {self._path}')
            self.export_finished.emit(True, '')

        except Exception as exc:
            self.export_finished.emit(False, str(exc))


# ---------------------------------------------------------------------------
# Export dialog
# ---------------------------------------------------------------------------

class ExportDialog(_dialog_base.BaseDialog):
    """Non-modal dialog for exporting all visible 3-D model data."""

    def __init__(self, parent: '_ui.MainFrame'):
        super().__init__(
            parent, 'Export Models', size=(720, 560),
            button_ids=QtWidgets.QDialogButtonBox.StandardButton.Close)

        self._worker: _ExportWorker | None = None

        # ── Format dropdown ──────────────────────────────────────────────
        self._format_ctrl = _choice_ctrl.ChoiceCtrl(
            self.panel, 'Format:', _FORMAT_DISPLAY_NAMES)
        self._format_ctrl.valueChanged.connect(self._on_format_changed)

        # ── File picker ──────────────────────────────────────────────────
        self._file_picker = _FilePickerRow(self.panel)

        # ── Separator ────────────────────────────────────────────────────
        sep = QtWidgets.QFrame(self.panel)
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)

        # ── Progress row ─────────────────────────────────────────────────
        self._phase_label = QtWidgets.QLabel('Ready', self.panel)
        self._phase_label.setFixedWidth(200)

        self._progress = QtWidgets.QProgressBar(self.panel)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)

        progress_row = QtWidgets.QHBoxLayout()
        progress_row.addWidget(self._phase_label)
        progress_row.addWidget(self._progress, 1)

        # ── Log ──────────────────────────────────────────────────────────
        self._log = QtWidgets.QPlainTextEdit(self.panel)
        self._log.setReadOnly(True)
        mono = QtGui.QFont('Courier New', 9)
        mono.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        self._log.setFont(mono)
        self._log.setMinimumHeight(160)

        # ── Panel layout ─────────────────────────────────────────────────
        panel_sizer = QtWidgets.QVBoxLayout(self.panel)
        panel_sizer.addWidget(self._format_ctrl)
        panel_sizer.addWidget(self._file_picker)
        panel_sizer.addWidget(sep)
        panel_sizer.addLayout(progress_row)
        panel_sizer.addWidget(self._log, 1)

        # ── Buttons: add Export alongside the inherited Close button ─────
        self._export_btn = self.button_box.addButton(
            'Export', QtWidgets.QDialogButtonBox.ButtonRole.ActionRole)
        self._export_btn.clicked.connect(self._on_export)

        # Seed the filter for the default format
        self._on_format_changed(_FORMAT_DISPLAY_NAMES[0])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log_line(self, text: str):
        self._log.appendPlainText(text)
        self._log.verticalScrollBar().setValue(
            self._log.verticalScrollBar().maximum())

    def _selected_export_type(self) -> int:
        return _FORMAT_TYPES[self._format_ctrl.GetSelection()]

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_format_changed(self, _display_name: str):
        export_type = self._selected_export_type()
        wx_wildcard = _exporter.FILE_WILDCARDS.get(export_type, 'All Files (*.*)')
        qt_filter = _wx_to_qt_filter(wx_wildcard)
        self._file_picker.set_filter(qt_filter)

    def _on_export(self):
        if self._worker and self._worker.isRunning():
            return

        project = self.mainframe.project
        if project is None:
            self._log_line('ERROR: No project is open.')
            return

        path = self._file_picker.get_path()
        if not path:
            self._log_line('ERROR: No output file selected.')
            return

        # ── Collect mesh data (main thread — fast numpy ops) ─────────────
        self._log.clear()
        self._log_line('=== Collecting mesh data ===')
        QtWidgets.QApplication.setOverrideCursor(
            QtCore.Qt.CursorShape.WaitCursor)
        self._export_btn.setEnabled(False)
        QtWidgets.QApplication.processEvents()

        try:
            all_verts, all_normals, obj_count, total_verts, total_tris = \
                self._collect_mesh_data(project)
        except Exception as exc:
            self._log_line(f'ERROR during collection: {exc}')
            QtWidgets.QApplication.restoreOverrideCursor()
            self._export_btn.setEnabled(True)
            return

        QtWidgets.QApplication.restoreOverrideCursor()

        if all_verts is None:
            self._log_line('No visible objects with 3D models were found. Nothing to export.')
            self._export_btn.setEnabled(True)
            return

        self._log_line('')
        self._log_line(
            f'=== Summary ===\n'
            f'  Objects added : {obj_count}\n'
            f'  Total vertices: {total_verts:,}\n'
            f'  Total triangles: {total_tris:,}')
        self._log_line('')
        self._log_line(f'=== Exporting to {path} ===')

        # ── Hand off to worker thread ─────────────────────────────────────
        export_type = self._selected_export_type()
        self._phase_label.setText('Starting...')
        self._progress.setValue(0)

        self._worker = _ExportWorker(all_verts, all_normals, path, export_type)
        self._worker.log_appended.connect(self._log_line)
        self._worker.step_started.connect(self._on_step_started)
        self._worker.step_progressed.connect(self._on_step_progressed)
        self._worker.export_finished.connect(self._on_export_finished)
        self._worker.start()

    def _on_step_started(self, description: str, total: int):
        self._phase_label.setText(description)
        self._progress.setRange(0, max(total, 1))
        self._progress.setValue(0)

    def _on_step_progressed(self, current: int):
        self._progress.setValue(current)

    def _on_export_finished(self, success: bool, error_msg: str):
        if success:
            self._phase_label.setText('Done')
            self._progress.setValue(self._progress.maximum())
        else:
            self._phase_label.setText('Failed')
            self._log_line(f'ERROR: {error_msg}')

        self._export_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Mesh collection
    # ------------------------------------------------------------------

    def _collect_mesh_data(self, project):
        """
        Walk all visible 3D objects, apply their world transforms, and
        concatenate all vertices and normals into two (N,3) float32 arrays.

        Returns (all_verts, all_normals, obj_count, total_verts, total_tris)
        or (None, None, 0, 0, 0) when nothing visible was found.
        """
        verts_list = []
        normals_list = []
        obj_count = 0
        total_verts = 0
        total_tris = 0

        for collection_name in _OBJECT_COLLECTIONS:
            collection = getattr(project, collection_name, [])
            for obj in collection:
                obj3d = obj.obj3d
                if obj3d is None or obj3d._vbo is None:
                    continue

                is_visible = obj3d.is_visible
                is_smooth = getattr(obj3d, 'smooth', False)
                vertex_count = obj3d._vbo.vertex_count
                triangle_count = vertex_count // 3
                label = _obj_label(obj)
                normals_type = 'smooth' if is_smooth else 'flat'

                self._log_line(
                    f'  {label}  '
                    f'visible={is_visible}  '
                    f'normals={normals_type}  '
                    f'vertices={vertex_count:,}  '
                    f'triangles={triangle_count:,}')

                if not is_visible:
                    continue

                # Raw arrays (local/model space)
                verts_local = obj3d._vbo.vertices.reshape(-1, 3)
                raw_normals = (obj3d._vbo.smooth_normals if is_smooth
                               else obj3d._vbo.face_normals)
                normals_local = raw_normals.reshape(-1, 3)

                # World transform: (v * scale) @ rotation + position
                scale = obj3d._scale.as_numpy          # (3,)
                angle = obj3d._angle                   # Angle — supports @
                pos = obj3d._position.as_numpy         # (3,)

                verts_world = (verts_local * scale) @ angle + pos

                # Normals rotate only (no translation, no scale)
                normals_world = normals_local @ angle
                norms_len = np.linalg.norm(normals_world, axis=1, keepdims=True)
                np.maximum(norms_len, 1e-8, out=norms_len)
                normals_world = normals_world / norms_len

                verts_list.append(verts_world.astype(np.float32))
                normals_list.append(normals_world.astype(np.float32))

                obj_count += 1
                total_verts += vertex_count
                total_tris += triangle_count

        if not verts_list:
            return None, None, 0, 0, 0

        all_verts = np.concatenate(verts_list, axis=0)
        all_normals = np.concatenate(normals_list, axis=0)
        return all_verts, all_normals, obj_count, total_verts, total_tris

    # ------------------------------------------------------------------
    # QDialog overrides
    # ------------------------------------------------------------------

    def GetValue(self):
        return None

    def closeEvent(self, event: QtGui.QCloseEvent):
        if self._worker and self._worker.isRunning():
            self._worker.wait(2000)
        super().closeEvent(event)
