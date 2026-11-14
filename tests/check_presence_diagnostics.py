import json,time,re
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8017'
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 browser=p.chromium.launch();contexts=[];pages=[];errors=[]
 for name in ['Peach','Berry']:
  context=browser.new_context(viewport={'width':390,'height':844},has_touch=True);contexts.append(context)
  context.add_init_script('''window.testHidden=false;Object.defineProperty(document,'hidden',{get:()=>window.testHidden});const v=new EventTarget();Object.assign(v,{height:844,width:390,offsetTop:0,scale:1});Object.defineProperty(window,'visualViewport',{value:v});''')
  page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)));page.route('https://www.youtube.com/**',lambda route:route.abort());pages.append(page)
 host,guest=pages;host.goto(BASE);host.locator('#homeCreate').click();host.locator('#displayName').fill('Peach');host.locator('#setupSubmit').click();host.wait_for_selector('body.room-connected');host.evaluate("showScreen('watch')");room=host.evaluate('roomId')
 guest.goto(BASE+'/?room='+room);guest.locator('#displayName').fill('Berry');guest.locator('#setupSubmit').click();guest.wait_for_selector('body.room-connected')
 host.wait_for_function('state.participants.length===2')
 def status(page,name,value):page.wait_for_function('''({name,value})=>state.participants.some(p=>p.name===name&&p.status===value)''',arg={'name':name,'value':value},timeout=1800)
 samples=[]
 for observer,peer,name in [(host,guest,'Berry'),(guest,host,'Peach')]:
  observer.locator('#message').focus();observer.locator('#message').fill('Unsent private draft')
  for height in [844,504,844]:
   observer.evaluate('(h)=>{visualViewport.height=h;visualViewport.dispatchEvent(new Event("resize"))}',height);observer.wait_for_timeout(100)
   observer.locator('.gesture-toggle').tap();observer.wait_for_timeout(100)
   bounds=observer.evaluate('''()=>{const r=s=>document.querySelector(s).getBoundingClientRect(),form=r('#chatForm'),tray=r('#gestureTray'),activity=r('.watch>.joined-names'),messages=r('#messages');return {valid:messages.bottom<=tray.top+1&&tray.bottom<=form.top+1&&activity.bottom<=messages.top+1&&form.bottom<=visualViewport.height+1,people:activity.height}}''');assert bounds['valid'],bounds
   start=time.monotonic();peer.evaluate("window.testHidden=true;document.dispatchEvent(new Event('visibilitychange'))");status(observer,name,'inactive');elapsed=time.monotonic()-start
   assert observer.locator('.joined-names .activity-person').filter(has_text=name).locator('.activity-dot.inactive').count()==1
   start=time.monotonic();peer.evaluate("window.testHidden=false;document.dispatchEvent(new Event('visibilitychange'))");status(observer,name,'active');active_elapsed=time.monotonic()-start
   samples.append({'peer':name,'viewport_height':height,'inactive_ms':round(elapsed*1000),'active_ms':round(active_elapsed*1000),'no_overlap':True})
   observer.locator('.gesture-toggle').tap()
  observer.locator('#message').blur()
 # Silently lost connections can only be inferred by heartbeat timeout.
 guest.route('**/api/rooms/**',lambda route:route.abort())
 start=time.monotonic();host.wait_for_function("state.participants.some(p=>p.name==='Berry'&&p.status==='reconnecting')",timeout=6000)
 host.wait_for_function("state.participants.some(p=>p.name==='Berry'&&p.status==='inactive')",timeout=10000);silent_seconds=time.monotonic()-start
 guest.unroute('**/api/rooms/**');guest.evaluate("window.dispatchEvent(new Event('online'))");status(host,'Berry','active')
 # Flush known snapshots, then confirm both roles and privacy in the actual private panel.
 for page in pages:page.wait_for_timeout(2200);page.evaluate('sendDiagnostics()')
 host.wait_for_timeout(500)
 admin=browser.new_context();request=admin.request
 login=request.get(BASE+'/ops/solace');csrf=re.search(r'name="csrf" value="([^"]+)"',login.text()).group(1)
 response=request.post(BASE+'/ops/solace',form={'csrf':csrf,'password':'Disposable-Smoke-Only-2026!'},headers={'Origin':BASE});assert response.ok
 data=request.get(BASE+'/ops/solace/data').json();reports=[r for r in data['client_diagnostics'] if r['room']==room]
 assert {r['role'] for r in reports}=={'host','peer'},reports
 assert all(r['details']['client']=='web' for r in reports)
 assert 'Unsent private draft' not in json.dumps(reports)
 panel=admin.new_page();panel.goto(BASE+'/ops/solace');panel.wait_for_selector('#clientDiagnostics tr');assert panel.locator('#clientDiagnostics').inner_text().find('Peach')>=0
 assert not errors,errors
 for page in pages:page.request.post(BASE+'/api/rooms/'+room+'/leave',data={})
 browser.close();report={'passed':True,'transitions':samples,'silent_disconnect_seconds':round(silent_seconds,2),'admin_roles_recorded':['host','peer'],'draft_not_recorded':True,'physical_phone':False}
 (ROOT/'presence-diagnostics-results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
