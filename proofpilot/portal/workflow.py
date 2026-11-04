"""Phase 2: local, review-only workflow. No model inference or write execution."""
import csv, io, json, re, time, uuid

HEADERS=['request_id','supplier_name','supplier_id','new_shipping_address']
RUN_TRANSITIONS={'READY':{'RUNNING','CANCELLED'},'RUNNING':{'AWAITING_APPROVAL','REVIEW_READY','CANCELLED'},'AWAITING_APPROVAL':{'REVIEW_READY','CANCELLED'},'REVIEW_READY':{'AWAITING_APPROVAL','CANCELLED'},'CANCELLED':set()}

def install(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,instruction TEXT NOT NULL,source_hash TEXT NOT NULL,contract_json TEXT NOT NULL,contract_hash TEXT NOT NULL,status TEXT NOT NULL,created_at INTEGER NOT NULL,approved_at INTEGER);
    CREATE TABLE IF NOT EXISTS workflow_runs(id TEXT PRIMARY KEY REFERENCES runs(id),task_id TEXT NOT NULL REFERENCES tasks(id),status TEXT NOT NULL,created_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS workflow_rows(run_id TEXT NOT NULL REFERENCES workflow_runs(id),request_id TEXT NOT NULL,status TEXT NOT NULL,candidates_json TEXT NOT NULL,selected_id TEXT,selected_version INTEGER,approval_id TEXT,approval_expires_at INTEGER,PRIMARY KEY(run_id,request_id));
    CREATE TABLE IF NOT EXISTS workflow_events(id INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT,task_id TEXT,event_type TEXT NOT NULL,detail_json TEXT NOT NULL,created_at INTEGER NOT NULL);
    ''')
    if 'approval_expires_at' not in {row[1] for row in c.execute('PRAGMA table_info(workflow_rows)')}:
        c.execute('ALTER TABLE workflow_rows ADD COLUMN approval_expires_at INTEGER')

def record(c,run,task,kind,detail):
    c.execute('INSERT INTO workflow_events(run_id,task_id,event_type,detail_json,created_at) VALUES(?,?,?,?,?)',(run,task,kind,json.dumps(detail,ensure_ascii=False),int(time.time())))

def parse_source(text,hash_fn,problem):
    if not isinstance(text,str) or not text or len(text.encode('utf-8'))>1_000_000: raise problem(400,'CSV must be non-empty UTF-8 and at most 1 MB')
    try:
        reader=csv.reader(io.StringIO(text,newline=''),strict=True)
        headers=next(reader)
        if headers!=HEADERS: raise problem(400,'CSV headers must exactly match: '+', '.join(HEADERS))
        rows=[]; ids=set()
        for line in reader:
            if len(line)!=4: raise problem(400,f'CSV line {reader.line_num} must contain exactly four fields')
            row=dict(zip(HEADERS,line))
            if any(len(value)>500 for value in line): raise problem(400,f'CSV line {reader.line_num} exceeds field length limit')
            if not all(row[k].strip() for k in ('request_id','supplier_name','new_shipping_address')): raise problem(400,f'CSV line {reader.line_num} has an empty required field')
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',row['request_id']): raise problem(400,f'Invalid request ID on line {reader.line_num}')
            if row['request_id'] in ids: raise problem(400,'Duplicate request ID: '+row['request_id'])
            if row['supplier_id'] and not re.fullmatch(r'SUP-\d+',row['supplier_id']): raise problem(400,f'Invalid supplier ID on line {reader.line_num}')
            ids.add(row['request_id']); row['row_hash']=hash_fn(row); rows.append(row)
            if len(rows)>100: raise problem(400,'CSV exceeds 100-row demo limit')
        if not rows: raise problem(400,'CSV must include at least one data row')
        return rows
    except problem: raise
    except (csv.Error,StopIteration,UnicodeError): raise problem(400,'Malformed CSV')

def create_task(c,body,hash_fn,problem):
    if set(body)!={'instruction','csv_text'} or not isinstance(body.get('instruction'),str) or not body['instruction'].strip() or len(body['instruction'])>2000: raise problem(400,'Provide an instruction and CSV text')
    # The arbitrary instruction is displayed as task context, not interpreted as authority.
    rows=parse_source(body['csv_text'],hash_fn,problem)
    source_hash=__import__('hashlib').sha256(body['csv_text'].encode('utf-8')).hexdigest()
    contract={'version':1,'instruction':body['instruction'],'source_sha256':source_hash,'rows':rows,'allowed_operations':['read_supplier','update_shipping_address'],'prohibited_operations':['update_bank_details','update_tax_details','send_external_message'],'approval_required':['ambiguous_supplier_match'],'verification':['read_back_saved_shipping_address']}
    task='task-'+uuid.uuid4().hex[:12]; ch=hash_fn(contract); now=int(time.time())
    c.execute('BEGIN IMMEDIATE')
    try:
        c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,NULL)',(task,body['instruction'],source_hash,json.dumps(contract,ensure_ascii=False),ch,'CONTRACT_REVIEW',now))
        record(c,None,task,'contract_proposed',{'contract_hash':ch,'source_sha256':source_hash,'row_count':len(rows)})
        c.execute('COMMIT')
    except: c.execute('ROLLBACK'); raise
    return get_task(c,task,problem)

def get_task(c,task,problem):
    row=c.execute('SELECT * FROM tasks WHERE id=?',(task,)).fetchone()
    if not row: raise problem(404,'Task not found')
    return {'task_id':row['id'],'status':row['status'],'contract':json.loads(row['contract_json']),'contract_hash':row['contract_hash'],'created_at':row['created_at'],'approved_at':row['approved_at']}

def approve_task(c,task,body,problem):
    if set(body)!={'contract_hash'}: raise problem(400,'Provide the exact contract_hash')
    c.execute('BEGIN IMMEDIATE')
    try:
        row=c.execute('SELECT * FROM tasks WHERE id=?',(task,)).fetchone()
        if not row: raise problem(404,'Task not found')
        if row['status']!='CONTRACT_REVIEW' or body['contract_hash']!=row['contract_hash']: raise problem(409,'Task is not reviewable or contract hash is stale')
        c.execute("UPDATE tasks SET status='APPROVED',approved_at=? WHERE id=?",(int(time.time()),task))
        record(c,None,task,'contract_approved',{'contract_hash':row['contract_hash'],'reviewer':'local-demo-user'})
        c.execute('COMMIT')
    except: c.execute('ROLLBACK'); raise
    return get_task(c,task,problem)

def start_run(c,task,problem):
    c.execute('BEGIN IMMEDIATE')
    try:
        t=c.execute('SELECT * FROM tasks WHERE id=?',(task,)).fetchone()
        if not t: raise problem(404,'Task not found')
        if t['status']!='APPROVED': raise problem(409,'Exact contract must be approved before a run starts')
        if c.execute('SELECT 1 FROM workflow_runs WHERE task_id=?',(task,)).fetchone(): raise problem(409,'A run already exists for this task')
        run='run-'+uuid.uuid4().hex[:12]; now=int(time.time())
        c.execute('INSERT INTO runs VALUES(?,?,?)',(run,t['contract_hash'],now))
        c.execute('INSERT INTO workflow_runs VALUES(?,?,?,?)',(run,task,'READY',now))
        for row in json.loads(t['contract_json'])['rows']:
            c.execute('INSERT INTO workflow_rows(run_id,request_id,status,candidates_json,selected_id,selected_version,approval_id) VALUES(?,?,?,?,?,?,?)',(run,row['request_id'],'PENDING','[]',None,None,None))
        record(c,run,task,'run_created',{'status':'READY','contract_hash':t['contract_hash']})
        # Phase 2 only matches records: it performs no target writes.
        transition(c,run,'RUNNING',problem)
        suppliers=[dict(x) for x in c.execute('SELECT id,name,shipping_address,version FROM suppliers ORDER BY id')]
        for row in json.loads(t['contract_json'])['rows']:
            if row['supplier_id']:
                matches=[s for s in suppliers if s['id']==row['supplier_id']]
                # ID/name mismatch is not silently resolved.
                if matches and matches[0]['name'].casefold()!=row['supplier_name'].strip().casefold():
                    status='NEEDS_REVIEW'; matches=[]
                else: status='READY_TO_WRITE' if len(matches)==1 else 'NEEDS_REVIEW'
            else:
                query=row['supplier_name'].strip().casefold()
                matches=[s for s in suppliers if query in s['name'].casefold()]
                # No identifier: never silently resolve, even if one candidate.
                status='AWAITING_APPROVAL' if matches else 'NEEDS_REVIEW'
            c.execute('UPDATE workflow_rows SET status=?,candidates_json=?,selected_id=?,selected_version=? WHERE run_id=? AND request_id=?',(status,json.dumps(matches),matches[0]['id'] if status=='READY_TO_WRITE' else None,matches[0]['version'] if status=='READY_TO_WRITE' else None,run,row['request_id']))
            record(c,run,task,'match_evaluated',{'request_id':row['request_id'],'status':status,'candidate_count':len(matches)})
        if c.execute("SELECT 1 FROM workflow_rows WHERE run_id=? AND status IN ('AWAITING_APPROVAL','NEEDS_REVIEW')",(run,)).fetchone(): transition(c,run,'AWAITING_APPROVAL',problem)
        else: transition(c,run,'REVIEW_READY',problem)
        c.execute('COMMIT')
    except: c.execute('ROLLBACK'); raise
    return get_run(c,run,problem)

def transition(c,run,status,problem):
    r=c.execute('SELECT * FROM workflow_runs WHERE id=?',(run,)).fetchone()
    if not r or status not in RUN_TRANSITIONS.get(r['status'],set()): raise problem(409,'Invalid run state transition')
    c.execute('UPDATE workflow_runs SET status=? WHERE id=?',(status,run))
    record(c,run,r['task_id'],'run_transition',{'from':r['status'],'to':status})

def get_run(c,run,problem):
    r=c.execute('SELECT * FROM workflow_runs WHERE id=?',(run,)).fetchone()
    if not r: raise problem(404,'Run not found')
    task=get_task(c,r['task_id'],problem)
    # Review selections expire and become invalid if the selected record changes.
    if r['status'] in ('AWAITING_APPROVAL','REVIEW_READY'):
        selections=c.execute("SELECT * FROM workflow_rows WHERE run_id=? AND approval_id IS NOT NULL AND status='READY_TO_WRITE'",(run,)).fetchall()
        for selection in selections:
            current=c.execute('SELECT version FROM suppliers WHERE id=?',(selection['selected_id'],)).fetchone()
            if selection['approval_expires_at'] is None or selection['approval_expires_at']<=int(time.time()) or not current or current['version']!=selection['selected_version']:
                # Refresh candidate snapshots; selection was only a review decision, never a write grant.
                candidates=json.loads(selection['candidates_json'])
                fresh=[]
                for candidate in candidates:
                    rec=c.execute('SELECT id,name,shipping_address,version FROM suppliers WHERE id=?',(candidate['id'],)).fetchone()
                    if rec: fresh.append(dict(rec))
                c.execute("UPDATE workflow_rows SET status='AWAITING_APPROVAL',candidates_json=?,selected_id=NULL,selected_version=NULL,approval_id=NULL,approval_expires_at=NULL WHERE run_id=? AND request_id=?",(json.dumps(fresh),run,selection['request_id']))
                record(c,run,r['task_id'],'match_approval_invalidated',{'request_id':selection['request_id'],'reason':'expired or selected record changed'})
                if r['status']=='REVIEW_READY':
                    transition(c,run,'AWAITING_APPROVAL',problem)
                    r=c.execute('SELECT * FROM workflow_runs WHERE id=?',(run,)).fetchone()
    rows=[]
    for row in c.execute('SELECT * FROM workflow_rows WHERE run_id=? ORDER BY rowid',(run,)):
        item=dict(row); item['candidates']=json.loads(item.pop('candidates_json')); rows.append(item)
    events=[{'id':e['id'],'type':e['event_type'],'detail':json.loads(e['detail_json']),'created_at':e['created_at']} for e in c.execute('SELECT * FROM workflow_events WHERE run_id=? ORDER BY id',(run,))]
    return {'run_id':run,'task_id':r['task_id'],'status':r['status'],'contract_hash':task['contract_hash'],'rows':rows,'events':events,'execution_enabled':True,'note':'Scripted demo execution is available for ready rows; no model controls the browser. Writes are not independently verified.'}

def decide(c,run,request,body,problem):
    if set(body)-{'decision','supplier_id','record_version','contract_hash'} or body.get('decision') not in ('approve','reject'): raise problem(400,'Invalid review decision')
    c.execute('BEGIN IMMEDIATE')
    try:
        r=c.execute('SELECT * FROM workflow_runs WHERE id=?',(run,)).fetchone()
        rr=c.execute('SELECT * FROM workflow_rows WHERE run_id=? AND request_id=?',(run,request)).fetchone()
        if not r or not rr: raise problem(404,'Run or row not found')
        if r['status']!='AWAITING_APPROVAL' or rr['status']!='AWAITING_APPROVAL': raise problem(409,'Row is not awaiting approval')
        task=get_task(c,r['task_id'],problem)
        if body.get('contract_hash')!=task['contract_hash']: raise problem(409,'Contract hash changed')
        if body['decision']=='reject':
            c.execute("UPDATE workflow_rows SET status='REJECTED' WHERE run_id=? AND request_id=?",(run,request)); record(c,run,r['task_id'],'match_rejected',{'request_id':request,'reviewer':'local-demo-user'})
        else:
            candidates=json.loads(rr['candidates_json']); candidate=next((x for x in candidates if x['id']==body.get('supplier_id')),None)
            current=c.execute('SELECT id,version FROM suppliers WHERE id=?',(body.get('supplier_id'),)).fetchone()
            if not candidate or not current or type(body.get('record_version')) is not int or candidate['version']!=body['record_version'] or current['version']!=body['record_version']: raise problem(409,'Candidate or record version changed; reset and review again')
            source=next(x for x in task['contract']['rows'] if x['request_id']==request)
            approval='selection-'+uuid.uuid4().hex[:12]
            c.execute("UPDATE workflow_rows SET status='READY_TO_WRITE',selected_id=?,selected_version=?,approval_id=?,approval_expires_at=? WHERE run_id=? AND request_id=?",(candidate['id'],candidate['version'],approval,int(time.time())+300,run,request))
            record(c,run,r['task_id'],'match_approved',{'request_id':request,'supplier_id':candidate['id'],'record_version':candidate['version'],'source_row_hash':source['row_hash'],'expected_address':source['new_shipping_address'],'contract_hash':task['contract_hash'],'reviewer':'local-demo-user','selection_id':approval,'expires_at':int(time.time())+300,'note':'Review selection only; not an executable write approval.'})
        if not c.execute("SELECT 1 FROM workflow_rows WHERE run_id=? AND status IN ('AWAITING_APPROVAL','NEEDS_REVIEW')",(run,)).fetchone(): transition(c,run,'REVIEW_READY',problem)
        c.execute('COMMIT')
    except: c.execute('ROLLBACK'); raise
    return get_run(c,run,problem)

def cancel(c,run,problem):
    c.execute('BEGIN IMMEDIATE')
    try:
        r=c.execute('SELECT * FROM workflow_runs WHERE id=?',(run,)).fetchone()
        if not r: raise problem(404,'Run not found')
        transition(c,run,'CANCELLED',problem)
        c.execute("UPDATE workflow_rows SET status='CANCELLED' WHERE run_id=? AND status IN ('PENDING','AWAITING_APPROVAL','READY_TO_WRITE','NEEDS_REVIEW')",(run,))
        c.execute('COMMIT')
    except: c.execute('ROLLBACK'); raise
    return get_run(c,run,problem)
