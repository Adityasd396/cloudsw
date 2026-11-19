"""Two real local media players, guest upgrade and private account browser journeys."""
import io,json,time,os
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright
from media_https_fixture import MediaFixture
ROOT=Path(__file__).resolve().parents[1];BASE=os.environ.get('SOLACE_TEST_BASE','http://127.0.0.1:8017')
clip=(ROOT/'.openai/stream-audit/media/clip.mp4').read_bytes()
with MediaFixture(clip) as fixture,sync_playwright() as p:
 engine=os.environ.get('SOLACE_TEST_BROWSER','chromium');browser=getattr(p,engine).launch(args=['--autoplay-policy=no-user-gesture-required'] if engine=='chromium' else []);errors=[];contexts=[];pages=[]
 for name in ['Peach','Berry']:
  context=browser.new_context(viewport={'width':390,'height':844},has_touch=True,ignore_https_errors=True);contexts.append(context)
  context.add_init_script("localStorage.setItem('solace-rotation','false');Object.defineProperty(document,'hidden',{get:()=>false})")
  def media(route):
   requested=route.request.headers.get('range','')
   if requested.startswith('bytes='):
    start,end=requested[6:].split('-');start=int(start or 0);end=min(int(end) if end else len(clip)-1,len(clip)-1)
    route.fulfill(status=206,body=clip[start:end+1],headers={'Content-Type':'video/mp4','Accept-Ranges':'bytes','Content-Range':f'bytes {start}-{end}/{len(clip)}'})
   else:route.fulfill(body=clip,content_type='video/mp4',headers={'Accept-Ranges':'bytes'})
  context.route('https://media.audit/**',media);context.route('https://www.youtube.com/**',lambda r:r.abort())
  page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)));pages.append(page)
 host,peer=pages;host.goto(BASE);assert host.get_by_role('heading',level=1).count()==1
 host.screenshot(path=str(ROOT/'solace-public-home.png'),full_page=True)
 for width,height in [(390,844),(844,390)]:
  host.set_viewport_size({'width':width,'height':height});assert host.evaluate('document.documentElement.scrollWidth<=innerWidth')
 host.set_viewport_size({'width':390,'height':844});host.goto(BASE+'/create');host.locator('#displayName').fill('Peach');host.locator('#setupSubmit').click();host.wait_for_selector('body.room-connected');host.evaluate("showScreen('watch')");room=host.evaluate('roomId');url=BASE+'/api/rooms/'+room
 peer.goto(BASE+'/?room='+room);peer.locator('#displayName').fill('Berry');peer.locator('#setupSubmit').click();peer.wait_for_selector('body.room-connected')
 host.evaluate("url=>action({action:'watch',url})",fixture.url)
 for page in pages:
  if engine=='webkit':
   page.wait_for_function('!!directElement')
   if page.evaluate('directElement.paused'):page.locator('#toggle').click()
  try:page.wait_for_function('directElement&&directElement.currentTime>.2',timeout=12000)
  except Exception:
   print(page.evaluate("({engine:navigator.userAgent,codec:document.createElement('video').canPlayType('video/mp4'),error:directElement?.error?.message,code:directElement?.error?.code,paused:directElement?.paused,ready:directElement?.readyState,notice:document.querySelector('#playerNoticeTitle').textContent})"));raise
 host.locator('#message').fill('Draft stays here');host.locator('#message').focus();host.locator('.gesture-toggle').click();host.get_by_role('button',name='Send hug',exact=True).click()
 for page in pages:
  page.locator('.reaction-hug').wait_for();assert page.locator('.screen-reaction span').count()==28
  page.locator('.gesture-message').wait_for();assert 'Wrapping you' in page.locator('.gesture-message p').inner_text()
  assert page.locator('.gesture-message time').is_visible()
 host.wait_for_timeout(600);before=peer.evaluate('directElement.currentTime');peer.wait_for_timeout(1000);assert peer.evaluate('directElement.currentTime')>before+.5
 assert host.locator('#message').input_value()=='Draft stays here';host.locator('#message').blur()
 for page in pages:page.locator('.reaction-hug').wait_for(state='detached',timeout=4000);page.locator('.gesture-message').wait_for(state='detached',timeout=1000)
 # Real decoded playback has already started a guest history sample; another observed sample credits elapsed time.
 host.evaluate("async()=>{const me=await(await fetch('/api/me')).json();await fetch('/api/me/watch',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':me.csrf},body:JSON.stringify({room:roomId,active:!directElement.paused,title:'Synthetic sunset'})})}")
 host.goto(BASE+'/signup');host.locator('[name=name]').fill('Public Peach');host.locator('[name=email]').fill('peach-'+str(time.time_ns())+'@example.test');host.locator('[name=password]').fill('a good public test password');host.locator('input[type=checkbox]').check();host.locator('#authForm button').click();host.wait_for_url('**/home');host.goto(BASE+'/account')
 assert host.locator('[name=name]').input_value()=='Public Peach';assert host.locator('#accountCreated').inner_text().startswith('Joined ')
 host.locator('[name=name]').fill('Peach Rose');host.locator('#profileForm button').click();host.get_by_text('Name saved.',exact=True).wait_for()
 image=io.BytesIO();Image.new('RGB',(300,300),'pink').save(image,'PNG');host.locator('[name=picture]').set_input_files({'name':'picture.png','mimeType':'image/png','buffer':image.getvalue()});host.locator('#pictureForm button').click();host.get_by_text('Picture updated.',exact=True).wait_for()
 host.screenshot(path=str(ROOT/'solace-public-profile.png'),full_page=True)
 host.goto(BASE+'/history');host.locator('.history-entry').wait_for();assert host.locator('.history-entry').count()==1;assert host.locator('#activityTable tr').count()>=28
 assert 'Berry' in host.locator('.history-entry').inner_text();assert peer.request.get(BASE+'/api/me/history').ok
 host.screenshot(path=str(ROOT/'solace-public-history.png'),full_page=True)
 host.locator('.history-entry button').click();host.get_by_text('No viewing sessions in these dates.',exact=False).wait_for()
 host.goto(BASE+'/account');host.locator('#removePicture').click();host.get_by_text('Picture removed.',exact=True).wait_for()
 host.locator('#signout').click();host.wait_for_url('**/signin');assert host.request.get(BASE+'/api/me/history').status==401
 assert not errors,errors
 peer.request.post(url+'/leave',data={});browser.close()
 print(json.dumps({'passed':True,'public_home_portrait_landscape':True,'shared_three_second_hug_chat_and_stream':True,'draft_focus_and_video_preserved':True,'guest_upgrade_preserves_real_history':True,'profile_picture_edit_remove':True,'history_graph_private_delete':True,'signout_revokes_access':True,'physical_phones':False}))
