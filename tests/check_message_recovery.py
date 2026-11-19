"""Lost replies, retries, concurrent drafts and viewport-keyboard layout models."""
import json,os,io
from PIL import Image
from playwright.sync_api import sync_playwright,expect
BASE=os.environ.get('SOLACE_TEST_BASE','http://127.0.0.1:8027')
with sync_playwright() as p:
 browser=p.chromium.launch();a=browser.new_context(viewport={'width':390,'height':844});b=browser.new_context()
 def post(c,path,data):
  t=c.request.get(BASE+'/api/me').json()['csrf'];r=c.request.post(BASE+path,data=data,headers={'X-CSRF-Token':t});assert r.ok,(path,r.status);return r.json()
 post(a,'/api/me/profile',{'name':'Peach'});post(b,'/api/me/profile',{'name':'Moon'});ac=a.request.get(BASE+'/api/me/connections').json()['friend_code'];bc=b.request.get(BASE+'/api/me/connections').json()['friend_code'];post(a,'/api/me/connections',{'action':'request','code':bc});post(b,'/api/me/connections',{'action':'accept','code':ac})
 a.add_init_script("const v=new EventTarget();Object.assign(v,{width:390,height:844,offsetTop:0,scale:1});Object.defineProperty(window,'visualViewport',{value:v});")
 page=a.new_page();page.goto(BASE+'/messages?friend='+bc);page.locator('#dmName').get_by_text('Moon',exact=True).wait_for();cid=page.url.split('chat=')[1];endpoint='/api/me/conversations/'+cid;lost=[False]
 def drop_once(route):
  if route.request.method=='POST' and not lost[0]:route.fetch();lost[0]=True;route.abort('failed')
  else:route.continue_()
 page.route(BASE+endpoint,drop_once);page.locator('#dmText').fill('Only once, even if the reply is lost');page.locator('#dmSend').click();page.locator('#dmPending').get_by_role('button',name='Retry',exact=True).wait_for();page.locator('#dmPending').get_by_role('button',name='Retry',exact=True).click();page.locator('#dmPending').get_by_text('Sending…',exact=True).wait_for(state='hidden');expect(page.locator('#dmSend')).to_be_enabled();assert len(a.request.get(BASE+endpoint).json()['messages'])==1;page.unroute(BASE+endpoint,drop_once)
 held=[]
 def hold(route):
  if route.request.method=='POST':held.append((route,route.fetch()))
  else:route.continue_()
 page.route(BASE+endpoint,hold);page.locator('#dmText').fill('The previous message');page.locator('#dmSend').click();page.wait_for_timeout(100);assert held;page.locator('#dmText').fill('My next draft stays');route,response=held.pop();route.fulfill(response=response);expect(page.locator('#dmSend')).to_be_enabled();assert page.locator('#dmText').input_value()=='My next draft stays';page.unroute(BASE+endpoint,hold)
 a.set_offline(True);page.locator('#dmText').fill('Offline draft');page.locator('#dmSend').click();page.locator('#dmPending').get_by_role('button',name='Retry',exact=True).wait_for();a.set_offline(False);page.locator('#dmPending').get_by_role('button',name='Retry',exact=True).click();expect(page.locator('#dmSend')).to_be_enabled();assert len(a.request.get(BASE+endpoint).json()['messages'])==3
 cycles=[]
 for w,h,k in [(390,844,440),(844,390,220)]:
  page.set_viewport_size({'width':w,'height':h});page.evaluate('''({w,h})=>{visualViewport.width=w;visualViewport.height=h;visualViewport.dispatchEvent(new Event('resize'))}''',{'w':w,'h':h});page.locator('#dmText').focus()
  for keyboard_height in [k,h,k,h]:
   page.evaluate("v=>{visualViewport.height=v;visualViewport.dispatchEvent(new Event('resize'))}",keyboard_height);page.wait_for_timeout(80);box=page.locator('#dmText').bounding_box();assert box and box['y']+box['height']<=keyboard_height+2,(w,keyboard_height,box);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');assert page.locator('#dmHistory').evaluate('(n)=>n.scrollHeight-n.scrollTop-n.clientHeight<3');cycles.append({'width':w,'viewport_height':keyboard_height,'composer_visible':True})
 page.locator('#dmText').blur();raw=io.BytesIO();Image.new('RGB',(80,60),'pink').save(raw,'PNG');failed=[False]
 def fail_upload(route):
  if not failed[0]:failed[0]=True;route.fulfill(status=503,content_type='application/json',body=json.dumps({'error':'Upload temporarily unavailable. Retry.'}))
  else:route.continue_()
 page.route(BASE+'/api/me/media',fail_upload);page.locator('#dmAttachment input').set_input_files({'name':'retry.png','mimeType':'image/png','buffer':raw.getvalue()});page.locator('#dmSend').click();page.get_by_role('button',name='Retry upload',exact=True).wait_for();page.get_by_role('button',name='Retry upload',exact=True).click();page.locator('.attachment-preview').get_by_text('Ready',exact=True).wait_for();page.locator('#dmPending').get_by_role('button',name='Retry',exact=True).click();expect(page.locator('#dmSend')).to_be_enabled();assert len(a.request.get(BASE+endpoint).json()['messages'])==4;page.unroute(BASE+'/api/me/media',fail_upload)
 waiting=[]
 def hold_upload(route):waiting.append(route)
 page.route(BASE+'/api/me/media',hold_upload);page.locator('#dmAttachment input').set_input_files({'name':'cancel.png','mimeType':'image/png','buffer':raw.getvalue()});page.locator('#dmSend').click();page.locator('.attachment-preview progress').wait_for();page.locator('.attachment-preview').get_by_role('button',name='Cancel',exact=True).click();page.wait_for_timeout(100)
 for route in waiting:
  try:route.abort()
  except Exception:pass
 page.unroute(BASE+'/api/me/media',hold_upload);assert page.locator('.attachment-preview').is_hidden();assert len(a.request.get(BASE+endpoint).json()['messages'])==4
 browser.close();print(json.dumps({'passed':True,'lost_reply_retry_exactly_once':True,'new_draft_preserved_during_send':True,'offline_retry':True,'upload_retry_and_inflight_cancel':True,'keyboard_models':cycles,'physical_devices':False}))
