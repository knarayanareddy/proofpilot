"""Controlled scripted-browser execution for fictional portal only.

Ephemeral Chromium context, offline static page, deny network at Playwright layer.
Not an OS sandbox; do not process untrusted live pages or real credentials.
"""
import hashlib
import html
import json
import time
import uuid
from pathlib import Path

class ExecutorError(Exception):
    def __init__(self,status,message): self.status=status; self.message=message

def install(c):
    c.execute('''CREATE TABLE IF NOT EXISTS executor_traces(id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES workflow_runs(id),request_id TEXT NOT NULL,mode TEXT NOT NULL,status TEXT NOT NULL,events_json TEXT NOT NULL,created_at INTEGER NOT NULL)''')

def authorize(c,run_id,request_id,server,attempt_id=None):
    """Create short-lived internal capability; ultimate enforcement occurs inside patch_supplier."""
    run=server.workflow.get_run(c,run_id,server.Problem)
    if run['status'] not in ('AWAITING_APPROVAL','REVIEW_READY'): raise ExecutorError(409,'Run is not active for execution')
    task=server.workflow.get_task(c,run['task_id'],server.Problem)
    row=next((r for r in run['rows'] if r['request_id']==request_id),None)
    src=next((r for r in task['contract']['rows'] if r['request_id']==request_id),None)
    if not row or not src: raise ExecutorError(404,'Request row not found')
    # A prior unresolved attempt must be reconciled before another executor can proceed.
    # Phase 1/2 stores may not yet have the attempts table; Phase 3 installs it at startup.
    prior=c.execute("SELECT id FROM execution_attempts WHERE run_id=? AND request_id=? AND status IN ('PREPARED','IN_FLIGHT','UNKNOWN_WRITE_STATE') AND (? IS NULL OR id<>?) LIMIT 1",(run_id,request_id,attempt_id,attempt_id)).fetchone()
    if prior: raise ExecutorError(409,'Another attempt is active or unresolved; reconcile before retrying')
    if task['status']!='APPROVED' or task['contract_hash']!=run['contract_hash'] or row['status']!='READY_TO_WRITE' or not row['selected_id']:
        raise ExecutorError(403,'Approved, ready row required; no action executed')
    record=c.execute('SELECT * FROM suppliers WHERE id=?',(row['selected_id'],)).fetchone()
    if not record or row['selected_version']!=record['version']: raise ExecutorError(409,'Record version changed; re-review required')
    if not src['supplier_id'] and (not row['approval_id'] or not row['approval_expires_at'] or row['approval_expires_at']<=int(time.time())):
        raise ExecutorError(403,'Exact target approval is missing or expired')
    payload={'role':'mutation','run_id':run_id,'request_id':request_id,'supplier_id':record['id'],'contract_hash':run['contract_hash'],'address':src['new_shipping_address'],'record_version':record['version'],'approval_id':row['approval_id'],'exp':int(time.time())+120}
    return run,src,dict(record),payload

def check_action(action,expected):
    """Accept only narrow semantic actions; no arbitrary coordinates, scripts or navigation."""
    if not isinstance(action,dict) or set(action)-{'type','value'}: raise ExecutorError(403,'Unknown action or fields denied')
    name=action.get('type')
    if name=='focus_shipping' and set(action)=={'type'}: return name
    if name=='fill_shipping' and set(action)=={'type','value'} and action['value']==expected: return name
    if name=='submit_shipping' and set(action)=={'type'}: return name
    raise ExecutorError(403,'Action is outside the approved shipping workflow')

