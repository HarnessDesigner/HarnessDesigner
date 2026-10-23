# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The scraper assistant: ask Claude to write, fix or explain the script.

Everything that is sent is chosen by the user and shown to them first: a
list of pieces of context to tick (the script, the text selected in the
page source, the network request picked in the inspector, ...), a preview of
the exact message with its size and an estimate of what it will cost, and
nothing is sent until Send is clicked. An answer is never applied by
itself: its code blocks can be inserted at the cursor, swapped in for the
whole script (after looking at the changes), or copied.

All the API work is in ``harness_designer.plugins.plugins.claude_ai``; this module is the
panel and the prompts (``scraping/assistant.py``) around it.
"""

from typing import TYPE_CHECKING, Any

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from ..widgets import wrap_label as _wrap_label
from ...scraping import assistant as _assistant
from ...scraping import assistant_tools as _assistant_tools
from ... import check_types as _check_types
from ...plugins.plugins import claude_ai as _claude
from ...plugins.plugins.claude_ai import qt as _claude_qt

if TYPE_CHECKING:
    from . import script_editor as _script_editor

# How often the panel looks at the browser for new context while visible.
_REFRESH_MILLISECONDS = 700

# The answer is re-rendered at most this often while it streams.
_RENDER_MILLISECONDS = 60

_TOOL_ARGUMENT_CHARS = 90

_ITEM_ORDER = ('script', 'script_selection', 'page_url', 'source_selection', 'request', 'page_source')

_DIFF_COLORS = {'+': QtGui.QColor('#6a9955'), '-': QtGui.QColor('#f44747'), '@': QtGui.QColor('#569cd6')}


class AssistantPanel(QtWidgets.QWidget):
    """:ivar settingsRequested: The user wants the Claude settings (or there
        is no key yet): open the settings dialog.
    """

    settingsRequested = QtCore.Signal()

    @_check_types.do
    def __init__(self, editor: "_script_editor.ScriptEditorPanel", client: _claude.ClaudeClient,
                 parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._editor = editor
        self._client = client
        self._context: _assistant.AssistantContext = _assistant.EmptyContext()

        self._chat: _claude.Conversation | None = None
        self._chat_settings: _claude.ClaudeSettings | None = None
        self._job: _claude_qt.ClaudeJob | None = None
        self._busy = False

        self._touched: set[str] = set()
        self._reply = ''
        self._blocks: list[_assistant.CodeBlock] = []
        self._tool_lines: list[str] = []

        self._build()
        self._connect()

        # Importing the SDK takes about three seconds; do it now, in the
        # background, rather than as the delay before the first answer.
        _claude.warm_up()
        self.refresh_header()
        self.refresh_context()

    # -- construction -------------------------------------------------------

    @_check_types.do
    def _build(self) -> None:
        self._model_label = _wrap_label.WrapLabel('', self, wrap=False)
        self._settings_button = QtWidgets.QPushButton('Claude settings...', self)
        self._new_chat_button = QtWidgets.QPushButton('New chat', self)
        self._new_chat_button.setToolTip('Forget this conversation and start again. Costs nothing.')

        header = QtWidgets.QHBoxLayout()
        header.addWidget(self._model_label, 1)
        header.addWidget(self._new_chat_button)
        header.addWidget(self._settings_button)

        self._item_boxes: dict[str, QtWidgets.QCheckBox] = {}
        items = QtWidgets.QVBoxLayout()
        items.setSpacing(0)
        items.addWidget(QtWidgets.QLabel('Send Claude:', self))
        for item_id in _ITEM_ORDER:
            box = QtWidgets.QCheckBox(self)
            self._item_boxes[item_id] = box
            items.addWidget(box)

        self._edit_mode = QtWidgets.QRadioButton('Edit my script', self)
        self._question_mode = QtWidgets.QRadioButton('Just answer', self)
        self._edit_mode.setChecked(True)
        self._edit_mode.setToolTip('Claude finishes with a complete updated script you can swap in.')
        self._question_mode.setToolTip('Claude answers the question; it will not rewrite the whole script.')
        modes = QtWidgets.QHBoxLayout()
        modes.addWidget(self._edit_mode)
        modes.addWidget(self._question_mode)
        modes.addStretch(1)

        self._prompt = QtWidgets.QPlainTextEdit(self)
        self._prompt.setPlaceholderText('What do you want? e.g. "Get every price on this page into a list"   '
                                        '(Ctrl+Enter sends)')
        self._prompt.setMaximumHeight(70)
        self._send_button = QtWidgets.QPushButton('Send', self)
        self._stop_button = QtWidgets.QPushButton('Stop', self)
        self._stop_button.setEnabled(False)
        self._preview_button = QtWidgets.QPushButton('Preview', self)
        self._preview_button.setCheckable(True)
        self._preview_button.setToolTip('Show exactly what will be sent.')

        buttons = QtWidgets.QVBoxLayout()
        buttons.addWidget(self._send_button)
        buttons.addWidget(self._stop_button)
        buttons.addWidget(self._preview_button)

        prompt_row = QtWidgets.QHBoxLayout()
        prompt_row.addWidget(self._prompt, 1)
        prompt_row.addLayout(buttons)

        self._size_label = _wrap_label.WrapLabel('', self, wrap=False)
        self._preview = QtWidgets.QPlainTextEdit(self)
        self._preview.setReadOnly(True)
        self._preview.setMaximumHeight(160)
        self._preview.hide()
        mono = QtGui.QFont('Consolas', 9)
        mono.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        self._preview.setFont(mono)

        self._activity = _wrap_label.WrapLabel('', self)
        self._activity.setStyleSheet('color: gray;')
        self._activity.hide()

        self._answer = QtWidgets.QTextBrowser(self)
        self._answer.setOpenLinks(False)
        self._answer.setPlaceholderText('Claude\'s answer appears here.')

        self._block_box = QtWidgets.QComboBox(self)
        self._insert_button = QtWidgets.QPushButton('Insert at cursor', self)
        self._replace_button = QtWidgets.QPushButton('Replace script', self)
        self._copy_button = QtWidgets.QPushButton('Copy', self)
        self._diff_button = QtWidgets.QPushButton('View changes', self)
        self._diff_button.setCheckable(True)
        actions = QtWidgets.QHBoxLayout()
        actions.addWidget(QtWidgets.QLabel('Code in the answer:', self))
        actions.addWidget(self._block_box, 1)
        actions.addWidget(self._diff_button)
        actions.addWidget(self._insert_button)
        actions.addWidget(self._replace_button)
        actions.addWidget(self._copy_button)

        self._diff = QtWidgets.QPlainTextEdit(self)
        self._diff.setReadOnly(True)
        self._diff.setMaximumHeight(200)
        self._diff.setFont(mono)
        self._diff.hide()

        self._status = _wrap_label.WrapLabel('', self)
        self._cost = QtWidgets.QLabel(self)
        self._cost.setStyleSheet('color: gray;')

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(header)
        layout.addLayout(items)
        layout.addLayout(modes)
        layout.addLayout(prompt_row)
        layout.addWidget(self._size_label)
        layout.addWidget(self._preview)
        layout.addWidget(self._status)
        layout.addWidget(self._activity)
        layout.addWidget(self._answer, 1)
        layout.addLayout(actions)
        layout.addWidget(self._diff)
        layout.addWidget(self._cost)

        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.setInterval(_REFRESH_MILLISECONDS)
        self._render_timer = QtCore.QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(_RENDER_MILLISECONDS)

        self._set_blocks([])

    @_check_types.do
    def _connect(self) -> None:
        self._settings_button.clicked.connect(self.settingsRequested.emit)
        self._new_chat_button.clicked.connect(self.new_chat)
        self._send_button.clicked.connect(self.send)
        self._stop_button.clicked.connect(self.stop)
        self._preview_button.toggled.connect(self._toggle_preview)
        self._insert_button.clicked.connect(self._insert)
        self._replace_button.clicked.connect(self._replace)
        self._copy_button.clicked.connect(self._copy)
        self._diff_button.toggled.connect(self._toggle_diff)
        self._block_box.currentIndexChanged.connect(self._block_changed)

        self._prompt.textChanged.connect(self._update_size)
        self._edit_mode.toggled.connect(self._update_size)
        for item_id, box in self._item_boxes.items():
            box.clicked.connect(lambda checked, key=item_id: self._item_clicked(key))

        self._refresh_timer.timeout.connect(self.refresh_context)
        self._render_timer.timeout.connect(self._render_reply)
        self._editor.editor.textChanged.connect(self._editor_changed)
        self._editor.editor.selectionChanged.connect(self._editor_changed)

        for keys in ('Ctrl+Return', 'Ctrl+Enter'):
            send_shortcut = QtGui.QShortcut(QtGui.QKeySequence(keys), self._prompt)
            send_shortcut.setContext(QtCore.Qt.ShortcutContext.WidgetShortcut)
            send_shortcut.activated.connect(self.send)

    # -- public ---------------------------------------------------------------

    @_check_types.do
    def set_context(self, context: _assistant.AssistantContext | None) -> None:
        """Where the page, its selection and the picked request come from
        (the inspector); ``None`` means there is no browser."""
        if context is None:
            self._context = _assistant.EmptyContext()
        else:
            self._context = context

        self.refresh_context()

    @_check_types.do
    def refresh_header(self) -> None:
        """Show which model and effort are in use (call after the settings
        dialog closes)."""
        settings = self._client.settings
        info = _claude.model_info(settings.model)
        if info is None:
            name = settings.model
        else:
            name = info.name

        self._model_label.setText(f'{name}, {settings.effort} effort')

    @_check_types.do
    def refresh_context(self) -> None:
        """Re-read what can be sent, update the tick boxes and the size."""
        found = _assistant.list_items(self._context, self._editor.script_text(), self._editor.selected_text())
        for item in found:
            box = self._item_boxes[item.id]
            box.setText(item.title)
            box.setEnabled(item.available)
            box.setToolTip(item.note)

            if not item.available:
                box.setChecked(False)
            elif item.id not in self._touched:
                box.setChecked(item.default)

        self._update_size()

    @_check_types.do
    def is_busy(self) -> bool:
        return self._busy

    @_check_types.do
    def new_chat(self) -> None:
        """Forget the conversation. The next Send starts a fresh one."""
        self.stop()
        self._chat = None
        self._chat_settings = None
        self._reply = ''
        self._answer.clear()
        self._set_blocks([])
        self._activity.hide()
        self._cost.clear()
        self._set_status('Started a new chat.')

    @_check_types.do
    def stop(self) -> None:
        if self._busy and self._job is not None:
            self._job.cancel()

    @_check_types.do
    def shutdown(self) -> None:
        """Stop anything in flight (the application is closing)."""
        self._refresh_timer.stop()
        self.stop()

    @_check_types.do
    def send(self) -> None:
        """Send the task with the chosen context."""
        if self.is_busy():
            return

        # The boxes are only as fresh as the last look at the browser; what
        # the user has selected at the moment they press Send is what counts.
        self.refresh_context()
        message = self._assemble()
        if not message.ok:
            self._set_status(message.problems[0])
            return

        try:
            has_key = self._client.key_store.has_key()
        except _claude.KeyStoreError as problem:
            self._set_status(problem.user_message)
            return

        if not has_key:
            self._set_status('Add your Anthropic API key first.')
            self.settingsRequested.emit()
            return

        chat = self._conversation()

        self._reply = ''
        self._answer.clear()
        self._set_blocks([])
        self._tool_lines = []
        self._activity.hide()
        self._set_status('Waiting for Claude...')

        job = _claude_qt.ClaudeJob.send(chat, message.text, self)
        job.textDelta.connect(self._text_arrived)
        job.toolCalled.connect(self._tool_called)
        job.finished.connect(self._finished)
        job.failed.connect(self._failed)
        job.cancelled.connect(self._cancelled)
        self._job = job
        self._set_busy(True)
        job.start()

    # -- building the request ------------------------------------------------------

    @_check_types.do
    def _mode(self) -> str:
        if self._edit_mode.isChecked():
            return _assistant.MODE_EDIT

        return _assistant.MODE_ANSWER

    @_check_types.do
    def _enabled_items(self) -> set[str]:
        return {item_id for item_id, box in self._item_boxes.items() if box.isEnabled() and box.isChecked()}

    @_check_types.do
    def _assemble(self) -> _assistant.AssembledMessage:
        return _assistant.assemble(
            self._prompt.toPlainText(), self._mode(), self._enabled_items(), self._context,
            self._editor.script_text(), self._editor.selected_text())

    @_check_types.do
    def _conversation(self) -> _claude.Conversation:
        """The chat to continue; a new one when there is none or the user
        changed the model or effort (a conversation's settings are fixed)."""
        settings = self._client.settings
        if self._chat is None or self._chat_settings != settings:
            if self._chat is not None:
                self._set_status('The Claude settings changed, so this is a new chat.')

            self._chat = self._client.conversation(
                system=_assistant.SYSTEM_PROMPT,
                tools=_assistant_tools.make_tools(self._current_context),
                topic='scraping')
            self._chat_settings = settings

        return self._chat

    @_check_types.do
    def _current_context(self) -> _assistant.AssistantContext:
        return self._context

    # -- the answer ----------------------------------------------------------------

    @_check_types.do
    def _text_arrived(self, piece: str) -> None:
        self._reply += piece
        if not self._render_timer.isActive():
            self._render_timer.start()

    @_check_types.do
    def _render_reply(self) -> None:
        scrollbar = self._answer.verticalScrollBar()
        at_end = scrollbar.value() >= scrollbar.maximum() - 4
        self._answer.setMarkdown(self._reply)
        if at_end:
            scrollbar.setValue(scrollbar.maximum())

    @_check_types.do
    def _tool_called(self, name: str, arguments: dict[str, Any], result: str, is_error: bool) -> None:
        shown = ', '.join(f'{key}={value!r}' for key, value in arguments.items())
        if len(shown) > _TOOL_ARGUMENT_CHARS:
            shown = shown[:_TOOL_ARGUMENT_CHARS] + '...'

        if is_error:
            outcome = 'failed'
        else:
            outcome = 'ok'

        self._tool_lines.append(f'Claude checked: {name}({shown}) - {outcome}')
        self._activity.setText('\n'.join(self._tool_lines[-4:]))
        self._activity.show()

    @_check_types.do
    def _finished(self, response: _claude.Response) -> None:
        self._render_timer.stop()
        self._reply = response.text
        self._render_reply()
        self._set_busy(False)
        self._set_blocks(_assistant.extract_code_blocks(response.text))
        self._prompt.clear()
        self._set_status('Done.')
        self._show_cost(response)

    @_check_types.do
    def _failed(self, problem: _claude.ClaudeError) -> None:
        self._render_timer.stop()
        self._render_reply()
        self._set_busy(False)
        self._set_status(problem.user_message)
        if isinstance(problem, _claude.NoApiKeyError):
            self.settingsRequested.emit()

    @_check_types.do
    def _cancelled(self) -> None:
        self._render_timer.stop()
        self._render_reply()
        self._set_busy(False)
        self._set_status('Stopped. What was written so far is not part of the chat.')

    @_check_types.do
    def _show_cost(self, response: _claude.Response) -> None:
        parts: list[str] = []
        cost = response.estimated_cost
        if cost is not None:
            parts.append(f'This answer: about ${cost:.3f}')

        if self._chat is not None:
            total = self._chat.usage.estimated_cost(response.requested_model)
            if total is not None:
                parts.append(f'this chat: about ${total:.3f}')

        if response.served_by_fallback:
            parts.append(f'answered by {response.model} after a refusal')

        if response.tool_calls:
            parts.append(f'{response.tool_calls} check(s) made')

        self._cost.setText(' - '.join(parts))

    # -- the code in the answer ------------------------------------------------------

    @_check_types.do
    def _set_blocks(self, blocks: list[_assistant.CodeBlock]) -> None:
        self._blocks = blocks
        self._block_box.blockSignals(True)
        self._block_box.clear()
        for number, block in enumerate(blocks, start=1):
            first_line = block.code.strip().split('\n', 1)[0][:50]
            label = block.language or 'code'
            self._block_box.addItem(f'{number}. {label}: {first_line}', number - 1)

        proposed = _assistant.proposed_script(blocks)
        if proposed is not None:
            self._block_box.setCurrentIndex(blocks.index(proposed))

        self._block_box.blockSignals(False)
        has_code = bool(blocks)
        for widget in (self._block_box, self._insert_button, self._replace_button, self._copy_button,
                       self._diff_button):
            widget.setEnabled(has_code)

        if not has_code:
            self._diff_button.setChecked(False)

        self._block_changed()

    @_check_types.do
    def _chosen_block(self) -> _assistant.CodeBlock | None:
        index = self._block_box.currentIndex()
        if index < 0 or index >= len(self._blocks):
            return None

        return self._blocks[index]

    @_check_types.do
    def _insert(self) -> None:
        block = self._chosen_block()
        if block is not None:
            self._editor.insert_at_cursor(block.code)
            self._set_status('Inserted at the cursor. Ctrl+Z undoes it.')

    @_check_types.do
    def _replace(self) -> None:
        block = self._chosen_block()
        if block is not None:
            self._editor.replace_script(block.code)
            self._set_status('The script was replaced. Ctrl+Z undoes it.')
            self.refresh_context()

    @_check_types.do
    def _copy(self) -> None:
        block = self._chosen_block()
        if block is not None:
            QtWidgets.QApplication.clipboard().setText(block.code)
            self._set_status('Copied.')

    @_check_types.do
    def _block_changed(self, *_args: tuple[Any]) -> None:
        if self._diff_button.isChecked():
            self._show_diff()

    @_check_types.do
    def _toggle_diff(self, shown: bool) -> None:
        if shown:
            self._show_diff()
            self._diff.show()
        else:
            self._diff.hide()

    @_check_types.do
    def _show_diff(self) -> None:
        self._diff.clear()
        block = self._chosen_block()
        if block is None:
            return

        lines = _assistant.unified_diff(self._editor.script_text(), block.code)
        if not lines:
            self._diff.setPlainText('No difference from your script.')
            return

        cursor = self._diff.textCursor()
        for line in lines:
            text_format = QtGui.QTextCharFormat()
            color = _DIFF_COLORS.get(line[:1])
            if color is not None and not line.startswith(('---', '+++')):
                text_format.setForeground(color)

            cursor.insertText(line + '\n', text_format)

        self._diff.moveCursor(QtGui.QTextCursor.MoveOperation.Start)

    # -- the controls -----------------------------------------------------------------

    @_check_types.do
    def _item_clicked(self, item_id: str) -> None:
        self._touched.add(item_id)
        self._update_size()

    @_check_types.do
    def _editor_changed(self) -> None:
        self.refresh_context()

    @_check_types.do
    def _toggle_preview(self, shown: bool) -> None:
        self._preview.setVisible(shown)
        self._update_size()

    @_check_types.do
    def _update_size(self, *_args: tuple[Any]) -> None:
        message = self._assemble()
        text = f'About {message.estimated_tokens:,} tokens to send'

        info = _claude.model_info(self._client.settings.model)
        if info is not None:
            cost = _claude.Usage(input_tokens=message.estimated_tokens).estimated_cost(info.id)
            text += f' (roughly ${cost:.3f} on {info.name}, before the answer)'

        if self.is_busy():
            text += '. Sending...'

        self._size_label.setText(text)
        self._size_label.setStyleSheet('')
        if message.problems and self._prompt.toPlainText().strip():
            self._size_label.setText(text + '. ' + message.problems[0])
            self._size_label.setStyleSheet('color: #d7ba7d;')

        if self._preview.isVisible():
            self._preview.setPlainText(message.text)

    @_check_types.do
    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._send_button.setEnabled(not busy)
        self._stop_button.setEnabled(busy)
        self._new_chat_button.setEnabled(not busy)
        self._prompt.setReadOnly(busy)
        self._update_size()

    @_check_types.do
    def _set_status(self, text: str) -> None:
        self._status.setText(text)

    @_check_types.do
    def showEvent(self, event: QtGui.QShowEvent) -> None:  # NOQA -- Qt override
        super().showEvent(event)
        self._refresh_timer.start()
        self.refresh_context()

    @_check_types.do
    def hideEvent(self, event: QtGui.QHideEvent) -> None:  # NOQA -- Qt override
        super().hideEvent(event)
        self._refresh_timer.stop()
