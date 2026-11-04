import json
import os
import threading
import time
import unittest
from unittest.mock import patch

from harness import PortalTestCase, server
from portal import agent, proof, mock_loop


class PortalTests(PortalTestCase):
    def test_seed_and_reset(self):
        s,items=self.call('/portal/api/suppliers',token=self.viewer); self.assertEqual(s,200); self.assertEqual(len(items['suppliers']),5)
        self.assertNotIn('bank_account',items['suppliers'][0]); self.assertEqual(self.read()['bank_account'],'DEMO-BANK-1001')
        _,cap=self.grant(); self.write(cap['capability'],self.valid()); self.call('/demo/reset','POST',{})
        # Reset invalidates the previous run's read and mutation capabilities.
        self.assertEqual(self.call('/portal/api/suppliers/SUP-1001', token=self.verifier)[0],403)
        self.assertEqual(self.write(cap['capability'],self.valid())[0],403)
        with server.conn() as c: self.assertEqual(c.execute("select shipping_address from suppliers where id='SUP-1001'").fetchone()[0],'1 Old Quay, Amsterdam')
    def test_success_and_independent_read(self):
        _,cap=self.grant(); status,body=self.write(cap['capability'],self.valid()); self.assertEqual(status,200)
        read=self.read(); self.assertEqual(read['shipping_address'],'12 Canal Road, Amsterdam'); self.assertEqual(read['read_principal'],'verifier'); self.assertEqual(read['version'],2)
        events=self.call('/demo/events',token=self.verifier)[1]['events']; self.assertEqual(events[-1]['decision'],'allow')
    def test_ambiguous_requires_bound_approval(self):
        self.assertEqual(self.grant('REQ-002','SUP-2001')[0],403)
        status,approval=self.approval(); self.assertEqual(status,201)
        self.assertEqual(self.grant('REQ-002','SUP-2002',approval['approval_id'])[0],403)
        _,cap=self.grant('REQ-002','SUP-2001',approval['approval_id'])
        status,_=self.write(cap['capability'],{'shipping_address':'44 Foundry Lane, Rotterdam','expected_version':1,'idempotency_key':'ambiguous'},'SUP-2001'); self.assertEqual(status,200)
        self.assertEqual(self.read('SUP-2001')['shipping_address'],'44 Foundry Lane, Rotterdam')
        self.assertEqual(self.read('SUP-2002')['shipping_address'],'22 Star Road, Rotterdam')
        self.assertEqual(self.grant('REQ-002','SUP-2001',approval['approval_id'])[0],403)
    def test_wrong_contract_or_record_version_approval_rejected(self):
        self.assertEqual(self.approval(version=99)[0],409)
        body={'run_id':self.run['run_id'],'request_id':'REQ-002','supplier_id':'SUP-2001','contract_hash':'wrong','record_version':1}
        self.assertEqual(self.call('/demo/approve','POST',body)[0],409)
    def test_simulated_503_and_unchanged(self):
        _,cap=self.grant('REQ-003','SUP-1003'); before=self.read('SUP-1003')
        status,_=self.write(cap['capability'],{'shipping_address':'8 Dock Street, Utrecht','expected_version':1,'idempotency_key':'fail'},'SUP-1003')
        self.assertEqual(status,503); self.assertEqual(self.read('SUP-1003')['shipping_address'],before['shipping_address'])
    def test_bank_and_mixed_fields_denied_atomically(self):
        _,cap=self.grant(); before=self.read(); b={**self.valid(),'bank_account':'ATTACK'}
        self.assertEqual(self.write(cap['capability'],b)[0],403); after=self.read()
        self.assertEqual((before['bank_account'],before['shipping_address'],before['version']),(after['bank_account'],after['shipping_address'],after['version']))
        events=self.call('/demo/events',token=self.verifier)[1]['events']; self.assertEqual(events[-1]['decision'],'deny')
    def test_tax_unknown_fields_wrong_target_and_wrong_value(self):
        _,cap=self.grant(); self.assertEqual(self.write(cap['capability'],{**self.valid(),'tax_id':'x'})[0],403)
        self.assertEqual(self.write(cap['capability'],self.valid(), 'SUP-1004')[0],403)
        self.assertEqual(self.write(cap['capability'],{**self.valid(),'shipping_address':'attacker address'})[0],403)
        self.assertEqual(self.grant('REQ-001','SUP-1004')[0],403)
    def test_verifier_cannot_write(self): self.assertEqual(self.write(self.verifier,self.valid())[0],403)
    def test_stale_version(self):
        _,cap=self.grant(); self.assertEqual(self.write(cap['capability'],self.valid(version=2))[0],409)
        self.assertEqual(self.read()['shipping_address'],'1 Old Quay, Amsterdam')
    def test_idempotency(self):
        _,cap=self.grant(); token=cap['capability']; body=self.valid(); a=self.write(token,body); b=self.write(token,body)
        self.assertEqual((a[0],b[0]),(200,200)); self.assertEqual(a[1],b[1]); self.assertEqual(self.read()['version'],2)
        self.assertEqual(self.write(token,{**body,'expected_version':2})[0],409)
    def test_capability_expiry_and_tampering(self):
        token=server.encode({'role':'mutation','exp':int(time.time())-1}); self.assertEqual(self.write(token,self.valid())[0],403)
        _,cap=self.grant(); self.assertEqual(self.write(cap['capability']+'x',self.valid())[0],403)
        self.assertEqual(self.write(None,self.valid())[0],401)
    def test_origin_and_no_secrets_in_events(self):
        self.assertEqual(self.call('/demo/runs','POST',{},headers={'Origin':'https://malicious.invalid'})[0],403)
        _,cap=self.grant(); self.write(cap['capability'],self.valid()); raw=json.dumps(self.call('/demo/events',token=self.verifier)[1]); self.assertNotIn(cap['capability'],raw)
    def test_empty_or_unknown_mutation_fields_fail(self):
        _,cap=self.grant(); self.assertEqual(self.write(cap['capability'],{})[0],403)
        self.assertEqual(self.write(cap['capability'],{**self.valid(),'note':'bad'})[0],403)
    def task(self, text=None):
        return self.call('/api/tasks','POST',{'instruction':'Update shipping addresses only', 'csv_text': text if text is not None else server.CSV_TEXT})
    def test_workflow_contract_validation(self):
        status,task=self.task(); self.assertEqual(status,201); self.assertEqual(task['status'],'CONTRACT_REVIEW')
        self.assertEqual(len(task['contract']['rows']),3); self.assertIn('row_hash',task['contract']['rows'][0])
        bad=['request_id,request_id,supplier_id,new_shipping_address\na,b,c,d\n',
             'request_id,supplier_name,supplier_id,new_shipping_address\nx,a,SUP-1001,z\nx,b,SUP-1003,z\n',
             'request_id,supplier_name,supplier_id,new_shipping_address\nx,,SUP-1001,z\n',
             'request_id,supplier_name,supplier_id,new_shipping_address\nx,a,SUP-1001\n',
             'request_id,supplier_name,supplier_id,new_shipping_address\nx,a,SUP-1001,"unclosed\n']
        for text in bad: self.assertEqual(self.task(text)[0],400,text)
    def test_workflow_requires_approval_and_never_writes(self):
        task,run=self.prepared_workflow(); self.assertEqual(run['status'],'AWAITING_APPROVAL'); self.assertTrue(run['execution_enabled'])
        rows={r['request_id']:r for r in run['rows']}; self.assertEqual(rows['REQ-001']['status'],'READY_TO_WRITE'); self.assertEqual(rows['REQ-002']['status'],'AWAITING_APPROVAL'); self.assertEqual(len(rows['REQ-002']['candidates']),2)
        self.assertEqual(self.read()['shipping_address'],'1 Old Quay, Amsterdam')
        self.assertEqual(self.call('/demo/grant','POST',{'run_id':run['run_id'],'request_id':'REQ-001','supplier_id':'SUP-1001'})[0],403)
        self.assertEqual(self.call('/api/tasks/'+task['task_id']+'/runs','POST',{})[0],409)
    def test_workflow_approval_binding_and_replay(self):
        task,run=self.prepared_workflow(); path='/api/runs/'+run['run_id']+'/rows/REQ-002/decision'
        body={'decision':'approve','supplier_id':'SUP-2001','record_version':1,'contract_hash':task['contract_hash']}
        self.assertEqual(self.call(path,'POST',{**body,'contract_hash':'wrong'})[0],409)
        self.assertEqual(self.call(path,'POST',{**body,'supplier_id':'SUP-1004'})[0],409)
        self.assertEqual(self.call(path,'POST',{**body,'record_version':2})[0],409)
        status,res=self.call(path,'POST',body); self.assertEqual(status,200); self.assertEqual(res['status'],'REVIEW_READY')
        row=next(r for r in res['rows'] if r['request_id']=='REQ-002'); self.assertEqual(row['selected_id'],'SUP-2001'); self.assertEqual(row['status'],'READY_TO_WRITE')
        self.assertEqual(self.call(path,'POST',body)[0],409); self.assertEqual(self.read('SUP-2001')['shipping_address'],'10 North Road, Rotterdam')
    def test_workflow_reject_cancel_and_reset(self):
        task,run=self.prepared_workflow(); path='/api/runs/'+run['run_id']+'/rows/REQ-002/decision'
        status,res=self.call(path,'POST',{'decision':'reject','contract_hash':task['contract_hash']}); self.assertEqual(status,200); self.assertEqual(res['status'],'REVIEW_READY')
        self.assertEqual(self.call('/api/runs/'+run['run_id']+'/cancel','POST',{})[1]['status'],'CANCELLED')
        self.assertEqual(self.call('/api/runs/'+run['run_id']+'/cancel','POST',{})[0],409)
        self.call('/demo/reset','POST',{}); self.assertEqual(self.call('/api/runs/'+run['run_id'])[0],404)
    def test_workflow_stale_candidate_version_fails(self):
        task,run=self.prepared_workflow()
        c=server.conn(); c.execute("UPDATE suppliers SET version=2 WHERE id='SUP-2001'"); c.close()
        body={'decision':'approve','supplier_id':'SUP-2001','record_version':1,'contract_hash':task['contract_hash']}
        self.assertEqual(self.call('/api/runs/'+run['run_id']+'/rows/REQ-002/decision','POST',body)[0],409)
    def test_workflow_name_id_mismatch_needs_review(self):
        text='request_id,supplier_name,supplier_id,new_shipping_address\nREQ-X,Wrong Name,SUP-1001,Example\n'
        _,task=self.task(text); self.call('/api/tasks/'+task['task_id']+'/approve','POST',{'contract_hash':task['contract_hash']})
        _,run=self.call('/api/tasks/'+task['task_id']+'/runs','POST',{}); self.assertEqual(run['rows'][0]['status'],'NEEDS_REVIEW')
        self.assertTrue(run['execution_enabled']); self.assertEqual(self.read()['shipping_address'],'1 Old Quay, Amsterdam')
    def test_workflow_selection_expires_and_version_change_invalidates(self):
        task,run=self.prepared_workflow(); path='/api/runs/'+run['run_id']+'/rows/REQ-002/decision'
        body={'decision':'approve','supplier_id':'SUP-2001','record_version':1,'contract_hash':task['contract_hash']}
        self.assertEqual(self.call(path,'POST',body)[0],200)
        c=server.conn(); c.execute("UPDATE workflow_rows SET approval_expires_at=0 WHERE run_id=? AND request_id='REQ-002'",(run['run_id'],)); c.close()
        _,refresh=self.call('/api/runs/'+run['run_id']); self.assertEqual(refresh['status'],'AWAITING_APPROVAL'); self.assertEqual(refresh['rows'][1]['status'],'AWAITING_APPROVAL')
        self.assertEqual(self.call(path,'POST',body)[0],200)
        c=server.conn(); c.execute("UPDATE suppliers SET version=2 WHERE id='SUP-2001'"); c.close()
        _,refresh=self.call('/api/runs/'+run['run_id']); self.assertEqual(refresh['status'],'AWAITING_APPROVAL'); self.assertEqual(refresh['rows'][1]['candidates'][0]['version'],2)
        self.assertEqual(self.call(path,'POST',body)[0],409)
        self.assertEqual(self.call(path,'POST',{**body,'record_version':2})[0],200)
    def test_agent_no_key_fails_without_attempt_or_action(self):
        _,run=self.prepared_workflow()
        with patch.dict(os.environ,{'PROOFPILOT_ENABLE_META':'1'},clear=True):
            status,body=self.call('/api/runs/'+run['run_id']+'/agent/observe','POST',{})
        self.assertEqual(status,503); self.assertIn('No Meta request was made',body['error'])
        self.assertEqual(self.call('/api/runs/'+run['run_id']+'/agent/observations')[1]['observations'],[])
        self.assertEqual(self.read()['shipping_address'],'1 Old Quay, Amsterdam')
    def test_agent_all_action_types_denied_and_redacted(self):
        result=agent.inspect_response({'output':[{'type':'computer_call','actions':[{'type':'click','x':10,'y':20},{'type':'type','text':'SECRET-LEAK'},{'type':'unknown'}],'pending_safety_checks':[{'id':'check'}]}]})
        self.assertEqual(result['executed_actions'],0); self.assertEqual(result['decision'],'stopped_safety_review')
        self.assertTrue(all(a['decision']=='deny' for a in result['actions'])); self.assertNotIn('SECRET-LEAK',json.dumps(result))
        with self.assertRaises(agent.AgentError): agent.inspect_response({'output':[{'type':'computer_call','actions':'invalid'}]})
    def test_agent_endpoint_with_mocked_transport_is_not_real_evidence(self):
        _,run=self.prepared_workflow()
        fake={'model':agent.MODEL,'mode':'test_transport','actions':[{'type':'click','decision':'deny'}],'executed_actions':0,'decision':'observe_only','notice':'Mocked test; no action executed.'}
        with patch.dict(os.environ,{'MODEL_API_KEY':'test-key','PROOFPILOT_ENABLE_META':'1'}), patch.object(agent,'real_inference',return_value=fake):
            status,result=self.call('/api/runs/'+run['run_id']+'/agent/observe','POST',{})
        self.assertEqual(status,200); self.assertEqual(result['mode'],'test_transport'); self.assertEqual(result['executed_actions'],0)
        history=self.call('/api/runs/'+run['run_id']+'/agent/observations')[1]['observations']; self.assertEqual(len(history),1); self.assertNotIn('test-key',json.dumps(history))
        self.assertEqual(self.read()['shipping_address'],'1 Old Quay, Amsterdam')
    def test_agent_cancelled_run_rejected(self):
        _,run=self.prepared_workflow(); self.call('/api/runs/'+run['run_id']+'/cancel','POST',{})
        with patch.dict(os.environ,{'MODEL_API_KEY':'test-key','PROOFPILOT_ENABLE_META':'1'}): self.assertEqual(self.call('/api/runs/'+run['run_id']+'/agent/observe','POST',{})[0],409)
    def test_agent_quota_is_bounded(self):
        _,run=self.prepared_workflow(); fake={'model':agent.MODEL,'mode':'test_transport','actions':[],'executed_actions':0,'decision':'observe_only','notice':'test'}
        with patch.dict(os.environ,{'MODEL_API_KEY':'test-key','PROOFPILOT_ENABLE_META':'1'}), patch.object(agent,'real_inference',return_value=fake):
            for _ in range(agent.MAX_CALLS): self.assertEqual(self.call('/api/runs/'+run['run_id']+'/agent/observe','POST',{})[0],200)
            self.assertEqual(self.call('/api/runs/'+run['run_id']+'/agent/observe','POST',{})[0],429)
    def test_agent_meta_opt_in_required(self):
        _,run=self.prepared_workflow()
        with patch.dict(os.environ,{'MODEL_API_KEY':'test-key'},clear=True):
            status,body=self.call('/api/runs/'+run['run_id']+'/agent/observe','POST',{})
        self.assertEqual(status,503); self.assertIn('disabled',body['error'])
    def test_real_adapter_request_shape_and_redaction_with_fake_http(self):
        class Resp:
            headers={'x-request-id':'fixture-request'}
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,n): return json.dumps({'output':[{'type':'computer_call','actions':[{'type':'type','text':'sensitive text'}],'pending_safety_checks':[]}]}).encode()
        class Transport:
            def open(self,req,timeout):
                self.req=req; self.timeout=timeout; return Resp()
        tr=Transport(); out=agent.real_inference(b'\x89PNG\r\n\x1a\nfixture','demo-key',tr)
        self.assertEqual(tr.req.full_url,agent.ENDPOINT); payload=json.loads(tr.req.data)
        self.assertEqual(payload['model'],'muse-wonder-1.0'); self.assertEqual(payload['tools'],[{'type':'computer'}])
        self.assertEqual(out['executed_actions'],0); self.assertNotIn('sensitive text',json.dumps(out)); self.assertNotIn('demo-key',json.dumps(out))
    def test_scripted_browser_writes_allowed_and_captures_trace(self):
        _,run=self.prepared_workflow()
        path='/api/runs/'+run['run_id']+'/rows/REQ-001/execute-scripted'
        self.assertEqual(self.call(path,'POST',{})[0],400)
        status,res=self.call(path,'POST',{'confirm':'execute-fictional-shipping-update'})
        self.assertEqual(status,200); self.assertEqual(res['status'],'WRITTEN_UNVERIFIED'); self.assertEqual(res['mode'],'scripted_browser')
        self.assertEqual(self.read()['shipping_address'],'12 Canal Road, Amsterdam')
        self.assertTrue(any(e.get('network_route_probe_blocked') for e in res['events']))
        self.assertTrue(any(e['event']=='browser_screenshot' for e in res['events']))
        self.assertEqual(self.call(path,'POST',{'confirm':'execute-fictional-shipping-update'})[0],403)
    def test_scripted_browser_blocked_for_ambiguous_or_cancelled(self):
        _,run=self.prepared_workflow(); path='/api/runs/'+run['run_id']+'/rows/REQ-002/execute-scripted'
        self.assertEqual(self.call(path,'POST',{'confirm':'execute-fictional-shipping-update'})[0],403)
        self.call('/api/runs/'+run['run_id']+'/cancel','POST',{})
        self.assertEqual(self.call('/api/runs/'+run['run_id']+'/rows/REQ-001/execute-scripted','POST',{'confirm':'execute-fictional-shipping-update'})[0],409)
        self.assertEqual(self.read()['shipping_address'],'1 Old Quay, Amsterdam')
    def test_scripted_browser_simulated_save_failure(self):
        _,run=self.prepared_workflow(); before=self.read('SUP-1003')
        status,res=self.call('/api/runs/'+run['run_id']+'/rows/REQ-003/execute-scripted','POST',{'confirm':'execute-fictional-shipping-update'})
        self.assertEqual(status,200); self.assertEqual(res['status'],'FAILED'); self.assertEqual(self.read('SUP-1003')['shipping_address'],before['shipping_address'])
    def test_executor_action_policy_denies_extra_or_wrong_actions(self):
        from portal import executor
        for action in [{'type':'navigate','value':'https://evil.invalid'},{'type':'fill_shipping','value':'wrong'},{'type':'submit_shipping','extra':'bad'},{'type':'write_bank'}]:
            with self.assertRaises(executor.ExecutorError): executor.check_action(action,'approved')
    def test_workflow_bound_capability_denies_bank_and_cancelled_write(self):
        from portal import executor
        _,run=self.prepared_workflow(); c=server.conn()
        try:
            _,_,rec,cap=executor.authorize(c,run['run_id'],'REQ-001',server)
            with self.assertRaises(server.Problem) as err:
                server.patch_supplier(c,rec['id'],cap,{**self.valid(),'bank_account':'bad'},'test-bank')
            self.assertEqual(err.exception.status,403)
            self.assertEqual(c.execute("SELECT bank_account FROM suppliers WHERE id='SUP-1001'").fetchone()[0],'DEMO-BANK-1001')
            self.call('/api/runs/'+run['run_id']+'/cancel','POST',{})
            with self.assertRaises(server.Problem) as err:
                server.patch_supplier(c,rec['id'],cap,self.valid(),'test-cancel')
            self.assertEqual(err.exception.status,403)
        finally: c.close()
    def run_written(self):
        task,run=self.prepared_workflow()
        status,res=self.call('/api/runs/'+run['run_id']+'/rows/REQ-001/execute-scripted','POST',{'confirm':'execute-fictional-shipping-update'})
        self.assertEqual(status,200);self.assertEqual(res['status'],'WRITTEN_UNVERIFIED')
        return task,run,res
    def test_phase4_real_http_readback_and_evidence(self):
        task,run,trace=self.run_written();path='/api/runs/'+run['run_id']+'/rows/REQ-001/verify'
        status,result=self.call(path,'POST',{}); self.assertEqual(status,200);self.assertEqual(result['status'],'VERIFIED');self.assertEqual(result['read_principal'],'verifier')
        self.assertEqual(result['observed_raw'],'12 Canal Road, Amsterdam');self.assertEqual(result['restricted_fields']['bank_account']['status'],'unchanged')
        status,doc=self.call('/api/runs/'+run['run_id']+'/evidence.json');self.assertEqual(status,200)
        self.assertEqual(doc['rows'][0]['status'],'VERIFIED');self.assertEqual(doc['rows'][0]['verification']['verification_id'],result['verification_id'])
        self.assertEqual(doc['scripted_browser_traces'][0]['mode'],'scripted_browser');self.assertNotIn('verifier_token',json.dumps(doc))
        self.assertEqual(self.call(path,'POST',{})[0],409)
    def test_phase4_verify_requires_real_write(self):
        _,run=self.prepared_workflow()
        self.assertEqual(self.call('/api/runs/'+run['run_id']+'/rows/REQ-001/verify','POST',{})[0],409)
        self.assertEqual(self.call('/api/runs/'+run['run_id']+'/rows/REQ-002/verify','POST',{})[0],409)
    def test_phase4_unavailable_then_retry(self):
        _,run,_=self.run_written();c=server.conn()
        def unavailable(*args): raise proof.ProofError(502,'test unavailable')
        try:
            result=proof.verify(c,server,run['run_id'],'REQ-001','http://not-used',reader=unavailable)
            self.assertEqual(result['status'],'EXECUTED_UNVERIFIED');self.assertEqual(result['restricted_fields']['bank_account']['status'],'not_checked')
        finally: c.close()
        status,retry=self.call('/api/runs/'+run['run_id']+'/rows/REQ-001/verify','POST',{})
        self.assertEqual(status,200);self.assertEqual(retry['status'],'VERIFIED')
    def test_phase4_mismatch_is_failed(self):
        _,run,_=self.run_written(); c=server.conn()
        c.execute("UPDATE suppliers SET shipping_address='Unexpected value' WHERE id='SUP-1001'"); c.close()
        status,result=self.call('/api/runs/'+run['run_id']+'/rows/REQ-001/verify','POST',{})
        self.assertEqual(status,200);self.assertEqual(result['status'],'FAILED');self.assertFalse(result['address_matches'])
    def test_phase4_changed_restricted_field_not_verified(self):
        _,run,_=self.run_written(); c=server.conn()
        c.execute("UPDATE suppliers SET bank_account='changed' WHERE id='SUP-1001'"); c.close()
        status,result=self.call('/api/runs/'+run['run_id']+'/rows/REQ-001/verify','POST',{})
        self.assertEqual(status,200);self.assertEqual(result['status'],'FAILED');self.assertEqual(result['restricted_fields']['bank_account']['status'],'changed')
    def test_phase4_zip_and_missing_artifact_disclosure(self):
        import io,zipfile
        _,run,trace=self.run_written();self.call('/api/runs/'+run['run_id']+'/rows/REQ-001/verify','POST',{})
        c=server.conn()
        try:
            doc=proof.bundle(c,server,run['run_id']);z=zipfile.ZipFile(io.BytesIO(proof.zip_bundle(doc,server)))
            names=z.namelist();self.assertIn('evidence.json',names);self.assertIn('report.html',names);self.assertIn('artifacts/'+trace['trace_id']+'.png',names)
            (server.DATA/'artifacts'/(trace['trace_id']+'.png')).unlink()
            z=zipfile.ZipFile(io.BytesIO(proof.zip_bundle(doc,server)));d=json.loads(z.read('evidence.json'))
            self.assertEqual(d['artifact_omissions'],['artifacts/'+trace['trace_id']+'.png'])
            self.assertNotIn('artifacts/'+trace['trace_id']+'.png',z.namelist())
        finally: c.close()
    def test_phase4_html_escapes_untrusted_values(self):
        doc={'run_id':'run-test','contract_hash':'h','rows':[{'request_id':'r','supplier_name':'<script>alert(1)</script>','selected_supplier_id':'s','expected_raw':'x','status':'PENDING','verification':None}],'verifications':[],'scripted_browser_traces':[],'limitations':[]}
        rendered=proof.report_html(doc);self.assertNotIn('<script>',rendered);self.assertIn('&lt;script&gt;',rendered)
    def test_phase5_concurrent_idempotency_commits_once(self):
        from concurrent.futures import ThreadPoolExecutor
        _,cap=self.grant(); body=self.valid('parallel-key')
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _: self.write(cap['capability'],body),range(2)))
        self.assertEqual(sorted(x[0] for x in results),[200,200])
        self.assertEqual(self.read()['version'],2)
        events=self.call('/demo/events',token=self.verifier)[1]['events']
        self.assertEqual(sum(e['decision']=='allow' for e in events),1)
        self.assertEqual(sum(e['decision']=='replay' for e in events),1)
    def test_phase5_untrusted_supplier_note_does_not_change_policy(self):
        _,cap=self.grant('REQ-003','SUP-1003'); before=self.read('SUP-1003')
        status,_=self.write(cap['capability'],{'shipping_address':'8 Dock Street, Utrecht','bank_account':'ATTACK','expected_version':1,'idempotency_key':'note-test'},'SUP-1003')
        self.assertEqual(status,403);self.assertEqual(self.read('SUP-1003')['bank_account'],before['bank_account'])
    def test_mock_model_loop_isolation_and_verification(self):
        _,run=self.prepared_workflow()
        status,res=self.call('/api/runs/'+run['run_id']+'/rows/REQ-001/execute-mock','POST',{'confirm':'execute-fictional-mock-model'})
        self.assertEqual(status,200);self.assertEqual(res['status'],'WRITTEN_UNVERIFIED');self.assertEqual(res['mode'],'mock_model_browser')
        iso=next(e for e in res['events'] if e['event']=='os_isolation_probe')
        for field in ('host_port_unreachable','external_unreachable','workspace_inaccessible','model_key_absent','system_readonly'):self.assertTrue(iso[field],field)
        self.assertEqual(len([e for e in res['events'] if e['event']=='observation']),3)
        self.assertEqual(self.read()['version'],2)
        status,verified=self.call('/api/runs/'+run['run_id']+'/rows/REQ-001/verify','POST',{})
        self.assertEqual(status,200);self.assertEqual(verified['status'],'VERIFIED')
    def test_mock_malicious_action_denied_before_write(self):
        _,run=self.prepared_workflow();c=server.conn()
        try:
            model=mock_loop.MockModel('12 Canal Road, Amsterdam',[{'type':'write_bank','value':'attacker'}])
            result=mock_loop.run(c,run['run_id'],'REQ-001',server,self.http.server_port,model=model)
            self.assertEqual(result['status'],'STOPPED');self.assertEqual(self.read()['shipping_address'],'1 Old Quay, Amsterdam');self.assertEqual(self.read()['bank_account'],'DEMO-BANK-1001')
        finally:c.close()
    def test_mock_cancel_before_write(self):
        _,run=self.prepared_workflow();c=server.conn()
        try:
            result=mock_loop.run(c,run['run_id'],'REQ-001',server,self.http.server_port,fault='cancel_before_write')
            self.assertEqual(result['status'],'CANCELLED_BEFORE_WRITE');self.assertEqual(self.read()['version'],1)
            self.assertEqual(mock_loop.reconcile(c,result['attempt_id'],server)['status'],'CANCELLED_BEFORE_WRITE')
        finally:c.close()
    def test_mock_lost_ack_recovers_without_retry(self):
        _,run=self.prepared_workflow();c=server.conn()
        try:
            result=mock_loop.run(c,run['run_id'],'REQ-001',server,self.http.server_port,fault='disconnect_after_commit')
            self.assertEqual(result['status'],'WRITTEN_UNVERIFIED');self.assertEqual(self.read()['version'],2)
            rec=mock_loop.reconcile(c,result['attempt_id'],server);self.assertFalse(rec['retry_performed']);self.assertEqual(self.read()['version'],2)
            self.assertTrue(any(e['event']=='reconciled' for e in result['events']))
        finally:c.close()
    def test_mock_unknown_inflight_never_blindly_retries(self):
        _,run=self.prepared_workflow();c=server.conn()
        try:
            result=mock_loop.run(c,run['run_id'],'REQ-001',server,self.http.server_port,fault='timeout_before_commit')
            self.assertEqual(result['status'],'UNKNOWN_WRITE_STATE');self.assertEqual(self.read()['version'],1)
            again=mock_loop.reconcile(c,result['attempt_id'],server);self.assertEqual(again['status'],'UNKNOWN_WRITE_STATE');self.assertFalse(again['retry_performed'])
            self.assertEqual(self.call('/api/runs/'+run['run_id']+'/rows/REQ-001/execute-mock','POST',{'confirm':'execute-fictional-mock-model'})[0],409)
        finally:c.close()
    def test_mock_sandbox_missing_fails_closed(self):
        _,run=self.prepared_workflow();c=server.conn()
        try:
            with patch.object(mock_loop.shutil,'which',return_value=None):result=mock_loop.run(c,run['run_id'],'REQ-001',server,self.http.server_port)
            self.assertEqual(result['status'],'STOPPED');self.assertEqual(self.read()['version'],1)
        finally:c.close()
    def test_mock_concurrent_cancel_before_commit_denied(self):
        from concurrent.futures import ThreadPoolExecutor
        _,run=self.prepared_workflow(); entered=threading.Event(); release=threading.Event(); original=server.patch_supplier
        def blocked(*args,**kwargs):
            entered.set(); self.assertTrue(release.wait(5)); return original(*args,**kwargs)
        def execute():
            c=server.conn()
            try:return mock_loop.run(c,run['run_id'],'REQ-001',server,self.http.server_port)
            finally:c.close()
        with patch.object(server,'patch_supplier',side_effect=blocked),ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(execute)
            try:
                self.assertTrue(entered.wait(10));self.assertEqual(self.call('/api/runs/'+run['run_id']+'/cancel','POST',{})[0],200)
            finally:release.set()
            result=future.result(timeout=10)
        self.assertEqual(result['status'],'STOPPED');self.assertEqual(self.read()['version'],1)
        self.assertTrue(any(e.get('status')==403 for e in result['events'] if e['event']=='portal_write'))
    def test_mock_concurrent_cancel_after_commit_preserves_unverified(self):
        from concurrent.futures import ThreadPoolExecutor
        _,run=self.prepared_workflow(); committed=threading.Event(); release=threading.Event(); original=server.patch_supplier
        def blocked(*args,**kwargs):
            result=original(*args,**kwargs);committed.set();self.assertTrue(release.wait(5));return result
        def execute():
            c=server.conn()
            try:return mock_loop.run(c,run['run_id'],'REQ-001',server,self.http.server_port)
            finally:c.close()
        with patch.object(server,'patch_supplier',side_effect=blocked),ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(execute)
            try:
                self.assertTrue(committed.wait(10));self.assertEqual(self.call('/api/runs/'+run['run_id']+'/cancel','POST',{})[0],200)
            finally:release.set()
            result=future.result(timeout=10)
        self.assertEqual(result['status'],'WRITTEN_UNVERIFIED');self.assertEqual(self.read()['version'],2)
        self.assertEqual(self.call('/api/runs/'+run['run_id']+'/rows/REQ-001/verify','POST',{})[0],409)
    def test_mock_unresolved_attempt_blocks_both_executors(self):
        _,run=self.prepared_workflow();c=server.conn()
        try:
            result=mock_loop.run(c,run['run_id'],'REQ-001',server,self.http.server_port,fault='timeout_before_commit')
            self.assertEqual(result['status'],'UNKNOWN_WRITE_STATE')
            attempts=self.call('/api/runs/'+run['run_id']+'/attempts')[1]['attempts'];self.assertEqual(attempts[0]['status'],'UNKNOWN_WRITE_STATE')
            self.assertEqual(self.call('/api/runs/'+run['run_id']+'/rows/REQ-001/execute-scripted','POST',{'confirm':'execute-fictional-shipping-update'})[0],409)
            self.assertEqual(self.read()['version'],1)
        finally:c.close()
if __name__=='__main__': unittest.main()
