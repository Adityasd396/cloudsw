"""Accelerated 3-hour protocol replay, not a physical-phone or wall-clock soak.

Samples two device sessions every five simulated seconds, with chat, controls,
ads, background gaps, network gaps, queue changes and saved-data checks.
"""
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import app,db
from test_app import WatchPartyTests


def main():
    fixture=WatchPartyTests('test_validation_and_access');fixture.setUp()
    clients=[fixture.host,fixture.guest];names=['Android model','iPhone model']
    for client,name in zip(clients,names):client.post(fixture.url,json={'action':'join','name':name})
    snapshots=[None,None];history=[[],[]];cursors=[0,0];assertions=0;polls=0;chat_count=0;bytes_delta=0
    started=time.perf_counter();origin=time.time();now=[origin];error=None;final={}

    def check(condition,label):
        nonlocal assertions
        assertions+=1
        if not condition:raise AssertionError(label)

    def post(index,data,suffix=''):
        response=clients[index].post(fixture.url+suffix,json=data)
        check(response.status_code==200,f'{suffix or data.get("action")} HTTP {response.status_code}: {response.json}')
        return response.json

    def available(index,second):
        gaps=[(1200,1230),(4200,4290),(5400,5430)] if index==0 else [(2400,2475),(5400,5430),(8400,8490)]
        return not any(start<=second<end for start,end in gaps)

    try:
        with patch('app.time.time',side_effect=lambda:now[0]):
            for second in range(0,10801,5):
                now[0]=origin+second
                active=[available(i,second) for i in range(2)]
                for index in range(2):
                    if second and active[index]!=available(index,second-5):
                        # Screen background can report inactivity; network loss cannot.
                        if second not in (4200,8400):post(index,{'active':active[index]},'/presence')
                    if not active[index]:continue
                    response=clients[index].get(fixture.url+'?after='+str(cursors[index]));polls+=1;bytes_delta+=len(response.data)
                    check(response.status_code==200,'Active device lost its room')
                    state=response.json;check(state['messages_delta'],'Delta flag missing')
                    check(all(m['id']>cursors[index] for m in state['messages']),'Repeated chat history in delta')
                    merged={m['id']:m for m in history[index]}
                    for message in state['messages']:merged[message['id']]=message
                    history[index]=sorted(merged.values(),key=lambda m:m['id'])[-100:]
                    if history[index]:cursors[index]=history[index][-1]['id']
                    check(len(history[index])<=100,'Visible message history grew without bound')
                    snapshots[index]=state
                if not any(active):continue
                actor=0 if active[0] else 1
                if second%15==0:
                    author=(second//15)%2
                    if not active[author]:author=actor
                    text=f'{names[author]} at {second}s '+'x'*160
                    post(author,{'action':'chat','body':text});chat_count+=1
                if second%300==0:
                    post(actor,{'action':'add','url':'aqz-KE-bpKQ','title':f'Queued {second}'})
                    post(actor,{'action':'ad_status','active':True})
                if second%300==10:post(actor,{'action':'ad_status','active':False})
                if second%600==0:
                    state=clients[actor].get(fixture.url).json;token=state['playback_id']
                    post(actor,{'action':'next','expected_playback_id':token})
                    duplicate=clients[actor].post(fixture.url,json={'action':'next','expected_playback_id':token})
                    check(duplicate.status_code==409,'Duplicate end skipped a song')
                if second%600 in (120,125):
                    post(actor,{'action':'playback','position':max(0,second-30),'playing':second%600==125})
                if active[0]:
                    state=clients[0].get(fixture.url).json
                    position=state['position']+max(0,now[0]-state['updated'])*bool(state['playing'])
                    post(0,{'action':'playback','position':position,'playing':bool(state['playing']),'expected_updated':state['updated'],'compact':True})
                if second%1800==0:print(f'PASS simulated {second//60}/180 minutes; polls={polls}; chat={chat_count}',flush=True)
            now[0]=origin+10805
            for index in range(2):
                response=clients[index].get(fixture.url+'?after='+str(cursors[index]));state=response.json
                check(response.status_code==200,'Final room state missing')
                check(clients[index].get('/api/profile').json['name']==names[index],'Device session identity changed')
                check(state['can_control'],'Shared controls lost after three hours')
                check(len(state['participants'])==2,'Device membership changed')
            full=clients[0].get(fixture.url);delta=clients[0].get(fixture.url+'?after='+str(cursors[0]))
            check(len(full.json['messages'])==100,'Final visible history is not bounded at 100')
            with app.app_context():
                stored=db().execute('SELECT count(*) FROM messages').fetchone()[0]
                check(stored==chat_count,'Saved chat messages were lost')
                final={'stored_messages':stored,'profiles':db().execute('SELECT count(*) FROM profiles').fetchone()[0],'queue_entries':db().execute('SELECT count(*) FROM queue').fetchone()[0]}
            final.update(full_snapshot_bytes=len(full.data),final_delta_bytes=len(delta.data),total_delta_response_bytes=bytes_delta)
            post(0,{},'/leave');last=post(1,{},'/leave');check(last['room_deleted'],'Last Leave did not delete the room')
            check(clients[0].get(fixture.url).status_code==404,'Deleted room reopened')
    except Exception as exception:error=type(exception).__name__+': '+str(exception)
    finally:
        elapsed=time.perf_counter()-started
        sizes={file.name:file.stat().st_size for file in Path(app.instance_path).glob('*.db')}
        fixture.tearDown()
    report={'kind':'accelerated protocol replay','physical_devices':False,'simulated_seconds':10800,'sampling_interval_seconds':5,'elapsed_seconds':round(elapsed,2),'polls':polls,'assertions':assertions,'passed':error is None,'error':error,'final':final,'database_file_bytes':sizes}
    (ROOT/'long-session-backend-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)
    return 0 if error is None else 1


if __name__=='__main__':raise SystemExit(main())
