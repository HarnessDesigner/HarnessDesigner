# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The Claude client against a fake Messages API: what is sent, what comes
back, how errors are translated, and how conversations and tools behave."""

import json
import threading
import time
import unittest

from tests import _bootstrap
from tests.claude import fake_api
from tests.claude.helpers import FakeKeyring

claude = _bootstrap.load('claude')
conversation_module = _bootstrap.load('claude.conversation')

API = None


def setUpModule():
    global API
    API = fake_api.FakeAPI().start()


def tearDownModule():
    API.stop()


class Base(unittest.TestCase):
    def setUp(self):
        API.reset()
        self.keyring = FakeKeyring()
        self.keys = claude.ApiKeyStore(backend=self.keyring)
        self.keys.set_key('sk-ant-test-key')

    def settings(self, **changes):
        return claude.ClaudeSettings(max_retries=0).changed(**changes)

    def client(self, **changes):
        return claude.ClaudeClient(self.keys, self.settings(**changes), base_url=API.url)

    @staticmethod
    def path(recorded):
        return recorded.path.split('?')[0]


class RequestShape(Base):
    def test_default_request(self):
        API.queue(fake_api.text('Hello there'))
        self.client().ask('Say hi', system='Be brief.')

        sent = API.last
        self.assertEqual(self.path(sent), '/v1/messages')
        self.assertEqual(sent.headers['x-api-key'], 'sk-ant-test-key')
        self.assertIn('anthropic-version', sent.headers)

        body = sent.body
        self.assertEqual(body['model'], 'claude-opus-5-5')
        self.assertEqual(body['max_tokens'], 64000)
        self.assertIs(body['stream'], True)
        self.assertEqual(body['messages'], [{'role': 'user', 'content': 'Say hi'}])
        self.assertEqual(body['system'], 'Be brief.')
        self.assertEqual(body['output_config'], {'effort': 'medium'})
        self.assertEqual(body['cache_control'], {'type': 'ephemeral'})

    def test_parameters_these_models_reject_are_never_sent(self):
        API.queue(fake_api.text('x'))
        self.client().ask('hi', tools=[claude.Tool('t', 'd', {'type': 'object'}, lambda arguments: 1)])
        for name in ('temperature', 'top_p', 'top_k', 'thinking', 'tool_choice'):
            self.assertNotIn(name, API.last.body)

    def test_refusal_fallback_is_on_by_default(self):
        API.queue(fake_api.text('x'))
        self.client().ask('hi')
        sent = API.last
        self.assertIn('beta=true', sent.path)
        self.assertIn('server-side-fallback-2026-07-01', sent.headers['anthropic-beta'])
        self.assertEqual(sent.body['fallbacks'], 'default')

    def test_refusal_fallback_can_be_turned_off(self):
        API.queue(fake_api.text('x'))
        self.client(refusal_fallback=False).ask('hi')
        sent = API.last
        self.assertNotIn('beta=true', sent.path)
        self.assertNotIn('fallbacks', sent.body)
        self.assertNotIn('server-side-fallback-2026-07-01', sent.headers.get('anthropic-beta', ''))

    def test_haiku_never_gets_the_fallback(self):
        API.queue(fake_api.text('x', model='claude-haiku-5-5'))
        self.client(model='claude-haiku-5-5').ask('hi')
        self.assertNotIn('fallbacks', API.last.body)
        self.assertEqual(API.last.body['model'], 'claude-haiku-5-5')

    def test_per_call_overrides(self):
        API.queue(fake_api.text('x'))
        self.client().ask('hi', model='claude-sonnet-5-5', effort='high', max_tokens=2000)
        body = API.last.body
        self.assertEqual((body['model'], body['max_tokens'], body['output_config']['effort']),
                         ('claude-sonnet-5-5', 2000, 'high'))

    def test_a_bad_override_is_refused_before_anything_is_sent(self):
        with self.assertRaises(ValueError):
            self.client().ask('hi', effort='extreme')

        self.assertEqual(API.requests, [])

    def test_background_is_part_of_the_system_prompt(self):
        API.queue(fake_api.text('x'))
        self.client().ask('hi', system='You help.', context=[claude.StaticContext('Rules', 'Twist tight.')],
                          topic='twisting')
        self.assertEqual(API.last.body['system'], 'You help.\n\n# Background\n\n## Rules\nTwist tight.')

    def test_application_settings_apply_to_the_next_call(self):
        settings = _bootstrap.load('claude.settings')
        client = claude.ClaudeClient(self.keys, None, base_url=API.url)
        try:
            settings.update(max_retries=0, effort='high')
            API.queue(fake_api.text('x'))
            client.ask('hi')
            self.assertEqual(API.last.body['output_config']['effort'], 'high')

            settings.update(effort='low')
            API.queue(fake_api.text('x'))
            client.ask('hi')
            self.assertEqual(API.last.body['output_config']['effort'], 'low')
        finally:
            settings.set_backend(None)

    def test_a_changed_key_is_used_on_the_next_call(self):
        client = self.client()
        API.queue(fake_api.text('one'), fake_api.text('two'))
        client.ask('hi')
        self.keys.set_key('sk-ant-second-key')
        client.ask('hi')
        self.assertEqual([r.headers['x-api-key'] for r in API.requests], ['sk-ant-test-key', 'sk-ant-second-key'])


class Responses(Base):
    def test_text_usage_and_cost(self):
        API.queue(fake_api.text('Hello there', input_tokens=100, output_tokens=50, cache_read=10, cache_write=20))
        reply = self.client().ask('hi')

        self.assertEqual(reply.text, 'Hello there')
        self.assertEqual(reply.stop_reason, 'end_turn')
        self.assertEqual(reply.model, 'claude-opus-5-5')
        self.assertEqual(reply.usage, claude.Usage(100, 50, 10, 20))
        expected = (100 * 4.0 + 50 * 20.0 + 10 * 0.20 + 20 * 4.0 * 1.25) / 1_000_000
        self.assertAlmostEqual(reply.estimated_cost, expected)
        self.assertEqual(reply.rounds, 1)
        self.assertEqual(reply.request_id, 'req_fake_stream')
        self.assertEqual(reply.tool_calls, 0)
        self.assertFalse(reply.served_by_fallback)

    def test_text_arrives_piece_by_piece(self):
        API.queue(fake_api.text('A fairly long answer that arrives in many small pieces.'))
        pieces = []
        reply = self.client().ask('hi', on_text=pieces.append)
        self.assertGreater(len(pieces), 3)
        self.assertEqual(''.join(pieces), reply.text)

    def test_thinking_is_not_part_of_the_text(self):
        API.queue(fake_api.thinking_text('let me consider', 'The answer.'))
        self.assertEqual(self.client().ask('hi').text, 'The answer.')

    def test_the_client_keeps_a_running_total(self):
        client = self.client()
        API.queue(fake_api.text('a', input_tokens=10, output_tokens=5), fake_api.text('b', input_tokens=20, output_tokens=7))
        client.ask('one')
        client.ask('two')
        self.assertEqual(client.usage, claude.Usage(30, 12))

    def test_structured_output(self):
        schema = {'type': 'object', 'properties': {'layer': {'type': 'integer'}}, 'required': ['layer'],
                  'additionalProperties': False}
        API.queue(fake_api.text('{"layer": 2}'))
        reply = self.client().ask('which layer', output_schema=schema)

        self.assertEqual(reply.data, {'layer': 2})
        self.assertEqual(API.last.body['output_config'],
                         {'effort': 'medium', 'format': {'type': 'json_schema', 'schema': schema}})

    def test_structured_output_that_is_not_json(self):
        API.queue(fake_api.text('not json at all'))
        with self.assertRaises(claude.InvalidStructuredReply) as caught:
            self.client().ask('x', output_schema={'type': 'object'})

        self.assertIn('not json', caught.exception.details)

    def test_plain_answers_have_no_data(self):
        API.queue(fake_api.text('{"looks": "like json"}'))
        self.assertIsNone(self.client().ask('hi').data)

    def test_served_by_a_fallback_model(self):
        iterations = [
            {'type': 'message', 'input_tokens': 100, 'output_tokens': 3},
            {'type': 'fallback_message', 'input_tokens': 100, 'output_tokens': 40}]
        API.queue(fake_api.Reply(events=fake_api.message_events(
            [('fallback', 'claude-opus-5-5', 'claude-opus-4-8'), ('text', 'Answer.')],
            model='claude-opus-4-8', iterations=iterations)))
        reply = self.client().ask('hi')

        self.assertEqual(reply.text, 'Answer.')
        self.assertEqual(reply.model, 'claude-opus-4-8')
        self.assertEqual(reply.requested_model, 'claude-opus-5-5')
        self.assertTrue(reply.served_by_fallback)
        self.assertEqual(reply.usage.output_tokens, 43)


class Failures(Base):
    def assert_raises_for(self, reply, error_type):
        API.reset()
        API.queue(reply)
        with self.assertRaises(error_type) as caught:
            self.client().ask('hi')

        return caught.exception

    def test_no_key(self):
        self.keys.clear_key()
        with self.assertRaises(claude.NoApiKeyError):
            self.client().ask('hi')

        self.assertEqual(API.requests, [])

    def test_authentication(self):
        error = self.assert_raises_for(fake_api.error(401, 'authentication_error', 'invalid x-api-key'),
                                       claude.AuthenticationFailed)
        self.assertEqual(error.status_code, 401)
        self.assertEqual(error.request_id, 'req_fake')
        self.assert_raises_for(fake_api.error(403, 'permission_error', 'not allowed'), claude.AuthenticationFailed)

    def test_rate_limit(self):
        error = self.assert_raises_for(
            fake_api.error(429, 'rate_limit_error', 'slow down', {'retry-after': '12'}), claude.RateLimited)
        self.assertEqual(error.retry_after, 12.0)

    def test_server_errors(self):
        self.assert_raises_for(fake_api.error(500, 'api_error', 'oops'), claude.ServiceUnavailable)
        self.assert_raises_for(fake_api.error(529, 'overloaded_error', 'busy'), claude.ServiceUnavailable)

    def test_bad_requests(self):
        self.assert_raises_for(fake_api.error(400, 'invalid_request_error', 'messages: bad'), claude.BadRequest)
        self.assert_raises_for(fake_api.error(404, 'not_found_error', 'model: nope'), claude.BadRequest)
        self.assert_raises_for(fake_api.error(413, 'request_too_large', 'too big'), claude.BadRequest)

    def test_beta_not_enabled(self):
        error = self.assert_raises_for(
            fake_api.error(400, 'invalid_request_error',
                           'Unexpected value(s) `server-side-fallback-2026-07-01` for the `anthropic-beta` header.'),
            claude.BetaNotAvailable)
        self.assertIsInstance(error, claude.BadRequest)
        self.assertIn('Turn off', error.user_message)

    def test_no_connection(self):
        client = claude.ClaudeClient(self.keys, self.settings(), base_url='http://127.0.0.1:1')
        with self.assertRaises(claude.ServiceUnavailable):
            client.ask('hi')

    def test_refusal(self):
        API.queue(fake_api.refusal('bio', 'Not that kind of question.'))
        with self.assertRaises(claude.Refused) as caught:
            self.client().ask('hi')

        self.assertEqual(caught.exception.category, 'bio')
        self.assertIn('Not that kind', caught.exception.user_message)

    def test_running_out_of_room(self):
        API.queue(fake_api.text('half an ans', stop_reason='max_tokens'))
        with self.assertRaises(claude.Truncated):
            self.client().ask('hi')

    def test_the_sdk_retries_when_asked_to(self):
        API.queue(fake_api.error(500, 'api_error', 'oops'), fake_api.text('worked'))
        client = claude.ClaudeClient(self.keys, claude.ClaudeSettings(max_retries=1), base_url=API.url)
        self.assertEqual(client.ask('hi').text, 'worked')
        self.assertEqual(len(API.requests), 2)

    def test_every_failure_can_be_caught_as_a_claude_error(self):
        for reply in (fake_api.error(401, 'authentication_error', 'x'), fake_api.error(429, 'rate_limit_error', 'x'),
                      fake_api.error(500, 'api_error', 'x'), fake_api.error(400, 'invalid_request_error', 'x'),
                      fake_api.refusal()):
            API.reset()
            API.queue(reply)
            with self.assertRaises(claude.ClaudeError) as caught:
                self.client().ask('hi')

            self.assertTrue(caught.exception.user_message)


class Conversations(Base):
    def test_history_grows_and_thinking_is_sent_back_unchanged(self):
        chat = self.client().conversation(system='You help.')
        API.queue(fake_api.thinking_text('first thought', 'First answer.', signature='sig-abc'),
                  fake_api.text('Second answer.'))

        self.assertEqual(chat.send('one').text, 'First answer.')
        self.assertEqual(chat.send('two').text, 'Second answer.')

        second = API.requests[1].body
        self.assertEqual(second['system'], 'You help.')
        roles = [message['role'] for message in second['messages']]
        self.assertEqual(roles, ['user', 'assistant', 'user'])

        assistant = second['messages'][1]['content']
        self.assertEqual([block['type'] for block in assistant], ['thinking', 'text'])
        self.assertEqual(assistant[0]['signature'], 'sig-abc')
        self.assertEqual(assistant[0]['thinking'], 'first thought')
        self.assertEqual(second['messages'][2]['content'], 'two')

    def test_the_prefix_never_changes_between_sends(self):
        chat = self.client().conversation(
            system='Frozen.', context=[claude.StaticContext('Rules', 'r')],
            tools=[claude.Tool('b', 'd', {'type': 'object'}, lambda a: 1), claude.Tool('a', 'd', {'type': 'object'}, lambda a: 1)])
        API.queue(fake_api.text('1'), fake_api.text('2'), fake_api.text('3'))
        for prompt in ('x', 'y', 'z'):
            chat.send(prompt)

        first = API.requests[0].body
        for later in API.requests[1:]:
            self.assertEqual(later.body['system'], first['system'])
            self.assertEqual(later.body['tools'], first['tools'])
            self.assertEqual(later.body['model'], first['model'])

        self.assertEqual([tool['name'] for tool in first['tools']], ['a', 'b'])

    def test_notes_go_in_as_system_messages_after_the_users_message(self):
        chat = self.client().conversation(system='Frozen.')
        chat.note('The user chose the 7-wire core.')
        chat.note('  ')
        API.queue(fake_api.text('ok'), fake_api.text('ok again'))
        chat.send('Arrange them.')
        chat.send('And now?')

        first = API.requests[0].body
        self.assertEqual(first['system'], 'Frozen.')
        self.assertEqual(first['messages'], [
            {'role': 'user', 'content': 'Arrange them.'},
            {'role': 'system', 'content': 'The user chose the 7-wire core.'}])

        second = API.requests[1].body['messages']
        self.assertEqual([m['role'] for m in second], ['user', 'system', 'assistant', 'user'])

    def test_a_failed_send_leaves_the_conversation_as_it_was(self):
        chat = self.client().conversation()
        API.queue(fake_api.text('fine'), fake_api.error(500, 'api_error', 'oops'), fake_api.text('retry worked'))
        chat.send('one')
        chat.note('remember this')

        with self.assertRaises(claude.ServiceUnavailable):
            chat.send('two')

        self.assertEqual(chat.turns, 2)
        self.assertEqual(chat.send('two again').text, 'retry worked')

        retry = API.requests[2].body['messages']
        self.assertEqual([m['role'] for m in retry], ['user', 'assistant', 'user', 'system'])
        self.assertEqual(retry[2]['content'], 'two again')
        self.assertEqual(retry[3]['content'], 'remember this')

    def test_a_refusal_is_not_kept_either(self):
        chat = self.client().conversation()
        API.queue(fake_api.refusal())
        with self.assertRaises(claude.Refused):
            chat.send('hmm')

        self.assertEqual(chat.turns, 0)

    def test_usage_is_counted_even_for_a_failed_send(self):
        chat = self.client().conversation()
        API.queue(fake_api.text('half', stop_reason='max_tokens', input_tokens=11, output_tokens=22))
        with self.assertRaises(claude.Truncated):
            chat.send('x')

        self.assertEqual(chat.usage, claude.Usage(11, 22))

    def test_settings_are_fixed_when_the_conversation_starts(self):
        chat = self.client().conversation(effort='high')
        API.queue(fake_api.text('1'), fake_api.text('2'))
        chat.send('x')
        chat.send('y')
        self.assertEqual({r.body['output_config']['effort'] for r in API.requests}, {'high'})

    def test_duplicate_tool_names_are_refused(self):
        tool = claude.Tool('same', 'd', {'type': 'object'}, lambda a: 1)
        with self.assertRaises(ValueError):
            self.client().conversation(tools=[tool, tool])

    def test_only_one_send_at_a_time(self):
        chat = self.client().conversation()
        API.queue(fake_api.Reply(events=fake_api.message_events([('text', 'slow')]), event_delay=0.05),
                  fake_api.text('quick'))
        order = []

        def first():
            chat.send('a')
            order.append('a')

        thread = threading.Thread(target=first)
        thread.start()
        time.sleep(0.1)
        chat.send('b')
        order.append('b')
        thread.join()
        self.assertEqual(order, ['a', 'b'])
        self.assertEqual([m['role'] for m in API.requests[1].body['messages']], ['user', 'assistant', 'user'])


class ToolUse(Base):
    ADD = {'type': 'object', 'properties': {'a': {'type': 'integer'}, 'b': {'type': 'integer'}},
           'required': ['a', 'b'], 'additionalProperties': False}

    def add_tool(self, **options):
        self.calls = []

        def handler(arguments):
            self.calls.append(arguments)
            return {'sum': arguments['a'] + arguments['b']}

        return claude.Tool('add', 'Adds two integers.', self.ADD, handler, **options)

    def test_a_tool_round_trip(self):
        API.queue(fake_api.tools(('toolu_1', 'add', {'a': 2, 'b': 3}), thought='I should add.'),
                  fake_api.text('The sum is 5.'))
        seen = []
        reply = self.client().ask('2+3?', tools=[self.add_tool()],
                                  on_tool=lambda name, arguments, result, is_error: seen.append((name, arguments, result, is_error)))

        self.assertEqual(reply.text, 'The sum is 5.')
        self.assertEqual((reply.tool_calls, reply.rounds), (1, 2))
        self.assertEqual(self.calls, [{'a': 2, 'b': 3}])
        self.assertEqual(seen, [('add', {'a': 2, 'b': 3}, '{"sum": 5}', False)])

        second = API.requests[1].body['messages']
        self.assertEqual([m['role'] for m in second], ['user', 'assistant', 'user'])
        self.assertEqual([b['type'] for b in second[1]['content']], ['thinking', 'tool_use'])
        self.assertEqual(second[1]['content'][0]['signature'], 'sig-tool')
        self.assertEqual(second[2]['content'], [
            {'type': 'tool_result', 'tool_use_id': 'toolu_1', 'content': '{"sum": 5}'}])

    def test_the_tool_definition_is_sent(self):
        API.queue(fake_api.text('x'))
        self.client().ask('hi', tools=[self.add_tool(strict=True)])
        self.assertEqual(API.last.body['tools'], [{
            'name': 'add', 'description': 'Adds two integers.', 'input_schema': self.ADD, 'strict': True}])

    def test_several_tool_calls_in_one_turn_are_answered_together(self):
        API.queue(fake_api.tools(('toolu_1', 'add', {'a': 1, 'b': 1}), ('toolu_2', 'add', {'a': 2, 'b': 2})),
                  fake_api.text('done'))
        reply = self.client().ask('go', tools=[self.add_tool()])

        results = API.requests[1].body['messages'][2]['content']
        self.assertEqual([r['tool_use_id'] for r in results], ['toolu_1', 'toolu_2'])
        self.assertEqual(reply.tool_calls, 2)
        self.assertEqual(len(API.requests), 2)

    def test_a_tool_that_raises_is_reported_to_the_model(self):
        def broken(arguments):
            raise RuntimeError('the solver blew up')

        tool = claude.Tool('add', 'd', self.ADD, broken)
        API.queue(fake_api.tools(('toolu_1', 'add', {'a': 1, 'b': 2})), fake_api.text('sorry'))
        seen = []
        reply = self.client().ask('go', tools=[tool], on_tool=lambda *args: seen.append(args))

        result = API.requests[1].body['messages'][2]['content'][0]
        self.assertTrue(result['is_error'])
        self.assertIn('RuntimeError: the solver blew up', result['content'])
        self.assertTrue(seen[0][3])
        self.assertEqual(reply.text, 'sorry')

    def test_an_unknown_tool_is_reported_to_the_model(self):
        API.queue(fake_api.tools(('toolu_1', 'nope', {})), fake_api.text('ok'))
        self.client().ask('go', tools=[self.add_tool()])
        result = API.requests[1].body['messages'][2]['content'][0]
        self.assertTrue(result['is_error'])
        self.assertIn("'nope'", result['content'])

    def test_a_runaway_loop_is_stopped(self):
        API.queue(*[fake_api.tools((f'toolu_{n}', 'add', {'a': 1, 'b': 1})) for n in range(5)])
        chat = self.client().conversation(tools=[self.add_tool()], max_tool_rounds=3)
        with self.assertRaises(claude.ToolLoopLimit):
            chat.send('go')

        self.assertEqual(len(API.requests), 3)
        self.assertEqual(chat.turns, 0)

    def test_a_cut_off_tool_call_is_never_run(self):
        API.queue(fake_api.Reply(events=fake_api.message_events(
            [('tool', 'toolu_1', 'add', {'a': 1, 'b': 1})], stop_reason='max_tokens')))
        with self.assertRaises(claude.Truncated):
            self.client().ask('go', tools=[self.add_tool()])

        self.assertEqual(self.calls, [])

    def test_a_tool_can_cancel_the_call(self):
        token = claude.CancelToken()

        def handler(arguments):
            token.cancel()
            return 'x'

        tool = claude.Tool('add', 'd', self.ADD, handler)
        API.queue(fake_api.tools(('toolu_1', 'add', {'a': 1, 'b': 1}), ('toolu_2', 'add', {'a': 1, 'b': 1})))
        with self.assertRaises(claude.Cancelled):
            self.client().ask('go', tools=[tool], cancel=token)

        self.assertEqual(len(API.requests), 1)

    def test_results_that_are_not_text_are_encoded_as_json(self):
        tool = claude.Tool('add', 'd', self.ADD, lambda arguments: [1, 2, {'k': None}])
        API.queue(fake_api.tools(('toolu_1', 'add', {'a': 1, 'b': 1})), fake_api.text('ok'))
        self.client().ask('go', tools=[tool])
        self.assertEqual(API.requests[1].body['messages'][2]['content'][0]['content'], '[1, 2, {"k": null}]')

    def test_fallback_turns_are_cleaned_before_they_are_sent_back(self):
        API.queue(
            fake_api.Reply(events=fake_api.message_events(
                [('thinking', 'first model thought', 'sig-old'), ('text', 'Partial. '),
                 ('fallback', 'claude-opus-5-5', 'claude-opus-4-8'),
                 ('tool', 'toolu_1', 'add', {'a': 1, 'b': 1})], stop_reason='tool_use', model='claude-opus-4-8')),
            fake_api.text('done'))
        self.client().ask('go', tools=[self.add_tool()])

        assistant = API.requests[1].body['messages'][1]['content']
        self.assertEqual([block['type'] for block in assistant], ['text', 'tool_use'])
        self.assertEqual(assistant[0]['text'], 'Partial. ')


class Cancelling(Base):
    def slow_reply(self):
        return fake_api.Reply(events=fake_api.message_events([('text', 'x' * 400)]), event_delay=0.2)

    def test_cancelling_a_call_that_is_waiting_for_the_next_piece(self):
        API.queue(self.slow_reply())
        token = claude.CancelToken()
        threading.Timer(0.4, token.cancel).start()

        started = time.monotonic()
        with self.assertRaises(claude.Cancelled):
            self.client().ask('hi', cancel=token)

        self.assertLess(time.monotonic() - started, 3.0)

    def test_cancelling_before_starting(self):
        token = claude.CancelToken()
        token.cancel()
        with self.assertRaises(claude.Cancelled):
            self.client().ask('hi', cancel=token)

        self.assertEqual(API.requests, [])

    def test_a_cancelled_send_is_not_kept(self):
        chat = self.client().conversation()
        API.queue(self.slow_reply())
        token = claude.CancelToken()
        threading.Timer(0.3, token.cancel).start()
        with self.assertRaises(claude.Cancelled):
            chat.send('x', cancel=token)

        self.assertEqual(chat.turns, 0)

    def test_cancel_is_raised_from_the_text_callback_too(self):
        API.queue(self.slow_reply())
        token = claude.CancelToken()
        with self.assertRaises(claude.Cancelled):
            self.client().ask('hi', cancel=token, on_text=lambda piece: token.cancel())


class CheckConnection(Base):
    def test_a_cheap_real_request(self):
        API.queue(fake_api.text('OK'))
        reply = self.client().check_connection()
        self.assertEqual(reply.text, 'OK')
        self.assertEqual(API.last.body['output_config']['effort'], 'low')
        self.assertEqual(API.last.body['max_tokens'], 1024)


if __name__ == '__main__':
    unittest.main()
