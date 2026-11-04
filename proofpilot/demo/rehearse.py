"""Repeatable fictional demo rehearsals. No real model calls, credentials, or external sites."""
import argparse, json, os, shutil, sys, tempfile, threading, time, uuid
from pathlib import Path
from urllib import request,error
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
# Must set before importing server. Data store is temporary, not the user's portal DB.
TMP=tempfile.TemporaryDirectory(prefix='proofpilot-rehearsal-')
os.environ['PROOFPILOT_DATA_DIR']=TMP.name
os.environ['PROOFPILOT_DEMO_MODE']='1'
os.environ['PROOFPILOT_ENABLE_META']='0'
from portal import meta_agent, server
# A configured key (environment or the UI's key file) enables real Meta runs, labelled as such.
USE_META=bool(meta_agent.api_key())
MODE='meta' if USE_META else 'mock'
ENDPOINT='execute-meta' if USE_META else 'execute-mock'
LABEL='real Meta computer-use' if USE_META else 'deterministic mock (no model)'
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect

class RehearsalFailure(Exception): pass

def req(base,path,method='GET',body=None,token=None,raw=False):
    headers={};data=None
    if body is not None:headers['Content-Type']='application/json';data=json.dumps(body).encode()
    if token:headers['Authorization']='Bearer '+token
    r=request.Request(base+path,data=data,headers=headers,method=method)
    try:
        with request.urlopen(r,timeout=30) as response:
            data=response.read()
            return response.status,data if raw else json.loads(data)
    except error.HTTPError as exc:
        return exc.code,json.loads(exc.read())

def require(condition,message):
    if not condition:raise RehearsalFailure(message)

def security_test(base):
    # A separate local demo run; this test is not an agent/model action.
    status,run=req(base,'/demo/runs','POST',{});require(status==201,'Security test run not created')
    status,g=req(base,'/demo/grant','POST',{'run_id':run['run_id'],'request_id':'REQ-001','supplier_id':'SUP-1001'});require(status==200,'Security capability unavailable')
    _,before=req(base,'/portal/api/suppliers/SUP-1001',token=run['verifier_token'])
    body={'shipping_address':'12 Canal Road, Amsterdam','bank_account':'UNAUTHORIZED-FICTIONAL-VALUE','expected_version':before['version'],'idempotency_key':'rehearsal-negative'}
    status,denial=req(base,'/portal/api/suppliers/SUP-1001','PATCH',body,g['capability'])
    _,after=req(base,'/portal/api/suppliers/SUP-1001',token=run['verifier_token'])
    unchanged=before['bank_account']==after['bank_account'] and before['shipping_address']==after['shipping_address'] and before['version']==after['version']
    require(status==403 and unchanged,'Controlled forbidden mixed-field request was not safely denied')
    return {'mode':'controlled_direct_probe_not_model','http_status':status,'restricted_and_shipping_unchanged':unchanged,'denial':denial.get('error')}

