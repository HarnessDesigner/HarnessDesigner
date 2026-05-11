# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu


if TYPE_CHECKING:
    from ... import ui as _ui


class ViewMenu(QMenu):

    def __init__(self, mainframe: "_ui.MainFrame"):
        super().__init__('View', mainframe)
        self.mainframe = mainframe

        self.addAction('Schematic Editor').triggered.connect(self.on_show_editor2d)
        self.addAction('Object Editor').triggered.connect(self.on_show_editor_obj)
        self.addAction('Log Viewer').triggered.connect(self.on_show_log_viewer)
        self.addAction('Database Editor').triggered.connect(self.on_show_editor_db)
        self.addAction('Assembly Editor').triggered.connect(self.on_show_editor_assembly)
        self.addAction('Script Editor').triggered.connect(self.on_show_editor_script)

    # Each action shows the dock that wraps the editor.  QDockWidget.show()
    # both makes the dock visible and raises it if it is tabbed behind another.

    def on_show_editor2d(self):
        self.mainframe._dock_editor2d.show()
        self.mainframe._dock_editor2d.raise_()

    def on_show_editor_obj(self):
        self.mainframe._dock_editor_obj.show()
        self.mainframe._dock_editor_obj.raise_()

    def on_show_log_viewer(self):
        self.mainframe._dock_log_viewer.show()
        self.mainframe._dock_log_viewer.raise_()

    def on_show_editor_db(self):
        self.mainframe._dock_editor_db.show()
        self.mainframe._dock_editor_db.raise_()

    def on_show_editor_assembly(self):
        self.mainframe._dock_editor_assembly.show()
        self.mainframe._dock_editor_assembly.raise_()

    def on_show_editor_script(self):
        # self.mainframe._dock_editor_script.show()
        pass
