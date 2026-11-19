"""Two-user community/navigation checks; keyboard viewports are simulated."""
import json,os,sys,io
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from PIL import Image
BASE=os.environ.get('SOLACE_TEST_BASE','http://127.0.0.1:8045');ROOT=Path(__file__).resolve().parents[1];OUT=Path(os.environ.get('SOLACE_SCREENSHOT_DIR',str(ROOT/'audit-results')));OUT.mkdir(parents=True,exist_ok=True)
from media_https_fixture import MediaFixture
STUB="""()=>{window.media={at:performance.now(),pos:0,playing:true};const position=()=>media.pos+(media.playing?(performance.now()-media.at)/1000:0),set=(p,v)=>{media.pos=p;media.playing=v;media.at=performance.now()};player={getCurrentTime:position,getPlayerState:()=>media.playing?1:2,getDuration:()=>3600,getVideoData:()=>({video_id:state.video,title:'Synthetic stream'}),seekTo:p=>set(p,media.playing),playVideo:()=>set(position(),true),pauseVideo:()=>set(position(),false),loadVideoById:v=>set(v.startSeconds||0,true),cueVideoById:v=>set(v.startSeconds||0,false),isMuted:()=>false,mute(){},unMute(){}};ready=true;playerNotice.hidden=true;pageRecovery.reset();window.keptPlayer=player;window.keptStage=videoStage;synchronize(true)}"""
results=[]
with MediaFixture((ROOT/'.openai/stream-audit/media/soak.mp4').read_bytes()) as fixture,sync_playwright() as p:
 for engine in ['chromium','webkit']:
  browser=getattr(p,engine).launch(args=['--autoplay-policy=no-user-gesture-required'] if engine=='chromium' else []);contexts=[browser.new_context(viewport={'width':390,'height':844},has_touch=True,ignore_https_errors=True) for _ in range(2)];pages=[];errors=[];dialogs=[];navigation_diagnostics=[]
  for context in contexts:
   context.add_init_script("localStorage.setItem('solace-rotation','false');Object.defineProperty(document,'hidden',{get:()=>false})")
   page=context.new_page();page.on('pageerror',lambda e:(navigation_diagnostics if str(e).startswith('/127.0.0.1:') and 'due to access control checks.' in str(e) else errors).append(str(e)));page.on('dialog',lambda d:(dialogs.append(d.message),d.dismiss()));page.route('https://www.youtube.com/**',lambda r:r.abort());pages.append(page)
  host,peer=pages
  def post(context,path,data):
   me=context.request.get(BASE+'/api/me').json();r=context.request.post(BASE+path,data=data,headers={'X-CSRF-Token':me['csrf']});assert r.ok,(path,r.status,r.text());return r.json()
  for context,name in zip(contexts,['Peach','Moon']):post(context,'/api/me/profile',dict(name=name+' '+engine))
  host.goto(BASE+'/create');host.locator('#setupSubmit').click();host.locator('body.room-connected').wait_for();host.evaluate("showScreen('watch')");room=host.evaluate('roomId');peer.goto(BASE+'/?room='+room);peer.locator('body.room-connected').wait_for();peer.evaluate("showScreen('watch')")
  if engine=='chromium':
   host.evaluate('url=>action({action:"watch",url})',fixture.url)
   for page in pages:page.wait_for_function('directElement&&directElement.currentTime>.2');page.evaluate('window.keptPlayer=player;window.keptStage=videoStage')
  else:
   host.evaluate("action({action:'watch',url:'aqz-KE-bpKQ'})")
   for page in pages:page.evaluate(STUB)
  host.wait_for_timeout(700);before=contexts[0].request.get(BASE+'/api/rooms/'+room).json()['command_revision'];start=host.evaluate('player.getCurrentTime()')
  def open_world(page):
   page.evaluate("SolaceRoomNavigation.open('/world')");frame=page.frame_locator('.room-private-screen iframe');frame.locator('#worldChoice').wait_for();assert not frame.locator('input[type=checkbox]').count();frame.locator('#worldJoin').click();expect(frame.locator('#worldComposer')).to_be_visible();return frame
  a=open_world(host);b=open_world(peer);expect(a.locator('#worldOnline')).to_contain_text('2 online');greeting='Hello '+__import__('uuid').uuid4().hex;a.locator('#worldText').fill(greeting);a.locator('#worldSend').click();expect(b.locator('#worldMessages')).to_contain_text(greeting)
  raw=io.BytesIO();Image.new('RGB',(60,40),'pink').save(raw,'GIF',save_all=True,append_images=[Image.new('RGB',(60,40),'purple')],duration=150,loop=0);a.locator('#worldAttachment input').set_input_files({'name':'public.gif','mimeType':'image/gif','buffer':raw.getvalue()});a.locator('#worldSend').click();expect(b.locator('#worldMessages .shared-media').get_by_role('button',name='Play GIF',exact=True).last).to_be_visible();b.locator('#worldMessages .shared-media').get_by_role('button',name='Play GIF',exact=True).last.click();b.locator('#worldMessages .shared-media').get_by_role('button',name='Pause GIF',exact=True).last.click()
  # A second tab belongs to the same identity and is counted only once.
  extra=contexts[0].new_page();extra.goto(BASE+'/world');expect(extra.locator('#worldChoice')).to_be_hidden();expect(extra.locator('#worldOnline')).to_contain_text('2 online');extra.close()
  for path,selector in [('/home','.home-greeting'),('/messages','#dmList'),('/settings','#prefWorld'),('/world','#worldComposer')]:
   host.evaluate('(path)=>SolaceRoomNavigation.open(path)',path);frame=host.frame_locator('.room-private-screen iframe');frame.locator(selector).wait_for();assert host.evaluate('player===keptPlayer&&videoStage===keptStage');assert host.evaluate('roomId')==room;assert not host.locator('dialog[open]').count()
   if path=='/world':expect(frame.locator('#worldChoice')).to_be_hidden()
   if path=='/settings':
    expect(frame.locator('#prefWorld')).to_be_checked();frame.locator('#prefAlerts').uncheck();expect(frame.locator('#settingsStatus')).to_have_text('Saved');frame.locator('[data-theme=rose]').click();expect(frame.locator('[data-theme=rose]')).to_have_attribute('aria-pressed','true');assert not contexts[0].request.get(BASE+'/api/me/preferences').json()['preferences']['in_app_alerts']
  assert host.evaluate('player.getCurrentTime()')>start+1
  assert contexts[0].request.get(BASE+'/api/rooms/'+room).json()['command_revision']==before
  a=host.frame_locator('.room-private-screen iframe');cycles=[]
  for width,height in [(390,844),(844,390)]:
   host.set_viewport_size(dict(width=width,height=height));a.locator('#worldText').fill('A draft while typing quickly');a.locator('#worldText').focus()
   for cycle in range(2):
    target_height=540 if width<height else 260;host.set_viewport_size(dict(width=width,height=target_height));newest='Newest '+str(width)+' '+str(cycle)+' '+__import__('uuid').uuid4().hex[:8];post(contexts[1],'/api/me/world/messages',dict(body=newest,request_id=__import__('uuid').uuid4().hex));expect(a.locator('#worldMessages')).to_contain_text(newest);host.wait_for_timeout(150)
    state=a.locator('#worldComposer').evaluate('(n)=>{const r=n.getBoundingClientRect(),h=document.getElementById("worldHistory");return {visible:r.bottom<=innerHeight+1,height:h.clientHeight,bottom:h.scrollHeight-h.scrollTop-h.clientHeight,overlap:h.getBoundingClientRect().bottom>r.top+1}}');assert state['visible'] and not state['overlap'] and state['height']>50 and state['bottom']<4,state
    assert a.locator('#worldText').evaluate('(n)=>n.getBoundingClientRect().width>innerWidth*.45'), 'Composer must leave most of the row available for typing'
    host.set_viewport_size(dict(width=width,height=height));host.wait_for_timeout(100);cycles.append(dict(orientation='portrait' if width<height else 'landscape',latest_visible=True,overlap=False))
  a.locator('#worldText').fill('');a.locator('#worldText').blur();host.set_viewport_size(dict(width=390,height=844));host.screenshot(path=str(OUT/('community-room-'+engine+'.png')))
  contexts[0].set_offline(True);expect(a.locator('#worldStatus')).to_contain_text('offline');a.locator('#worldText').fill('Draft survives reconnect');reconnected='After reconnect '+__import__('uuid').uuid4().hex;post(contexts[1],'/api/me/world/messages',dict(body=reconnected,request_id=__import__('uuid').uuid4().hex));contexts[0].set_offline(False);expect(a.locator('#worldMessages')).to_contain_text(reconnected,timeout=15000);expect(a.locator('#worldText')).to_have_value('Draft survives reconnect');assert host.evaluate('player===keptPlayer&&videoStage===keptStage');a.locator('#worldText').fill('');a.locator('#worldText').blur()
  settings_tab=contexts[0].new_page();settings_tab.goto(BASE+'/settings');expect(settings_tab.locator('#prefAlerts')).not_to_be_checked();expect(settings_tab.locator('[data-theme=rose]')).to_have_attribute('aria-pressed','true');settings_tab.close()
  post(contexts[0],'/api/me/preferences',dict(world_choice='skipped'));expect(a.locator('#worldJoinLater')).to_be_visible();expect(a.locator('#worldComposer')).to_be_hidden();post(contexts[0],'/api/me/preferences',dict(world_choice='joined'));expect(a.locator('#worldComposer')).to_be_visible()
  contexts[0].route('**/api/me/world/messages?*',lambda route:route.fulfill(status=403,content_type='application/json',body='{"error":"Synthetic temporary restriction"}'));expect(a.locator('#worldText')).to_be_disabled();contexts[0].unroute('**/api/me/world/messages?*');expect(a.locator('#worldText')).to_be_enabled();expect(a.locator('#worldAttachment input')).to_be_enabled()
  # Returning and leaving are distinct: only the explicit leave action asks.
  host.locator('.room-private-screen .screen-back').click();assert host.evaluate("activeScreen==='watch'");assert host.evaluate('player===keptPlayer');host.evaluate("showScreen('room')");host.get_by_role('button',name='Leave room',exact=True).click();expect(host.get_by_role('dialog',name='Change your room?')).to_be_visible();host.get_by_role('button',name='Stay here',exact=True).click();assert host.evaluate('roomId')==room
  host.evaluate("SolaceRoomNavigation.open('/home')");home_frame=host.frame_locator('.room-private-screen iframe');home_frame.locator('a[href="/create"]').first.click();create=host.frame_locator('.room-private-screen iframe');create.locator('#setupSubmit').wait_for();created=[];host.on('request',lambda r:created.append(r.url) if r.method=='POST' and r.url==BASE+'/api/rooms' else None);create.locator('#setupSubmit').click();expect(host.get_by_role('dialog',name='Change your room?')).to_be_visible();host.get_by_role('button',name='Stay here',exact=True).click();host.wait_for_timeout(100);assert not created;assert host.evaluate('roomId')==room;assert host.evaluate('player===keptPlayer')
  create.locator('#setupSubmit').click();host.get_by_role('dialog',name='Change your room?').get_by_role('button',name='Continue',exact=True).click();host.wait_for_function('(old)=>typeof roomId!=="undefined"&&roomId!==old&&typeof state!=="undefined"&&!!state',arg=room);new_room=host.evaluate('roomId');assert len(created)==1;old_state=contexts[1].request.get(BASE+'/api/rooms/'+room).json();assert old_state['is_host'] and len(old_state['participants'])==1
  assert not dialogs,dialogs;assert not errors,errors
  for context,rid in zip(contexts,[new_room,room]):post(context,'/api/me/preferences',dict(world_choice='skipped'));context.request.post(BASE+'/api/rooms/'+rid+'/leave',data={})
  results.append(dict(engine=engine,passed=True,media='actual decoded synthetic HTTPS video' if engine=='chromium' else 'simulated player',navigation_keeps_player_and_command_revision=True,public_chat_between_strangers=True,choice_saved=True,multiple_tabs_unique=True,settings_persisted=True,reconnect_preserves_draft_and_player=True,explicit_room_switch_verified=True,navigation_unload_diagnostics=len(navigation_diagnostics),keyboard_cycles=cycles,physical_devices=False));browser.close()
print(json.dumps(results));(OUT/'community-browser-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
