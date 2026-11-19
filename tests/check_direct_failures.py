"""App adapter errors, user retry and non-seekable progressive delivery."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:8017';clip=(ROOT/'.openai/stream-audit/media/clip.mp4').read_bytes()
with sync_playwright() as p:
 browser=p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required']);context=browser.new_context();errors=[];valid=False
 def media(route):
  if not valid:route.fulfill(status=404,body=b'missing')
  else:
   requested=route.request.headers.get('range','bytes=0-')[6:];start,end=requested.split('-');start=int(start or 0);end=int(end) if end else len(clip)-1
   route.fulfill(status=206,body=clip[start:end+1],headers={'Content-Type':'video/mp4','Accept-Ranges':'bytes','Content-Range':f'bytes {start}-{end}/{len(clip)}'})
 context.route('https://media.failure/**',media)
 page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.route('https://www.youtube.com/**',lambda r:r.abort());page.goto(BASE+'/create');page.locator('#displayName').fill('Synthetic');page.locator('#setupSubmit').click();page.wait_for_selector('body.room-connected');page.evaluate("showScreen('watch')");room=page.evaluate('roomId')
 page.evaluate("action({action:'watch',url:'https://media.failure/missing.mp4'})");page.locator('#playerNotice').wait_for();page.wait_for_function("document.querySelector('#playerNoticeTitle').textContent.includes('could not play')")
 valid=True;page.locator('#retryYoutube').click();page.wait_for_function('directElement.currentTime>.1')
 page.locator('#toggle').click();page.wait_for_function('directElement.paused');page.locator('#toggle').click();page.wait_for_function('!directElement.paused')
 # A non-seekable source must not be reset to zero by automatic drift correction.
 page.evaluate('''()=>{Object.defineProperty(directElement,'seekable',{configurable:true,value:{length:0}});state.position=10;state.server_time=state.updated;window.seekCount=0;const original=player.seekTo;player.seekTo=(...args)=>{seekCount++;return original(...args)};synchronize(true)}''');assert page.evaluate('seekCount')==0
 assert not errors,errors
 page.request.post(BASE+'/api/rooms/'+room+'/leave',data={});browser.close();print(json.dumps({'passed':True,'missing_source_notice':True,'user_retry_recovers':True,'pause_resume':True,'nonseekable_drift_guard':True,'physical_phones':False}))