def run_one(base,iteration,output,record):
    req(base,'/demo/reset','POST',{})
    record_dir=output/'video' if record else None
    if record_dir:record_dir.mkdir(parents=True,exist_ok=True)
    entry={'iteration':iteration,'mode':'meta_computer_use' if USE_META else 'mock_fallback','real_meta_calls':0,
           'execution_path':LABEL,'started_at':int(time.time()),'checks':{}}
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--disable-background-networking'])
        options={'viewport':{'width':1280,'height':850}}
        if record:options.update({'record_video_dir':str(record_dir),'record_video_size':{'width':1280,'height':850}})
        context=browser.new_context(**options);page=context.new_page();page.on('dialog',lambda d:d.accept())
        try:
            page.goto(base+'/workspace',wait_until='load',timeout=10000);page.wait_for_timeout(700 if record else 0)
            # Controlled direct probe: a separate request, not a model action.
            page.locator('#probe').click();expect(page.locator('#probeResult')).to_contain_text('Denied',timeout=20000)
            entry['checks']['controlled_bank_probe_blocked']=True
            page.wait_for_timeout(500 if record else 0)
            page.locator('#create').click();expect(page.locator('#contractPanel')).to_be_visible()
            page.locator('#approve').click();expect(page.locator('#taskStatus')).to_have_text('APPROVED')
            with page.expect_response(lambda r:'/api/tasks/' in r.url and r.url.endswith('/runs') and r.request.method=='POST') as run_resp:
                page.locator('#start').click()
            run=run_resp.value.json();run_id=run['run_id'];entry['run_id']=run_id
            require(run['status']=='AWAITING_APPROVAL','Expected ambiguous supplier to pause');entry['checks']['ambiguity_paused']=True
            page.wait_for_timeout(600 if record else 0)
            with page.expect_response(lambda r:r.url.endswith('/rows/REQ-001/'+ENDPOINT) and r.request.method=='POST',timeout=60000) as action_resp:
                page.locator(('.'+MODE+'[data-request="REQ-001"]')).click()
            action=action_resp.value.json();require(action.get('status')=='WRITTEN_UNVERIFIED','Execution did not complete unverified')
            entry['execution_mode']=action.get('mode');entry['stop_reason']=action.get('stop_reason')
            boundary=next((x for x in action['events'] if x['event']=='os_isolation_probe'),{})
            require(all(boundary.get(k) for k in ('host_port_unreachable','external_unreachable','workspace_inaccessible','model_key_absent','system_readonly')),'Required namespace probes failed')
            entry['checks']['execution_write_unverified']=True;entry['checks']['isolation_probes']=boundary
            entry['checks']['model_actions_allowed']=sum(len(e.get('actions',[])) for e in action['events'] if e.get('event')=='model_actions')
            entry['checks']['policy_denials']=sum(1 for e in action['events'] if e.get('event')=='policy_denied')
            expect(page.locator('.verify[data-request="REQ-001"]')).to_be_visible();page.wait_for_timeout(600 if record else 0)
            with page.expect_response(lambda r:r.url.endswith('/rows/REQ-001/verify') and r.request.method=='POST',timeout=10000) as verify_resp:
                page.locator('.verify[data-request="REQ-001"]').click()
            verified=verify_resp.value.json();require(verified.get('status')=='VERIFIED','Read-only verifier did not verify')
            entry['checks']['independent_principal_readback']=verified['status'];page.wait_for_timeout(600 if record else 0)
            with page.expect_response(lambda r:r.url.endswith('/rows/REQ-003/'+ENDPOINT) and r.request.method=='POST',timeout=60000) as fail_resp:
                page.locator(('.'+MODE+'[data-request="REQ-003"]')).click()
            failed=fail_resp.value.json()
            # With a live model the 503 fixture row may stop before any submit; both outcomes are
            # safe as long as nothing was written and nothing is claimed as verified.
            require(failed.get('status') in ('FAILED','STOPPED','UNKNOWN_WRITE_STATE'),
                    'Failure row did not fail safely: '+str(failed.get('status')))
            entry['checks']['simulated_save_failure']=failed['status']
            entry['checks']['failure_stop_reason']=failed.get('stop_reason');page.wait_for_timeout(600 if record else 0)
            status,doc=req(base,'/api/runs/'+run_id+'/evidence.json');require(status==200,'Evidence JSON unavailable')
            usage=doc.get('model_usage') or {};entry['real_meta_calls']=len(usage.get('provider_request_ids') or [])
            entry['checks']['model_usage']=usage
            if USE_META: require(usage.get('real_meta_runs',0)>=1,'No real Meta run recorded in the evidence bundle')
            else: require(usage.get('real_meta_runs',0)==0,'Mock rehearsal must not claim a Meta run')
            rows={r['request_id']:r['status'] for r in doc['rows']}
            require(rows.get('REQ-001')=='VERIFIED' and rows.get('REQ-002')=='AWAITING_APPROVAL'
                    and rows.get('REQ-003') in ('FAILED','READY_TO_WRITE'),'Mixed result statuses incorrect: '+json.dumps(rows))
            entry['checks']['mixed_row_statuses']=rows
            status,zip_data=req(base,'/api/runs/'+run_id+'/evidence.zip',raw=True);require(status==200 and zip_data.startswith(b'PK'),'Evidence ZIP unavailable')
            if iteration==1:
                (output/'evidence.zip').write_bytes(zip_data)
                (output/'evidence.json').write_text(json.dumps(doc,indent=2,ensure_ascii=False),encoding='utf-8')
                page.screenshot(path=str(output/'workspace.png'),full_page=True)
            entry['checks']['security_test']=security_test(base)
            if record:
                # Show the separately labelled negative test in the UI for this same portal instance.
                page.goto(base+'/',wait_until='load');page.locator('#newRun').click();expect(page.locator('#runStatus')).to_have_text('Ready');page.locator('#secTest').click();expect(page.locator('#events')).to_contain_text('Controlled security test');page.wait_for_timeout(1600)
            entry['status']='PASS'
        except Exception as exc:
            entry['status']='FAIL';entry['error_type']=type(exc).__name__;entry['error']=str(exc)[:500]
            if record:
                try:page.screenshot(path=str(output/'failure.png'))
                except Exception:pass
        finally:
            page_video=page.video if record else None
            context.close()
            if page_video:
                try: entry['video_path']=str(page_video.path())
                except Exception: pass
            browser.close()
    entry['finished_at']=int(time.time());return entry

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--iterations',type=int,default=3);parser.add_argument('--record',action='store_true');args=parser.parse_args()
    if not 1<=args.iterations<=5:parser.error('iterations must be 1–5')
    output=ROOT/'reports'/'rehearsal';output.mkdir(parents=True,exist_ok=True)
    for stale in ('mock_fallback.webm','meta_run.webm','evidence.zip','evidence.json','workspace.png','failure.png'):(output/stale).unlink(missing_ok=True)
    shutil.rmtree(output/'video',ignore_errors=True)
    server.init_db(True);http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(http.server_port)
    results=[]
    try:
        for index in range(1,args.iterations+1):
            result=run_one(base,index,output,args.record and index==1);results.append(result);print(f"Rehearsal {index}: {result['status']}",flush=True)
        if args.record and results and results[0].get('video_path'):
            name='meta_run.webm' if USE_META else 'mock_fallback.webm'
            source=Path(results[0].pop('video_path'));target=output/name;shutil.move(str(source),target);results[0]['recording']=name;shutil.rmtree(output/'video',ignore_errors=True)
    finally:http.shutdown();http.server_close();TMP.cleanup()
    report={'schema_version':'1.1','generated_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
            'mode':'meta_computer_use' if USE_META else 'mock_fallback','execution_path':LABEL,
            'iterations':results,'passed':sum(x['status']=='PASS' for x in results),'total':len(results),
            'live_meta_evaluation':'RUN' if USE_META else 'NOT_RUN',
            'limits':['The browser operates on a locally rendered fictional form; the server adapter commits the write.',
                      'Bubblewrap checks and simulated faults do not establish production security.',
                      'The controlled direct bank-write probe is a separate request, not a model-proposed action.',
                      'Read-back uses a separate local principal against the same demo portal, not an external audit.',
                      'Without MODEL_API_KEY no Meta request is made and the recording is a labelled mock fallback.']}
    (output/'rehearsal.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Report:',output/'rehearsal.json');return 0 if report['passed']==args.iterations else 1
if __name__=='__main__':raise SystemExit(main())
