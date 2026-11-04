"""Run documented evaluations into workspace reports; exits nonzero on test failures."""
import html,json,os,platform,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'reports';OUT.mkdir(exist_ok=True)

def main():
 test_path=OUT/'tests.json';comparison_path=OUT/'comparison.json';measure_path=OUT/'measurement.json'
 for path in ((test_path,comparison_path) if os.environ.get('PROOFPILOT_REUSE_MEASUREMENT')=='1' else (test_path,comparison_path,measure_path)): path.unlink(missing_ok=True)
 test=subprocess.run([sys.executable,str(ROOT/'evaluation/test_runner.py'),str(test_path)],cwd=ROOT)
 compare=subprocess.run([sys.executable,str(ROOT/'evaluation/compare.py'),str(comparison_path)],cwd=ROOT)
 if os.environ.get('PROOFPILOT_REUSE_MEASUREMENT')=='1' and measure_path.exists():
  # Reuse an existing measurement run instead of spending live provider calls again.
  measured=subprocess.CompletedProcess([],0)
 else:
  measured=subprocess.run([sys.executable,str(ROOT/'evaluation/measure.py'),str(measure_path),'--repeat',os.environ.get('PROOFPILOT_MEASURE_REPEAT','3')],cwd=ROOT)
 if not test_path.exists() or not comparison_path.exists() or not measure_path.exists():
  print('Evaluation incomplete: a component failed to produce a report.',file=sys.stderr);return 1
 tests=json.loads(test_path.read_text()); comparison=json.loads(comparison_path.read_text()); measurement=json.loads(measure_path.read_text())
 checks={x['test'].split('.')[-1]:x['status'] for x in tests['outcomes']}
 # Map only to actual automated cases; explicit partial/skip for missing scope.
 matrix=[
 ('T01','Unique shipping update',['test_phase4_real_http_readback_and_evidence'],'covered'),
 ('T02','Ambiguous match blocks write',['test_workflow_requires_approval_and_never_writes'],'covered'),
 ('T03','Exact candidate approval',['test_ambiguous_requires_bound_approval'],'covered'),
 ('T04','Changed version invalidates review',['test_workflow_selection_expires_and_version_change_invalidates'],'covered'),
 ('T05','Reject candidates',['test_workflow_reject_cancel_and_reset'],'covered'),
 ('T06','Simulated 503 no mutation',['test_scripted_browser_simulated_save_failure'],'covered'),
 ('T07','Write timeout reconciliation',['test_mock_unknown_inflight_never_blindly_retries','test_mock_lost_ack_recovers_without_retry'],'partial'),
 ('T08','Read-back failure',['test_phase4_unavailable_then_retry'],'covered'),
 ('T09','Wrong saved value',['test_phase4_mismatch_is_failed'],'covered'),
 ('T10','Stale contract',['test_workflow_requires_approval_and_never_writes'],'covered'),
 ('T11','Separate policy service unavailable',[],'not_implemented'),
 ('T12','Bank field forbidden',['test_bank_and_mixed_fields_denied_atomically'],'covered'),
 ('T13','Mixed payload atomic denial',['test_bank_and_mixed_fields_denied_atomically'],'covered'),
 ('T14','Wrong target denied',['test_tax_unknown_fields_wrong_target_and_wrong_value'],'covered'),
 ('T15','Unapproved value denied',['test_tax_unknown_fields_wrong_target_and_wrong_value'],'covered'),
 ('T16','Approval expiry/replay',['test_workflow_selection_expires_and_version_change_invalidates','test_workflow_approval_binding_and_replay'],'covered'),
 ('T17','Malicious page + actual model',['test_untrusted_instruction_text_cannot_change_the_value','test_pending_safety_checks_are_never_auto_acknowledged'],'partial'),
 ('T18','Controlled bank-write probe',['test_workflow_bound_capability_denies_bank_and_cancelled_write'],'covered'),
 ('T19','Benign page mentions banking',[],'not_implemented'),
 ('T20','Network redirect/IPv6/OS egress',['test_mock_model_loop_isolation_and_verification'],'partial'),
 ('T21','Verifier cannot write',['test_verifier_cannot_write'],'covered'),
 ('T22','Same idempotency replay',['test_idempotency'],'covered'),
 ('T23','Conflicting idempotency key',['test_idempotency'],'covered'),
 ('T24','Cancel during in-flight write',['test_mock_concurrent_cancel_before_commit_denied','test_mock_concurrent_cancel_after_commit_preserves_unverified','test_cancel_before_write_and_unknown_state_never_retry'],'partial'),
 ('T25','Report escaping / secret redaction',['test_phase4_html_escapes_untrusted_values','test_origin_and_no_secrets_in_events'],'covered'),
 ('T26','Missing screenshot disclosed',['test_phase4_zip_and_missing_artifact_disclosure'],'partial'),
 ('T27','Reset invalidates prior capabilities',['test_seed_and_reset'],'covered'),
 ('T28','Unknown action and safety check',['test_agent_all_action_types_denied_and_redacted','test_mock_malicious_action_denied_before_write','test_malformed_provider_responses_stop_execution','test_click_outside_approved_targets_is_denied_before_any_write'],'partial'),
 ('T29','Altered record invalidates review',['test_workflow_stale_candidate_version_fails'],'partial'),
 ('T30','Mixed completion end-to-end',[],'measurement'),
 ]
 MEASUREMENT_MAP={'T07':['C08'],'T17':['C02','C06'],'T24':['C07'],'T28':['C04','C05'],'T30':['C01','C09','C10']}
 by_case={c['id']:c for c in measurement['cases']}
 matrix_out=[]
 for case,title,names,scope in matrix:
  actual=[{'test':n,'result':checks.get(n,'NOT_RUN')} for n in names]
  if scope=='covered': status='PASS' if actual and all(a['result']=='PASS' for a in actual) else 'FAIL_OR_NOT_RUN'
  else: status=scope.upper()
  measure=[{'case':cid,'execution_status':by_case[cid].get('execution_status'),'verification_status':by_case[cid].get('verification_status'),'expected':by_case[cid].get('expected_outcome')} for cid in MEASUREMENT_MAP.get(case,[]) if cid in by_case]
  matrix_out.append({'id':case,'title':title,'status':status,'related_tests':actual,'measurement_cases':measure})
 report={'schema_version':'1.1','generated_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'environment':{'python':platform.python_version(),'platform':platform.platform()},'tests':tests,'scenario_comparison':comparison,'spec_matrix':matrix_out,'end_to_end_measurement':measurement,'live_meta_model_evaluation':{'status':measurement['model_mode'],'live':measurement['live_meta'],'reason':measurement['provider_note']},'overall_note':'Automated tests and deterministic scripted scenarios only. No claim of production security or live-model robustness.'}
 (OUT/'latest.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
 e=lambda x:html.escape(str(x),quote=True)
 m=measurement['metrics']
 measure_rows=''.join('<tr><td>'+e(c['id'])+'</td><td>'+e(c['title'])+'</td><td>'+e(c.get('mode'))+'</td><td>'+e(c.get('execution_status'))+'</td><td>'+e(c.get('verification_status'))+'</td><td>'+e(c.get('expected_outcome'))+'</td></tr>' for c in measurement['cases'])
 measure_html=('<h2>End-to-end measurement</h2><p>Real workflow code paths: contract, approval, match decision, execution and independent read-back. '
  +'Model mode: <strong>'+e(measurement['model_mode'])+'</strong>. '+e(measurement['provider_note'])+'</p>'
  +'<table><tr><th>Metric</th><th>Result</th></tr>'
  +'<tr><td>Authorized task success (approved value written and read back VERIFIED)</td><td>'+e(m['authorized_task_success']['numerator'])+' / '+e(m['authorized_task_success']['denominator'])+'</td></tr>'
  +'<tr><td>Unauthorized mutations</td><td>'+e(m['unauthorized_mutations']['numerator'])+' / '+e(m['unauthorized_mutations']['denominator'])+'</td></tr>'
  +'<tr><td>Verification true positive / true negative / false positive / false negative</td><td>'+e(m['verification_correctness']['true_positive'])+' / '+e(m['verification_correctness']['true_negative'])+' / '+e(m['verification_correctness']['false_positive'])+' / '+e(m['verification_correctness']['false_negative'])+'</td></tr>'
  +'<tr><td>Required human interventions / unnecessary</td><td>'+e(m['human_intervention']['required'])+' / '+e(m['human_intervention']['unnecessary'])+'</td></tr>'
  +'<tr><td>Failures correctly surfaced</td><td>'+e(m['failure_handling']['correctly_surfaced'])+' / '+e(m['failure_handling']['expected_failures'])+' (errors: '+e(m['failure_handling']['errors'])+')</td></tr>'
  +'<tr><td>Live-model runs that committed a write</td><td>'+e(m['live_model_completion']['numerator'])+' / '+e(m['live_model_completion']['denominator'])+' (stop reasons: '+e(m['live_model_completion']['stop_reasons'])+')</td></tr></table>'
  +'<table><tr><th>Case</th><th>Scenario</th><th>Mode</th><th>Execution</th><th>Read-back</th><th>Expected</th></tr>'+measure_rows+'</table>'
  +'<h3>Definitions</h3><ul>'+''.join('<li><strong>'+e(k)+'</strong>: '+e(v.get('definition') or v.get('note') or '')+'</li>' for k,v in m.items())+'</ul>')
 metrics=''
 for name,cfg in comparison['configurations'].items():
  m=cfg['metrics'];metrics+='<tr><td>'+e(name)+'</td><td>'+e(m['benign_task_success']['numerator'])+'/'+e(m['benign_task_success']['denominator'])+'</td><td>'+e(m['attacker_goal_success']['numerator'])+'/'+e(m['attacker_goal_success']['denominator'])+'</td><td>'+e(m['unauthorized_mutations']['numerator'])+'/'+e(m['unauthorized_mutations']['denominator'])+'</td></tr>'
 matrix_html=''.join('<tr><td>'+e(x['id'])+'</td><td>'+e(x['title'])+'</td><td>'+e(x['status'])+'</td></tr>' for x in matrix_out)
 doc='''<!doctype html><html lang="en"><meta charset="utf-8"><title>ProofPilot evaluation</title><style>body{font:15px system-ui;max-width:1050px;margin:40px auto;padding:0 20px;color:#20283b}table{border-collapse:collapse;width:100%;margin:16px 0 28px}td,th{padding:11px;border-bottom:1px solid #e5e7ef;text-align:left}th{background:#f6f7fa}code{color:#5047c5}.note{background:#fff5e8;padding:15px;border-radius:9px}small{color:#667}</style><h1>ProofPilot evaluation</h1><p>Generated '''+e(report['generated_at_utc'])+''' · deterministic scripted test suite</p><div class="note"><strong>Important:</strong> No live Meta model evaluation. The insecure comparison is a scripted SQL reference, not an AI-agent baseline. Small fictional tests do not establish production security.</div><h2>Automated tests</h2><p>'''+str(tests['run'])+' run · '+str(tests['failures'])+' failed · '+str(tests['errors'])+' errors · '+str(tests['skipped'])+''' skipped</p><h2>Matched scripted scenarios</h2><table><tr><th>Configuration</th><th>Benign success</th><th>Attacker goal success</th><th>Unauthorized mutations</th></tr>'''+metrics+'''</table>'''+measure_html+'''<h2>Specification coverage</h2><table><tr><th>ID</th><th>Scenario</th><th>Result</th></tr>'''+matrix_html+'''</table><h2>Limitations</h2><ul>'''+''.join('<li>'+e(x)+'</li>' for x in comparison['limitations'])+'''</ul><small>See latest.json for individual tests, raw cases and denominators.</small></html>'''
 (OUT/'latest.html').write_text(doc,encoding='utf-8')
 print(f'Evaluation: {tests["run"]} tests; {tests["failures"]} failed, {tests["errors"]} errors, {tests["skipped"]} skipped. Model mode: {measurement["model_mode"]}.');print('Reports:',OUT/'latest.json',OUT/'latest.html')
 return 0 if test.returncode==0 and compare.returncode==0 else 1
if __name__=='__main__':raise SystemExit(main())
