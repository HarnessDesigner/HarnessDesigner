# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The Claude package's pure parts: errors, cancel tokens, the key store,
models, settings, context, tools and message cleaning."""

import threading
import types
import unittest

import keyring.errors

from tests import _bootstrap
from tests.claude.helpers import FakeKeyring

claude = _bootstrap.load('claude')
errors = _bootstrap.load('claude.errors')
keys = _bootstrap.load('claude.keys')
models = _bootstrap.load('claude.models')
settings_module = _bootstrap.load('claude.settings')
messages = _bootstrap.load('claude.messages')
context = _bootstrap.load('claude.context')
wire = _bootstrap.load('claude.wire')


class Errors(unittest.TestCase):
    def test_every_error_has_a_message_for_the_user(self):
        for error in (errors.ClaudeError('boom'), errors.NoApiKeyError('x'), errors.KeyStoreError('x'),
                      errors.AuthenticationFailed('x'), errors.RateLimited('x'), errors.ServiceUnavailable('x'),
                      errors.BadRequest('x'), errors.BetaNotAvailable('x'), errors.Refused('x'),
                      errors.Truncated('x'), errors.Cancelled(), errors.InvalidStructuredReply('x'),
                      errors.ToolLoopLimit('x')):
            with self.subTest(error=type(error).__name__):
                self.assertTrue(error.user_message)
                self.assertIsInstance(error, errors.ClaudeError)

    def test_rate_limit_message_uses_retry_after(self):
        self.assertIn('30 seconds', errors.RateLimited('x', retry_after=30).user_message)
        self.assertNotIn('seconds', errors.RateLimited('x').user_message)

    def test_beta_error_tells_the_user_which_setting_to_change(self):
        error = errors.BetaNotAvailable('x')
        self.assertIsInstance(error, errors.BadRequest)
        self.assertIn('refusal-fallback', error.user_message)

    def test_refusal_carries_its_category(self):
        error = errors.Refused('x', category='cyber', explanation='Not that.')
        self.assertEqual(error.category, 'cyber')
        self.assertIn('Not that.', error.user_message)

    def test_request_id_is_kept(self):
        self.assertEqual(errors.BadRequest('x', status_code=400, request_id='req_1').request_id, 'req_1')


class CancelTokens(unittest.TestCase):
    def test_cancel_runs_callbacks_once(self):
        token = claude.CancelToken()
        calls = []
        token.add_callback(lambda: calls.append(1))
        token.cancel()
        token.cancel()
        self.assertEqual(calls, [1])
        self.assertTrue(token.is_cancelled)

    def test_callback_added_after_cancel_runs_at_once(self):
        token = claude.CancelToken()
        token.cancel()
        calls = []
        token.add_callback(lambda: calls.append(1))
        self.assertEqual(calls, [1])

    def test_removed_callback_does_not_run(self):
        token = claude.CancelToken()
        calls = []
        callback = lambda: calls.append(1)  # noqa: E731
        token.add_callback(callback)
        token.remove_callback(callback)
        token.cancel()
        self.assertEqual(calls, [])

    def test_raise_if_cancelled(self):
        token = claude.CancelToken()
        token.raise_if_cancelled()
        token.cancel()
        with self.assertRaises(claude.Cancelled):
            token.raise_if_cancelled()

    def test_cancel_from_another_thread_wakes_a_waiter(self):
        token = claude.CancelToken()
        threading.Timer(0.05, token.cancel).start()
        self.assertTrue(token.wait(5))


class ApiKeyStore(unittest.TestCase):
    def setUp(self):
        self.backend = FakeKeyring()
        self.store = claude.ApiKeyStore(backend=self.backend)

    def test_round_trip(self):
        self.assertFalse(self.store.has_key())
        self.assertIsNone(self.store.get_key())
        self.store.set_key('  sk-ant-abc  ')
        self.assertEqual(self.store.get_key(), 'sk-ant-abc')
        self.assertTrue(self.store.has_key())

    def test_clear(self):
        self.store.set_key('sk-ant-abc')
        self.store.clear_key()
        self.assertIsNone(self.store.get_key())

    def test_clearing_nothing_is_fine(self):
        self.store.clear_key()

    def test_empty_key_is_refused(self):
        with self.assertRaises(ValueError):
            self.store.set_key('   ')

    def test_blank_stored_value_counts_as_no_key(self):
        self.backend.passwords[(keys.SERVICE, keys.USERNAME)] = '   '
        self.assertIsNone(self.store.get_key())

    def test_store_failures_become_key_store_errors(self):
        self.backend.fail_with = keyring.errors.KeyringError('locked')
        for action in (self.store.get_key, self.store.clear_key, lambda: self.store.set_key('sk-ant-x')):
            with self.subTest(action=action):
                with self.assertRaises(claude.KeyStoreError):
                    action()

    def test_uses_the_same_slot_as_before(self):
        self.store.set_key('sk-ant-abc')
        self.assertEqual(list(self.backend.passwords), [('HarnessDesigner', 'anthropic_api_key')])

    def test_looks_like_a_key(self):
        self.assertTrue(claude.ApiKeyStore.looks_like_a_key(' sk-ant-api03-xyz '))
        self.assertFalse(claude.ApiKeyStore.looks_like_a_key('hunter2'))


class Models(unittest.TestCase):
    def test_default_model_is_offered(self):
        self.assertEqual(claude.DEFAULT_MODEL, 'claude-opus-5-5')
        self.assertIsNotNone(claude.model_info(claude.DEFAULT_MODEL))

    def test_ids_have_no_date_suffix_and_are_unique(self):
        ids = [info.id for info in claude.MODELS]
        self.assertEqual(len(ids), len(set(ids)))
        for model_id in ids:
            self.assertFalse(model_id[-8:].isdigit(), model_id)

    def test_unknown_model(self):
        self.assertIsNone(claude.model_info('claude-nonsense'))

    def test_haiku_has_no_fallback(self):
        self.assertFalse(claude.model_info('claude-haiku-5-5').supports_fallback)
        self.assertTrue(claude.model_info('claude-opus-5-5').supports_fallback)

    def test_cost_estimate(self):
        usage = claude.Usage(input_tokens=1_000_000, output_tokens=1_000_000)
        self.assertAlmostEqual(usage.estimated_cost('claude-opus-5-5'), 24.0)
        self.assertAlmostEqual(usage.estimated_cost('claude-haiku-5-5'), 0.6)
        self.assertIsNone(usage.estimated_cost('claude-nonsense'))

    def test_cache_pricing(self):
        usage = claude.Usage(cache_read_tokens=1_000_000, cache_write_tokens=1_000_000)
        self.assertAlmostEqual(usage.estimated_cost('claude-opus-5-5'), 0.20 + 4.00 * 1.25)

    def test_usage_adds(self):
        total = claude.Usage(1, 2, 3, 4) + claude.Usage(10, 20, 30, 40)
        self.assertEqual(total, claude.Usage(11, 22, 33, 44))


class FakeBackend(claude.SettingsBackend):
    def __init__(self, saved=None):
        self.saved = dict(saved or {})
        self.writes = []

    def load(self):
        return dict(self.saved)

    def save(self, values):
        self.writes.append(values)
        self.saved = dict(values)


class Settings(unittest.TestCase):
    def tearDown(self):
        settings_module.set_backend(None)

    def test_defaults(self):
        settings = claude.ClaudeSettings()
        settings.validate()
        self.assertEqual((settings.model, settings.effort), ('claude-opus-5-5', 'medium'))
        self.assertTrue(settings.refusal_fallback)

    def test_validation(self):
        for changes in ({'model': ' '}, {'effort': 'extreme'}, {'max_tokens': 0}, {'max_retries': -1},
                        {'timeout_seconds': 0}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    claude.ClaudeSettings().changed(**changes)

    def test_changed_returns_a_copy(self):
        original = claude.ClaudeSettings()
        changed = original.changed(effort='high')
        self.assertEqual((original.effort, changed.effort), ('medium', 'high'))

    def test_fallback_needs_the_setting_and_a_model_that_has_one(self):
        base = claude.ClaudeSettings()
        self.assertTrue(base.uses_fallback)
        self.assertFalse(base.changed(refusal_fallback=False).uses_fallback)
        self.assertFalse(base.changed(model='claude-haiku-5-5').uses_fallback)
        self.assertFalse(base.changed(model='some-future-model').uses_fallback)

    def test_update_persists_through_the_backend(self):
        backend = FakeBackend()
        claude.set_settings_backend(backend)
        updated = claude.update_settings(effort='high', model='claude-sonnet-5-5')
        self.assertEqual(updated.effort, 'high')
        self.assertEqual(claude.current_settings().model, 'claude-sonnet-5-5')
        self.assertEqual(backend.writes[-1]['effort'], 'high')

    def test_a_bad_update_changes_nothing(self):
        backend = FakeBackend()
        claude.set_settings_backend(backend)
        with self.assertRaises(ValueError):
            claude.update_settings(effort='nope')

        self.assertEqual(claude.current_settings().effort, 'medium')
        self.assertEqual(backend.writes, [])

    def test_current_is_a_copy(self):
        claude.current_settings().effort = 'max'
        self.assertEqual(claude.current_settings().effort, 'medium')

    def test_backend_values_are_loaded_and_junk_is_ignored(self):
        saved = {'effort': 'high', 'max_tokens': 'lots', 'model': 'claude-sonnet-5-5', 'from_the_future': 1}
        loaded = claude.set_settings_backend(FakeBackend(saved))
        self.assertEqual((loaded.effort, loaded.model), ('high', 'claude-sonnet-5-5'))
        self.assertEqual(loaded.max_tokens, 64000)

    def test_removing_the_backend_resets_to_defaults(self):
        claude.set_settings_backend(FakeBackend({'effort': 'high'}))
        self.assertEqual(claude.set_settings_backend(None).effort, 'medium')


class Context(unittest.TestCase):
    def test_nothing_to_say(self):
        self.assertIsNone(context.compose_system(None, [], ''))
        self.assertIsNone(context.compose_system('  ', [], ''))

    def test_system_and_background(self):
        text = context.compose_system(
            ' Be brief. ', [claude.StaticContext('Rules', 'No gaps.'), claude.StaticContext('History', 'Used 20 AWG.')],
            'twisting')
        self.assertEqual(text, 'Be brief.\n\n# Background\n\n## Rules\nNo gaps.\n\n## History\nUsed 20 AWG.')

    def test_blank_blocks_are_left_out(self):
        self.assertIsNone(context.compose_system(None, [claude.StaticContext('Empty', '  ')], ''))

    def test_providers_are_given_the_topic(self):
        seen = []

        class Provider(claude.ContextProvider):
            def blocks(self, topic):
                seen.append(topic)
                return [claude.ContextBlock('T', 'x')]

        context.compose_system(None, [Provider()], 'bundle layers')
        self.assertEqual(seen, ['bundle layers'])

    def test_base_provider_is_abstract(self):
        with self.assertRaises(NotImplementedError):
            claude.ContextProvider().blocks('')


class Tools(unittest.TestCase):
    schema = {'type': 'object', 'properties': {'a': {'type': 'integer'}}, 'required': ['a'],
              'additionalProperties': False}

    def test_param(self):
        tool = claude.Tool('add-one', 'Adds one.', self.schema, lambda arguments: arguments['a'] + 1)
        self.assertEqual(tool.to_param(), {'name': 'add-one', 'description': 'Adds one.', 'input_schema': self.schema})

    def test_strict_param(self):
        tool = claude.Tool('t', 'd', self.schema, lambda arguments: 1, strict=True)
        self.assertIs(tool.to_param()['strict'], True)

    def test_bad_names_are_refused(self):
        for name in ('', 'has space', 'x' * 65, 'dot.name'):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    claude.Tool(name, 'd', self.schema, lambda arguments: 1)

    def test_schema_must_be_an_object(self):
        with self.assertRaises(ValueError):
            claude.Tool('t', 'd', {'type': 'string'}, lambda arguments: 1)

    def test_strict_needs_a_closed_schema(self):
        open_schema = {'type': 'object', 'properties': {'a': {'type': 'integer'}}, 'required': ['a']}
        with self.assertRaises(ValueError):
            claude.Tool('t', 'd', open_schema, lambda arguments: 1, strict=True)

        optional = {'type': 'object', 'properties': {'a': {}, 'b': {}}, 'required': ['a'],
                    'additionalProperties': False}
        with self.assertRaises(ValueError):
            claude.Tool('t', 'd', optional, lambda arguments: 1, strict=True)

    def test_result_text(self):
        self.assertEqual(messages.result_text('plain'), 'plain')
        self.assertEqual(messages.result_text({'ok': True, 'n': 1}), '{"ok": true, "n": 1}')
        self.assertEqual(messages.result_text(None), 'null')
        self.assertEqual(messages.result_text({'name': 'Ångström'}), '{"name": "Ångström"}')

    def test_long_results_are_cut_and_the_model_is_told(self):
        text = messages.result_text('x' * (messages.MAX_TOOL_RESULT_CHARS + 500))
        self.assertIn('500 more characters', text)
        self.assertLess(len(text), messages.MAX_TOOL_RESULT_CHARS + 100)


def block(kind, **fields):
    return types.SimpleNamespace(type=kind, **fields)


class EchoContent(unittest.TestCase):
    def test_normal_content_is_kept_whole(self):
        content = [block('thinking'), block('text'), block('tool_use')]
        self.assertEqual(wire.echo_content(content), content)

    def test_everything_but_text_before_a_fallback_marker_is_dropped(self):
        thinking, early_text, early_tool = block('thinking'), block('text'), block('tool_use')
        marker, late_text, late_tool = block('fallback'), block('text'), block('tool_use')
        content = [thinking, early_text, early_tool, marker, late_text, late_tool]
        self.assertEqual(wire.echo_content(content), [early_text, late_text, late_tool])

    def test_the_last_marker_is_the_boundary(self):
        first_thinking, first_marker, middle_text = block('thinking'), block('fallback'), block('text')
        second_thinking, second_marker, last = block('thinking'), block('fallback'), block('text')
        content = [first_thinking, first_marker, middle_text, second_thinking, second_marker, last]
        self.assertEqual(wire.echo_content(content), [middle_text, last])


if __name__ == '__main__':
    unittest.main()
