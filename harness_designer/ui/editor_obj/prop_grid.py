# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QTabWidget


class PropertyGrid(QTabWidget):
    """Represent a property grid in :mod:`harness_designer.ui.editor_obj.prop_grid`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`PropertyGrid` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.North)
        self.setUsesScrollButtons(True)

    def Clear(self):
        """Execute the clear operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.clear()

    def Append(self, item):
        """Execute the append operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        """
        item.Realize()
        self.addTab(item, item.GetLabel())
