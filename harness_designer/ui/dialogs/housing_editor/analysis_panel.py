# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Optional

import numpy as np
from PySide6 import QtCore
from PySide6 import QtWidgets
from dataclasses import dataclass
from .... import check_types as _check_types


@dataclass
class AnalysisItem:
    name: str
    kind: str        # 'circle' or 'rect'
    params: dict     # center, normal, u, v, plus radius / half_w, half_h
    d_start: float
    d_end: float
    verts: np.ndarray   # (3N, 3) float32 — triangle soup for the 3D overlay
    wire_surf_si: int = -1   # index into picker.surfaces for the matched wire surface
    term_surf_si: int = -1   # index into picker.surfaces for this terminal surface
    is_manual: bool = False  # True if hand-drawn on a single-plane housing
    # Full coplanar surface-index groups wire_surf_si/term_surf_si were
    # picked from (may cover several disconnected mesh islands on the same
    # plane). Persisted to Cavity.wire_surf_indices/terminal_surf_indices so
    # match_cavity_surfaces() can skip its OBB nearest-neighbor heuristic on
    # later loads. Empty for manual (synthetic-marker) cavities.
    wire_surf_indices: list = None
    term_surf_indices: list = None
    # True when wire_surf_si is shared with another cavity in this same
    # analysis run (no distinguishable per-cavity wire-side mesh geometry).
    # Committed as Cavity.render_wire_marker so match_cavity_surfaces()
    # renders/click-tests a synthetic wire-side marker from this cavity's
    # own OBB back face instead of the shared real surface.
    wire_is_shared: bool = False

    @_check_types.do
    def __post_init__(self):
        if self.wire_surf_indices is None:
            self.wire_surf_indices = [self.wire_surf_si] if self.wire_surf_si >= 0 else []
        if self.term_surf_indices is None:
            self.term_surf_indices = [self.term_surf_si] if self.term_surf_si >= 0 else []

    @property
    @_check_types.do
    def radius(self) -> float:
        return float(self.params.get('radius', 0.0))

    @property
    @_check_types.do
    def half_w(self) -> float:
        return float(self.params.get('half_w', 0.0))

    @property
    @_check_types.do
    def half_h(self) -> float:
        return float(self.params.get('half_h', 0.0))


class EditPanel(QtWidgets.QWidget):
    """No fields remain here -- name/shape/radius/half-w/half-h/length were
    all removed as inline-editable. Kept as a no-op placeholder widget
    (always empty/disabled) since housing_editor.py still parents a widget
    at this spot below the cavity-preview tree; itemChanged never fires."""

    itemChanged: QtCore.SignalInstance = QtCore.Signal()

    @_check_types.do
    def __init__(self, parent=None):
        super().__init__(parent)
        self._item: Optional[AnalysisItem] = None

        QtWidgets.QFormLayout(self)
        self.setEnabled(False)

    @_check_types.do
    def load(self, item: Optional[AnalysisItem]):
        self._item = item
        self.setEnabled(item is not None)
