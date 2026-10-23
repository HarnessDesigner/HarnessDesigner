# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The Script Editor dock: where the scraper script is written, with the
Claude assistant underneath.

It is also where code from the browser's inspector lands: the editor
implements :class:`~harness_designer.ui.scraper_inspector.SnippetSink`, so
"take the text after this" in the Source tab inserts its code here.

The script is never lost to a crash or a closed window: what is in the
editor is saved to a scratch file a moment after every change, and comes
back the next time the editor is opened. Saving to a real file is atomic.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

import os

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from . import assistant_panel as _assistant_panel
from . import console_panel as _console_panel
from . import message_dialog as _message_dialog
from .. import dock_base as _dock_base
from ..scraper_inspector import insertion as _insertion
from ...scraping import examples as _examples
from ...scraping import runner as _runner
from ...scraping import script_files as _script_files
from ...scraping import snippets as _snippets
from ...utils import paths as _paths
from ... import check_types as _check_types
from ...plugins.plugins import claude_ai as _claude
from ... import image as _image
from ..widgets import code_editor_ctrl as _code_editor_ctrl
from ..widgets import wrap_label as _wrap_label

if TYPE_CHECKING:
    from .. import mainframe as _mainframe

# How long after the last keystroke the working copy is written to disk.
_AUTOSAVE_MILLISECONDS = 1000

_FILE_FILTER = 'Python scripts (*.py);;All files (*)'

_ICON_SIZE = 20


@_check_types.do
def _toolbar_icon(picture: "_image.Image") -> QtGui.QIcon:
    return QtGui.QIcon(picture.resize(_ICON_SIZE, _ICON_SIZE).pixmap)


@_check_types.do
def stop_warning_text(run: _runner.ScriptRun) -> str:
    """What the user is told when a script is still running after Stop."""
    return (
        f'Script {run.number} ({run.label}) is still running '
        f'{_console_panel.STOP_WARNING_SECONDS:.0f} seconds after Stop.\n\n'
        'Stop works by raising an exception inside the script\'s thread, and that only takes effect while '
        'the thread is running Python code. A script that is waiting at the operating system level -- '
        'time.sleep(), a network read with no timeout, Thread.join(), Queue.get(), a lock -- cannot be '
        'reached. The Stop stays pending and takes effect the moment the wait ends.\n\n'
        'If the script keeps the socket or Event it is waiting on as an attribute of its thread, another '
        'script can end the wait from outside: open the example below, put the thread\'s name in it, and '
        'run it. Otherwise wait for the call to return, or close Harness Designer.\n\n'
        'A very slow regular expression or other long native call also freezes this window, and nothing '
        'in the application can interrupt it.')


