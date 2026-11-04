"""Run unittest suite and export structured results without pretending skips passed."""
import json,sys,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs): super().__init__(*args,**kwargs);self.outcomes=[]
    def addSuccess(self,test): super().addSuccess(test);self.outcomes.append({'test':test.id(),'status':'PASS'})
    def addFailure(self,test,err): super().addFailure(test,err);self.outcomes.append({'test':test.id(),'status':'FAIL','detail':self._exc_info_to_string(err,test)[-3000:]})
    def addError(self,test,err): super().addError(test,err);self.outcomes.append({'test':test.id(),'status':'ERROR','detail':self._exc_info_to_string(err,test)[-3000:]})
    def addSkip(self,test,reason): super().addSkip(test,reason);self.outcomes.append({'test':test.id(),'status':'SKIP','detail':reason})
if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('usage: test_runner.py output.json')
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(verbosity=1,resultclass=Result).run(suite)
    data={'mode':'deterministic_unittest_and_scripted_browser','created_at':int(time.time()),'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'outcomes':result.outcomes}
    Path(sys.argv[1]).write_text(json.dumps(data,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
