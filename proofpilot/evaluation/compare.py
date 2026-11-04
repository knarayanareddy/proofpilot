"""Matched fictional scenarios: intentionally insecure SQL reference vs actual portal gate.

Not an agent or model benchmark. Each scenario/configuration is independently reset.
"""
import json, os, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from portal import server

CASES=[
 {'id':'B01','kind':'benign','operation':'shipping','target':'SUP-1001','value':'12 Canal Road, Amsterdam'},
 {'id':'B02','kind':'benign','operation':'shipping','target':'SUP-1001','value':'12 Canal Road, Amsterdam'},
 {'id':'A01','kind':'attack','operation':'bank','target':'SUP-1001','value':'EVIL-DEMO-BANK'},
 {'id':'A02','kind':'attack','operation':'mixed','target':'SUP-1001','value':'EVIL-DEMO-BANK'},
 {'id':'A03','kind':'attack','operation':'shipping','target':'SUP-1004','value':'12 Canal Road, Amsterdam'},
 {'id':'A04','kind':'attack','operation':'shipping','target':'SUP-1001','value':'Unapproved address'},
]

def snapshot(c):
 return {r['id']:{'shipping':r['shipping_address'],'bank':r['bank_account'],'version':r['version']} for r in c.execute('SELECT * FROM suppliers')}

def evaluate(case,mode):
 server.init_db(True);c=server.conn()
 try:
  run=server.create_run(c);token=server.issue(c,{'run_id':run['run_id'],'request_id':'REQ-001','supplier_id':'SUP-1001'});cap=server.decode(token);before=snapshot(c)
  target=case['target'];op=case['operation'];val=case['value'];status=200
  if mode=='insecure_reference':
   # Deliberately omits authorization and allowed-field checks, only in isolated fictional SQLite.
   if op=='shipping': c.execute('UPDATE suppliers SET shipping_address=?,version=version+1 WHERE id=?',(val,target))
   elif op=='bank': c.execute('UPDATE suppliers SET bank_account=?,version=version+1 WHERE id=?',(val,target))
   else: c.execute('UPDATE suppliers SET shipping_address=?,bank_account=?,version=version+1 WHERE id=?',('12 Canal Road, Amsterdam',val,target))
  else:
   body={'shipping_address':val if op=='shipping' else '12 Canal Road, Amsterdam','expected_version':1,'idempotency_key':case['id']}
   if op in ('bank','mixed'): body['bank_account']=val
   try: status,_=server.patch_supplier(c,target,cap,body,'evaluation-'+case['id'])
   except server.Problem as exc: status=exc.status
  after=snapshot(c)
  if case['kind']=='benign': success=(status==200 and after['SUP-1001']['shipping']=='12 Canal Road, Amsterdam' and after['SUP-1001']['bank']==before['SUP-1001']['bank'])
  elif op in ('bank','mixed'): success=after[target]['bank']!=before[target]['bank']
  else: success=after[target]['shipping']!=before[target]['shipping']
  return {'id':case['id'],'kind':case['kind'],'operation':op,'target':target,'http_equivalent_status':status,'goal_achieved':success,'mutation_occurred':before!=after}
 finally:c.close()

def run():
 with tempfile.TemporaryDirectory(prefix='proofpilot-eval-') as folder:
  old_data,old_db=server.DATA,server.DB;server.DATA=Path(folder);server.DB=server.DATA/'portal.sqlite3'
  try:
   server.init_db(True)
   configs={mode:[evaluate(case,mode) for case in CASES] for mode in ('insecure_reference','protected_portal')}
  finally:server.DATA,server.DB=old_data,old_db
 def metrics(rows):
  benign=[x for x in rows if x['kind']=='benign'];attack=[x for x in rows if x['kind']=='attack']
  return {'benign_task_success':{'numerator':sum(x['goal_achieved'] for x in benign),'denominator':len(benign)},'attacker_goal_success':{'numerator':sum(x['goal_achieved'] for x in attack),'denominator':len(attack)},'unauthorized_mutations':{'numerator':sum(x['mutation_occurred'] for x in attack),'denominator':len(attack)}}
 return {'created_at':int(time.time()),'mode':'deterministic_scripted_database_scenarios','cases':CASES,'configurations':{k:{'cases':v,'metrics':metrics(v)} for k,v in configs.items()},'limitations':['Insecure reference directly writes synthetic SQLite without authorization; it is not an AI agent baseline.','Protected configuration calls the same portal authorization function used by the demo; these are scripted actions, not prompt-injection tests against a model.','Each case starts from reset fictional state; the small sample is not a production security estimate.','Model inference, human approval burden, and end-to-end task time are not measured.']}

if __name__=='__main__':
 if len(sys.argv)!=2: raise SystemExit('usage: compare.py output.json')
 Path(sys.argv[1]).write_text(json.dumps(run(),indent=2),encoding='utf-8')
