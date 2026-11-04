"""Tests for the real Meta computer-use loop.

The provider is replaced by a scripted transport that speaks the documented Responses API
shape, so these tests exercise ProofPilot's own request building, response validation,
coordinate resolution, policy denial and commit path. They do NOT prove anything about the
real model: a live run with MODEL_API_KEY is still required before claiming real evaluation.
"""
import hashlib
import io
import json
import os
import unittest
from unittest.mock import patch

from harness import PortalTestCase, server
from portal import executor, meta_agent, sandbox

EXPECTED = '12 Canal Road, Amsterdam'


class FakeResponse:
    def __init__(self, payload, request_id='provider-req-test'):
        self._payload = json.dumps(payload).encode()
        self.headers = {'x-request-id': request_id}

    def read(self, limit=None):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeTransport:
    """Returns scripted payloads in order and records every request body."""

    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.bodies = []
        self.calls = 0

    def open(self, req, timeout=None):
        self.calls += 1
        self.bodies.append(json.loads(req.data))
        if not self.payloads:
            raise AssertionError('Meta loop made an unexpected extra request')
        payload = self.payloads.pop(0)
        if isinstance(payload, Exception):
            raise payload
        return FakeResponse(payload)


def computer_call(actions, call_id='call-1', pending=None, response_id='resp-1'):
    return {'id': response_id, 'output': [{'type': 'computer_call', 'call_id': call_id, 'actions': actions,
                                           'pending_safety_checks': pending or []}],
            'usage': {'input_tokens': 100, 'output_tokens': 20}}


def click(x, y):
    return {'type': 'click', 'x': x, 'y': y}


def type_text(text):
    return {'type': 'type', 'text': text}


