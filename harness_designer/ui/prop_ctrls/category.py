# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QTabWidget


class Category(QScrollArea):
    """Represent a category in :mod:`harness_designer.ui.prop_ctrls.category`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, label):
        """Initialise the :class:`Category` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        """
        QScrollArea.__init__(self, parent)
        self._label = label

        self._container = QWidget()
        self._sizer = QVBoxLayout(self._container)
        self._sizer.setContentsMargins(0, 0, 0, 0)
        self._container.setLayout(self._sizer)

        self.setWidget(self._container)
        self.setWidgetResizable(True)

    def Realize(self):
        """Execute the realize operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        for i in range(self._sizer.count()):
            item = self._sizer.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if widget is None:
                continue
            if hasattr(widget, 'Realize'):
                widget.Realize()

        self._container.adjustSize()
        self.update()

    def GetLabel(self):
        """Execute the get label operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._label

    def SetLabel(self, value):
        """Execute the set label operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        self._label = value

    def addChild(self, widget):
        """Add a property widget to this category."""
        if isinstance(widget, QTabWidget):
            self._sizer.addWidget(widget, stretch=1)
        else:
            self._sizer.addWidget(widget)
