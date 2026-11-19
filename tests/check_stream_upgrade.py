import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:8017';clip=(ROOT/'tests/fixtures/stream-test.mp4').read_bytes()
with sync_playwright() as p:
 browser=p.chromium.launch();pages=[];errors=[]
 for name in ['Peach','Berry']:
  context=browser.new_context(viewport={'width':390,'height':844},has_touch=True)
  context.route('https://media.example/**',lambda route:route.fulfill(body=clip,content_type='video/mp4'))
  page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)));page.route('https://www.youtube.com/**',lambda route:route.abort());pages.append(page)
 host,guest=pages
 host.goto(BASE);assert host.locator('.hero').is_visible();assert not host.locator('.shell').count()
 host.goto(BASE+'/join');host.wait_for_url('**/join');host.reload();assert host.locator('#joinCode').is_visible();assert not host.locator('.workspace').is_visible()
 host.goto(BASE+'/create');host.reload();assert host.locator('#displayName').is_visible();assert not host.locator('#joinCode').is_visible()
 host.locator('#displayName').fill('Peach');host.locator('#setupSubmit').click();host.wait_for_selector('body.room-connected');host.evaluate("showScreen('watch')");room=host.evaluate('roomId');url=BASE+'/api/rooms/'+room
 guest.goto(BASE+'/?room='+room);guest.locator('#displayName').fill('Berry');guest.locator('#setupSubmit').click();guest.wait_for_selector('body.room-connected')
 # Queue a direct video followed by YouTube; play a first direct video.
 awaitable="async()=>{await action({action:'add',url:'https://media.example/two.mp4'});await action({action:'add',url:'aqz-KE-bpKQ'});await action({action:'watch',url:'https://media.example/one.mp4'})}"
 host.evaluate(awaitable)
 for page in pages:page.wait_for_function('directElement&&directElement.readyState>=2');page.wait_for_function('directElement.currentTime>0')
 for page in pages:assert page.locator('.bottom-nav').is_visible();assert page.evaluate("getComputedStyle(document.querySelector('.bottom-nav')).display==='flex'")
 host.evaluate("Object.defineProperty(window.screen.orientation,'type',{value:'portrait-primary',configurable:true})");host.set_viewport_size({'width':390,'height':300});host.evaluate('syncLandscape()');assert not host.evaluate("document.body.classList.contains('solace-fullscreen')");assert host.locator('.bottom-nav').is_visible();host.set_viewport_size({'width':390,'height':844})
 # A real media ended event must advance both viewers to the next queued source.
 host.evaluate('directElement.currentTime=5.8;directElement.play()')
 for page in pages:page.wait_for_function("state.video==='https://media.example/two.mp4'",timeout=10000)
 host.evaluate('sendControlIntent(player.getCurrentTime(),false);player.pauseVideo()');host.wait_for_timeout(400)
 assert len(host.request.get(url).json()['queue'])==1
 host.evaluate("directElement.dispatchEvent(new Event('ended'))");host.wait_for_timeout(400);assert len(host.request.get(url).json()['queue'])==1
 # Search cards and API pagination, with task-screen controls isolated.
 host.route('**/api/videos?**',lambda route:route.fulfill(json={'items':[{'id':'aqz-KE-bpKQ','title':'A lovely evening','channel':'Solace test','description':'Search result details'}],'next_page':'' if 'page=' in route.request.url else 'next'}))
 host.evaluate('openVideoSelection()');host.locator('#selectionQuery').fill('evening');host.locator('#selectionSearch button').click();host.locator('.result-copy').wait_for();assert host.locator('#searchMore').is_visible();host.locator('#searchMore').click();host.wait_for_function("document.querySelectorAll('.selection-video').length===2")
 host.screenshot(path=str(ROOT/'solace-premium-search.png'))
 host.locator('[data-provider="direct"]').click();assert host.locator('#directUrl').is_visible();assert not host.locator('#searchMore').is_visible()
 host.locator('[data-provider="netflix"]').click();assert host.locator('#netflixUrl').is_visible();assert 'not synced' in host.locator('.source-panel').last.inner_text()
 # Shared goal and cheers on the refreshed court.
 game=host.context.new_page();game.goto(BASE+'/static/game.html?room='+room);game.locator('#join').click();game.wait_for_function('!!game.you')
 other=guest.context.new_page();other.goto(BASE+'/static/game.html?room='+room);other.locator('#join').click();other.wait_for_function('!!game.you');game.wait_for_function('Object.keys(game.players).length===2')
 response=host.request.post(url+'/basketball',data={'action':'shoot','aim':.5,'revision':game.evaluate('game.revision')});assert response.ok
 game.locator('#goal').wait_for(state='visible');assert 'love goal' in game.locator('#goal').inner_text();assert game.locator('#confetti span').count()>0
 other.locator('[data-cheer="🫶"]').click();game.locator('#cheerBubble').wait_for(state='visible');assert 'Berry' in game.locator('#cheerBubble').inner_text()
 game.locator('#goal').wait_for(state='hidden');game.screenshot(path=str(ROOT/'solace-premium-hoops.png'))
 assert not errors,errors
 for page in pages:page.request.post(url+'/leave',data={})
 browser.close();print(json.dumps({'passed':True,'separate_entry_refresh':True,'portrait_footer_during_real_video':True,'actual_media_auto_queue_both_users':True,'stale_end_ignored':True,'search_pagination':True,'provider_screens':True,'shared_goal_cheer':True,'physical_phone':False}))
