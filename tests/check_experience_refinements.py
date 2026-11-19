"""Two Chromium participants; keyboard models are simulated, not physical phones."""
import hashlib,json,time,re,os
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];BASE=os.environ.get('SOLACE_TEST_BASE','http://127.0.0.1:8017')
STUB='''()=>{window.media={position:0,playing:false,at:performance.now()};const current=()=>media.position+(media.playing?(performance.now()-media.at)/1000:0),set=(position,playing)=>{media.position=position;media.playing=playing;media.at=performance.now()};player={getCurrentTime:current,getPlayerState:()=>media.playing?1:2,getDuration:()=>3600,getVideoData:()=>({video_id:state.video,title:'Test stream'}),seekTo:p=>set(p,media.playing),playVideo:()=>set(current(),true),pauseVideo:()=>set(current(),false),loadVideoById:v=>set(v.startSeconds,true),cueVideoById:v=>set(v.startSeconds,false),isMuted:()=>false,mute(){},unMute(){}};ready=true;playerNotice.hidden=true;document.querySelector('#playerPlaceholder').style.display='none';pageRecovery.reset();synchronize(true);window.keptStage=videoStage}'''
results=[]
with sync_playwright() as p:
 browser=getattr(p,os.environ.get('SOLACE_TEST_BROWSER','chromium')).launch();errors=[]
 admin=browser.new_context().request
 login=admin.get(BASE+'/ops/solace');token=re.search(r'name="csrf" value="([^"]+)"',login.text()).group(1)
 assert admin.post(BASE+'/ops/solace',form={'csrf':token,'password':'Disposable-Smoke-Only-2026!'},max_redirects=0).status==303
 dashboard=admin.get(BASE+'/ops/solace');token=re.search(r'name="csrf" value="([^"]+)"',dashboard.text()).group(1)
 assert admin.post(BASE+'/ops/solace/settings',data={'love_enabled':True},headers={'X-CSRF-Token':token}).ok
 for model in ['iphone-viewport','android-resize']:
  pages=[]
  for name in ['Peach','Berry']:
   c=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
   c.add_init_script('''localStorage.setItem('solace-rotation','false');Object.defineProperty(document,'hidden',{get:()=>false});const v=new EventTarget();Object.assign(v,{height:844,width:390,offsetTop:0,scale:1});Object.defineProperty(window,'visualViewport',{value:v});''')
   page=c.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.route('https://www.youtube.com/**',lambda r:r.abort());pages.append(page)
  host,guest=pages;host.goto(BASE+'/create');host.locator('#displayName').fill('Peach');host.locator('#setupSubmit').click();host.wait_for_selector('body.room-connected');host.evaluate("showScreen('watch')");room=host.evaluate('roomId')
  guest.goto(BASE+'/?room='+room);guest.locator('#displayName').fill('Berry');guest.locator('#setupSubmit').click();guest.wait_for_selector('body.room-connected')
  for page in pages:page.evaluate(STUB)
  host.wait_for_function('state.participants.length===2')
  for orientation,w,h,kh in [('portrait',390,844,504),('landscape',844,390,260)]:
   for page in pages:
    page.locator('#message').blur();page.set_viewport_size({'width':w,'height':h});page.evaluate('''({w,h,orientation})=>{Object.defineProperty(window.screen.orientation,'type',{value:orientation+'-primary',configurable:true});visualViewport.width=w;visualViewport.height=h;visualViewport.dispatchEvent(new Event('resize'));exitSolaceFullscreen()}''',{'w':w,'h':h,'orientation':orientation})
    page.wait_for_timeout(150)
   for cycle in range(3):
    sender,peer=pages[cycle%2],pages[(cycle+1)%2]
    sender.locator('#message').focus()
    if model=='android-resize':sender.set_viewport_size({'width':w,'height':kh})
    sender.evaluate('(h)=>{visualViewport.height=h;visualViewport.dispatchEvent(new Event("resize"))}',kh);sender.wait_for_timeout(180)
    sender.locator('#message').press_sequentially('Together '+orientation+' '+str(cycle),delay=3)
    sender.locator('.gesture-toggle').tap();sender.wait_for_timeout(150)
    sender.evaluate('''()=>{const r=s=>document.querySelector(s).getBoundingClientRect(),f=r('#chatForm'),t=r('#gestureTray'),m=r('#messages');if(f.bottom>visualViewport.height+1||t.bottom>f.top+1||m.bottom>t.top+1||m.height<24)throw Error('Keyboard/gesture overlap '+JSON.stringify({f,t,m}));}''')
    sender.locator('.gesture-toggle').tap();sender.locator('.send').tap();sender.wait_for_function('!chatSendPending');sender.wait_for_timeout(150)
    sender.evaluate('''()=>{const list=document.querySelector('#messages'),last=list.lastElementChild,l=list.getBoundingClientRect(),r=last.getBoundingClientRect();if(r.bottom>l.bottom+2||r.bottom<=l.top||list.scrollHeight-list.scrollTop-list.clientHeight>3)throw Error('Latest message hidden');const time=last.querySelector('time').getBoundingClientRect();if(time.bottom>l.bottom+2)throw Error('Timestamp hidden')}''')
    peer.wait_for_function('pageRecovery.canPublish()&&!controlBusy',timeout=15000)
    previous_revision=peer.evaluate('state.playback_revision')
    peer.evaluate('''async(c)=>{player.seekTo(c.position);c.playing?player.playVideo():player.pauseVideo();await sendControlIntent(c.position,c.playing)}''',{'position':30+cycle*5,'playing':cycle%2==0})
    try:sender.wait_for_function('(c)=>state.playback_revision>c.before&&!!state.playing===c.playing',arg={'before':previous_revision,'playing':cycle%2==0},timeout=10000)
    except Exception:
     print({'model':model,'orientation':orientation,'cycle':cycle,'previous_revision':previous_revision,'players':[page.evaluate('({position:player.getCurrentTime(),actual:player.getPlayerState(),playing:state.playing,revision:state.playback_revision,publish:pageRecovery.canPublish(),pending:controlBusy,toast:document.getElementById("toast").textContent})') for page in pages]},flush=True);raise
    sender.wait_for_function('''()=>{const target=state.position+(state.playing?state.server_time-state.updated:0);return (player.getPlayerState()===1)===!!state.playing&&Math.abs(player.getCurrentTime()-target)<1.5}''',timeout=7000)
    a,b=[page.evaluate('({position:player.getCurrentTime(),playing:player.getPlayerState()===1})') for page in pages]
    assert a['playing']==b['playing'] and abs(a['position']-b['position'])<1.5,(a,b)
    sender.locator('#message').blur()
    if model=='android-resize':sender.set_viewport_size({'width':w,'height':h})
    sender.evaluate('(h)=>{visualViewport.height=h;visualViewport.dispatchEvent(new Event("resize"))}',h);sender.wait_for_timeout(650)
    assert sender.evaluate('videoStage===keptStage')
    results.append({'keyboard_model':model,'orientation':orientation,'cycle':cycle,'no_overlap':True,'latest_visible':True,'drift_seconds':round(abs(a['position']-b['position']),3)})
   host.screenshot(path=str(ROOT/('solace-refined-'+orientation+'.png')))
   # Full-page search can never share the hit-testing layer with playback.
   host.evaluate("showScreen('queue')");host.locator('.queue-add').click();host.locator('#selectionQuery').fill('our song')
   assert host.evaluate('shell.inert')
   assert host.locator('.bottom-nav button').count()==5
   assert host.locator('#selectionQuery').evaluate('(el)=>{const r=el.getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)===el}')
   host.locator('#closeSelection').click();host.wait_for_function("activeScreen==='queue'");host.locator('section[data-screen=queue] .screen-back').click()
   host.evaluate("showScreen('room')");host.locator('section[data-screen=room]').get_by_role('button',name='Settings',exact=True).click();settings=host.frame_locator('.room-private-screen iframe');settings.locator('#spacePrivacy').wait_for();assert settings.locator('#spacePrivacy [role=switch]').count()==4
   assert host.evaluate('videoStage===keptStage');host.locator('.room-private-screen .screen-back').click();host.wait_for_function("activeScreen==='watch'")
  host.wait_for_timeout(600);host.locator('#message').fill('/iloveyou');host.locator('.send').tap()
  for page in pages:
   page.locator('.love-overlay').wait_for(state='visible');frame=page.frame_locator('.love-overlay iframe');frame.locator('#loveTitle').wait_for();assert frame.locator('#loveTitle').inner_text()=='You are my solace.'
   assert frame.locator('#loveVideo').evaluate('v=>!v.muted')
   for w,h in [(390,844),(844,390)]:
    page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(100);assert frame.locator('.film').evaluate('(el)=>el.getBoundingClientRect().right<=innerWidth+1');page.screenshot(path=str(ROOT/('solace-love-'+str(w)+'.png')))
  assert admin.post(BASE+'/ops/solace/settings',data={'love_enabled':False},headers={'X-CSRF-Token':token}).ok
  for page in pages:
   page.locator('.love-overlay').wait_for(state='detached');assert page.evaluate('videoStage===keptStage')
  assert admin.post(BASE+'/ops/solace/settings',data={'love_enabled':True},headers={'X-CSRF-Token':token}).ok
  for page in pages:page.request.post(BASE+'/api/rooms/'+room+'/leave',data={})
  for page in pages:page.context.close()
 assert admin.post(BASE+'/ops/solace/settings',data={'love_enabled':False},headers={'X-CSRF-Token':token}).ok
 assert not errors,errors
 browser.close()
assert 'Jaanu' not in (ROOT/'static/love.html').read_text()
assert not (ROOT/'static/media/for-jaanu.mp4').exists()
assert 'You are my solace.' in (ROOT/'static/love.html').read_text()
report={'passed':True,'physical_phone':False,'media':'simulated player with real Flask room transport','four_destinations':True,'back_ancestry':True,'love_copy_anonymized_private_film_excluded':True,'cycles':results}
(ROOT/'experience-refinements-results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

