# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu


if TYPE_CHECKING:
    from ... import ui as _ui


class ViewMenu(QMenu):
    """Represent a view menu in :mod:`harness_designer.ui.system_menu.view`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, mainframe: "_ui.MainFrame"):
        """Initialise the :class:`ViewMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """
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
        """Handle the show editor 2D event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.mainframe._dock_editor2d.show()
        self.mainframe._dock_editor2d.raise_()

    def on_show_editor_obj(self):
        """Handle the show editor obj event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.mainframe._dock_editor_obj.show()
        self.mainframe._dock_editor_obj.raise_()

    def on_show_log_viewer(self):
        """Handle the show log viewer event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.mainframe._dock_log_viewer.show()
        self.mainframe._dock_log_viewer.raise_()

    def on_show_editor_db(self):
        """Handle the show editor database event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.mainframe._dock_editor_db.show()
        self.mainframe._dock_editor_db.raise_()

    def on_show_editor_assembly(self):
        """Handle the show editor assembly event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.mainframe._dock_editor_assembly.show()
        self.mainframe._dock_editor_assembly.raise_()

    def on_show_editor_script(self):
        """Handle the show editor script event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        # self.mainframe._dock_editor_script.show()
        pass
