# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Read-only dialog showing the wires contained within a bundle."""

import math
from typing import TYPE_CHECKING

from PySide6 import QtWidgets, QtCore

from . import dialog_base as _dialog_base

if TYPE_CHECKING:
    from ...objects.objects3d import bundle as _objects3d_bundle


# ---------------------------------------------------------------------------
# Wire label helpers
# ---------------------------------------------------------------------------

def _color_name(color_obj) -> str:
    if color_obj is None:
        return 'None'
    return str(color_obj.name)


def _wire_label(conc_wire) -> str:
    pjt_wire = conc_wire.wire
    part = pjt_wire.part

    circuit = pjt_wire.circuit
    circuit_name = circuit.name if circuit is not None else '?'

    nc = part.num_conductors if part is not None else 1
    size_mm2 = part.size_mm2 if part is not None else 0.0
    size_awg = part.size_awg if part is not None else 0

    primary = _color_name(part.color if part is not None else None)
    stripe = _color_name(part.stripe_color if part is not None else None)

    return f'{circuit_name}  ·  {nc}C  ·  {size_mm2:.2f}mm²({size_awg}AWG)  ·  {primary}/{stripe}'


def _effective_diameter(conc_wires) -> float:
    total_area = sum(
        math.pi * (cw.wire.part.od_mm / 2.0) ** 2
        for cw in conc_wires
        if cw.wire.part and cw.wire.part.od_mm
    )
    if not total_area:
        return 0.0
    return 2.0 * math.sqrt(total_area * 1.15 / math.pi)


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class BundleWiresDialog(_dialog_base.BaseDialog):
    """Read-only view of all wires contained in a bundle.

    Styled after the transition routing dialog (group box + scroll area) but
    with no drag-and-drop — wires are shown for reference only.
    """

    def __init__(self, parent, bundle_3d: "_objects3d_bundle.Bundle"):
        super().__init__(parent, 'Bundle Wire Contents', size=(620, 420))
        self._build_ui(bundle_3d)

    def _build_ui(self, bundle_3d: "_objects3d_bundle.Bundle"):
        bundle_db = bundle_3d.db_obj
        g_part = bundle_db.part  # BundleCover global part

        try:
            conc_wires = bundle_db.wires
        except (IndexError, KeyError):
            conc_wires = []

        # ------------------------------------------------------------------
        # Scroll area wrapping a single group box (the whole bundle)
        # ------------------------------------------------------------------
        scroll = QtWidgets.QScrollArea(self.panel)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(container)
        row.setContentsMargins(4, 4, 4, 4)
        row.setSpacing(8)

        # Group box labelled with the bundle cover part number
        grp_title = g_part.part_number if g_part is not None else 'Bundle'
        grp = QtWidgets.QGroupBox(grp_title, container)
        inner = QtWidgets.QVBoxLayout(grp)
        inner.setContentsMargins(4, 4, 4, 4)
        inner.setSpacing(4)

        # Capacity label (current packed diameter vs cover max_dia)
        cap_label = QtWidgets.QLabel(grp)
        cap_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight |
            QtCore.Qt.AlignmentFlag.AlignVCenter)
        inner.addWidget(cap_label)

        used = _effective_diameter(conc_wires)
        max_d = float(g_part.max_dia) if g_part is not None else 0.0
        if max_d > 0:
            pct = min(100.0, used / max_d * 100.0)
            cap_label.setText(f'{used:.2f} mm / {max_d:.2f} mm  ({pct:.0f}%)')
            if used > max_d:
                cap_label.setStyleSheet('color: #e84040;')
            else:
                cap_label.setStyleSheet('color: #40c040;')
        else:
            cap_label.setText(f'{used:.2f} mm')
            cap_label.setStyleSheet('color: #40c040;')

        # Wire list — read-only, no drag-and-drop
        list_widget = QtWidgets.QListWidget(grp)
        list_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        list_widget.setDragEnabled(False)
        list_widget.setAcceptDrops(False)

        if conc_wires:
            for cw in conc_wires:
                list_widget.addItem(_wire_label(cw))
        else:
            list_widget.addItem('(no wires)')

        inner.addWidget(list_widget, 1)

        row.addWidget(grp)
        scroll.setWidget(container)

        panel_layout = QtWidgets.QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(scroll)

    def GetValue(self):
        return None
