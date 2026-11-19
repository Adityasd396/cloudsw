import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:8017'
with sync_playwright() as p:
 browser=p.chromium.launch();contexts=[browser.new_context(viewport={'width':390,'height':844},has_touch=True) for _ in range(2)];errors=[]
 # Test-only room membership; each context has an independent cookie session.
 room=contexts[0].request.post(BASE+'/api/rooms',data={}).json()['id'];url=BASE+'/api/rooms/'+room
 for context,name in zip(contexts,['Peach','Berry']):assert context.request.post(url,data={'action':'join','name':name}).ok
 hoops=[]
 for context in contexts:
  page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)));page.goto(BASE+'/static/game.html?room='+room);page.locator('#join').click();page.wait_for_function('!!game.you');hoops.append(page)
 host,guest=hoops;host.wait_for_function('Object.keys(game.players).length===2');guest.wait_for_function('Object.keys(game.players).length===2')
 host.evaluate("aim=game.challenge.target;document.querySelector('#shoot').dispatchEvent(new PointerEvent('pointerdown',{pointerId:1,pointerType:'touch',button:0}))")
 guest.wait_for_function("document.querySelector('#liveStatus').textContent.includes('holding the ball')",timeout=1500)
 host.wait_for_function('power>=game.challenge.power',timeout=1200);host.locator('#shoot').dispatch_event('pointerup',{'pointerId':1,'pointerType':'touch'})
 for page in hoops:page.wait_for_function('game.scores.X===1');page.locator('#goal').wait_for(state='visible')
 assert 'basketball-ball.svg' in host.locator('#ball').evaluate('(e)=>getComputedStyle(e).backgroundImage')
 # Cancellation publishes idle without submitting a shot.
 guest.wait_for_function('canShoot()');guest.evaluate("aim=game.challenge.target;document.querySelector('#shoot').dispatchEvent(new PointerEvent('pointerdown',{pointerId:2,pointerType:'touch',button:0}))");guest.wait_for_timeout(320);guest.locator('#shoot').dispatch_event('pointercancel',{'pointerId':2,'pointerType':'touch'});host.wait_for_function("game.live?.phase==='idle'",timeout=1800)
 assert guest.evaluate('game.attempts.O')==0
 guest.locator('[data-cheer="🫶"]').click();host.locator('#cheerBubble').wait_for(state='visible');assert 'Berry' in host.locator('#cheerBubble').inner_text()
 host.locator('#goal').wait_for(state='hidden');host.screenshot(path=str(ROOT/'solace-moonlight-hoops.png'))
 for page in hoops:
  page.set_viewport_size({'width':844,'height':390});page.wait_for_timeout(200);assert page.locator('#shoot').bounding_box()['x']>=0;assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 ludo=[]
 for context in contexts:
  page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)));page.goto(BASE+'/static/ludo.html?room='+room);page.locator('#join').click();page.wait_for_function('!!game.you');ludo.append(page)
 a,b=ludo;a.wait_for_function('Object.keys(game.players).length===2');a.locator('#start').click();b.wait_for_function('game.started');assert a.evaluate('TRACK.length')==52
 for _ in range(64):
  current=a if a.evaluate('game.turn')=='red' else b;old=current.evaluate('game.revision');current.locator('#roll').click();current.wait_for_function('(old)=>game.revision>old',arg=old)
  state=current.evaluate('game');other=b if current==a else a;other.wait_for_function('(rev)=>game.revision>=rev',arg=state['revision'])
  if state['dice']==6:
   current.locator('.pawn.legal').first.click();current.wait_for_function('(rev)=>game.revision>rev',arg=state['revision']);break
 else:raise AssertionError('No six in 64 server rolls')
 revision=current.evaluate('game.revision');other.wait_for_function('(rev)=>game.revision>=rev',arg=revision)
 assert a.evaluate('JSON.stringify(game.pawns)')==b.evaluate('JSON.stringify(game.pawns)')
 assert len(a.locator('.pawn:visible').all())==8;assert a.evaluate('document.documentElement.scrollWidth<=innerWidth')
 a.screenshot(path=str(ROOT/'solace-little-ludo.png'));a.set_viewport_size({'width':844,'height':390});a.wait_for_timeout(200);assert a.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert not errors,errors
 for context in contexts:context.request.post(url+'/leave',data={})
 browser.close();print(json.dumps({'passed':True,'hoops_live_charge_visible_to_peer':True,'power_goal_shared':True,'cancel_does_not_shoot':True,'textured_ball':True,'shared_cheers':True,'ludo_server_roll_and_pawn_move_shared':True,'portrait_landscape_layouts':True,'physical_phone':False}))
