"""Real HTTP smoke journey against Waitress, using disposable data only.

python -B tests/run_local_smoke.py --serve --port 8017
The optional --serve mode leaves the test app open for browser verification.
Its password is a public test fixture, never a real administrator credential.
"""
from contextlib import closing
import sqlite3
import argparse
import http.cookiejar
import json
from pathlib import Path
import re
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import app
from test_app import WatchPartyTests
from waitress import create_server
from werkzeug.security import generate_password_hash

PASSWORD='Disposable-Smoke-Only-2026!'
RESULTS=[]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def client():
    jar=http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(jar),NoRedirect()),jar


def check(name,passed):
    RESULTS.append({'name':name,'passed':bool(passed)})
    print(('PASS ' if passed else 'FAIL ')+name,flush=True)
    if not passed:raise AssertionError(name)


def journey(base):
    admin,jar=client();host,_=client();guest,_=client()
    def request(c,path,data=None,form=False,origin=None,extra=None):
        headers=dict(extra or {})
        if data is not None:
            headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json'
            body=urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode()
        else:body=None
        if origin is not None:headers['Origin']=origin
        req=urllib.request.Request(base+path,data=body,headers=headers)
        try:response=c.open(req,timeout=15)
        except urllib.error.HTTPError as error:response=error
        with response:
            raw=response.read();status=response.code;headers=response.headers
        try:value=json.loads(raw)
        except (ValueError,UnicodeDecodeError):value=raw.decode('utf-8',errors='replace')
        return status,value,headers

    def login():
        status,page,headers=request(admin,'/ops/solace')
        check('Admin GET preserves same-origin form policy',status==200 and headers['Referrer-Policy']=='same-origin')
        token=re.search(r'name="csrf" value="([^"]+)"',page).group(1)
        status,_,headers=request(admin,'/ops/solace',{'csrf':token,'password':PASSWORD},form=True,origin=base)
        check('Admin login redirects to private dashboard',status==303 and headers['Location']=='/ops/solace')
        return request(admin,'/ops/solace')

    status,page,_=request(host,'/')
    check('Home page loads',status==200 and 'Solace' in page)
    health=request(host,'/api/health')[1]
    check('Modern reliability capabilities and reconnect grace',{'ordered_playback_v1','safe_retries_v1'}<=set(health['capabilities']) and health['reconnect_grace_seconds']==1800)
    assets=set(re.findall(r'(?:src|href)="(/static/[^\"]+)"',page))
    check('All home script/style assets load',all(request(host,asset)[0]==200 for asset in assets))
    for path in ('/ops/solace/data','/ops/solace/chat-backup.json'):
        check('Unauthenticated access denied: '+path,request(admin,path)[0]==401)
    _,page,_=request(admin,'/ops/solace');csrf=re.search(r'name="csrf" value="([^"]+)"',page).group(1)
    check('Missing login CSRF rejected',request(admin,'/ops/solace',{'password':PASSWORD},form=True,origin=base)[0]==403)
    wrong_port=base.rsplit(':',1)[0]+(':'+str(8001 if urllib.parse.urlparse(base).port==8000 else 8000))
    for origin in ('null','http://evil.invalid',wrong_port):
        check('Invalid Origin rejected: '+origin,request(admin,'/ops/solace',{'csrf':csrf,'password':PASSWORD},form=True,origin=origin)[0]==403)
    check('Wrong password rejected',request(admin,'/ops/solace',{'csrf':csrf,'password':'incorrect'},form=True,origin=base)[0]==401)
    status,dashboard,_=login()
    check('Dashboard HTML and controls render',status==200 and 'Lock panel' in dashboard and 'Chat backup' in dashboard)
    check('Dashboard JavaScript loads',request(admin,'/static/admin.js')[0]==200)
    status,stats,headers=request(admin,'/ops/solace/data')
    check('Authenticated stats are available and non-cacheable',status==200 and stats['status']=='online' and headers['Cache-Control']=='no-store')
    check('Reliability aggregates stay behind admin login','reliability' in stats)
    check('Logout without CSRF rejected',request(admin,'/ops/solace/logout',{},form=True,origin=base)[0]==403)
    csrf=re.search(r'name="csrf" value="([^"]+)"',dashboard).group(1)
    check('Admin logout succeeds',request(admin,'/ops/solace/logout',{'csrf':csrf},form=True,origin=base)[0]==303)
    check('Stats inaccessible after logout',request(admin,'/ops/solace/data')[0]==401)
    check('Backup inaccessible after logout',request(admin,'/ops/solace/chat-backup.json')[0]==401)
    check('Login screen restored after logout','Unlock panel' in request(admin,'/ops/solace')[1])
    login()
    with closing(sqlite3.connect(Path(app.instance_path)/'solace-admin.db')) as connection:
        connection.execute('UPDATE admin_sessions SET expires=?',(time.time()-1,));connection.commit()
    check('Expired admin session denied',request(admin,'/ops/solace/data')[0]==401)
    login()

    status,created,_=request(host,'/api/rooms',{},origin=base)
    check('Create room',status==201 and len(created['id'])==6)
    path='/api/rooms/'+created['id']
    for c,name in ((host,'Smoke Host'),(guest,'Smoke Guest')):
        check(name+' joins',request(c,path,{'action':'join','name':name},origin=base)[0]==200)
    _,sent,_=request(host,path,{'action':'chat','body':'Smoke hello'},origin=base)
    quote=sent['messages'][-1]['id']
    _,reply,_=request(guest,path,{'action':'chat','body':'Smoke reply','reply_to':quote},origin=base)
    check('Chat and quoted replies shared',reply['messages'][-1]['reply']['id']==quote)
    _,state,_=request(host,path)
    check('Sender identity and host crown metadata',state['messages'][0]['you'] and state['messages'][0]['is_host'] and not state['messages'][1]['you'])
    request(guest,path,{'action':'typing','active':True},origin=base)
    check('Typing indicator shared','Smoke Guest' in request(host,path)[1]['typing'])
    request(guest,path,{'action':'playback','position':30,'playing':False},origin=base)
    check('Guest pause and seek shared',request(host,path)[1]['position']==30)
    _,paused,_=request(host,path)
    request(host,path,{'action':'playback','position':30,'playing':True},origin=base)
    check('Stale pause cannot undo Resume',request(guest,path,{'action':'playback','position':30,'playing':False,'expected_updated':paused['updated']},origin=base)[0]==409)
    for title in ('First','Second'):request(guest,path,{'action':'add','url':'aqz-KE-bpKQ','title':title},origin=base)
    _,state,_=request(guest,path)
    request(guest,path,{'action':'move','id':state['queue'][1]['id'],'direction':'up'},origin=base)
    check('Guest can reorder playlist',request(host,path)[1]['queue'][0]['title']=='Second')
    token=state['playback_id'];request(guest,path,{'action':'next','expected_playback_id':token},origin=base)
    check('Duplicate end notification cannot skip another song',request(host,path,{'action':'next','expected_playback_id':token},origin=base)[0]==409 and len(request(host,path)[1]['queue'])==1)
    request(guest,path,{'action':'ad_status','active':True},origin=base)
    check('Guest ad alert reaches other participant',request(host,path)[1]['ad_alerts'][0]['name']=='Smoke Guest')
    endpoint=path+'/game';request(host,endpoint,{'action':'join'},origin=base);_,game,_=request(guest,endpoint,{'action':'join'},origin=base)
    for c,cell in ((host,0),(guest,3),(host,1),(guest,4),(host,2)):
        status,game,_=request(c,endpoint,{'action':'move','cell':cell,'revision':game['revision']},origin=base)
        check('Game move '+str(cell),status==200)
    check('Game winner synchronizes',request(guest,endpoint)[1]['winner']=='X')
    hoops=path+'/basketball'
    check('Basketball first player joins',request(host,hoops,{'action':'join'},origin=base)[0]==200)
    status,basket,_=request(guest,hoops,{'action':'join'},origin=base)
    check('Basketball second player joins',status==200 and len(basket['players'])==2)
    shot={'action':'shoot','aim':.5,'revision':basket['revision']}
    status,basket,_=request(host,hoops,shot,origin=base)
    check('Basketball love goal reaches both players',status==200 and basket['shot']['goal'] and request(guest,hoops)[1]['scores']['X']==1)
    check('Basketball duplicate shot cannot score twice',request(host,hoops,shot,origin=base)[0]==409)
    for actor,viewer,position,playing in ((host,guest,45,True),(guest,host,45,False),(host,guest,75,False),(guest,host,65,True)):
        status,_,_=request(actor,path,{'action':'playback','position':position,'playing':playing},origin=base)
        observed=request(viewer,path)[1]
        check('Two-user playback sync '+str(position)+' '+str(playing),status==200 and observed['position']==position and bool(observed['playing'])==playing)
    check('Basketball assets load',all(request(host,asset)[0]==200 for asset in ['/static/game.html','/static/basketball.js','/static/basketball.css','/static/tictactoe.html']))
    replay={'action':'chat','body':'Exactly one acknowledged message'}
    header={'X-Request-ID':'http-retry-chat-0001'}
    request(host,path,replay,origin=base,extra=header);status,snapshot,_=request(host,path,replay,origin=base,extra=header)
    check('Lost-response chat retry delivers once',status==200 and sum(m['body']==replay['body'] for m in snapshot['messages'])==1)
    count=len(snapshot['queue']);header={'X-Request-ID':'http-retry-add-0001'}
    for _ in range(2):status,snapshot,_=request(guest,path,{'action':'add','url':'aqz-KE-bpKQ'},origin=base,extra=header)
    check('Video-add retry has one effect',status==200 and len(snapshot['queue'])==count+1)
    revision=snapshot['playback_revision']
    status,clock,_=request(guest,path,{'action':'playback','position':65,'playing':False,'compact':True,'expected_revision':revision},origin=base)
    check('Playback command receives a server revision',status==200 and clock['playback_revision']==revision+1)
    status,_,_=request(host,path,{'action':'playback','position':0,'playing':True,'source':'observation','expected_revision':revision},origin=base)
    check('Old player observation cannot override a newer command',status==409 and not request(guest,path)[1]['playing'])
    status,_,headers=request(host,'/static/media/for-jaanu.mp4',extra={'Range':'bytes=0-1023'})
    check('Love video supports byte-range playback',status==206 and headers['Content-Range'].startswith('bytes 0-1023/'))
    request(host,path+'/leave',{},origin=base);_,left,_=request(guest,path+'/leave',{},origin=base)
    check('Last participant leaving deletes room',left['room_deleted'] and request(host,path)[0]==404)
    check('Deleted room game inaccessible',request(host,endpoint)[0]==404)
    status,backup,_=request(admin,'/ops/solace/chat-backup.json')
    check('Private backup survives public room deletion',status==200 and len(backup['messages'])>=2)
    _,dashboard,_=request(admin,'/ops/solace');csrf=re.search(r'name="csrf" value="([^"]+)"',dashboard).group(1)
    request(admin,'/ops/solace/logout',{'csrf':csrf},form=True,origin=base)
    check('Final logout closes protected access',request(admin,'/ops/solace/data')[0]==401)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--serve',action='store_true');parser.add_argument('--port',type=int,default=0);args=parser.parse_args()
    fixture=WatchPartyTests('test_validation_and_access');fixture.setUp()
    fixture.host.post(fixture.url+'/leave',json={});fixture.guest.post(fixture.url+'/leave',json={})
    app.secret_key=secrets.token_hex(32);app.config.update(TESTING=False,SESSION_COOKIE_NAME='solace_smoke_session',OPS_PASSWORD_HASH=generate_password_hash(PASSWORD,method='scrypt'))
    server=create_server(app,host='127.0.0.1',port=args.port,threads=4,channel_timeout=15)
    base='http://127.0.0.1:'+str(server.effective_port)
    thread=threading.Thread(target=server.run,daemon=True);thread.start();success=False
    try:
        journey(base);success=True
    except Exception as error:
        RESULTS.append({'name':'Uncompleted smoke journey','passed':False,'detail':type(error).__name__+': '+str(error)})
        print(type(error).__name__+': '+str(error),flush=True)
    finally:
        report={'base':base,'passed':sum(r['passed'] for r in RESULTS),'total':len(RESULTS),'results':RESULTS}
        (ROOT/'local-http-smoke-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('RESULT '+str(report['passed'])+'/'+str(report['total']),flush=True)
    try:
        if args.serve and success:
            print('BROWSER TEST READY '+base+'/ops/solace (disposable data)',flush=True)
            while True:time.sleep(1)
    except KeyboardInterrupt:pass
    finally:
        server.close();server.task_dispatcher.shutdown();thread.join(timeout=2);fixture.tearDown()
    return 0 if success else 1


if __name__=='__main__':raise SystemExit(main())