class MetaLoopTests(PortalTestCase):
    def supplier_html_and_boxes(self):
        """Render the exact page the worker renders, in the same sandbox, to read element boxes."""
        c = server.conn()
        try:
            rec = c.execute("SELECT * FROM suppliers WHERE id='SUP-1001'").fetchone()
        finally:
            c.close()
        html = sandbox.make_html(rec)
        proc = sandbox.spawn_worker(server, self.http.server_port)
        try:
            response = sandbox.send(proc, {'html': html, 'probe_port': self.http.server_port})
        finally:
            sandbox.shutdown(proc)
        elements = response.get('elements') or {}
        self.assertTrue(elements.get('shipping') and elements.get('save'), 'approved elements must be resolvable')
        return html, elements

    def centers(self, elements):
        def center(box):
            return box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
        return center(elements['shipping']), center(elements['save'])

    def without_key(self):
        """Isolate the key lookup from the developer's real environment or stored key file."""
        import contextlib
        import tempfile
        from pathlib import Path as _P
        holder = tempfile.TemporaryDirectory()
        missing = _P(holder.name) / 'absent-key'

        @contextlib.contextmanager
        def ctx():
            with patch.dict(os.environ, {}, clear=True), patch.object(meta_agent, 'KEY_FILE', missing):
                yield
            holder.cleanup()
        return ctx()

    def run_meta(self, transport, request_id='REQ-001', fault=None):
        task, run = self.prepared_workflow()
        c = server.conn()
        try:
            with patch.dict(os.environ, {'MODEL_API_KEY': 'test-key'}):
                result = meta_agent.run(c, run['run_id'], request_id, server, self.http.server_port, transport=transport, fault=fault)
        finally:
            c.close()
        return task, run, result

    def test_resolve_batch_maps_only_approved_semantics(self):
        elements = {'shipping': {'x': 10, 'y': 10, 'width': 100, 'height': 20}, 'save': {'x': 10, 'y': 40, 'width': 60, 'height': 20}}
        plan, denied = meta_agent.resolve_batch([{'type': 'click', 'x': 20, 'y': 15}, type_text(EXPECTED), {'type': 'click', 'x': 20, 'y': 45}],
                                                elements, EXPECTED, '')
        self.assertIsNone(denied)
        self.assertEqual([p['semantic'] for p in plan], ['focus_shipping', 'type_shipping', 'submit_shipping'])
        for case in ([{'type': 'click', 'x': 900, 'y': 600}], [type_text('attacker')], [{'type': 'navigate', 'url': 'https://evil.invalid'}],
                     [{'type': 'keypress', 'keys': ['ctrl', 'l']}], [type_text(EXPECTED), {'type': 'click', 'x': 20, 'y': 45}, type_text('more')],
                     [{'type': 'click'}], [{'type': 'keypress', 'keys': ['enter']}]):
            with self.subTest(case=case):
                _, denied = meta_agent.resolve_batch(case, elements, EXPECTED, '')
                self.assertIsNotNone(denied, case)
        # Chunked typing is allowed while it stays a prefix of the approved value.
        plan, denied = meta_agent.resolve_batch([type_text(EXPECTED[:5]), type_text(EXPECTED[5:])], elements, EXPECTED, '')
        self.assertIsNone(denied)
        self.assertEqual([p['semantic'] for p in plan], ['type_shipping', 'type_shipping'])
        # Enter submits only when the field already holds the approved value.
        plan, denied = meta_agent.resolve_batch([{'type': 'keypress', 'keys': ['enter']}], elements, EXPECTED, EXPECTED)
        self.assertIsNone(denied)
        self.assertEqual(plan[0]['semantic'], 'submit_shipping')

    def test_status_reports_configuration_without_exposing_key(self):
        with self.without_key():
            state = meta_agent.status()
            self.assertFalse(state['configured'])
            self.assertEqual(state['model'], meta_agent.MODEL)
        with self.without_key(), patch.dict(os.environ, {'MODEL_API_KEY': 'secret-value'}):
            state = meta_agent.status()
            self.assertTrue(state['configured'])
            self.assertFalse(state['worker_has_key'])
            self.assertNotIn('secret-value', json.dumps(state))

    def test_stored_key_file_is_used_but_never_returned(self):
        import tempfile
        from pathlib import Path as _P
        with tempfile.TemporaryDirectory() as folder:
            target = _P(folder) / 'key'
            target.write_text('file-based-secret', encoding='utf-8')
            with patch.dict(os.environ, {}, clear=True), patch.object(meta_agent, 'KEY_FILE', target):
                self.assertEqual(meta_agent.api_key(), 'file-based-secret')
                state = meta_agent.status()
                self.assertTrue(state['configured'])
                self.assertEqual(state['key_source'], 'local_file')
                self.assertNotIn('file-based-secret', json.dumps(state))

    def test_computer_tool_rejection_falls_back_to_vision_planner(self):
        """When the provider rejects the computer tool, the run continues on the vision planner."""
        import urllib.error
        _, elements = self.supplier_html_and_boxes()
        shipping, save = self.centers(elements)

        def planner_response(action, value=None, call_id='call-p1'):
            args = {'action': action} if value is None else {'action': action, 'value': value}
            return {'id': 'resp-p1', 'output': [{'type': 'function_call', 'call_id': call_id, 'name': 'propose_action', 'arguments': json.dumps(args)}]}

        class RejectFirst(FakeTransport):
            def open(self, req, timeout=None):
                body = json.loads(req.data)
                tools = body.get('tools') or []
                if any(t.get('type') == 'computer' for t in tools):
                    self.calls += 1
                    message = b'{"error":{"message":"Unsupported tool type: ' + b"'" + b'computer' + b"'" + b'}"}}'
                    raise urllib.error.HTTPError(req.full_url, 400, 'Bad Request', {}, io.BytesIO(message))
                return super().open(req, timeout)

        transport = RejectFirst([planner_response('focus_shipping'), planner_response('fill_shipping', '12 Canal Road, Amsterdam'), planner_response('submit_shipping')])
        task, run, result = self.run_meta(transport)
        self.assertEqual(result['status'], 'WRITTEN_UNVERIFIED')
        self.assertEqual(result['protocol'], 'vision_function_tool')
        self.assertTrue(any(e['event'] == 'protocol_fallback' for e in result['events']))
        self.assertEqual(self.read()['shipping_address'], '12 Canal Road, Amsterdam')
        status, verified = self.call('/api/runs/' + run['run_id'] + '/rows/REQ-001/verify', 'POST', {})
        self.assertEqual((status, verified['status']), (200, 'VERIFIED'))

    def test_no_key_makes_no_request_and_changes_nothing(self):
        _, elements = self.supplier_html_and_boxes()
        shipping, save = self.centers(elements)
        task, run = self.prepared_workflow()
        transport = FakeTransport([computer_call([click(*shipping)]), computer_call([type_text(EXPECTED)]), computer_call([click(*save)])])
        c = server.conn()
        try:
            with self.without_key():
                with self.assertRaises(meta_agent.MetaError) as err:
                    meta_agent.run(c, run['run_id'], 'REQ-001', server, self.http.server_port, transport=transport)
        finally:
            c.close()
        self.assertEqual(err.exception.status, 503)
        self.assertEqual(transport.calls, 0, 'no provider request may be attempted without a key')
        self.assertEqual(self.read()['shipping_address'], '1 Old Quay, Amsterdam')

    def test_approved_actions_write_and_verify(self):
        _, elements = self.supplier_html_and_boxes()
        shipping, save = self.centers(elements)
        transport = FakeTransport([computer_call([click(*shipping)]),
                                   computer_call([type_text(EXPECTED)]),
                                   computer_call([click(*save)])])
        task, run, result = self.run_meta(transport)
        self.assertEqual(result['mode'], 'meta_computer_use')
        self.assertEqual(result['status'], 'WRITTEN_UNVERIFIED')
        self.assertEqual(result['stop_reason'], 'submitted')
        self.assertEqual(self.read()['shipping_address'], EXPECTED)
        self.assertEqual(self.read()['version'], 2)
        # Requests follow the documented computer-use protocol.
        self.assertEqual(transport.bodies[0]['tools'], [{'type': 'computer'}])
        self.assertEqual(transport.bodies[1]['input'][0]['type'], 'computer_call_output')
        self.assertEqual(transport.bodies[1]['input'][0]['call_id'], 'call-1')
        self.assertEqual(transport.bodies[1]['input'][0]['output']['type'], 'computer_screenshot')
        # Provenance is recorded; the key and typed text are not.
        raw = json.dumps(result['events'])
        self.assertNotIn('test-key', raw)
        self.assertNotIn('Bearer', raw)
        self.assertNotIn(EXPECTED, raw, 'approved value is executed but not duplicated into the trace')
        self.assertTrue(any(e['event'] == 'meta_call' and e['provider_request_id'] == 'provider-req-test' for e in result['events']))
        self.assertTrue(any(e['event'] == 'model_actions' and all(a['decision'] == 'allow' for a in e['actions']) for e in result['events']))
        self.assertTrue(any(e['event'] == 'portal_write' and e['status'] == 200 for e in result['events']))
        self.assertTrue(any(e['event'] == 'os_isolation_probe' and e['model_key_absent'] for e in result['events']))
        status, verified = self.call('/api/runs/' + run['run_id'] + '/rows/REQ-001/verify', 'POST', {})
        self.assertEqual(status, 200, verified)
        self.assertEqual(verified['status'], 'VERIFIED')
        self.assertEqual(verified['observed_raw'], EXPECTED)
        self.assertEqual(verified['restricted_fields']['bank_account']['status'], 'unchanged')

    def test_click_outside_approved_targets_is_denied_before_any_write(self):
        _, elements = self.supplier_html_and_boxes()
        shipping, _ = self.centers(elements)
        transport = FakeTransport([computer_call([click(*shipping)]), computer_call([click(5, 5)]), computer_call([click(2000, 2000)])])
        task, run, result = self.run_meta(transport)
        self.assertEqual(result['status'], 'STOPPED')
        self.assertEqual(result['stop_reason'], 'policy_denied')
        self.assertEqual(self.read()['shipping_address'], '1 Old Quay, Amsterdam')
        denial = next(e for e in result['events'] if e['event'] == 'policy_denied')
        self.assertIn('outside', denial['reason'])
        self.assertEqual(denial['actions'], [{'type': 'click'}])

    def test_untrusted_instruction_text_cannot_change_the_value(self):
        _, elements = self.supplier_html_and_boxes()
        shipping, save = self.centers(elements)
        transport = FakeTransport([computer_call([click(*shipping)]),
                                   computer_call([type_text('attacker bank details')]),
                                   computer_call([click(*save)])])
        task, run, result = self.run_meta(transport)
        self.assertEqual(result['status'], 'STOPPED')
        self.assertEqual(result['stop_reason'], 'policy_denied')
        self.assertEqual(self.read()['shipping_address'], '1 Old Quay, Amsterdam')
        self.assertEqual(self.read()['version'], 1)
        self.assertEqual(transport.calls, 2, 'execution stops as soon as a batch is denied')

    def test_pending_safety_checks_are_never_auto_acknowledged(self):
        _, elements = self.supplier_html_and_boxes()
        shipping, save = self.centers(elements)
        transport = FakeTransport([computer_call([click(*shipping), type_text(EXPECTED), click(*save)],
                                                 pending=[{'id': 'check-1', 'code': 'malicious_instruction'}])])
        task, run, result = self.run_meta(transport)
        self.assertEqual(result['status'], 'STOPPED')
        self.assertEqual(result['stop_reason'], 'pending_safety_checks')
        self.assertEqual(self.read()['shipping_address'], '1 Old Quay, Amsterdam')
        denial = next(e for e in result['events'] if e['event'] == 'policy_denied')
        self.assertEqual(denial['reason'], 'pending_safety_checks')
        self.assertNotIn('acknowledged_safety_checks', json.dumps(transport.bodies))

    def test_malformed_provider_responses_stop_execution(self):
        _, elements = self.supplier_html_and_boxes()
        shipping, save = self.centers(elements)
        for payload in ({'output': []},
                        {'output': [{'type': 'computer_call', 'actions': []}]},
                        {'output': [{'type': 'computer_call', 'call_id': 'c', 'actions': [{'type': 'click', 'x': 1, 'y': 1}] * 13}]},
                        {'output': [{'type': 'computer_call', 'call_id': 'c', 'actions': 'not-a-list'}]},
                        {'output': 'not-a-list'}):
            with self.subTest(payload=str(payload)[:60]):
                transport = FakeTransport([payload])
                task, run, result = self.run_meta(transport)
                self.assertEqual(result['status'], 'STOPPED')
                self.assertEqual(self.read()['shipping_address'], '1 Old Quay, Amsterdam')
                self.assertTrue(any(e['event'] == 'execution_stopped' for e in result['events']))

    def test_cancel_before_write_and_unknown_state_never_retry(self):
        _, elements = self.supplier_html_and_boxes()
        shipping, save = self.centers(elements)
        script = lambda: [computer_call([click(*shipping)]), computer_call([type_text(EXPECTED)]), computer_call([click(*save)])]
        task, run, result = self.run_meta(FakeTransport(script()), fault='cancel_before_write')
        self.assertEqual(result['status'], 'CANCELLED_BEFORE_WRITE')
        self.assertEqual(self.read()['version'], 1)
        task, run, result = self.run_meta(FakeTransport(script()), fault='timeout_before_commit')
        self.assertEqual(result['status'], 'UNKNOWN_WRITE_STATE')
        self.assertEqual(self.read()['version'], 1)
        c = server.conn()
        try:
            again = sandbox.reconcile(c, result['attempt_id'], server)
        finally:
            c.close()
        self.assertFalse(again['retry_performed'])
        self.assertEqual(again['status'], 'UNKNOWN_WRITE_STATE')

    def test_ambiguous_row_cannot_be_executed_by_the_model(self):
        _, elements = self.supplier_html_and_boxes()
        transport = FakeTransport([computer_call([click(0, 0)])])
        task, run = self.prepared_workflow()
        c = server.conn()
        try:
            with patch.dict(os.environ, {'MODEL_API_KEY': 'test-key'}):
                with self.assertRaises(executor.ExecutorError):
                    meta_agent.run(c, run['run_id'], 'REQ-002', server, self.http.server_port, transport=transport)
        finally:
            c.close()
        self.assertEqual(transport.calls, 0)


    def test_endpoint_requires_confirmation_and_reports_missing_key(self):
        _, elements = self.supplier_html_and_boxes()
        shipping, save = self.centers(elements)
        task, run = self.prepared_workflow()
        path = '/api/runs/' + run['run_id'] + '/rows/REQ-001/execute-meta'
        self.assertEqual(self.call(path, 'POST', {})[0], 400)
        with self.without_key():
            status, body = self.call(path, 'POST', {'confirm': 'execute-real-meta-computer-use'})
        self.assertEqual(status, 503)
        self.assertIn('No Meta API key is configured', body['error'])
        self.assertEqual(self.read()['shipping_address'], '1 Old Quay, Amsterdam')

    def test_key_file_roundtrip_is_masked_and_permissions_tight(self):
        import tempfile
        from pathlib import Path as _P
        with tempfile.TemporaryDirectory() as folder:
            target = _P(folder) / 'key'
            with patch.object(meta_agent, 'KEY_FILE', target), patch.dict(os.environ, {}, clear=True):
                self.assertFalse(meta_agent.status()['configured'])
                state = meta_agent.save_key('fixture-secret-key-value')
                self.assertTrue(state['configured'])
                self.assertEqual(state['key_source'], 'local_file')
                self.assertEqual(state['key_fingerprint'], hashlib.sha256(b'fixture-secret-key-value').hexdigest()[:12])
                self.assertNotIn('fixture-secret-key-value', json.dumps(state))
                self.assertEqual(oct(target.stat().st_mode & 0o777), '0o600')
                self.assertEqual(meta_agent.api_key(), 'fixture-secret-key-value')
                with self.assertRaises(meta_agent.MetaError):
                    meta_agent.save_key('bad key with spaces')
                state = meta_agent.clear_key()
                self.assertFalse(state['configured'])
                self.assertFalse(target.exists())

    def test_key_endpoint_never_returns_the_key(self):
        import tempfile
        from pathlib import Path as _P
        with tempfile.TemporaryDirectory() as folder:
            target = _P(folder) / 'key'
            with patch.object(server, 'meta_agent', meta_agent), patch.object(meta_agent, 'KEY_FILE', target), patch.dict(os.environ, {}, clear=True):
                status, body = self.call('/api/meta/key', 'POST', {'key': 'endpoint-secret-value'})
                self.assertEqual(status, 200, body)
                self.assertTrue(body['configured'])
                self.assertNotIn('endpoint-secret-value', json.dumps(body))
                self.assertEqual(body['key_fingerprint'], hashlib.sha256(b'endpoint-secret-value').hexdigest()[:12])
                status, body = self.call('/api/meta/key', 'DELETE')
                self.assertEqual(status, 200)
                self.assertFalse(body['configured'])
                self.assertFalse(target.exists())

    def test_process_call_cap_blocks_further_requests(self):
        _, elements = self.supplier_html_and_boxes()
        shipping, save = self.centers(elements)
        task, run = self.prepared_workflow()
        c = server.conn()
        try:
            with patch.dict(os.environ, {'MODEL_API_KEY': 'test-key'}), patch.object(meta_agent, 'MAX_CALLS_PER_PROCESS', 1):
                meta_agent._call_count['attempts'] = 0
                with self.assertRaises(meta_agent.MetaError) as err:
                    meta_agent.run(c, run['run_id'], 'REQ-001', server, self.http.server_port,
                                   transport=FakeTransport([computer_call([click(*shipping)])]))
                self.assertEqual(err.exception.status, 429)
                # The stop is still recorded: a capped run leaves a trace instead of vanishing.
                self.assertEqual(c.execute("SELECT COUNT(*) FROM executor_traces WHERE run_id=? AND mode='meta_computer_use'", (run['run_id'],)).fetchone()[0], 1)
        finally:
            c.close()
            meta_agent._call_count['attempts'] = 0
        self.assertEqual(self.read()['shipping_address'], '1 Old Quay, Amsterdam')

    def test_endpoint_runs_loop_and_verification_through_http(self):
        _, elements = self.supplier_html_and_boxes()
        shipping, save = self.centers(elements)
        payloads = [computer_call([click(*shipping)]), computer_call([type_text(EXPECTED)]), computer_call([click(*save)])]
        calls = []

        def fake_request(body, key, transport=None):
            calls.append(body)
            return payloads.pop(0), 'provider-req-endpoint'

        task, run = self.prepared_workflow()
        with patch.dict(os.environ, {'MODEL_API_KEY': 'test-key'}), patch.object(meta_agent, 'request', side_effect=fake_request):
            status, result = self.call('/api/runs/' + run['run_id'] + '/rows/REQ-001/execute-meta', 'POST', {'confirm': 'execute-real-meta-computer-use'})
        self.assertEqual(status, 200, result)
        self.assertEqual(result['status'], 'WRITTEN_UNVERIFIED')
        self.assertEqual(result['mode'], 'meta_computer_use')
        self.assertEqual(len(calls), 3)
        status, verified = self.call('/api/runs/' + run['run_id'] + '/rows/REQ-001/verify', 'POST', {})
        self.assertEqual((status, verified['status']), (200, 'VERIFIED'))
        _, doc = self.call('/api/runs/' + run['run_id'] + '/evidence.json')
        self.assertEqual(doc['model_usage']['real_meta_runs'], 1)
        self.assertEqual(doc['model_usage']['provider_request_ids'], ['provider-req-endpoint'] * 3)
        self.assertTrue(any('scripted' in x or 'mock' in x for x in doc['limitations']))

if __name__ == "__main__":
    unittest.main()
