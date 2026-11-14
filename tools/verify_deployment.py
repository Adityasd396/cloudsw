"""Read-only health/assets check, with optional disposable two-user deployed smoke."""
import argparse
import http.cookiejar
import json
import re
import urllib.request
from urllib.parse import urlparse

def verify(base,journey=False,expected_version=None):
    if urlparse(base).scheme not in ('http','https'):raise ValueError('Use a website URL')
    base=base.rstrip('/');host=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));guest=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def request(client,path,data=None):
        req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json','Origin':base} if data is not None else {})
        with client.open(req,timeout=20) as response:
            body=response.read();return json.loads(body) if 'json' in response.headers.get('Content-Type','') else body.decode()
    health=request(host,'/api/health')
    if not {'ordered_playback_v1','safe_retries_v1'}<=set(health.get('capabilities',[])):raise ValueError('Old backend is still running')
    if expected_version and health.get('release',{}).get('version')!=expected_version:raise ValueError('A different release is running')
    page=request(host,'/')
    assets=re.findall(r'(?:src|href)="(/static/[^"\s]+)"',page)
    for asset in assets:request(host,asset)
    if journey:
        room=request(host,'/api/rooms',{})['id'];path='/api/rooms/'+room
        try:
            request(host,path,{'action':'join','name':'Deployment host'});request(guest,path,{'action':'join','name':'Deployment guest'})
            for sender,viewer,position,playing in [(host,guest,12,True),(guest,host,22,False)]:
                request(sender,path,{'action':'playback','position':position,'playing':playing})
                state=request(viewer,path)
                if state['position']!=position or bool(state['playing'])!=playing:raise ValueError('Shared controls did not match')
            request(host,path,{'action':'chat','body':'Deployment smoke'})
            if request(guest,path)['messages'][-1]['body']!='Deployment smoke':raise ValueError('Chat delivery failed')
        finally:
            request(host,path+'/leave',{});result=request(guest,path+'/leave',{})
            if not result.get('room_deleted'):raise ValueError('Final Leave did not delete the room')
    return {'ok':True,'release':health.get('release'),'assets_checked':len(assets),'disposable_journey':journey}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('url');parser.add_argument('--expected-version');parser.add_argument('--journey',action='store_true',help='Create and delete one disposable test room');args=parser.parse_args();print(json.dumps(verify(args.url,args.journey,args.expected_version),indent=2))
