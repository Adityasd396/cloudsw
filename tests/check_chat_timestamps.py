import json
from playwright.sync_api import sync_playwright

BASE='http://127.0.0.1:8017'
with sync_playwright() as p:
 browser=p.chromium.launch();context=browser.new_context(viewport={'width':390,'height':844},has_touch=True)
 context.add_init_script('const vv=new EventTarget();Object.assign(vv,{height:844,offsetTop:0,scale:1});Object.defineProperty(window,"visualViewport",{value:vv});')
 page=context.new_page();page.route('https://www.youtube.com/**',lambda route:route.abort());page.goto(BASE)
 page.locator('#homeCreate').click();page.locator('#displayName').fill('Peach');page.locator('#setupSubmit').click();page.wait_for_selector('body.room-connected');page.evaluate("showScreen('watch')");room=page.evaluate('roomId');url=BASE+'/api/rooms/'+room
 peer=browser.new_context();assert peer.request.post(url,data={'action':'join','name':'Berry'}).ok
 for request in [page.request,peer.request]:
  for body in ['Hi','A longer message with a timestamp that must remain visible. '*5,'🥰']:
   response=request.post(url,data={'action':'chat','body':body});assert response.ok,response.text();page.wait_for_timeout(550)
 page.wait_for_function('state.messages.length===6');assert page.locator('.message-grouped').count()>=4
 results=[]
 for mode,width,height in [('portrait',390,844),('keyboard-open',390,504),('narrow-keyboard',320,450),('keyboard-closed',390,844),('landscape',844,390)]:
  page.set_viewport_size({'width':width,'height':height});page.evaluate('(height)=>{visualViewport.height=height;visualViewport.dispatchEvent(new Event("resize"))}',height)
  if 'keyboard' in mode and mode!='keyboard-closed':page.locator('#message').focus();page.locator('#message').press_sequentially('Typing a reply',delay=5)
  else:page.locator('#message').blur()
  page.wait_for_timeout(700)
  rows=page.evaluate('''()=>[...document.querySelectorAll('#messages .chat-message')].map(row=>{const t=row.querySelector(':scope > div:not(.mini-avatar) > time'),r=t.getBoundingClientRect(),b=t.parentElement.getBoundingClientRect(),s=getComputedStyle(t);return {grouped:row.classList.contains('message-grouped'),mine:row.classList.contains('message-mine'),width:r.width,height:r.height,clip:s.clipPath,position:s.position,inside:r.left>=b.left-1&&r.right<=b.right+1&&r.top>=b.top-1&&r.bottom<=b.bottom+1}})''')
  assert len(rows)==6
  assert all(r['width']>10 and r['height']>5 and r['clip']=='none' and r['position']=='static' and r['inside'] for r in rows),(mode,rows)
  results.append({'mode':mode,'timestamps_visible':len(rows),'grouped_messages':sum(r['grouped'] for r in rows)})
 # A live incoming grouped message must also retain its timestamp while typing.
 response=peer.request.post(url,data={'action':'chat','body':'One more reply'});assert response.ok
 page.wait_for_function('state.messages.length===7');assert page.locator('.chat-message').last.locator('time').evaluate('(t)=>getComputedStyle(t).clipPath==="none"&&t.getBoundingClientRect().width>10')
 for request in [page.request,peer.request]:request.post(url+'/leave',data={})
 browser.close();print(json.dumps({'passed':True,'layouts':results,'live_incoming_timestamp':True,'physical_phone':False}))
