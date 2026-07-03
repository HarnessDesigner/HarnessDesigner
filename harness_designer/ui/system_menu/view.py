# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtWidgets


if TYPE_CHECKING:
    from ... import ui as _ui


class ViewMenu(QtWidgets.QMenu):
    """
    Represent a view menu in :mod:`harness_designer.ui.system_menu.view`.
    """

    def __init__(self, mainframe: "_ui.MainFrame"):
        """
        Initialise the :class:`ViewMenu` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """

        super().__init__('View', mainframe)
        self.mainframe = mainframe

        self.schematic_editor = self.addAction('Schematic Editor')
        self.schematic_editor.triggered.connect(self.on_show_editor2d)

        self.database_editor = self.addAction('Database Editor')
        self.database_editor.triggered.connect(self.on_show_editor_db)

        self.circuit_editor = self.addAction('Circuit Editor')
        self.circuit_editor.triggered.connect(self.on_show_editor_circuit)

        self.object_editor = self.addAction('Object Editor')
        self.object_editor.triggered.connect(self.on_show_editor_obj)

        self.assembly_editor = self.addAction('Assembly Editor')
        self.assembly_editor.triggered.connect(self.on_show_editor_assembly)

        self.object_browser = self.addAction('Object Browser')
        self.object_browser.triggered.connect(self.on_show_object_browser)

        self.log_viewer = self.addAction('Log Viewer')
        self.log_viewer.triggered.connect(self.on_show_log_viewer)

        self.script_editor = self.addAction('Script Editor')
        self.script_editor.triggered.connect(self.on_show_editor_script)

        self.addSeparator()

        self.general_toolbar = self.addAction('General Toolbar')
        self.general_toolbar.triggered.connect(self.on_show_general_toolbar)

        self.editor_toolbar = self.addAction('Editor Toolbar')
        self.editor_toolbar.triggered.connect(self.on_show_editor_toolbar)

        self.note_toolbar = self.addAction('Note Toolbar')
        self.note_toolbar.triggered.connect(self.on_show_note_toolbar)

        self.object_toolbar = self.addAction('Object Toolbar')
        self.object_toolbar.triggered.connect(self.on_show_object_toolbar)

        self.settings3d_toolbar = self.addAction('3D Settings Toolbar')
        self.settings3d_toolbar.triggered.connect(self.on_show_settings3d_toolbar)

    def on_show_general_toolbar(self):
        self.mainframe.general_toolbar.show()
        self.mainframe.general_toolbar.raise_()

    def on_show_editor_toolbar(self):
        self.mainframe.editor_toolbar.show()
        self.mainframe.editor_toolbar.raise_()

    def on_show_note_toolbar(self):
        self.mainframe.note_toolbar.show()
        self.mainframe.note_toolbar.raise_()

    def on_show_object_toolbar(self):
        self.mainframe.object_toolbar.show()
        self.mainframe.object_toolbar.raise_()

    def on_show_settings3d_toolbar(self):
        self.mainframe.settings3d_toolbar.show()
        self.mainframe.settings3d_toolbar.raise_()

    def on_show_object_browser(self):
        self.mainframe.object_browser.dock.show()
        self.mainframe.object_browser.dock.raise_()

    def on_show_editor_circuit(self):
        self.mainframe.editor_circuit.dock.show()
        self.mainframe.editor_circuit.dock.raise_()

    def on_show_editor2d(self):
        """
        Handle the show editor 2D event.
        """

        self.mainframe.editor2d.dock.show()
        self.mainframe.editor2d.dock.raise_()

    def on_show_editor_obj(self):
        """
        Handle the show editor obj event.
        """

        self.mainframe.editor_obj.dock.show()
        self.mainframe.editor_obj.dock.raise_()

    def on_show_log_viewer(self):
        """
        Handle the show log viewer event.
        """

        self.mainframe.log_viewer.dock.show()
        self.mainframe.log_viewer.dock.raise_()

    def on_show_editor_db(self):
        """
        Handle the show editor database event.
        """

        self.mainframe.editor_db.dock.show()
        self.mainframe.editor_db.dock.raise_()

    def on_show_editor_assembly(self):
        """
        Handle the show editor assembly event.
        """

        self.mainframe.editor_assembly.dock.show()
        self.mainframe.editor_assembly.dock.raise_()

    def on_show_editor_script(self):
        """
        Handle the show editor script event.
        """

        self.mainframe.editor_script.dock.show()
        self.mainframe.editor_script.dock.raise_()
