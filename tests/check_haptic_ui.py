import json
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8017'
with sync_playwright() as p:
 browser=p.chromium.launch();context=browser.new_context(viewport={'width':390,'height':844},has_touch=True)
 context.add_init_script("window.vibrations=[];Object.defineProperty(navigator,'vibrate',{value:n=>{window.vibrations.push(n);return true},configurable:true})")
 page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.route('https://www.youtube.com/**',lambda route:route.abort());page.goto(BASE+'/create');page.locator('#displayName').fill('Peach');page.locator('#setupSubmit').click();page.wait_for_selector('body.room-connected');page.evaluate("showScreen('watch')");room=page.evaluate('roomId');url=BASE+'/api/rooms/'+room
 page.locator('#message').fill('A quiet hello');page.locator('.send').click();page.wait_for_function('state.messages.length===1');page.wait_for_timeout(150);assert page.evaluate('vibrations.includes(5)')
 page.evaluate("showScreen('room')");page.get_by_role('button',name='Settings',exact=True).click();assert page.locator('section[data-screen="settings"]').is_visible();switches=page.locator('.setting-row input');assert switches.nth(0).is_checked();assert not switches.nth(1).is_checked()
 switches.nth(0).uncheck();assert page.evaluate("JSON.parse(localStorage.getItem('solace-haptics-v1')).enabled===false")
 page.locator('section[data-screen="settings"] .screen-back').click();page.wait_for_function("activeScreen==='room'");page.locator('section[data-screen="room"] .screen-back').click();page.wait_for_timeout(550);before=page.evaluate('vibrations.filter(n=>n>0).length');page.locator('#message').fill('No buzz');page.locator('.send').click();page.wait_for_function('state.messages.length===2');assert page.evaluate('vibrations.filter(n=>n>0).length')==before
 page.reload();page.wait_for_selector('body.room-connected');page.wait_for_timeout(200);assert page.evaluate('SolaceHaptics.get().enabled===false');assert page.evaluate('vibrations.filter(n=>n>0).length')==0
 page.evaluate("showScreen('room')");page.get_by_role('button',name='Settings',exact=True).click();switches=page.locator('.setting-row input');switches.nth(0).check();switches.nth(1).check();assert page.locator('.tempo-panel').is_visible()
 page.locator('.tempo-panel button').click();page.wait_for_timeout(500);page.locator('.tempo-panel button').click();assert 100<=page.evaluate('SolaceHaptics.get().bpm')<=140
 page.evaluate('SolaceHaptics.set({...SolaceHaptics.get(),bpm:90})');page.locator('section[data-screen="settings"] .screen-back').click();page.wait_for_function("activeScreen==='room'");page.locator('section[data-screen="room"] .screen-back').click()
 # Read-only synthetic media clock: no playback writes or network sync commands.
 revision=page.request.get(url).json()['playback_revision']
 page.evaluate("""()=>{polling=true;state.is_host=false;state.playing=1;window.testPosition=0;window.testPlaying=true;window.mediaWrites=0;player={getCurrentTime:()=>testPosition,getPlayerState:()=>testPlaying?1:2,getDuration:()=>300,getVideoData:()=>({video_id:state.video}),isMuted:()=>false,getVolume:()=>50,seekTo:()=>mediaWrites++,playVideo:()=>mediaWrites++,pauseVideo:()=>mediaWrites++};ready=true;pageRecovery.reset();lastRoomContact=Date.now();playerNotice.hidden=true}""")
 page.wait_for_timeout(200)
 for position in [.7,1.4]:page.evaluate('(p)=>testPosition=p',position);page.wait_for_timeout(200)
 assert page.evaluate('vibrations.includes(4)');beats=page.evaluate('vibrations.filter(n=>n===4).length')
 page.evaluate('testPlaying=false;state.playing=0;testPosition=8');page.wait_for_timeout(250);assert page.evaluate('vibrations.filter(n=>n===4).length')==beats
 page.evaluate('SolaceHaptics.set({...SolaceHaptics.get(),enabled:false});testPlaying=true;state.playing=1;testPosition=9.4');page.wait_for_timeout(250);assert page.evaluate('vibrations.filter(n=>n===4).length')==beats
 assert page.evaluate('mediaWrites')==0;assert page.request.get(url).json()['playback_revision']==revision
 game=context.new_page();game.on('pageerror',lambda e:errors.append(str(e)));game.goto(BASE+'/static/game.html?room='+room);assert game.locator('.hint').count()==0;assert game.locator('#roundSummary').count()==0;game.locator('#join').click();game.wait_for_function('!!game.you');assert game.evaluate('vibrations.filter(n=>n>0).length')==0
 page.evaluate('SolaceHaptics.set({enabled:true,music:false,bpm:90})');game.wait_for_function('SolaceHaptics.get().enabled');game.locator('[data-cheer="🫶"]').click();game.wait_for_timeout(150);assert game.evaluate('vibrations.includes(6)')
 ludo=context.new_page();ludo.on('pageerror',lambda e:errors.append(str(e)));ludo.goto(BASE+'/static/ludo.html?room='+room);assert ludo.locator('details').count()==0
 assert not errors,errors
 page.request.post(url+'/leave',data={});browser.close()
 print(json.dumps({'passed':True,'chat_feedback':True,'settings_persist_off':True,'no_history_buzz':True,'tempo_tap':True,'alternate_media_rhythm':True,'pause_off_suppress_music':True,'no_media_writes':True,'same_origin_game_preferences':True,'tutorials_removed':True,'vibration_api_stubbed':True,'physical_phone':False}))
