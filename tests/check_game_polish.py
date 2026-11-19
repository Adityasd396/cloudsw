"""Two users, shared games and independent streaming; mobile layouts are simulated."""
import json,time
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:8017'
STUB='''()=>{window.media={position:0,playing:false,at:performance.now()};const current=()=>media.position+(media.playing?(performance.now()-media.at)/1000:0),set=(position,playing)=>{media.position=position;media.playing=playing;media.at=performance.now()};player={getCurrentTime:current,getPlayerState:()=>media.playing?1:2,getDuration:()=>3600,getVideoData:()=>({video_id:state.video,title:'Test stream'}),seekTo:p=>set(p,media.playing),playVideo:()=>set(current(),true),pauseVideo:()=>set(current(),false),loadVideoById:v=>set(v.startSeconds,true),cueVideoById:v=>set(v.startSeconds,false),isMuted:()=>false,mute(){},unMute(){}};ready=true;playerNotice.hidden=true;pageRecovery.reset();synchronize(true);window.keptStage=videoStage}'''
with sync_playwright() as p:
 browser=p.chromium.launch();pages=[];errors=[]
 for name in ['Peach','Berry']:
  c=browser.new_context(viewport={'width':390,'height':844},has_touch=True)
  c.add_init_script("Object.defineProperty(document,'hidden',{get:()=>false});localStorage.setItem('solace-rotation','false')")
  page=c.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.route('https://www.youtube.com/**',lambda r:r.abort());pages.append(page)
 host,peer=pages;host.goto(BASE+'/create');host.locator('#displayName').fill('Peach');host.locator('#setupSubmit').click();host.wait_for_selector('body.room-connected');host.evaluate("showScreen('watch')");room=host.evaluate('roomId');url=BASE+'/api/rooms/'+room
 peer.goto(BASE+'/?room='+room);peer.locator('#displayName').fill('Berry');peer.locator('#setupSubmit').click();peer.wait_for_selector('body.room-connected')
 for page in pages:page.evaluate(STUB)
 # Themes are local, survive refresh, and do not publish playback commands.
 before=host.request.get(url).json()['playback_revision']
 for page,key in [(host,'rose'),(peer,'ocean')]:
  page.evaluate("showScreen('settings')");page.locator('[data-theme='+key+']').click();assert page.evaluate('document.body.dataset.chatTheme')==key
  page.reload();page.wait_for_selector('body.room-connected');page.evaluate("showScreen('watch')");page.evaluate(STUB);assert page.evaluate('document.body.dataset.chatTheme')==key
 assert host.request.get(url).json()['playback_revision']==before
 counter=0;drifts=[]
 def sync_check():
  global counter
  counter+=1;controller=pages[counter%2]
  controller.evaluate('''async(p)=>{player.seekTo(p);player.playVideo();await sendControlIntent(p,true)}''',40+counter*5)
  rev=controller.evaluate('state.playback_revision')
  for page in pages:
   page.wait_for_function('(r)=>state.playback_revision>=r',arg=rev)
   page.wait_for_function('''()=>player.getPlayerState()===1&&Math.abs(player.getCurrentTime()-(state.position+state.server_time-state.updated))<1.5''',timeout=7000)
   assert page.evaluate('keptStage===videoStage')
  positions=[page.evaluate('player.getCurrentTime()') for page in pages];assert abs(positions[0]-positions[1])<1.5;drifts.append(round(abs(positions[0]-positions[1]),3))
 def orientations():
  for page in pages:
   for w,h in [(844,390),(390,844)]:
    page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(100);assert page.frame_locator('.game-screen-frame').locator('body').evaluate('document.documentElement.scrollWidth<=innerWidth')
 def frames(kind):
  result=[]
  for page in pages:
   page.evaluate('''(path)=>{showScreen('game');gameFrame.src=path}''',BASE+'/static/'+kind+'?room='+room)
   frame=page.frame_locator('.game-screen-frame');frame.locator('.agree-options').wait_for(state='attached');result.append(frame)
  return result
 def state(frame):return frame.locator('body').evaluate("()=>typeof match!=='undefined'?match:game")
 def send(frame,action):
  frame.locator('body').evaluate('(element,data)=>gpSend(data)',action)
 def wait_revision(frame,revision):frame.locator('body').evaluate('''async(element,r)=>{const end=Date.now()+6000;while((typeof match!=='undefined'?match:game).revision<r){if(Date.now()>end)throw Error('Peer did not update');await new Promise(resolve=>setTimeout(resolve,40))}}''',revision)
 def configure(fs,values):
  for f in fs:
   if f.locator('#ludoSettings').count():f.locator('#ludoSettings').click()
   for key,value in values.items():
    label='Match' if key in ['best_of','pawn_count'] else 'Play' if key=='mode' else 'Challenge'
    f.get_by_label(label,exact=True).select_option(str(value))
   before=state(f)['revision'];f.locator('.agree-options').click()
   try:wait_revision(f,before+1)
   except Exception:
    raise AssertionError(json.dumps({'state':state(f),'text':f.locator('main').inner_text(),'errors':errors}))
   rev=state(f)['revision']
   for other in fs:wait_revision(other,rev)
  for f in fs:
   if f.locator('#ludoSettingsBack').is_visible():f.locator('#ludoSettingsBack').click()
 # Best-of-three, shared marks/winning line, alternating starter and mutual rematch.
 fs=frames('tictactoe.html')
 for f in fs:f.locator('#joinGame').click()
 host.wait_for_timeout(800);fs.sort(key=lambda f:state(f)['you']!='X');configure(fs,{'best_of':3});assert state(fs[0])['best_of']==3,state(fs[0])
 for mark,cell in [('X',0),('O',3),('X',1),('O',4),('X',2)]:
  f=fs[0] if mark=='X' else fs[1];send(f,{'action':'move','cell':cell,'revision':state(f)['revision']});host.wait_for_timeout(150);rev=state(f)['revision']
  for other in fs:wait_revision(other,rev)
 for f in fs:assert state(f)['wins']['X']==1,state(f);assert f.locator('.winning-line').count()==1;assert f.locator('.mark-icon').first.inner_text()=='♡'
 fs[0].locator('#resetGame').click();host.wait_for_timeout(200);wait_revision(fs[1],state(fs[0])['revision']);assert state(fs[1])['winner']=='X'
 fs[1].locator('#resetGame').click();host.wait_for_timeout(200);wait_revision(fs[0],state(fs[1])['revision']);assert state(fs[0])['turn']=='O'
 fs[0].locator('.polish-cheers button').first.click();fs[1].locator('.shared-game-cheer').wait_for(state='visible');assert 'Peach' in fs[1].locator('.shared-game-cheer').inner_text()
 sync_check();orientations();host.screenshot(path=str(ROOT/'solace-games-ttt.png'))
 # Cooperative Hoops: shared charging and physically styled goal feedback.
 fs=frames('game.html')
 for f in fs:f.locator('#join').click()
 host.wait_for_timeout(700);configure(fs,{'mode':'together','difficulty':'relaxed'})
 for shot in range(8):
  current=state(fs[0]);f=fs[0] if current['turn']=='X' else fs[1]
  send(f,{'action':'shoot','aim':current['challenge']['target'],'power':current['challenge']['power'],'revision':current['revision']})
  host.wait_for_timeout(150);rev=state(f)['revision']
  for other in fs:wait_revision(other,rev)
  host.wait_for_timeout(1100)
 for f in fs:assert state(f)['winner']=='together';assert 'together' in f.locator('#status').inner_text().lower();assert f.locator('.fans svg').count()==2
 sync_check();orientations();host.screenshot(path=str(ROOT/'solace-games-hoops.png'))
 # Quick Ludo, selection preview/confirmation, shared dice and movement.
 fs=frames('ludo.html')
 for f in fs:f.locator('#join').click()
 host.wait_for_timeout(800);configure(fs,{'pawn_count':2});fs[0].locator('#start').click();host.wait_for_timeout(700)
 for _ in range(64):
  current=state(fs[0]);f=fs[0] if current['turn']=='red' else fs[1]
  send(f,{'action':'roll','revision':current['revision']});host.wait_for_timeout(150);rev=state(f)['revision']
  for other in fs:wait_revision(other,rev)
  current=state(f)
  if current['legal']:
   f.locator('#moves button').first.click();host.wait_for_timeout(200);rev=state(f)['revision']
   for other in fs:wait_revision(other,rev)
   break
 else:raise AssertionError('No legal roll')
 for f in fs:assert state(f)['pawn_count']==2
 assert state(fs[0])['pawns']==state(fs[1])['pawns'];fs[0].locator('.polish-cheers button').first.click();fs[1].locator('.shared-game-cheer').wait_for(state='visible');sync_check();host.wait_for_timeout(1200);host.screenshot(path=str(ROOT/'solace-games-ludo.png'))
 # Both orientations fit, and reduced motion does not break gameplay controls.
 for page in pages:
  for w,h in [(390,844),(844,390)]:
   page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(150)
   assert page.frame_locator('.game-screen-frame').locator('body').evaluate('document.documentElement.scrollWidth<=innerWidth')
 for page in pages:
  page.emulate_media(reduced_motion='reduce');page.evaluate('gameFrame.contentWindow.location.reload()');page.frame_locator('.game-screen-frame').locator('.agree-options').wait_for(state='attached');page.wait_for_timeout(200)
  assert page.frame_locator('.game-screen-frame').locator('body').evaluate('gpReduced===true')
 assert not errors,errors
 for page in pages:page.request.post(url+'/leave',data={})
 browser.close();print(json.dumps({'passed':True,'themes_saved_per_device':True,'ttt_series_mutual_rematch':True,'hoops_cooperative_win':True,'ludo_quick_preview_move':True,'both_orientations':True,'stream_drift_seconds':drifts,'physical_phones':False}))