class ScriptEditorPanel(QtWidgets.QWidget, _insertion.SnippetSink):
    """The editor, its toolbar, and the assistant.

    :ivar settingsRequested: The assistant needs the Claude settings dialog.
    """

    settingsRequested = QtCore.Signal()

    @_check_types.do
    def __init__(self, client: _claude.ClaudeClient, scratch_path: str | None, scripts_folder: str,
                 parent: QtWidgets.QWidget | None = None):
        """
        :param client: The Claude client the assistant uses.
        :param scratch_path: Where the unsaved working copy is kept between
            sessions; ``None`` turns that off.
        :param scripts_folder: Where the open / save dialogs start.
        """
        super().__init__(parent)
        self._scratch_path = scratch_path
        self._scripts_folder = scripts_folder
        self._path: str | None = None
        self._recovered = False

        self.editor = _code_editor_ctrl.CodeEditorCtrl(self)
        self._name_label = _wrap_label.WrapLabel('', self, wrap=False)
        self._message_label = _wrap_label.WrapLabel('', self, wrap=False)
        self._message_label.setStyleSheet('color: gray;')

        self._toolbar = QtWidgets.QToolBar(self)
        self._toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toolbar.setIconSize(QtCore.QSize(_ICON_SIZE, _ICON_SIZE))
        self._new_action = self._add_action('New', 'Ctrl+N', self.new_script)
        self._open_action = self._add_action('Open...', 'Ctrl+O', self.open_script)
        self._save_action = self._add_action('Save', 'Ctrl+S', self.save_script)
        self._save_as_action = self._add_action('Save as...', 'Ctrl+Shift+S', self.save_script_as)
        self._toolbar.addSeparator()
        self._undo_action = self._add_action('Undo', '', self.editor.undo)
        self._redo_action = self._add_action('Redo', '', self.editor.redo)
        self._toolbar.addSeparator()
        self._run_action = self._add_action('Run', 'F5', self.run_script, _toolbar_icon(_image.icons.run_script))
        self._stop_action = self._add_action('Stop', 'Shift+F5', self.stop_script,
                                             _toolbar_icon(_image.icons.stop_script))
        self._stop_action.setEnabled(False)
        self._toolbar.addSeparator()
        self._toolbar.addWidget(self._build_examples_button())

        top = QtWidgets.QWidget(self)
        top_layout = QtWidgets.QVBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(2)
        top_layout.addWidget(self._toolbar)
        top_layout.addWidget(self._name_label)
        top_layout.addWidget(self.editor, 1)
        top_layout.addWidget(self._message_label)

        self.assistant = _assistant_panel.AssistantPanel(self, client, self)
        self._runner = _runner.Runner()
        self.console = _console_panel.ConsolePanel(self._runner, self)
        self._tabs = QtWidgets.QTabWidget(self)
        self._tabs.addTab(self.assistant, 'Assistant')
        self._tabs.addTab(self.console, 'Console')

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical, self)
        self._splitter.addWidget(top)
        self._splitter.addWidget(self._tabs)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 2)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._splitter)

        self._autosave_timer = QtCore.QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(_AUTOSAVE_MILLISECONDS)
        self._autosave_timer.timeout.connect(self._autosave)

        self.editor.document().modificationChanged.connect(self._modification_changed)
        self.editor.textChanged.connect(self._text_changed)
        self.editor.undoAvailable.connect(self._undo_action.setEnabled)
        self.editor.redoAvailable.connect(self._redo_action.setEnabled)
        self.assistant.settingsRequested.connect(self.settingsRequested.emit)
        self.console.activityChanged.connect(self._stop_action.setEnabled)
        self.console.stopIgnored.connect(self._stop_ignored)
        self.console.messageRaised.connect(self._set_message)
        self._undo_action.setEnabled(False)
        self._redo_action.setEnabled(False)

        self._restore_scratch()
        self._show_name()

    @_check_types.do
    def _add_action(self, text: str, shortcut: str, callback: Callable[[], object],
                    icon: QtGui.QIcon | None = None) -> QtGui.QAction:
        action = QtGui.QAction(text, self)
        if icon is not None:
            action.setIcon(icon)

        if shortcut:
            action.setShortcut(QtGui.QKeySequence(shortcut))
            action.setShortcutContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)

        # `triggered` passes a `checked` flag; swallow it so it cannot land
        # in the callback's first parameter (open_script(path), ...).
        action.triggered.connect(lambda checked=False: callback())
        self._toolbar.addAction(action)
        self.addAction(action)
        return action

    # -- the SnippetSink the inspector sends code to ------------------------------------

    @_check_types.do
    def taken_names(self) -> set[str]:
        return _snippets.taken_names(self.editor.toPlainText())

    @_check_types.do
    def insert_snippet(self, snippet: _snippets.Snippet) -> None:
        _insertion.insert_snippet(self.editor, snippet)
        self._set_message(f'Added: {snippet.description}')

    # -- what the assistant needs ---------------------------------------------------------

    @_check_types.do
    def script_text(self) -> str:
        return self.editor.toPlainText()

    @_check_types.do
    def selected_text(self) -> str:
        """The text selected in the editor ('' if none)."""
        return self.editor.textCursor().selection().toPlainText()

    @_check_types.do
    def insert_at_cursor(self, text: str) -> None:
        """Insert *text* where the cursor is (over the selection, if any) as
        one undo step."""
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        cursor.insertText(text)
        cursor.endEditBlock()
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()

    @_check_types.do
    def replace_script(self, text: str) -> None:
        """Make *text* the whole script, as one undo step."""
        cursor = QtGui.QTextCursor(self.editor.document())
        cursor.beginEditBlock()
        cursor.select(QtGui.QTextCursor.SelectionType.Document)
        cursor.insertText(text)
        cursor.endEditBlock()

        start = self.editor.textCursor()
        start.setPosition(0)
        self.editor.setTextCursor(start)

    # -- running ------------------------------------------------------------------------------

    @_check_types.do
    def run_script(self) -> _runner.ScriptRun | None:
        """Run the script in the editor, as it is now (saved or not), in a
        thread. Returns the run, or ``None`` if there is nothing to run."""
        source = self.editor.toPlainText()
        if not source.strip():
            self._set_message('There is nothing to run.')
            return None

        label = 'untitled'
        if self._path is not None:
            label = os.path.basename(self._path)

        run = self._runner.start(source, label, self._path)
        self.console.show_run(run)
        self._tabs.setCurrentWidget(self.console)
        self._set_message(f'Started {label} (run {run.number}).')
        return run

    @_check_types.do
    def stop_script(self) -> None:
        """Send Stop to the run shown in the console."""
        if self.console.stop_selected():
            self._set_message('Stop sent.')

    @_check_types.do
    def open_example(self, example_id: str) -> None:
        """Put an example in the editor (asking first if that would lose changes)."""
        example = _examples.get(example_id)
        if not self._can_discard():
            return

        self._load(example.code, None)
        self._set_message(f'Opened the example "{example.title}". Run it with F5.')

    @_check_types.do
    def _build_examples_button(self) -> QtWidgets.QToolButton:
        button = QtWidgets.QToolButton(self._toolbar)
        button.setText('Examples')
        button.setToolTip('Scripts that show how to write a script whose waits can be ended from outside.')
        button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)

        menu = QtWidgets.QMenu(button)
        menu.setToolTipsVisible(True)
        for example in _examples.EXAMPLES:
            action = menu.addAction(example.title)
            action.setToolTip(example.summary)
            action.triggered.connect(lambda checked=False, key=example.id: self.open_example(key))

        button.setMenu(menu)
        return button

    @_check_types.do
    def _stop_ignored(self, run: _runner.ScriptRun) -> None:
        answer = self._show_stop_warning(run)
        if answer.extra:
            self.open_example(_examples.RELEASE_STUCK)

    @_check_types.do
    def _show_stop_warning(self, run: _runner.ScriptRun) -> _message_dialog.Answer:
        return _message_dialog.ask(self.window(), 'The script did not stop', stop_warning_text(run),
                                   extra='Open the "Release a stuck script" example')

    # -- files ----------------------------------------------------------------------------

    @property
    @_check_types.do
    def path(self) -> str | None:
        """The file being edited; ``None`` for an unsaved script."""
        return self._path

    @_check_types.do
    def has_unsaved_changes(self) -> bool:
        return self.editor.document().isModified()

    @_check_types.do
    def new_script(self) -> None:
        if not self._can_discard():
            return

        self._load('', None)

    @_check_types.do
    def open_script(self, path: str | None = None) -> None:
        if not self._can_discard():
            return

        if path is None:
            path = self._ask_open_path()
            if not path:
                return

        try:
            text = _script_files.read_script(path)
        except (OSError, UnicodeDecodeError) as problem:
            self._warn(f'{os.path.basename(path)} could not be opened: {problem}')
            return

        self._load(text, path)

    @_check_types.do
    def save_script(self) -> bool:
        """Save to the current file (asking for one the first time).
        Returns whether the script was saved."""
        if self._path is None:
            return self.save_script_as()

        return self._write(self._path)

    @_check_types.do
    def save_script_as(self, path: str | None = None) -> bool:
        if path is None:
            path = self._ask_save_path()
            if not path:
                return False

        return self._write(path)

    @_check_types.do
    def _write(self, path: str) -> bool:
        try:
            _script_files.write_script(path, self.editor.toPlainText())
        except OSError as problem:
            self._warn(f'The script could not be saved: {problem}')
            return False

        self._path = path
        self._recovered = False
        self.editor.document().setModified(False)
        self._remove_scratch()
        self._show_name()
        self._set_message(f'Saved {os.path.basename(path)}.')
        return True

    @_check_types.do
    def _load(self, text: str, path: str | None) -> None:
        self.editor.setPlainText(text)
        self.editor.document().clearUndoRedoStacks()
        self.editor.document().setModified(False)
        self._path = path
        self._recovered = False
        self._remove_scratch()
        self._show_name()

    @_check_types.do
    def _can_discard(self) -> bool:
        """True when it is fine to replace what is in the editor: it has no
        unsaved changes, or the user chose to save or discard them."""
        if not self.has_unsaved_changes() or not self.editor.toPlainText().strip():
            return True

        answer = self._ask_save_changes()
        if answer == QtWidgets.QDialogButtonBox.StandardButton.Save:
            return self.save_script()

        return answer == QtWidgets.QDialogButtonBox.StandardButton.Discard

    # These are the only places that show a dialog (with `_show_stop_warning`).

    @_check_types.do
    def _ask_open_path(self) -> str:
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Open script', self._scripts_folder, _FILE_FILTER)
        return path

    @_check_types.do
    def _ask_save_path(self) -> str:
        suggestion = os.path.join(self._scripts_folder, 'scraper.py')
        if self._path is not None:
            suggestion = self._path

        path, _filter = QtWidgets.QFileDialog.getSaveFileName(self, 'Save script', suggestion, _FILE_FILTER)
        return path

    @_check_types.do
    def _ask_save_changes(self) -> QtWidgets.QDialogButtonBox.StandardButton | None:
        """Save, Discard or Cancel; ``None`` if the dialog was dismissed (counts as Cancel)."""
        Buttons = QtWidgets.QDialogButtonBox.StandardButton
        return _message_dialog.ask(self.window(), 'Unsaved script', 'The script has changes that are not saved.',
                                   Buttons.Save | Buttons.Discard | Buttons.Cancel).button

    @_check_types.do
    def _warn(self, text: str) -> None:
        self._set_message(text)
        _message_dialog.ask(self.window(), 'Script editor', text)

    # -- the working copy ---------------------------------------------------------------------

    @_check_types.do
    def _restore_scratch(self) -> None:
        if self._scratch_path is None or not os.path.exists(self._scratch_path):
            return

        try:
            text = _script_files.read_script(self._scratch_path)
        except (OSError, UnicodeDecodeError):
            return

        if not text.strip():
            return

        self.editor.setPlainText(text)
        self.editor.document().clearUndoRedoStacks()
        self.editor.document().setModified(True)
        self._recovered = True

    @_check_types.do
    def _text_changed(self) -> None:
        if self._scratch_path is not None:
            self._autosave_timer.start()

    @_check_types.do
    def _autosave(self) -> None:
        """Write the working copy now (also called when the editor closes)."""
        if self._scratch_path is None:
            return

        text = self.editor.toPlainText()
        if not self.has_unsaved_changes() or not text.strip():
            self._remove_scratch()
            return

        try:
            _script_files.write_script(self._scratch_path, text)
        except OSError as problem:
            self._set_message(f'The working copy could not be saved: {problem}')

    @_check_types.do
    def _remove_scratch(self) -> None:
        self._autosave_timer.stop()
        if self._scratch_path is not None and os.path.exists(self._scratch_path):
            try:
                os.remove(self._scratch_path)
            except OSError:
                pass

    @_check_types.do
    def shutdown(self) -> None:
        """Write the working copy and stop the assistant (the application is closing)."""
        self._autosave_timer.stop()
        self._autosave()
        self.console.shutdown()
        self.assistant.shutdown()

    # -- display -----------------------------------------------------------------------------

    @_check_types.do
    def _modification_changed(self, modified: bool) -> None:
        self._show_name()

    @_check_types.do
    def _show_name(self) -> None:
        if self._path is not None:
            name = os.path.basename(self._path)
        elif self._recovered:
            name = 'Untitled (recovered from last time)'
        else:
            name = 'Untitled'

        if self.has_unsaved_changes():
            name += ' *'

        self._name_label.setText(name)

    @_check_types.do
    def _set_message(self, text: str) -> None:
        self._message_label.setText(text)


