"""Shared plumbing for browser execution: Bubblewrap worker, attempts, durable reconciliation.

Extracted from the mock loop so the real Meta computer-use loop and the deterministic mock
loop use the identical isolation, attempt and commit rules. Everything here fails closed:
without Bubblewrap and browser files no worker is started, and no unsandboxed fallback exists.
"""
import base64
import hashlib
import html
import json
import os
import selectors
import shutil
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path

try:
    from . import executor
except ImportError:
    import executor


def install(c):
    c.execute('''CREATE TABLE IF NOT EXISTS execution_attempts(id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES workflow_runs(id),request_id TEXT NOT NULL,idempotency_key TEXT NOT NULL,expected_version INTEGER NOT NULL,expected_value TEXT NOT NULL,supplier_id TEXT NOT NULL,status TEXT NOT NULL,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)''')
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_unresolved_attempt ON execution_attempts(run_id,request_id) WHERE status IN ('PREPARED','IN_FLIGHT','UNKNOWN_WRITE_STATE')")


def spawn_worker(server, probe_port):
    bwrap = shutil.which('bwrap')
    browser_dir = Path(os.environ.get('PLAYWRIGHT_BROWSERS_PATH', str(Path.home() / '.cache/ms-playwright')))
    if not bwrap or not browser_dir.is_dir():
        raise executor.ExecutorError(503, 'Bubblewrap or Playwright browser files are missing; refusing unsandboxed execution.')
    worker = Path(__file__).resolve().with_name('sandbox_worker.py')
    command = [bwrap, '--die-with-parent', '--new-session', '--unshare-user', '--unshare-net', '--unshare-pid', '--unshare-ipc', '--unshare-uts', '--clearenv',
               '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64',
               '--dir', '/etc', '--ro-bind', '/etc/ld.so.cache', '/etc/ld.so.cache', '--ro-bind', '/etc/fonts', '/etc/fonts',
               '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/opt', '--ro-bind', str(worker), '/opt/worker.py',
               '--ro-bind', str(browser_dir), '/opt/browsers',
               '--setenv', 'HOME', '/tmp', '--setenv', 'PATH', '/usr/local/bin:/usr/bin:/bin', '--setenv', 'LANG', 'C.UTF-8', '--setenv', 'PLAYWRIGHT_BROWSERS_PATH', '/opt/browsers',
               '/usr/local/bin/python3', '-u', '/opt/worker.py']
    return subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1, env={'PATH': '/usr/local/bin:/usr/bin:/bin'})


def send(proc, command, timeout=20):
    proc.stdin.write(json.dumps(command) + '\n')
    proc.stdin.flush()
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    try:
        if not sel.select(timeout):
            raise executor.ExecutorError(504, 'Sandbox worker timeout; stopping.')
        line = proc.stdout.readline()
    finally:
        sel.close()
    if not line or len(line) > 4_000_000:
        raise executor.ExecutorError(503, 'Sandbox worker stopped or emitted oversized output.')
    try:
        response = json.loads(line)
    except ValueError:
        raise executor.ExecutorError(503, 'Malformed sandbox worker response.')
    if not response.get('ok'):
        raise executor.ExecutorError(503, 'Sandbox worker failed; no unsafe fallback.')
    return response


def make_html(rec):
    esc = lambda x: html.escape(str(x), quote=True)
    return '''<!doctype html><meta charset="utf-8"><title>Fictional task view</title><style>body{font:16px system-ui;background:#f6f7fb;padding:48px;color:#20283b}.card{background:white;padding:30px;max-width:720px;border:1px solid #e2e5ee;border-radius:14px}input{width:90%;font:16px system-ui;padding:12px}button{padding:12px;background:#443bd2;color:white;border:0;border-radius:8px}.note{background:#fff6e8;padding:10px}</style><div class="card"><h1>Fictional supplier record</h1><p>''' + esc(rec['name']) + ' · ' + esc(rec['id']) + '''</p><p class="note">Untrusted note: ''' + esc(rec['note']) + '''</p><label>Shipping address<br><input id="shipping" value="''' + esc(rec['shipping_address']) + '''"></label><p><button id="save" type="button">Submit through policy</button></p></div>'''


