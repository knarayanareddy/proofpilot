"""Shared test harness: a temporary data directory and a live demo portal in a thread.

Imported by every test module. Not collected by unittest (filename does not match test*.py).
"""
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib import request, error

_temp = tempfile.TemporaryDirectory()
os.environ['PROOFPILOT_DATA_DIR'] = _temp.name
os.environ['PROOFPILOT_SECRET'] = 'test-only-secret'

from portal import server  # noqa: E402  (env must be set before import)


class PortalTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.init_db(True)
        cls.http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.base = 'http://127.0.0.1:' + str(cls.http.server_port)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()

    def call(self, path, method='GET', body=None, token=None, headers=None):
        hdr = {'Content-Type': 'application/json', **(headers or {})}
        if token:
            hdr['Authorization'] = 'Bearer ' + token
        req = request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, method=method, headers=hdr)
        try:
            with request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read())
        except error.HTTPError as e:
            return e.code, json.loads(e.read())

    def setUp(self):
        self.call('/demo/reset', 'POST', {})
        _, self.run = self.call('/demo/runs', 'POST', {})
        self.viewer = self.run['viewer_token']
        self.verifier = self.run['verifier_token']

    def grant(self, req='REQ-001', supplier='SUP-1001', approval=None):
        b = {'run_id': self.run['run_id'], 'request_id': req, 'supplier_id': supplier}
        if approval:
            b['approval_id'] = approval
        return self.call('/demo/grant', 'POST', b)

    def read(self, id='SUP-1001', token=None):
        return self.call('/portal/api/suppliers/' + id, token=token or self.verifier)[1]

    def write(self, token, body, id='SUP-1001'):
        return self.call('/portal/api/suppliers/' + id, 'PATCH', body, token)

    def valid(self, key='one', version=1):
        return {'shipping_address': '12 Canal Road, Amsterdam', 'expected_version': version, 'idempotency_key': key}

    def approval(self, id='SUP-2001', version=1):
        return self.call('/demo/approve', 'POST', {'run_id': self.run['run_id'], 'request_id': 'REQ-002', 'supplier_id': id,
                                                   'contract_hash': self.run['contract_hash'], 'record_version': version})

    def task(self, csv=None):
        body = {'instruction': 'Update supplier shipping addresses from the approved CSV.',
                'csv_text': server.CSV_TEXT if csv is None else csv}
        return self.call('/api/tasks', 'POST', body)

    def prepared_workflow(self):
        status, task = self.task()
        self.assertEqual(status, 201)
        self.assertEqual(self.call('/api/tasks/' + task['task_id'] + '/runs', 'POST', {})[0], 409)
        self.assertEqual(self.call('/api/tasks/' + task['task_id'] + '/approve', 'POST', {'contract_hash': 'stale'})[0], 409)
        self.assertEqual(self.call('/api/tasks/' + task['task_id'] + '/approve', 'POST', {'contract_hash': task['contract_hash']})[0], 200)
        status, run = self.call('/api/tasks/' + task['task_id'] + '/runs', 'POST', {})
        self.assertEqual(status, 201)
        return task, run
