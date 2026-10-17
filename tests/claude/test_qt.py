# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The Qt layer of the Claude package, headless: the threaded job, a tool
that asks the user a question from the worker thread, and the settings
dialog."""

import sys
import threading
import time
import types
import unittest

from tests import _bootstrap
from tests.claude import fake_api
from tests.claude.helpers import FakeKeyring

APP = _bootstrap.make_app()

from PySide6 import QtCore, QtTest, QtWidgets  # noqa: E402

claude = _bootstrap.load('claude')
settings_module = _bootstrap.load('claude.settings')
gui_call = _bootstrap.load('claude.qt.gui_call')
job_module = _bootstrap.load('claude.qt.job')
claude_qt = _bootstrap.load('claude.qt')

# The real dialog header needs the application's image package; the dialog
# under test only needs something that sits at the top.
_fake_header = types.ModuleType('hd_under_test.ui.dialogs.header')


class _Header(QtWidgets.QWidget):
    def __init__(self, parent, title, size=(-1, -1)):
        super().__init__(parent)
        self.title = title


_fake_header.Header = _Header
sys.modules['hd_under_test.ui.dialogs.header'] = _fake_header
sys.modules['hd_under_test.utils'].safe_center = lambda geometry, size: geometry.center()

key_dialog = _bootstrap.load('claude.qt.key_dialog')

API = None


def setUpModule():
    global API
    API = fake_api.FakeAPI().start()


def tearDownModule():
    API.stop()


def pump(seconds: float) -> None:
    """Run the event loop for a while. Uses time.sleep, which lets other
    Python threads run: QTest.qWait does not release the GIL, so a worker
    doing its first (slow) import of the SDK would starve."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        APP.processEvents()
        time.sleep(0.005)


def wait_until(predicate, timeout: float = 15.0, what: str = 'the job') -> None:
    end = time.monotonic() + timeout
    while not predicate():
        pump(0.01)
        if time.monotonic() > end:
            raise AssertionError(f'timed out waiting for {what}')


class Base(unittest.TestCase):
    def setUp(self):
        API.reset()
        self.keys = claude.ApiKeyStore(backend=FakeKeyring())
        self.keys.set_key('sk-ant-test-key')
        self.client = claude.ClaudeClient(self.keys, claude.ClaudeSettings(max_retries=0), base_url=API.url)

    def watch(self, job):
        """Record every signal a job emits, in order."""
        events = []
        job.textDelta.connect(lambda piece: events.append(('text', piece)))
        job.toolCalled.connect(lambda name, args, result, is_error: events.append(('tool', name, result, is_error)))
        job.finished.connect(lambda response: events.append(('finished', response)))
        job.failed.connect(lambda error: events.append(('failed', error)))
        job.cancelled.connect(lambda: events.append(('cancelled',)))
        job.threads = []
        job.finished.connect(lambda response: job.threads.append(threading.current_thread()))
        return events

    @staticmethod
    def final(events):
        return [event for event in events if event[0] in ('finished', 'failed', 'cancelled')]


