"""Owner-created disposable server only; verifies signal exit and committed state."""
import json,os,signal,socket,sqlite3,subprocess,sys,tempfile,time
from pathlib import Path
import requests,psutil
from contextlib import closing
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='solace-shutdown-') as folder:
 env={**os.environ,'SOLACE_INSTANCE_PATH':folder,'SECRET_KEY':'isolated-shutdown-secret-32-characters','SOLACE_ENV':'development','COOKIE_SECURE':'0','PORT':'8040','HOST':'127.0.0.1'}
 process=subprocess.Popen([sys.executable,'-B',str(ROOT/'serve.py')],env=env,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0))
 try:
  session=requests.Session();base='http://127.0.0.1:8040';deadline=time.monotonic()+15
  while time.monotonic()<deadline:
   try:
    if session.get(base+'/api/health',timeout=.25).status_code==200:break
   except requests.RequestException:time.sleep(.05)
  else:raise TimeoutError('Local startup timeout')
  room=session.post(base+'/api/rooms',json={},timeout=3).json()['id'];session.post(base+'/api/rooms/'+room,json={'action':'join','name':'Shutdown fixture'},timeout=3)
  session.post(base+'/api/rooms/'+room,json={'action':'add','url':'aqz-KE-bpKQ'},timeout=3)
  began=time.monotonic();process.send_signal(signal.CTRL_BREAK_EVENT if os.name=='nt' else signal.SIGTERM);out,error=process.communicate(timeout=15);elapsed=time.monotonic()-began
  assert process.returncode==0,(process.returncode,error)
  with closing(sqlite3.connect(Path(folder)/'afterglow.db')) as connection:
   assert connection.execute('PRAGMA quick_check').fetchone()[0]=='ok';assert connection.execute('SELECT count(*) FROM queue WHERE room=?',(room,)).fetchone()[0]==1
  with socket.socket() as sock:sock.settimeout(.3);assert sock.connect_ex(('127.0.0.1',8040))!=0
  result={'passed':True,'shutdown_seconds':round(elapsed,3),'signal':'CTRL_BREAK' if os.name=='nt' else 'SIGTERM','committed_state_retained':True,'listener_released':True}
  (ROOT/'audit-results/shutdown.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
 finally:
  if process.poll() is None:
   children=psutil.Process(process.pid).children(recursive=True)
   for child in children:child.terminate()
   process.terminate();process.wait(5)
