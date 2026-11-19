import json,time
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:8017';clip=(ROOT/'.openai/stream-audit/media/clip.mp4').read_bytes()
with sync_playwright() as p:
 browser=p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required']);pages=[];errors=[]
 for name in ['Peach','Berry']:
  c=browser.new_context(viewport={'width':390,'height':844},has_touch=True)
  c.add_init_script("localStorage.setItem('solace-rotation','false');Object.defineProperty(document,'hidden',{get:()=>false})")
  def media(route):
   requested=route.request.headers.get('range','')
   if requested.startswith('bytes='):
    start,end=requested[6:].split('-');start=int(start or 0);end=min(int(end) if end else len(clip)-1,len(clip)-1)
    route.fulfill(status=206,body=clip[start:end+1],headers={'Content-Type':'video/mp4','Accept-Ranges':'bytes','Content-Range':f'bytes {start}-{end}/{len(clip)}'})
   else:route.fulfill(body=clip,content_type='video/mp4',headers={'Accept-Ranges':'bytes'})
  c.route('https://media.audit/**',media)
  page=c.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.route('https://www.youtube.com/**',lambda r:r.abort());pages.append(page)
 a,b=pages;a.goto(BASE+'/create');a.locator('#displayName').fill('Peach');a.locator('#setupSubmit').click();a.wait_for_selector('body.room-connected');a.evaluate("showScreen('watch')");room=a.evaluate('roomId');url=BASE+'/api/rooms/'+room
 b.goto(BASE+'/?room='+room);b.locator('#displayName').fill('Berry');b.locator('#setupSubmit').click();b.wait_for_selector('body.room-connected')
 a.evaluate("action({action:'watch',url:'https://media.audit/clip.mp4'})")
 for page in pages:
  try:page.wait_for_function('directElement&&directElement.currentTime>.1',timeout=8000)
  except Exception:
   print(json.dumps({'errors':errors,'state':page.evaluate("({video:state?.video,playing:state?.playing,ready,lastVideo,lastPlaybackId,active:pageRecovery.active,recover:pageRecovery.recovering,playerVideo:player?.getVideoData?.(),notice:document.querySelector('#playerNoticeTitle').textContent,element:directElement?{src:directElement.src,error:directElement.error?.message,time:directElement.currentTime,state:directElement.readyState,paused:directElement.paused}:null})")}));raise
 a.evaluate("document.getElementById('yt-script')?.onerror?.()");assert a.locator('#playerNotice').is_hidden()
 a.evaluate('''()=>{window.savedPlay=directElement.play;window.playCalls=0;player.pauseVideo();directElement.play=()=>{playCalls++;return new Promise(()=>{})};player.playVideo();player.playVideo();player.playVideo()}''');a.wait_for_timeout(60);assert a.evaluate('playCalls')==1;a.evaluate('''()=>{player.pauseVideo();directElement.play=savedPlay;player.playVideo()}''');a.wait_for_function('!directElement.paused')
 for page in pages:page.evaluate("window.mediaEvents=[];for(const type of ['loadstart','seeking','seeked','pause','playing','ended','ratechange'])directElement.addEventListener(type,()=>mediaEvents.push({type,time:directElement.currentTime,duration:directElement.duration,at:performance.now()}))")
 for command,effect in [('/love','love'),('/heartglitter','glitter'),('/clap','clap')]:
  a.locator('#message').fill(command);a.locator('.send').click()
  for page in pages:page.locator('.reaction-'+effect).wait_for();assert page.locator('.screen-reaction span').count()==28;assert page.locator('.screen-reaction').evaluate("n=>getComputedStyle(n).pointerEvents==='none'")
  b.locator('#message').focus();b.locator('#message').fill('Draft stays here');start=b.evaluate('directElement.currentTime');b.wait_for_timeout(1200);assert b.locator('#message').input_value()=='Draft stays here';assert b.evaluate('directElement.currentTime')>start+.5, {'command':command,'start':start,'after':b.evaluate('({time:directElement.currentTime,paused:directElement.paused,ready:directElement.readyState,error:directElement.error?.message,playing:state.playing,position:state.position,server_time:state.server_time,updated:state.updated,revision:state.playback_revision})'),'server':b.request.get(url).json()['playing'],'events':b.evaluate('mediaEvents.slice(-18)'),'duration':b.evaluate('directElement.duration')}
  for page in pages:page.locator('.screen-reaction').wait_for(state='detached',timeout=4000)
  a.evaluate('async()=>{player.seekTo(1);await sendControlIntent(1,true)}');revision=a.evaluate('state.playback_revision');b.wait_for_function('(r)=>state.playback_revision>=r&&Math.abs(player.getCurrentTime()-(state.position+state.server_time-state.updated))<1',arg=revision);b.locator('#message').blur()
 a.evaluate('async()=>{await videoStage.requestFullscreen();SolaceReactions.show("love")}')
 assert a.evaluate('document.fullscreenElement.contains(document.querySelector(".screen-reaction"))')
 a.evaluate('async()=>{SolaceReactions.clear();await document.exitFullscreen()}')
 a.emulate_media(reduced_motion='reduce');a.evaluate('SolaceReactions.show("glitter")')
 assert a.locator('.screen-reaction span').first.evaluate('n=>getComputedStyle(n).animationName')=='none'
 a.evaluate('SolaceReactions.clear()');a.emulate_media(reduced_motion='no-preference')
 # Color choice applies to actual server seats, not just local paint.
 games=[]
 for page in pages:
  game=page.context.new_page();game.on('pageerror',lambda e:errors.append(str(e)));game.goto(BASE+'/static/ludo.html?room='+room);games.append(game)
 g,h=games;g.locator('#ludoSettings').click();g.get_by_role('button',name='Choose green',exact=True).click();g.locator('#ludoSettingsBack').click();g.locator('#join').click();g.wait_for_function("game?.you==='green'")
 h.locator('#join').click();h.wait_for_function('!!game?.you');g.wait_for_function('Object.keys(game.players).length===2')
 g.locator('#start').click();g.wait_for_function('game.started');h.wait_for_function('game.started')
 current=g if g.evaluate('game.turn===game.you') else h
 current.locator('#roll').click();current.wait_for_function('!!game.last_roll')
 value=current.evaluate('game.last_roll.dice')
 for game in games:game.locator('.dice-result').wait_for();assert game.locator('.dice-result').get_attribute('aria-label').endswith(str(value));assert game.locator('.pawn text').all_text_contents()==['♡','✧','❀','☾']*4
 for page in pages:page.locator('.dice-result').wait_for();assert page.locator('.dice-result').get_attribute('aria-label').endswith(str(value))
 a.screenshot(path=str(ROOT/'solace-special-dice.png'))
 for page in pages:assert not page.evaluate('directElement.paused')
 g.locator('#ludoSettings').click();assert g.get_by_role('button',name='Choose blue',exact=True).is_disabled()
 assert not errors,errors
 for page in pages:page.request.post(url+'/leave',data={})
 browser.close();print(json.dumps({'passed':True,'shared_love_glitter_claps':True,'three_second_cleanup':True,'focus_and_draft_preserved':True,'real_video_continues':True,'color_choice_shared_and_locked':True,'big_roll_visible_on_both_streaming_and_game_screens':True,'symbol_pawns':True,'physical_phones':False}))