class JobTests(Base):
    def test_a_successful_call(self):
        API.queue(fake_api.text('An answer that arrives in a few small pieces.'))
        job = claude_qt.ClaudeJob.ask(self.client, 'hi')
        events = self.watch(job)
        job.start()
        wait_until(lambda: self.final(events))

        final = self.final(events)
        self.assertEqual([event[0] for event in final], ['finished'])
        response = final[0][1]
        self.assertEqual(response.text, 'An answer that arrives in a few small pieces.')
        self.assertEqual(''.join(event[1] for event in events if event[0] == 'text'), response.text)
        self.assertIs(job.threads[0], threading.main_thread(), 'signals must arrive on the GUI thread')

    def test_a_failure_is_reported_not_raised(self):
        self.keys.clear_key()
        job = claude_qt.ClaudeJob.ask(self.client, 'hi')
        events = self.watch(job)
        job.start()
        wait_until(lambda: self.final(events))

        final = self.final(events)
        self.assertEqual([event[0] for event in final], ['failed'])
        self.assertIsInstance(final[0][1], claude.NoApiKeyError)

    def test_cancelling(self):
        API.queue(fake_api.Reply(events=fake_api.message_events([('text', 'x' * 400)]), event_delay=0.2))
        job = claude_qt.ClaudeJob.ask(self.client, 'hi')
        events = self.watch(job)
        job.start()
        wait_until(lambda: any(event[0] == 'text' for event in events), what='the first text')
        job.cancel()
        wait_until(lambda: self.final(events), what='the cancel')

        self.assertEqual([event[0] for event in self.final(events)], ['cancelled'])
        wait_until(lambda: not job.is_running, what='the thread to end')

    def test_tool_calls_are_reported(self):
        tool = claude.Tool('ping', 'd', {'type': 'object'}, lambda arguments: 'pong')
        API.queue(fake_api.tools(('toolu_1', 'ping', {})), fake_api.text('done'))
        job = claude_qt.ClaudeJob.ask(self.client, 'go', tools=[tool])
        events = self.watch(job)
        job.start()
        wait_until(lambda: self.final(events))

        self.assertIn(('tool', 'ping', 'pong', False), events)
        self.assertEqual(self.final(events)[0][0], 'finished')

    def test_a_conversation_can_be_sent_through_a_job(self):
        chat = self.client.conversation()
        API.queue(fake_api.text('one'), fake_api.text('two'))
        for expected in ('one', 'two'):
            job = claude_qt.ClaudeJob.send(chat, 'next')
            events = self.watch(job)
            job.start()
            wait_until(lambda: self.final(events))
            self.assertEqual(self.final(events)[0][1].text, expected)

        self.assertEqual(chat.turns, 4)

    def test_a_bug_in_the_work_becomes_a_failure_with_details(self):
        def work(token, on_text, on_tool):
            raise ZeroDivisionError('oops')

        job = claude_qt.ClaudeJob(work)
        events = self.watch(job)
        job.start()
        wait_until(lambda: self.final(events))

        error = self.final(events)[0][1]
        self.assertEqual(self.final(events)[0][0], 'failed')
        self.assertIn('ZeroDivisionError', error.user_message)
        self.assertIn('Traceback', error.details)

    def test_a_job_starts_only_once(self):
        job = claude_qt.ClaudeJob(lambda token, on_text, on_tool: None)
        job.start()
        with self.assertRaises(RuntimeError):
            job.start()

    def test_running_jobs_are_kept_alive_until_done(self):
        API.queue(fake_api.text('x'))
        job = claude_qt.ClaudeJob.ask(self.client, 'hi')
        events = self.watch(job)
        job.start()
        self.assertIn(job, job_module._running)
        wait_until(lambda: self.final(events))
        wait_until(lambda: job not in job_module._running, what='the job to be released')


