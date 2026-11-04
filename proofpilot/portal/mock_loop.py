"""Deterministic mock loop: a fixed action script, no model inference.

Kept as an explicit fallback and for tests. It is never Meta-driven and the UI labels it as
mock. Shares isolation, attempt and commit rules with the real loop in portal/sandbox.py.
"""
import hashlib
import json
import shutil  # noqa: F401  (re-exported; tests patch shutil.which to simulate a missing Bubblewrap)
import uuid

try:
    from . import executor, sandbox
except ImportError:
    import executor
    import sandbox

MAX_STEPS = 6


class MockModel:
    """Fixed action list; a stand-in for a model, not an imitation of one."""

    def __init__(self, expected, actions=None):
        self.expected = expected
        self.actions = actions or [{'type': 'focus_shipping'}, {'type': 'fill_shipping', 'value': expected}, {'type': 'submit_shipping'}]
        self.index = 0

    def propose(self, observation):
        if not observation.get('screenshot_sha256'):
            raise executor.ExecutorError(400, 'Missing observation')
        if self.index >= len(self.actions):
            return {'type': 'finish'}
        action = self.actions[self.index]
        self.index += 1
        return action


def run(c, run_id, request_id, server, probe_port, model=None, fault=None):
    run, src, rec, cap = executor.authorize(c, run_id, request_id, server)
    cap['execution_mode'] = 'mock_model_browser'
    trace = 'trace-' + uuid.uuid4().hex[:12]
    key = run_id + ':' + request_id + ':mock-v1'
    attempt = sandbox.begin_attempt(c, run_id, request_id, key, rec['version'], src['new_shipping_address'], rec['id'])
    events = []

    def event(kind, **kwargs):
        events.append({'event': kind, **kwargs})

    event('restricted_fields_before', bank_account_sha256=hashlib.sha256(rec['bank_account'].encode()).hexdigest(),
          tax_id_sha256=hashlib.sha256(rec['tax_id'].encode()).hexdigest(), record_version=rec['version'],
          source='server-side demo portal pre-write snapshot')
    proc = None
    status = 'STOPPED'
    try:
        proc = sandbox.spawn_worker(server, probe_port)
        response = sandbox.send(proc, {'html': sandbox.make_html(rec), 'probe_port': probe_port})
        boundary = response['boundary']
        event('os_isolation_probe', **boundary)
        if not (boundary['host_port_unreachable'] and boundary['external_unreachable'] and boundary['system_readonly'] and boundary['workspace_inaccessible'] and boundary['model_key_absent']):
            raise executor.ExecutorError(503, 'OS isolation probe failed; no execution allowed.')
        model = model or MockModel(src['new_shipping_address'])
        for step in range(MAX_STEPS):
            png = sandbox.decode_png(response['screenshot'])
            obs = {'screenshot_sha256': sandbox.sha256(png), 'step': step}
            event('observation', step=step, screenshot_sha256=obs['screenshot_sha256'])
            action = model.propose(obs)
            # Never log typed values, capability or untrusted markup.
            kind = executor.check_action(action, src['new_shipping_address'])
            event('policy_decision', step=step, action=kind, decision='allow')
            # Re-check run/row/approval before every action; fails closed on cancellation or stale state.
            executor.authorize(c, run_id, request_id, server, attempt_id=attempt)
            response = sandbox.send(proc, {'command': kind, **({'value': action['value']} if kind == 'fill_shipping' else {})})
            if kind == 'submit_shipping':
                if response.get('input_value') != src['new_shipping_address']:
                    raise executor.ExecutorError(403, 'Browser value does not match contract')
                png = sandbox.decode_png(response['screenshot'])
                event('browser_screenshot', sha256=sandbox.sha256(png), artifact=sandbox.store_screenshot(server, trace, png))
                if fault == 'cancel_before_write':
                    server.workflow.cancel(c, run_id, server.Problem)
                    sandbox.set_attempt(c, attempt, 'CANCELLED_BEFORE_WRITE')
                    event('cancelled', phase='before_write')
                    status = 'CANCELLED_BEFORE_WRITE'
                    break
                sandbox.set_attempt(c, attempt, 'IN_FLIGHT')
                if fault == 'timeout_before_commit':
                    raise TimeoutError('simulated unknown in-flight state')
                try:
                    _, result = server.patch_supplier(c, rec['id'], cap, {'shipping_address': src['new_shipping_address'], 'expected_version': rec['version'], 'idempotency_key': key}, uuid.uuid4().hex)
                    event('portal_write', status=200, portal_request_id=result['request_id'])
                    if fault == 'disconnect_after_commit':
                        raise TimeoutError('simulated lost acknowledgement')
                    sandbox.set_attempt(c, attempt, 'WRITTEN_UNVERIFIED')
                    status = 'WRITTEN_UNVERIFIED'
                except server.Problem as err:
                    event('portal_write', status=err.status, error=err.message)
                    if err.status == 503:
                        c.execute("UPDATE workflow_rows SET status='FAILED' WHERE run_id=? AND request_id=? AND status='READY_TO_WRITE'", (run_id, request_id))
                        sandbox.set_attempt(c, attempt, 'FAILED')
                        status = 'FAILED'
                    else:
                        sandbox.set_attempt(c, attempt, 'STOPPED')
                        status = 'STOPPED'
                break
        else:
            raise executor.ExecutorError(429, 'Maximum mock steps exceeded')
    except Exception as err:
        current = c.execute('SELECT status FROM execution_attempts WHERE id=?', (attempt,)).fetchone()['status']
        if current == 'IN_FLIGHT':
            rec_result = sandbox.reconcile(c, attempt, server)
            status = rec_result['status']
            event('reconciled', status=status, retry_performed=False)
            if status == 'WRITTEN_UNVERIFIED':
                # Record durable committed result needed by verification, not a fabricated model action.
                hit = c.execute('SELECT response_json FROM idempotency WHERE run_id=? AND idem_key=?', (run_id, key)).fetchone()
                result = json.loads(hit['response_json'])
                event('portal_write', status=200, portal_request_id=result['request_id'], source='durable idempotency reconciliation')
            elif status == 'UNKNOWN_WRITE_STATE':
                c.execute("UPDATE workflow_rows SET status='UNKNOWN_WRITE_STATE' WHERE run_id=? AND request_id=? AND status='READY_TO_WRITE'", (run_id, request_id))
        else:
            status = 'STOPPED'
            sandbox.set_attempt(c, attempt, 'STOPPED')
        event('execution_stopped', error_type=type(err).__name__,
              reason=str(err) if isinstance(err, executor.ExecutorError) else 'Interruption; no blind retry')
    finally:
        sandbox.shutdown(proc)
    sandbox.save_trace(c, trace, run_id, request_id, 'mock_model_browser', status, events)
    return {'trace_id': trace, 'attempt_id': attempt, 'run_id': run_id, 'request_id': request_id, 'mode': 'mock_model_browser',
            'status': status, 'events': events, 'notice': 'Deterministic mock model; no Meta API call. Writes require separate verification.'}


install = sandbox.install
reconcile = sandbox.reconcile
