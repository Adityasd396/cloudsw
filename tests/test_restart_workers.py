"""Separate app processes share one disposable SQLite instance; no network load."""
import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class WorkerRestartTests(unittest.TestCase):
    def test_restart_and_two_process_mutations_preserve_shared_state(self):
        with tempfile.TemporaryDirectory(prefix='solace-workers-') as folder:
            env={**os.environ,'SOLACE_INSTANCE_PATH':folder,'SECRET_KEY':'isolated-worker-fixture-secret-32-characters','SOLACE_ENV':'development'}
            seed='''
import json
from app import app,db
a=app.test_client();b=app.test_client();room=a.post('/api/rooms',json={}).json['id'];url='/api/rooms/'+room
for client,name in [(a,'A'),(b,'B')]:client.post(url,json={'action':'join','name':name});client.post(url+'/game',json={'action':'join'})
game=a.get(url+'/game').json;a.post(url+'/game',json={'action':'move','cell':0,'revision':game['revision']})
with app.app_context():
 db().execute('ALTER TABLE accounts DROP COLUMN verified');db().execute('DELETE FROM launch_migrations WHERE version>=2');db().commit()
print(json.dumps({'room':room,'cookies':[a.get_cookie('session').value,b.get_cookie('session').value]}))
'''
            result=subprocess.run([sys.executable,'-B','-c',seed],cwd=ROOT,env=env,text=True,capture_output=True,timeout=20);self.assertEqual(result.returncode,0,result.stderr);data=json.loads(result.stdout)
            action='''
import json,sys
from app import app
data=json.load(sys.stdin);c=app.test_client();c.set_cookie('session',data['cookie'])
response=c.post('/api/rooms/'+data['room'],json={'action':'add','url':'aqz-KE-bpKQ','title':data['name']});assert response.status_code==200,response.text
print('ok')
'''
            processes=[subprocess.Popen([sys.executable,'-B','-c',action],cwd=ROOT,env=env,text=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(2)]
            for i,process in enumerate(processes):process.stdin.write(json.dumps({'cookie':data['cookies'][i],'room':data['room'],'name':'Worker '+str(i)}));process.stdin.flush();process.stdin.close();process.stdin=None
            for process in processes:
                out,error=process.communicate(timeout=20);self.assertEqual(process.returncode,0,error);self.assertIn('ok',out)
            probe='''
import json,sys
from app import app,db
data=json.load(sys.stdin);c=app.test_client();c.set_cookie('session',data['cookies'][0]);url='/api/rooms/'+data['room'];room=c.get(url).json
assert len(room['queue'])==2;assert c.get(url+'/game').json['board'][0]=='X'
with app.app_context():assert db().execute('SELECT MAX(version) FROM launch_migrations').fetchone()[0]==9
print('persisted')
'''
            result=subprocess.run([sys.executable,'-B','-c',probe],cwd=ROOT,env=env,input=json.dumps(data),text=True,capture_output=True,timeout=20);self.assertEqual(result.returncode,0,result.stderr);self.assertIn('persisted',result.stdout)