class GuiCallTests(Base):
    def test_a_worker_gets_an_answer_computed_on_the_gui_thread(self):
        seen = {}

        def ask_user():
            seen['thread'] = threading.current_thread()
            return 'the centre wire'

        result = {}

        def worker():
            result['value'] = gui_call.call_in_gui(ask_user)

        thread = threading.Thread(target=worker)
        thread.start()
        wait_until(lambda: not thread.is_alive(), what='the worker')

        self.assertEqual(result['value'], 'the centre wire')
        self.assertIs(seen['thread'], threading.main_thread())

    def test_an_exception_in_the_function_reaches_the_worker(self):
        result = {}

        def worker():
            try:
                gui_call.call_in_gui(lambda: 1 / 0)
            except ZeroDivisionError as error:
                result['error'] = error

        thread = threading.Thread(target=worker)
        thread.start()
        wait_until(lambda: not thread.is_alive(), what='the worker')
        self.assertIsInstance(result['error'], ZeroDivisionError)

    def test_on_the_gui_thread_it_just_runs(self):
        self.assertEqual(gui_call.call_in_gui(lambda: 7), 7)

    def test_cancelling_stops_the_wait(self):
        token = claude.CancelToken()
        release = threading.Event()
        result = {}

        # Like a modal dialog: runs on the GUI thread in a nested event loop
        # that only ends when the "user" answers.
        def dialog():
            while not release.is_set():
                APP.processEvents()
                time.sleep(0.005)

        def worker():
            try:
                gui_call.call_in_gui(dialog, token)
            except claude.Cancelled:
                result['cancelled'] = time.monotonic()

        threading.Timer(0.2, token.cancel).start()
        threading.Timer(1.0, release.set).start()
        started = time.monotonic()
        thread = threading.Thread(target=worker)
        thread.start()
        wait_until(lambda: not thread.is_alive() and release.is_set(), what='the worker and the dialog')

        self.assertIn('cancelled', result)
        self.assertLess(result['cancelled'] - started, 0.8, 'the wait must end when cancelled, not when the dialog does')

    def test_it_needs_install_first(self):
        saved = gui_call._invoker
        gui_call._invoker = None
        result = {}

        def worker():
            try:
                gui_call.call_in_gui(lambda: 1)
            except RuntimeError as error:
                result['error'] = error

        try:
            thread = threading.Thread(target=worker)
            thread.start()
            thread.join(5)
        finally:
            gui_call._invoker = saved

        self.assertIn('install', str(result['error']))

    def test_install_must_run_on_the_gui_thread(self):
        result = {}

        def worker():
            try:
                gui_call.install()
            except RuntimeError as error:
                result['error'] = error

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(5)
        self.assertIn('GUI thread', str(result['error']))

    def test_a_tool_can_ask_the_user_while_claude_waits(self):
        answers = []

        def choose_centre(arguments):
            answer = gui_call.call_in_gui(lambda: 'wire 7')
            answers.append(answer)
            return {'user_chose': answer}

        tool = claude.Tool('ask_user', 'Ask the user which wire goes in the centre.',
                           {'type': 'object', 'properties': {'question': {'type': 'string'}}}, choose_centre)
        API.queue(fake_api.tools(('toolu_1', 'ask_user', {'question': 'centre?'})), fake_api.text('Wire 7 it is.'))

        job = claude_qt.ClaudeJob.ask(self.client, 'Arrange the bundle.', tools=[tool])
        events = self.watch(job)
        job.start()
        wait_until(lambda: self.final(events))

        self.assertEqual(self.final(events)[0][0], 'finished')
        self.assertEqual(answers, ['wire 7'])
        result = API.requests[1].body['messages'][2]['content'][0]['content']
        self.assertEqual(result, '{"user_chose": "wire 7"}')


class FakeBackend(claude.SettingsBackend):
    def __init__(self):
        self.saved = {}

    def load(self):
        return dict(self.saved)

    def save(self, values):
        self.saved = dict(values)


