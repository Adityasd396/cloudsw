"""120-second local two-account real decoded playback soak; not a phone certification."""
import json,os,subprocess,time
from pathlib import Path
import psutil
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));from tools.benchmark_local import summary
BASE='http://127.0.0.1:8027';output=ROOT/'audit-results/launch-soak.json'
assert urlparse(BASE).hostname=='127.0.0.1'
media=ROOT/'.openai/stream-audit/media';film=media/'soak.mp4'
if not film.exists():subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-stream_loop','8','-i',str(media/'clip.mp4'),'-t','150','-c','copy','-movflags','+faststart',str(film)],check=True)
clip=film.read_bytes();drifts=[];latencies=[];resources=[];errors=[];cpu=[];status='running'
with sync_playwright() as p:
 browser=p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required']);pages=[];contexts=[]
 for index in range(2):
  context=browser.new_context(viewport={'width':390,'height':844},has_touch=True);contexts.append(context)
  context.add_init_script("localStorage.setItem('solace-rotation','false');Object.defineProperty(document,'hidden',{get:()=>false})")
  csrf=context.request.get(BASE+'/api/me').json()['csrf'];result=context.request.post(BASE+'/api/auth/signup',data={'name':'Soak '+str(index),'email':'soak-'+str(time.time_ns())+'@example.test','password':'a local soak test password','accept_terms':'on'},headers={'X-CSRF-Token':csrf});assert result.ok,result.text()
  def serve(route):
   header=route.request.headers.get('range','')
   if header.startswith('bytes='):
    start,end=header[6:].split('-');start=int(start or 0);end=min(int(end) if end else len(clip)-1,len(clip)-1);route.fulfill(status=206,body=clip[start:end+1],headers={'Content-Type':'video/mp4','Accept-Ranges':'bytes','Content-Range':f'bytes {start}-{end}/{len(clip)}'})
   else:route.fulfill(body=clip,content_type='video/mp4')
  context.route('https://media.audit/**',serve);context.route('https://www.youtube.com/**',lambda r:r.abort())
  page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));pages.append(page)
 host,peer=pages;host.goto(BASE+'/create');host.locator('#displayName').fill('Soak A');host.locator('#setupSubmit').click();host.wait_for_selector('body.room-connected');host.evaluate("showScreen('watch')");room=host.evaluate('roomId')
 peer.goto(BASE+'/?room='+room)
 if not peer.evaluate("document.body.classList.contains('room-connected')"):
  if peer.locator('#displayName').is_visible():peer.locator('#displayName').fill('Soak B')
  peer.locator('#setupSubmit').click()
 peer.wait_for_selector('body.room-connected')
 host.evaluate("action({action:'watch',url:'https://media.audit/soak.mp4'})")
 for page in pages:page.wait_for_function('directElement&&directElement.currentTime>.2',timeout=15000)
 info=contexts[0].request.get(BASE+'/__audit__/info').json();server=psutil.Process(info['pid']);server.cpu_percent();started=time.monotonic();next_control=20;next_chat=25;iteration=0
 try:
  while time.monotonic()-started<120:
   elapsed=time.monotonic()-started;iteration+=1
   if elapsed>=next_control:
    actor=pages[(next_control//20)%2];position=actor.evaluate('player.getCurrentTime()')
    actor.evaluate('async p=>{player.pauseVideo();await sendControlIntent(p,false)}',position)
    for page in pages:page.wait_for_function('player.getPlayerState()===2',timeout=6000)
    host.wait_for_timeout(500);position+=3
    actor.evaluate('async p=>{player.seekTo(p);player.playVideo();await sendControlIntent(p,true)}',position)
    for page in pages:page.wait_for_function('player.getPlayerState()===1',timeout=6000)
    host.wait_for_timeout(1000);next_control+=20
   if elapsed>=next_chat:
    actor=pages[(next_chat//25)%2];actor.locator('#message').fill('/hug');actor.locator('.send').click();actor.locator('#message').blur()
    for page in pages:
     page.set_viewport_size({'width':844 if next_chat%2 else 390,'height':390 if next_chat%2 else 844})
    next_chat+=25
   positions=[page.evaluate('player.getCurrentTime()') for page in pages];drift=abs(positions[0]-positions[1]);drifts.append(drift)
   if drift>1.5:raise AssertionError('Drift exceeded 1.5 seconds: '+str(drift))
   began=time.perf_counter();response=contexts[0].request.get(BASE+'/api/rooms/'+room);latencies.append((time.perf_counter()-began)*1000);assert response.ok
   memory=server.memory_info().rss/1048576;resources.append(memory);cpu.append(server.cpu_percent())
   if memory>512 or cpu[-1]>300:raise AssertionError('Resource stop condition')
   assert all(not page.evaluate('!!directElement.error') for page in pages)
   if errors:raise AssertionError(errors)
   host.wait_for_timeout(1800)
  status='passed'
 finally:
  actual=time.monotonic()-started
  for context in contexts:context.request.post(BASE+'/api/rooms/'+room+'/leave',data={})
  browser.close();result={'status':status,'seconds':round(actual,2),'clients':2,'accounts':True,'actual_media':'synthetic H264/AAC 150 seconds','drift_seconds':summary(drifts),'room_roundtrip_ms':summary(latencies),'server_rss_mib':summary(resources),'server_cpu_one_core_percent':summary(cpu),'browser_errors':errors,'physical_phones':False,'controls':'pause/resume/seek every 20 seconds; hug and orientation changes every 25 seconds','limit':'Short local soak; does not certify three hours, WAN or mobile hardware'};output.write_text(json.dumps(result,indent=2));print(json.dumps(result))
