# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QTabWidget


class PropertyGrid(QTabWidget):

    def __init__(self, parent):
        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.North)
        self.setUsesScrollButtons(True)

    def Clear(self):
        self.clear()

    def Append(self, item):
        item.Realize()
        self.addTab(item, item.GetLabel())