class KeyDialogTests(Base):
    def setUp(self):
        super().setUp()
        self.backend = FakeBackend()
        settings_module.set_backend(self.backend)
        self.client = claude.ClaudeClient(self.keys, None, base_url=API.url)
        self.window = QtWidgets.QMainWindow()
        self.window.resize(900, 700)
        self.window.show()
        self.dialog = key_dialog.ApiKeyDialog(self.window, self.client)

    def tearDown(self):
        self.dialog.close()
        self.window.close()
        settings_module.set_backend(None)

    def test_it_shows_the_current_state_without_revealing_the_key(self):
        self.assertIn('A key is saved', self.dialog.key_status.text())
        self.assertEqual(self.dialog.key_edit.text(), '')
        self.assertEqual(self.dialog.model_box.currentData(), 'claude-opus-5-5')
        self.assertEqual(self.dialog.effort_box.currentData(), 'medium')
        self.assertTrue(self.dialog.fallback_box.isChecked())
        self.assertTrue(self.dialog.clear_button.isEnabled())

    def test_with_no_key(self):
        self.keys.clear_key()
        dialog = key_dialog.ApiKeyDialog(self.window, self.client)
        self.assertIn('No key saved', dialog.key_status.text())
        self.assertFalse(dialog.clear_button.isEnabled())
        dialog.close()

    def test_every_model_is_offered_with_its_price(self):
        ids = [self.dialog.model_box.itemData(i) for i in range(self.dialog.model_box.count())]
        self.assertEqual(ids, [info.id for info in claude.MODELS])
        self.assertIn('$4.00 in / $20.00 out', self.dialog.price_label.text())

    def test_models_without_a_fallback_disable_that_option(self):
        self.dialog.model_box.setCurrentIndex(self.dialog.model_box.findData('claude-haiku-5-5'))
        self.assertFalse(self.dialog.fallback_box.isEnabled())
        self.dialog.model_box.setCurrentIndex(self.dialog.model_box.findData('claude-sonnet-5-5'))
        self.assertTrue(self.dialog.fallback_box.isEnabled())

    def test_show_toggles_the_key_echo(self):
        Echo = QtWidgets.QLineEdit.EchoMode
        self.assertEqual(self.dialog.key_edit.echoMode(), Echo.Password)
        self.dialog.show_key.setChecked(True)
        self.assertEqual(self.dialog.key_edit.echoMode(), Echo.Normal)

    def test_ok_saves_the_key_and_the_settings(self):
        self.dialog.key_edit.setText('  sk-ant-new-key  ')
        self.dialog.model_box.setCurrentIndex(self.dialog.model_box.findData('claude-sonnet-5-5'))
        self.dialog.effort_box.setCurrentIndex(self.dialog.effort_box.findData('high'))
        self.dialog.fallback_box.setChecked(False)
        self.dialog.accept()

        self.assertEqual(self.keys.get_key(), 'sk-ant-new-key')
        current = claude.current_settings()
        self.assertEqual((current.model, current.effort, current.refusal_fallback), ('claude-sonnet-5-5', 'high', False))
        self.assertEqual(self.backend.saved['effort'], 'high')
        self.assertEqual(self.dialog.result(), QtWidgets.QDialog.DialogCode.Accepted)

    def test_ok_without_typing_a_key_keeps_the_saved_one(self):
        self.dialog.effort_box.setCurrentIndex(self.dialog.effort_box.findData('low'))
        self.dialog.accept()
        self.assertEqual(self.keys.get_key(), 'sk-ant-test-key')
        self.assertEqual(claude.current_settings().effort, 'low')

    def test_something_that_is_not_a_key_does_not_close_the_dialog(self):
        self.dialog.key_edit.setText('hunter2')
        self.dialog.accept()
        self.assertEqual(self.keys.get_key(), 'sk-ant-test-key')
        self.assertIn('does not look like', self.dialog.result_label.text())
        self.assertNotEqual(self.dialog.result(), QtWidgets.QDialog.DialogCode.Accepted)

    def test_cancel_changes_nothing(self):
        self.dialog.key_edit.setText('sk-ant-other')
        self.dialog.effort_box.setCurrentIndex(self.dialog.effort_box.findData('max'))
        self.dialog.reject()
        self.assertEqual(self.keys.get_key(), 'sk-ant-test-key')
        self.assertEqual(claude.current_settings().effort, 'medium')

    def test_removing_the_saved_key(self):
        self.dialog.clear_button.click()
        self.assertIsNone(self.keys.get_key())
        self.assertIn('No key saved', self.dialog.key_status.text())

    def test_the_test_button_uses_the_typed_key_and_chosen_settings_without_saving(self):
        API.queue(fake_api.text('OK'))
        self.dialog.key_edit.setText('sk-ant-typed-key')
        self.dialog.model_box.setCurrentIndex(self.dialog.model_box.findData('claude-sonnet-5-5'))
        self.dialog.test_button.click()
        wait_until(lambda: 'It works' in self.dialog.result_label.text(), what='the test result')

        sent = API.last
        self.assertEqual(sent.headers['x-api-key'], 'sk-ant-typed-key')
        self.assertEqual(sent.body['model'], 'claude-sonnet-5-5')
        self.assertEqual(self.keys.get_key(), 'sk-ant-test-key', 'a test must not save the key')
        self.assertTrue(self.dialog.test_button.isEnabled())
        self.assertIn('cost about', self.dialog.result_label.text())

    def test_the_test_button_reports_a_rejected_key(self):
        API.queue(fake_api.error(401, 'authentication_error', 'invalid x-api-key'))
        self.dialog.key_edit.setText('sk-ant-wrong')
        self.dialog.test_button.click()
        wait_until(lambda: 'did not accept' in self.dialog.result_label.text(), what='the test result')
        self.assertTrue(self.dialog.test_button.isEnabled())

    def test_the_test_button_reports_a_missing_key(self):
        self.keys.clear_key()
        self.dialog.test_button.click()
        wait_until(lambda: 'No Anthropic API key' in self.dialog.result_label.text(), what='the test result')


if __name__ == '__main__':
    unittest.main()