def begin_attempt(c, run_id, request_id, key, expected_version, expected_value, supplier_id):
    """Reserve a durable attempt; the unique partial index blocks concurrent unresolved attempts."""
    attempt = 'attempt-' + uuid.uuid4().hex[:12]
    now = int(time.time())
    try:
        c.execute('INSERT INTO execution_attempts VALUES(?,?,?,?,?,?,?,?,?,?)',
                  (attempt, run_id, request_id, key, expected_version, expected_value, supplier_id, 'PREPARED', now, now))
    except sqlite3.IntegrityError:
        raise executor.ExecutorError(409, 'Another attempt is active or unresolved; reconcile before retrying')
    return attempt


def set_attempt(c, attempt, status):
    c.execute('UPDATE execution_attempts SET status=?,updated_at=? WHERE id=?', (status, int(time.time()), attempt))


def reconcile(c, attempt_id, server):
    """Reconcile from durable target idempotency record; never perform another write."""
    c.execute('BEGIN IMMEDIATE')
    try:
        a = c.execute('SELECT * FROM execution_attempts WHERE id=?', (attempt_id,)).fetchone()
        if not a:
            raise executor.ExecutorError(404, 'Attempt not found')
        if a['status'] not in ('IN_FLIGHT', 'UNKNOWN_WRITE_STATE', 'CANCELLED_BEFORE_WRITE'):
            c.execute('COMMIT')
            return {'attempt_id': attempt_id, 'status': a['status'], 'retry_performed': False}
        hit = c.execute('SELECT * FROM idempotency WHERE run_id=? AND idem_key=?', (a['run_id'], a['idempotency_key'])).fetchone()
        if hit:
            result = json.loads(hit['response_json'])
            status = 'WRITTEN_UNVERIFIED' if result.get('supplier_id') == a['supplier_id'] and result.get('shipping_address') == a['expected_value'] else 'UNKNOWN_WRITE_STATE'
        elif a['status'] == 'CANCELLED_BEFORE_WRITE':
            status = 'CANCELLED_BEFORE_WRITE'
        else:
            status = 'UNKNOWN_WRITE_STATE'
        c.execute('UPDATE execution_attempts SET status=?,updated_at=? WHERE id=?', (status, int(time.time()), attempt_id))
        c.execute('COMMIT')
        return {'attempt_id': attempt_id, 'status': status, 'retry_performed': False}
    except Exception:
        c.execute('ROLLBACK')
        raise


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def store_screenshot(server, trace, png):
    folder = server.DATA / 'artifacts'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (trace + '.png')).write_bytes(png)
    return 'artifacts/' + trace + '.png'


def decode_png(b64):
    try:
        png = base64.b64decode(b64, validate=True)
    except Exception:
        raise executor.ExecutorError(400, 'Invalid browser observation')
    if not png.startswith(b'\x89PNG\r\n\x1a\n') or len(png) > 3_000_000:
        raise executor.ExecutorError(400, 'Invalid or oversized browser observation')
    return png


def save_trace(c, tid, run, request, mode, status, events):
    c.execute('INSERT INTO executor_traces VALUES(?,?,?,?,?,?,?)', (tid, run, request, mode, status, json.dumps(events), int(time.time())))


def shutdown(proc):
    if not proc:
        return
    try:
        if proc.poll() is None:
            send(proc, {'command': 'close'}, timeout=2)
    except Exception:
        pass
    if proc.poll() is None:
        proc.kill()
    try:
        proc.wait(timeout=3)
    except Exception:
        pass
    for stream in (proc.stdin, proc.stdout):
        if stream:
            stream.close()
