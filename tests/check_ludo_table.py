"""Real room API with two Chromium phone layouts; no physical-device claim."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8017';ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 browser=p.chromium.launch();contexts=[browser.new_context(viewport={'width':390,'height':844},has_touch=True) for _ in range(2)];pages=[];errors=[]
 room=contexts[0].request.post(BASE+'/api/rooms',data={}).json()['id'];url=BASE+'/api/rooms/'+room
 for c,name in zip(contexts,['Peach','Berry']):
  c.add_init_script("Object.defineProperty(document,'hidden',{get:()=>false})")
  assert c.request.post(url,data={'action':'join','name':name}).ok
  page=c.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto(BASE+'/static/ludo.html?room='+room);page.locator('#join').click();page.wait_for_function('!!game?.you');pages.append(page)
 a,b=pages;a.wait_for_function('Object.keys(game.players).length===2');b.wait_for_function('Object.keys(game.players).length===2')
 a.locator('#start').click();b.wait_for_function('game.started')
 baseline=a.request.get(url).json();seen=set();preview=False;auto=False;rolls=0;rolling_seen=False
 for _ in range(64):
  state=a.request.get(url+'/ludo').json();current=a if state['turn']=='red' else b;other=b if current==a else a
  for page in pages:page.wait_for_function('(r)=>game.revision>=r',arg=state['revision']);page.wait_for_function('!visualBusy&&performance.now()>=diceUntil')
  current.locator('#roll').click();current.wait_for_function('(r)=>game.revision>r',arg=state['revision']);state=current.evaluate('game');roll=state['last_roll'];seen.add(roll['dice']);rolls+=1;rolling_seen=rolling_seen or current.evaluate('activeAnimations.some(a=>a.playState==="running")&&performance.now()<diceUntil')
  for page in pages:
   page.wait_for_function('(id)=>game.last_roll?.id===id',arg=roll['id']);page.wait_for_function('performance.now()>=diceUntil')
   assert page.locator('#dice').get_attribute('data-value')==str(roll['dice'])
   assert page.locator('.die-face').count()==6
   assert page.locator('.face-'+str(roll['dice'])+' .pip:not(.absent)').count()==roll['dice']
  state=current.evaluate('game')
  if state['legal']:
   rev=state['revision']
   if not preview:
    button=current.locator('#moves button').first;button.dispatch_event('pointerdown',{'pointerId':123,'pointerType':'touch','button':0,'clientX':10,'clientY':10});current.wait_for_timeout(450);current.locator('.destination-preview').wait_for();button.dispatch_event('pointercancel',{'pointerId':123});assert current.evaluate('game.revision')==rev;assert not current.locator('.confirm-move').count();preview=True
    current.wait_for_function('!busy')
   if len(state['legal'])==1 and not auto:
    current.locator('#ludoSettings').click();current.get_by_role('checkbox',name='Auto move a single legal pawn').check();current.locator('#ludoSettingsBack').click();current.wait_for_function('(r)=>game.revision>r',arg=rev);auto=True
    current.locator('#ludoSettings').click();current.get_by_role('checkbox',name='Auto move a single legal pawn').uncheck();current.locator('#ludoSettingsBack').click()
   else:current.locator('#moves button').first.click();current.wait_for_function('(r)=>game.revision>r',arg=rev)
   moved=current.evaluate('game');other.wait_for_function('(r)=>game.revision>=r',arg=moved['revision'])
   for page in pages:page.wait_for_function('!visualBusy')
   assert a.evaluate('JSON.stringify(game.pawns)')==b.evaluate('JSON.stringify(game.pawns)')
  if len(seen)==6 and preview and auto:break
 assert len(seen)==6 and preview and auto and rolling_seen,(seen,preview,auto,rolling_seen)
 # Deterministic presentation fixtures cover capture and exact-home effects.
 a.evaluate('''()=>{const next=structuredClone(game);next.revision++;next.event=null;next.pawns.red[0]=14;next.pawns.blue[0]=5;paint(next);const captured=structuredClone(next);captured.revision++;captured.pawns.red[0]=18;captured.pawns.blue[0]=-1;captured.event={id:'visual-capture',kind:'move',player:'red',token:0,from:14,to:18,captured:[['blue',0]],created:Date.now()/1000};paint(captured)}''')
 a.wait_for_function('!visualBusy');a.locator('#ludoMoment').wait_for();assert 'capture' in a.locator('#ludoMoment').inner_text()
 a.evaluate('''()=>{const next=structuredClone(game);next.revision++;next.event=null;next.pawns.red[0]=55;paint(next);const home=structuredClone(next);home.revision++;home.pawns.red[0]=56;home.event={id:'visual-home',kind:'move',player:'red',token:0,from:55,to:56,captured:[],created:Date.now()/1000};paint(home)}''')
 a.wait_for_function('!visualBusy');assert 'Home' in a.locator('#ludoMoment').inner_text();a.reload();a.wait_for_function('!!game')
 # Repeated polling keeps die and pawn nodes; neither rolls again on refresh.
 for page in pages:
  page.evaluate("window.savedCube=document.querySelector('#dice');window.savedPawn=nodes.get('red:0')")
  page.wait_for_timeout(1200);assert page.evaluate("savedCube===document.querySelector('#dice')&&savedPawn===nodes.get('red:0')")
  assert page.evaluate('activeAnimations.every(a=>a.playState!=="running")');assert page.evaluate('animationFailures===0')
  for width,height in [(390,844),(844,390),(320,640)]:
   page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(150)
   geometry=page.evaluate("()=>{const r=document.querySelector('.board-wrap').getBoundingClientRect(),h=document.querySelector('.ludo-heading').getBoundingClientRect();return {fit:document.documentElement.scrollWidth<=innerWidth,title:h.top>=0,board:r.width,view:innerWidth}}")
   assert geometry['fit'] and geometry['title'],geometry
   if width==390:assert geometry['board']>=365,geometry
  page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(ROOT/'solace-ludo-table-portrait.png'))
  page.set_viewport_size({'width':844,'height':390});page.screenshot(path=str(ROOT/'solace-ludo-table-landscape.png'))
  last=page.evaluate('game.last_roll');page.reload();page.wait_for_function('!!game');assert page.locator('#dice').get_attribute('data-value')==str(last['dice']);assert page.evaluate('diceUntil===0')
  page.emulate_media(reduced_motion='reduce');page.reload();page.wait_for_function('!!game');assert page.evaluate('reduceMotion()')
 after=a.request.get(url).json()
 for key in ['video','playing','playback_id','playback_revision','position']:assert baseline[key]==after[key],key
 assert not errors,errors
 for c in contexts:c.request.post(url+'/leave',data={})
 browser.close();print(json.dumps({'passed':True,'rolls':rolls,'all_six_faces_shared':True,'rolling_animation_seen':rolling_seen,'capture_home_animation_fixtures':True,'single_tap_moves':True,'hold_preview_no_move':True,'optional_auto_move':True,'stable_nodes':True,'portrait_landscape_narrow_fit':True,'reload_no_replay':True,'playback_unchanged':True,'physical_phones':False}))
