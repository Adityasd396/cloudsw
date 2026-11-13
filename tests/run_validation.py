"""Bounded validation: live API journeys plus isolated local load/error checks.

Run from the project root: python -B tests/run_validation.py --live
No live load test is performed. Live mutations use a newly created test room.
"""
import concurrent.futures
import http.cookiejar
import json
from pathlib import Path
import statistics
import sys
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
RESULTS=[]

def record(area,name,passed,detail=''):
    RESULTS.append(dict(area=area,name=name,passed=bool(passed),detail=detail))
    print(f'{"PASS" if passed else "FAIL"} [{area}] {name} {detail}',flush=True)

def local_checks():
    from test_app import WatchPartyTests
    from app import app,db
    fixture=WatchPartyTests('test_validation_and_access')
    fixture.setUp()
    try:
        cookie=fixture.host.get_cookie('session').value
        def poll(_):
            client=app.test_client();client.set_cookie('session',cookie)
            start=time.perf_counter();response=client.get(fixture.url)
            return response.status_code,(time.perf_counter()-start)*1000
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            samples=list(pool.map(poll,range(120)))
        times=sorted(t for _,t in samples)
        record('local-performance','120 room reads / 4 concurrent workers',all(code==200 for code,_ in samples),f'median={statistics.median(times):.1f}ms p95={times[int(len(times)*.95)-1]:.1f}ms max={max(times):.1f}ms; Flask test client, not internet latency')
        def add(i):
            client=app.test_client();client.set_cookie('session',cookie)
            return client.post(fixture.url,json={'action':'add','url':'aqz-KE-bpKQ','title':f'Concurrent {i}'}).status_code
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            writes=list(pool.map(add,range(20)))
        queue=fixture.host.get(fixture.url).json['queue']
        record('local-concurrency','20 concurrent playlist writes retain every item',all(code==200 for code in writes) and len(queue)==20 and len({v['id'] for v in queue})==20)
        for i in range(80):fixture.host.post(fixture.url,json={'action':'add','url':'aqz-KE-bpKQ'})
        overflow=fixture.host.post(fixture.url,json={'action':'add','url':'aqz-KE-bpKQ'})
        record('local-bounds','Playlist enforces 100-item bound',overflow.status_code==400 and len(fixture.host.get(fixture.url).json['queue'])==100)
        malformed=fixture.host.post(fixture.url,data='{bad',content_type='application/json')
        oversized=fixture.host.post(fixture.url,data=json.dumps({'action':'chat','body':'x'*20000}),content_type='application/json')
        record('local-validation','Malformed JSON rejected without server error',malformed.status_code==400)
        record('local-validation','Oversized requests rejected',oversized.status_code==413)
        response=fixture.host.post(fixture.url,json={'action':'playback','position':0,'playing':True},headers={'Origin':'https://untrusted.example'})
        record('local-security','Cross-origin mutations rejected',response.status_code==403)
        for action in ['chat','playback','move','transfer_host']:
            response=app.test_client().post(fixture.url,json={'action':action})
            record('local-security',f'Unjoined caller cannot {action}',response.status_code==403)
        profile=fixture.host.get('/api/profile')
        record('local-security','Session cookie has HttpOnly and SameSite',all(text in profile.headers.get('Set-Cookie','') for text in ['HttpOnly','SameSite=Lax']))
        for action in ['transfer_host']:
            response=fixture.guest.post(fixture.url,json={'action':action,'url':'aqz-KE-bpKQ','id':queue[0]['id'],'direction':'up'})
            record('local-security',f'Guest cannot {action}',response.status_code==403)
    finally:fixture.tearDown()