class ScriptEditor(_dock_base.DockBase, _insertion.SnippetSink):
    """The dock. Created the first time the user opens the editor, not at
    application start."""

    @_check_types.do
    def __init__(self, mainframe: "_mainframe.MainFrame"):
        app_data = _paths.get_appdata()
        scripts_folder = os.path.join(_paths.get_documents(), 'HarnessDesigner', 'scrapers')

        self._client = _claude.ClaudeClient()
        self._ui_obj = ScriptEditorPanel(self._client, _script_files.scratch_path(app_data), scripts_folder,
                                         mainframe)
        super().__init__(mainframe, 'Script Editor', 'script_editor', QtCore.Qt.DockWidgetArea.RightDockWidgetArea)

        self._ui_obj.settingsRequested.connect(self._open_settings)

    @property
    @_check_types.do
    def panel(self) -> ScriptEditorPanel:
        return self._ui_obj

    @_check_types.do
    def taken_names(self) -> set[str]:
        return self._ui_obj.taken_names()

    @_check_types.do
    def insert_snippet(self, snippet: _snippets.Snippet) -> None:
        """Insert code from the inspector, showing the dock if it was closed
        (an insertion nobody can see would look like nothing happened)."""
        if not self.IsShown():
            self.Show()

        self._ui_obj.insert_snippet(snippet)

    @_check_types.do
    def _open_settings(self) -> None:
        from ...plugins.plugins.claude_ai.qt import key_dialog

        dialog = key_dialog.ApiKeyDialog(self.mainframe, self._client)
        dialog.exec()
        self._ui_obj.assistant.refresh_header()

    @_check_types.do
    def Destroy(self) -> None:
        self._ui_obj.shutdown()
        super().Destroy()