def browser_demo(c,run_id,request_id,server):
    try: from playwright.sync_api import sync_playwright
    except ImportError: raise ExecutorError(503,'Playwright is not installed. Follow README browser setup.')
    run,src,rec,cap=authorize(c,run_id,request_id,server)
    trace='trace-'+uuid.uuid4().hex[:12]; events=[]; blocked=[]
    def event(kind,**data): events.append({'event':kind,**data})
    event('restricted_fields_before',bank_account_sha256=hashlib.sha256(rec['bank_account'].encode('utf-8')).hexdigest(),tax_id_sha256=hashlib.sha256(rec['tax_id'].encode('utf-8')).hexdigest(),record_version=rec['version'],source='server-side demo portal pre-write snapshot')
    # Explicitly only a self-contained static view. No credentials enter Chromium.
    page_html='''<!doctype html><meta charset="utf-8"><title>Fictional supplier record</title><style>body{font:16px system-ui;background:#f5f6fb;color:#242b3c;padding:48px}.card{background:#fff;padding:32px;max-width:720px;border:1px solid #e2e5ee;border-radius:16px}input{padding:12px;width:90%%;font:16px system-ui}button{background:#443bd2;color:#fff;border:0;border-radius:8px;padding:12px;margin-top:18px}.note{background:#fff8ed;padding:12px}</style><div class="card"><h1>Supplier record</h1><p>Fictional, network-blocked browser view · %s</p><p>Supplier: <strong>%s</strong></p><p class="note">Supplier note (untrusted): %s</p><label>Shipping address<br><input id="shipping" value="%s"></label><br><button type="button" id="save">Save shipping address</button><p id="status">Read-only local view. Writes pass through the server policy gate.</p></div>''' % tuple(html.escape(str(x),quote=True) for x in (rec['id'],rec['name'],rec['note'],rec['shipping_address']))
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--disable-background-networking','--disable-sync','--disable-extensions'])
            context=browser.new_context(viewport={'width':1100,'height':700},service_workers='block',java_script_enabled=False,accept_downloads=False)
            context.route('**/*',lambda route: (blocked.append(route.request.url),route.abort()))
            page=context.new_page();page.set_content(page_html,wait_until='load',timeout=10000)
            # Force a request to prove the application-level route guard observes and denies it.
            network_probe=False
            try: page.goto('https://blocked.example.invalid/probe',timeout=2500)
            except Exception: network_probe=bool(blocked)
            page.close()
            page=context.new_page()
            page.set_content(page_html,wait_until='load',timeout=10000)
            event('browser_started',network_route_probe_blocked=network_probe,limitations='Playwright route control is not OS-level isolation')
            # Deterministic scripted actions—not generated by a model.
            for action in [{'type':'focus_shipping'},{'type':'fill_shipping','value':src['new_shipping_address']},{'type':'submit_shipping'}]:
                kind=check_action(action,src['new_shipping_address']); event('policy_decision',action=kind,decision='allow')
                if kind=='focus_shipping': page.locator('#shipping').focus()
                elif kind=='fill_shipping': page.locator('#shipping').fill(action['value'])
                else:
                    if page.locator('#shipping').input_value()!=src['new_shipping_address']: raise ExecutorError(403,'Browser input changed from approved value')
                    page.locator('#save').click()
                    # Capture a real Chromium screenshot; artifact is local, fictional data only.
                    png=page.screenshot(); folder=server.DATA/'artifacts';folder.mkdir(parents=True,exist_ok=True);(folder/(trace+'.png')).write_bytes(png)
                    event('browser_screenshot',sha256=hashlib.sha256(png).hexdigest(),artifact='artifacts/'+trace+'.png')
                    request={'shipping_address':src['new_shipping_address'],'expected_version':rec['version'],'idempotency_key':run_id+':'+request_id+':v1'}
                    try:
                        status,result=server.patch_supplier(c,rec['id'],cap,request,uuid.uuid4().hex)
                        event('portal_write',status=status,portal_request_id=result['request_id'])
                    except server.Problem as err:
                        event('portal_write',status=err.status,error=err.message)
                        # 503 means fixture claims no commit; read-back here is diagnostic only, not Phase 4 verification.
                        after=c.execute('SELECT shipping_address,version FROM suppliers WHERE id=?',(rec['id'],)).fetchone()
                        if err.status==503 and after and after['version']==rec['version'] and after['shipping_address']==rec['shipping_address']:
                            c.execute("UPDATE workflow_rows SET status='FAILED' WHERE run_id=? AND request_id=? AND status='READY_TO_WRITE'",(run_id,request_id))
                        context.close();browser.close()
                        return save_trace(c,trace,run_id,request_id,'FAILED',events)
            context.close();browser.close()
        return save_trace(c,trace,run_id,request_id,'WRITTEN_UNVERIFIED',events)
    except ExecutorError: raise
    except Exception as err:
        # Browser errors do not imply a write did or did not happen; reconcile current portal state.
        row=c.execute('SELECT status FROM workflow_rows WHERE run_id=? AND request_id=?',(run_id,request_id)).fetchone()
        status='WRITTEN_UNVERIFIED' if row and row['status']=='WRITTEN' else 'STOPPED'
        event('executor_error',error_type=type(err).__name__,message='Execution stopped; inspect portal state before retry.')
        return save_trace(c,trace,run_id,request_id,status,events)

def save_trace(c,tid,run,request,status,events):
    c.execute('INSERT INTO executor_traces VALUES(?,?,?,?,?,?,?)',(tid,run,request,'scripted_browser',status,json.dumps(events),int(time.time())))
    return {'trace_id':tid,'run_id':run,'request_id':request,'mode':'scripted_browser','status':status,'events':events,'notice':'Scripted Chromium actions; no Meta inference. Written results are not independently verified.'}