def live_checks():
    base='https://aditya211.pythonanywhere.com'
    def client():return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    host,guest=client(),client()
    def request(c,path,data=None):
        req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'} if data is not None else {})
        start=time.perf_counter()
        try:
            with c.open(req,timeout=15) as response:return response.status,json.load(response),(time.perf_counter()-start)*1000
        except urllib.error.HTTPError as error:
            try:body=json.load(error)
            except Exception:body={}
            return error.code,body,(time.perf_counter()-start)*1000
    latencies=[];health_statuses=[]
    for _ in range(8):
        status,health,elapsed=request(host,'/api/health');latencies.append(elapsed);health_statuses.append(status)
    ordered=sorted(latencies)
    record('live-smoke','Health responds',status==200 and health.get('status')=='ok')
    record('live-performance','8 sequential health responses',all(s==200 for s in health_statuses),f'median={statistics.median(latencies):.0f}ms max={ordered[-1]:.0f}ms (8 samples; includes internet/TLS, not a capacity test)')
    status,created,_=request(host,'/api/rooms',{})
    record('live-functional','Create room',status==201)
    if status!=201:return
    path='/api/rooms/'+created['id']
    record('live-functional','Six-digit code',len(created['id'])==6 and created['id'].isdigit())
    try:
        status,state,_=request(host,path,{'action':'join','name':'Validation Host'})
        record('live-functional','Creator control metadata',status==200 and state.get('is_host') is True and state.get('can_control') is True)
        status,state,_=request(guest,path,{'action':'join','name':'Validation Guest'})
        record('live-functional','Guest joins',status==200 and state.get('is_host') is False)
        request(guest,path,{'action':'chat','body':'Validation message 🥰'})
        _,state,_=request(host,path)
        record('live-functional','Chat shared',any(m['body']=='Validation message 🥰' for m in state.get('messages',[])))
        request(guest,path,{'action':'typing','active':True});_,state,_=request(host,path)
        record('live-functional','Typing shared','Validation Guest' in state.get('typing',[]))
        request(guest,path,{'action':'typing','active':False})
        request(host,path,{'action':'playback','position':40,'playing':False});_,paused,_=request(guest,path)
        record('live-functional','Pause shared',paused.get('position')==40 and paused.get('playing')==0)
        request(host,path,{'action':'playback','position':40,'playing':True});_,resumed,_=request(guest,path)
        record('live-functional','Resume shared',resumed.get('playing')==1)
        status,_,_=request(host,path,{'action':'playback','position':40,'playing':False,'compact':True,'expected_updated':paused.get('updated')})
        record('live-regression','Stale pause rejected after resume',status==409,f'HTTP {status}')
        _,state,_=request(guest,path);record('live-regression','Resume survives old pause',state.get('playing')==1)
        request(host,path,{'action':'playback','position':100,'playing':False});_,state,_=request(guest,path)
        record('live-functional','Seek shared',state.get('position')==100)
        status,_,_=request(guest,path,{'action':'playback','position':0,'playing':True})
        record('live-functional','Guest playback allowed',status==200)
        request(guest,path,{'action':'add','url':'aqz-KE-bpKQ','title':'A'})
        _,state,_=request(guest,path,{'action':'add','url':'eRsGyueVLvQ','title':'B'})
        record('live-functional','Guest playlist additions',len(state.get('queue',[]))==2)
        if len(state.get('queue',[]))==2:
            second=state['queue'][1]['id'];status,state,_=request(host,path,{'action':'move','id':second,'direction':'up'})
            record('live-functional','Playlist reorder',status==200 and state['queue'][0]['id']==second)
            _,state,_=request(host,path,{'action':'next'});record('live-functional','Next uses order',state.get('video')=='eRsGyueVLvQ')
        status,_,_=request(host,path,{'action':'ad_status','active':True});_,state,_=request(guest,path)
        record('live-functional','Ad notice shared',status==200 and state.get('host_ad') is True)
        request(host,path,{'action':'ad_status','active':False})
        request(guest,path+'/presence',{'active':False});_,state,_=request(host,path)
        person=next((p for p in state.get('participants',[]) if p['name']=='Validation Guest'),{})
        record('live-functional','Inactive red status',person.get('status')=='inactive')
        request(guest,path+'/presence',{'active':True});_,state,_=request(host,path)
        target=next((m for m in state.get('members',[]) if m['name']=='Validation Guest'),None)
        if target:
            status,_,_=request(host,path,{'action':'transfer_host','member_id':target['member_id']});_,state,_=request(guest,path)
            record('live-functional','Host role transfers',status==200 and state.get('is_host') is True)
            record('live-functional','New host controls enabled',state.get('can_control') is True)
        request(guest,path,{'action':'playback','position':0,'playing':False})
    finally:
        first_status,_,_=request(host,path+'/leave',{});status,left,_=request(guest,path+'/leave',{})
        record('live-lifecycle','Last leave deletes room',status==200 and left.get('room_deleted') is True,f'first leave HTTP {first_status}; last leave HTTP {status}')
        room_status,state,_=request(guest,path)
        record('live-lifecycle','Deleted invite cannot reopen',room_status==404,f'HTTP {room_status}')
        if not left.get('room_deleted'):
            request(host,path+'/presence',{'active':False});request(guest,path+'/presence',{'active':False})
    with host.open(base,timeout=15) as response:
        page=response.read().decode();record('live-smoke','Home page HTTP 200',response.status==200)
    import re
    for asset in re.findall(r'(?:src|href)="(/static/[^\"]+)"',page):
        try:
            with host.open(base+asset,timeout=15) as response:record('live-assets',asset.split('?')[0],response.status==200)
        except Exception as error:record('live-assets',asset.split('?')[0],False,type(error).__name__)

if __name__=='__main__':
    try:
        live_checks() if '--live' in sys.argv else local_checks()
    except Exception as error:
        record('runner','Uncompleted checks',False,type(error).__name__+': '+str(error))
    output=ROOT/('validation-live.json' if '--live' in sys.argv else 'validation-local.json')
    output.write_text(json.dumps({'results':RESULTS,'passed':sum(r['passed'] for r in RESULTS),'total':len(RESULTS)},indent=2))
    print(f'RESULT {sum(r["passed"] for r in RESULTS)}/{len(RESULTS)}',flush=True)
    sys.exit(0 if RESULTS and all(r['passed'] for r in RESULTS) else 1)
