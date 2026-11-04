"""Phase 4 verification and inspectable demo evidence; not an external audit."""
import hashlib
import html
import io
import json
import re
import time
import urllib.error
import urllib.request
import uuid
import zipfile

class ProofError(Exception):
    def __init__(self,status,message): self.status=status; self.message=message

def install(c):
    c.execute('''CREATE TABLE IF NOT EXISTS verification_results(
      id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES workflow_runs(id),
      request_id TEXT NOT NULL,status TEXT NOT NULL,result_json TEXT NOT NULL,created_at INTEGER NOT NULL)''')

def norm(value): return re.sub(r'\s+',' ',value.strip())

def read_portal(base_url,supplier_id,token):
    """Read independently over local HTTP under verifier-only capability; no redirects."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl): return None
    req=urllib.request.Request(base_url+'/portal/api/suppliers/'+supplier_id,headers={'Authorization':'Bearer '+token,'Accept':'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=5) as response:
            if response.status!=200: raise ProofError(502,'Verifier read was not successful')
            data=response.read(100_001)
            if len(data)>100_000: raise ProofError(502,'Verifier response exceeded size limit')
            result=json.loads(data)
            if not isinstance(result,dict) or result.get('read_principal')!='verifier' or result.get('id')!=supplier_id or not isinstance(result.get('shipping_address'),str) or type(result.get('version')) is not int:
                raise ProofError(502,'Verifier returned an invalid or mismatched record')
            return result
    except ProofError: raise
    except (urllib.error.URLError,TimeoutError,OSError,ValueError,UnicodeError): raise ProofError(502,'Verifier read unavailable or invalid')

def verify(c,server,run_id,request_id,base_url,reader=read_portal):
    # The operation reserves a row and prevents concurrent verifier claims.
    c.execute('BEGIN IMMEDIATE')
    try:
        run=c.execute('SELECT * FROM workflow_runs WHERE id=?',(run_id,)).fetchone()
        row=c.execute('SELECT * FROM workflow_rows WHERE run_id=? AND request_id=?',(run_id,request_id)).fetchone()
        if not run or not row: raise ProofError(404,'Run or request not found')
        if run['status']=='CANCELLED': raise ProofError(409,'Cancelled runs cannot initiate verification')
        if row['status'] not in ('WRITTEN','EXECUTED_UNVERIFIED'): raise ProofError(409,'Only a written or unverified row can be verified')
        task=c.execute('SELECT * FROM tasks WHERE id=?',(run['task_id'],)).fetchone()
        contract=json.loads(task['contract_json']) if task else None
        source=next((x for x in contract['rows'] if x['request_id']==request_id),None) if contract else None
        if not task or task['status']!='APPROVED' or task['contract_hash']!=server.digest(contract) or not source or not row['selected_id']:
            raise ProofError(409,'Approved contract or selected target is invalid')
        source_no_hash={k:v for k,v in source.items() if k!='row_hash'}
        if source.get('row_hash')!=server.digest(source_no_hash): raise ProofError(409,'Source row hash mismatch')
        trace=c.execute("SELECT * FROM executor_traces WHERE run_id=? AND request_id=? AND status='WRITTEN_UNVERIFIED' ORDER BY rowid DESC LIMIT 1",(run_id,request_id)).fetchone()
        if not trace: raise ProofError(409,'No successful write trace is available')
        trace_events=json.loads(trace['events_json'])
        write=next((e for e in reversed(trace_events) if e.get('event')=='portal_write' and e.get('status')==200),None)
        if not write: raise ProofError(409,'Successful portal write evidence is missing')
        baseline=next((e for e in trace_events if e.get('event')=='restricted_fields_before'),None)
        c.execute("UPDATE workflow_rows SET status='VERIFYING' WHERE run_id=? AND request_id=?",(run_id,request_id))
        server.workflow.record(c,run_id,run['task_id'],'verification_started',{'request_id':request_id})
        c.execute('COMMIT')
    except:
        c.execute('ROLLBACK');raise
    vid='verify-'+uuid.uuid4().hex[:12]; now=int(time.time()); result={
      'verification_id':vid,'run_id':run_id,'request_id':request_id,'supplier_id':row['selected_id'],
      'contract_hash':task['contract_hash'],'source_row_hash':source['row_hash'],
      'source_sha256':task['source_hash'],'expected_raw':source['new_shipping_address'],
      'verification_method':'separate-read-only-demo-portal-http','write_trace_id':trace['id'],
      'write_request_id':write.get('portal_request_id'),'verified_at':now,
      'limitations':['Read-back reflects the same fictional portal’s reported state, not an external audit.','The original CSV file is not stored; source values and hashes are retained.','Status reflects this verification time, not a guarantee of later state.']}
    try:
        observed=reader(base_url,row['selected_id'],server.verifier_token(run_id))
        version_ok=observed.get('version')==row['selected_version']+1
        matches=norm(observed['shipping_address'])==norm(source['new_shipping_address'])
        restricted={}
        for field in ('bank_account','tax_id'):
            prior=baseline.get(field+'_sha256') if baseline else None
            if prior and isinstance(observed.get(field),str):
                actual=hashlib.sha256(observed[field].encode('utf-8')).hexdigest()
                restricted[field]={'status':'unchanged' if actual==prior else 'changed','before_sha256':prior,'after_sha256':actual}
            else: restricted[field]={'status':'not_checked'}
        result.update({'observed_raw':observed['shipping_address'],'read_request_id':observed.get('request_id'),'read_principal':observed['read_principal'],'observed_version':observed['version'],'expected_version':row['selected_version']+1,'address_matches':matches,'version_matches':version_ok,'restricted_fields':restricted})
        restricted_changed=any(value['status']=='changed' for value in restricted.values())
        status='VERIFIED' if matches and version_ok and not restricted_changed else 'FAILED'
        result['reason']='Expected address and committed version match; no checked restricted-field changes were found.' if status=='VERIFIED' else 'Address, version or checked restricted fields do not match; review required.'
    except ProofError as exc:
        status='EXECUTED_UNVERIFIED';result.update({'reason':exc.message,'restricted_fields':{'bank_account':{'status':'not_checked'},'tax_id':{'status':'not_checked'}}})
    except Exception:
        status='EXECUTED_UNVERIFIED';result.update({'reason':'Verifier encountered an unexpected error.','restricted_fields':{'bank_account':{'status':'not_checked'},'tax_id':{'status':'not_checked'}}})
    result['status']=status
    c.execute('BEGIN IMMEDIATE')
    try:
        current=c.execute('SELECT status FROM workflow_rows WHERE run_id=? AND request_id=?',(run_id,request_id)).fetchone()
        current_run=c.execute('SELECT status FROM workflow_runs WHERE id=?',(run_id,)).fetchone()
        if not current or current['status']!='VERIFYING' or not current_run or current_run['status']=='CANCELLED':
            status='EXECUTED_UNVERIFIED';result['status']=status;result['reason']='Run or row changed during verification; review required.'
        if current and current['status']=='VERIFYING': c.execute('UPDATE workflow_rows SET status=? WHERE run_id=? AND request_id=?',(status,run_id,request_id))
        c.execute('INSERT INTO verification_results VALUES(?,?,?,?,?,?)',(vid,run_id,request_id,status,json.dumps(result,ensure_ascii=False),now))
        server.workflow.record(c,run_id,run['task_id'],'verification_finished',{'request_id':request_id,'status':status,'verification_id':vid})
        c.execute('COMMIT')
    except: c.execute('ROLLBACK');raise
    return result

def summarize_model_usage(traces):
    """Provenance of who proposed the actions, counting real provider calls and denials."""
    summary={'modes':[],'real_meta_runs':0,'mock_runs':0,'scripted_runs':0,'provider_request_ids':[],'models':[],
             'policy_denials':0,'safety_check_stops':0,'unverified_stops':0}
    for trace in traces:
        mode=trace.get('mode'); summary['modes'].append(mode)
        if mode=='meta_computer_use': summary['real_meta_runs']+=1
        elif mode=='mock_model_browser': summary['mock_runs']+=1
        else: summary['scripted_runs']+=1
        for event in trace.get('events') or []:
            kind=event.get('event')
            if kind=='meta_call' and event.get('provider_request_id'): summary['provider_request_ids'].append(event['provider_request_id'])
            if kind=='meta_session' and event.get('model'): summary['models'].append(event['model'])
            if kind=='policy_denied':
                summary['policy_denials']+=1
                if event.get('reason')=='pending_safety_checks': summary['safety_check_stops']+=1
            if kind=='meta_stop' and event.get('reason') in ('max_turns_reached','model_returned_no_computer_call'): summary['unverified_stops']+=1
    summary['models']=sorted(set(summary['models']))
    return summary

def bundle(c,server,run_id):
    try: run=server.workflow.get_run(c,run_id,server.Problem)
    except server.Problem as exc: raise ProofError(exc.status,exc.message)
    task=server.workflow.get_task(c,run['task_id'],server.Problem)
    traces=[]
    for t in c.execute('SELECT * FROM executor_traces WHERE run_id=? ORDER BY rowid',(run_id,)):
        events=json.loads(t['events_json']); traces.append({'trace_id':t['id'],'request_id':t['request_id'],'mode':t['mode'],'status':t['status'],'events':events,'created_at':t['created_at']})
    verifications=[json.loads(v['result_json']) for v in c.execute('SELECT * FROM verification_results WHERE run_id=? ORDER BY rowid',(run_id,))]
    latest={x['request_id']:x for x in verifications}
    source={x['request_id']:x for x in task['contract']['rows']}
    rows=[]
    for row in run['rows']:
        src=source[row['request_id']]
        rows.append({'request_id':row['request_id'],'supplier_name':src['supplier_name'],'requested_supplier_id':src['supplier_id'],'selected_supplier_id':row['selected_id'],'expected_raw':src['new_shipping_address'],'source_row_hash':src['row_hash'],'status':row['status'],'verification':latest.get(row['request_id'])})
    model_usage=summarize_model_usage(traces)
    limitations=['Fictional demo; a trace is labelled with the mode that produced it (scripted, mock or real Meta computer-use).',
                 'Read-back reports the same demo portal’s state under a separate read-only principal, not an external audit.',
                 'Source CSV bytes are not retained; source values and file/row hashes are retained.',
                 'No universal proof of absence of side effects, no independent external audit, and no production security claim.']
    if model_usage['real_meta_runs']==0:
        limitations.insert(1,'No real Meta model run is included in this bundle; any trace shown was produced by the scripted or deterministic mock path.')
    return {'schema_version':'1.0-demo','generated_at':int(time.time()),'run_id':run_id,'task_id':task['task_id'],'contract_hash':task['contract_hash'],'source_sha256':task['contract']['source_sha256'],'task_status':task['status'],'run_status':run['status'],'rows':rows,'workflow_events':run['events'],'execution_traces':traces,'scripted_browser_traces':traces,'model_usage':model_usage,'verifications':verifications,'limitations':limitations}

def report_html(doc,embedded=False):
    esc=lambda x:html.escape(str(x if x is not None else '—'),quote=True)
    rows=''.join('<tr><td>'+esc(r['request_id'])+'</td><td>'+esc(r['supplier_name'])+'</td><td>'+esc(r['selected_supplier_id'])+'</td><td>'+esc(r['expected_raw'])+'</td><td><strong>'+esc(r['status'])+'</strong></td><td>'+esc(r['verification']['reason'] if r['verification'] else 'No verification result')+'</td></tr>' for r in doc['rows'])
    parts=[]
    for t in (doc.get('execution_traces') or doc['scripted_browser_traces']):
        events='<pre>'+esc(json.dumps(t['events'],indent=2,ensure_ascii=False))+'</pre>'
        screenshot=next((x.get('artifact') for x in t['events'] if x.get('event')=='browser_screenshot'),None)
        image=''
        if screenshot and re.fullmatch(r'artifacts/trace-[a-f0-9]+\.png',screenshot):
            src=screenshot if embedded else '/api/runs/'+doc['run_id']+'/'+screenshot
            image='<p><a href="'+esc(src)+'">View browser screenshot</a></p>'
        parts.append('<section><h3>'+esc(t['trace_id'])+' · '+esc(t['mode'])+'</h3>'+image+events+'</section>')
    usage=doc.get('model_usage') or {}
    provenance=('<section><h2>Model provenance</h2><p><strong>Real Meta computer-use runs:</strong> '+esc(usage.get('real_meta_runs',0))
                +' · <strong>Mock runs:</strong> '+esc(usage.get('mock_runs',0))+' · <strong>Scripted runs:</strong> '+esc(usage.get('scripted_runs',0))+'</p><p>Provider request IDs: '
                +(esc(', '.join(usage.get('provider_request_ids') or []) or 'none'))+' · Models: '+(esc(', '.join(usage.get('models') or []) or 'none'))
                +'</p><p>Policy denials: '+esc(usage.get('policy_denials',0))+' · Provider safety-check stops: '+esc(usage.get('safety_check_stops',0))+'</p></section>')
    limits=''.join('<li>'+esc(x)+'</li>' for x in doc['limitations'])
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>ProofPilot evidence report</title><style>body{font:15px system-ui;color:#243049;max-width:1100px;margin:40px auto;padding:0 20px}h1{letter-spacing:-.03em}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:12px;border-bottom:1px solid #ddd;vertical-align:top}pre{background:#f5f6fa;padding:12px;white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}section{margin-top:25px}small{color:#667}</style></head><body><h1>ProofPilot evidence report</h1><p><strong>Fictional demo · scripted/mock browser · verification is time-specific</strong></p><p>Run '+esc(doc['run_id'])+' · Contract <small>'+esc(doc['contract_hash'])+'</small></p><table><thead><tr><th>Request</th><th>Supplier</th><th>Selected ID</th><th>Expected address</th><th>Status</th><th>Verification</th></tr></thead><tbody>'+rows+'</tbody></table><section><h2>Verification details</h2><pre>'+esc(json.dumps(doc['verifications'],indent=2,ensure_ascii=False))+'</pre></section><h2>Execution traces (scripted, mock and real Meta)</h2>'+''.join(parts)+provenance+'<section><h2>Limitations</h2><ul>'+limits+'</ul></section></body></html>')

def zip_bundle(doc,server):
    out=io.BytesIO(); doc_copy=json.loads(json.dumps(doc))
    # Include only screenshots that exist and match recorded SHA-256; identify omitted artifacts.
    omissions=[]; artifacts=[]
    for trace in (doc_copy.get('execution_traces') or doc_copy['scripted_browser_traces']):
        for event in trace['events']:
            rel=event.get('artifact')
            if event.get('event')!='browser_screenshot' or not isinstance(rel,str) or not re.fullmatch(r'artifacts/trace-[a-f0-9]+\.png',rel): continue
            path=server.DATA/rel
            if path.is_file():
                data=path.read_bytes()
                if hashlib.sha256(data).hexdigest()==event.get('sha256'):
                    artifacts.append((rel,data));continue
            omissions.append(rel);event['artifact_status']='missing_or_hash_mismatch';event.pop('artifact',None)
    doc_copy['artifact_omissions']=omissions
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('evidence.json',json.dumps(doc_copy,indent=2,ensure_ascii=False))
        z.writestr('report.html',report_html(doc_copy,embedded=True))
        for rel,data in artifacts:z.writestr(rel,data)
    return out.getvalue()
