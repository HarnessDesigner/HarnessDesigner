# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import build123d

from PySide6 import QtWidgets

from ..widgets import text_ctrl as _text_ctrl
from ..widgets import choice_ctrl as _choice_ctrl
from ..widgets import int_ctrl as _int_ctrl
from ..widgets import color_ctrl as _color_ctrl
from . import dialog_base as _dialog_base


TEXT_ALIGN = ['Left', 'Center', 'Right']
TEXT_ALIGN_MAPPING = [build123d.TextAlign.LEFT,
                      build123d.TextAlign.CENTER,
                      build123d.TextAlign.RIGHT]


FONT_STYLE = ['Regular', 'Bold', 'Italic', 'Bold Italic']
FONT_STYLE_MAPPING = [build123d.FontStyle.REGULAR,
                      build123d.FontStyle.BOLD,
                      build123d.FontStyle.ITALIC,
                      build123d.FontStyle.BOLDITALIC]


class AddNoteDialog(_dialog_base.BaseDialog):
    """
    Represent an add note dialog in :mod:`harness_designer.ui.dialogs.add_note`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """
        Initialise the :class:`AddNoteDialog` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """

        _dialog_base.BaseDialog.__init__(
            self, parent, 'Add Note', size=(400, 300),
            button_ids=QtWidgets.QDialogButtonBox.StandardButton.Ok)

        self.note_ctrl = _text_ctrl.TextCtrl(
            self.panel, 'Note:',
            multiline=True, apply_button=False)

        self.align_ctrl = _choice_ctrl.ChoiceCtrl(
            self.panel, 'Text Align:', TEXT_ALIGN)

        self.align_ctrl.SetStringSelection('Left')

        self.style_ctrl = _choice_ctrl.ChoiceCtrl(
            self.panel, 'Font Style:', FONT_STYLE)

        self.style_ctrl.SetStringSelection('Regular')

        self.size_ctrl = _int_ctrl.IntCtrl(
            self.panel, 'Font Size:', 1, 99, False)

        self.color_ctrl = _color_ctrl.ColorCtrl(self.panel, 'Color:', parent.global_db.colors_table)
        self.color_ctrl.SetValue('Green')

        self.size_ctrl.SetValue(5)

        hsizer = QtWidgets.QHBoxLayout()
        hsizer.addWidget(self.align_ctrl)
        hsizer.addSpacing(10)
        hsizer.addWidget(self.style_ctrl)
        hsizer.addSpacing(10)
        hsizer.addWidget(self.size_ctrl)

        vsizer = QtWidgets.QVBoxLayout(self.panel)
        vsizer.addWidget(self.note_ctrl)
        vsizer.addLayout(hsizer)
        vsizer.addWidget(self.color_ctrl)

    def GetValue(self):
        """
        Get the set values.

        :returns: note, align, style, size
        :rtype: tuple[str, int, int, int]
        """
        align = TEXT_ALIGN_MAPPING[self.align_ctrl.GetSelection()].value
        style = FONT_STYLE_MAPPING[self.style_ctrl.GetSelection()].value

        color = self.color_ctrl.GetColor()
        color_id = int(color.db_id)

        return (self.note_ctrl.GetValue(), align,
                style, color_id, self.size_ctrl.GetValue())
