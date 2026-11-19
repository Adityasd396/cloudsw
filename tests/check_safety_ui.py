"""Local disposable users only; browser-engine checks are not physical phone tests."""
import base64,json,os,sys
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from staff_auth import totp
BASE=os.environ.get('SOLACE_TEST_BASE','http://127.0.0.1:8040');ROOT=Path(__file__).resolve().parents[1]
OUTPUT=Path(os.environ.get('SOLACE_SCREENSHOT_DIR',str(ROOT/'audit-results')));OUTPUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 for engine in ['chromium','webkit']:
  browser=getattr(p,engine).launch();a=browser.new_context(viewport={'width':390,'height':844});b=browser.new_context(viewport={'width':390,'height':844});errors=[];navigation_diagnostics=[]
  for context in [a,b]:context.add_init_script("Object.defineProperty(document,'hidden',{get:()=>false})")
  pa=a.new_page();pb=b.new_page()
  def capture(e):
   message=str(e)
   if message.startswith('/127.0.0.1:') and 'due to access control checks.' in message:navigation_diagnostics.append(message)
   else:errors.append(message)
  for page in [pa,pb]:page.on('pageerror',capture)
  def post(context,path,data):
   token=context.request.get(BASE+'/api/me').json()['csrf'];r=context.request.post(BASE+path,data=data,headers={'X-CSRF-Token':token});assert r.ok,(path,r.status,r.text());return r.json()
  post(a,'/api/me/profile',dict(name='Peach '+engine));post(b,'/api/me/profile',dict(name='Moon '+engine));pa.goto(BASE+'/settings');pb.goto(BASE+'/settings');expect(pa.locator('#prefWorld')).not_to_be_checked()
  for page in [pa,pb]:
   page.get_by_text('Public profile sharing',exact=True).click();page.locator('#discoverySettings [name=opted]').check();page.locator('#discoverySettings [name=bio]').fill('A synthetic music companion');page.locator('#discoverySettings button').click();expect(page.locator('#settingsStatus')).to_have_text('Saved')
  ac=a.request.get(BASE+'/api/me/connections').json()['friend_code'];bc=b.request.get(BASE+'/api/me/connections').json()['friend_code'];pa.evaluate('(code)=>SolacePeople.open(code)',bc);expect(pa.get_by_role('dialog')).to_contain_text('Moon');pa.get_by_role('dialog').get_by_role('button',name='Connect',exact=True).click();expect(pa.get_by_role('dialog')).to_contain_text('Request pending');pa.get_by_role('dialog').get_by_role('button',name='Close',exact=True).click()
  pb.evaluate('(code)=>SolacePeople.open(code)',ac);pb.get_by_role('dialog').get_by_role('button',name='Accept',exact=True).click();expect(pb.get_by_role('dialog').get_by_role('button',name='Message',exact=True)).to_be_visible()
  for w,h in [(390,844),(844,390),(1280,800)]:
   pb.set_viewport_size(dict(width=w,height=h));assert pb.get_by_role('dialog').evaluate('(n)=>{const r=n.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&r.top>=0&&r.bottom<=innerHeight+1}');assert pb.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  pb.set_viewport_size(dict(width=390,height=844));pb.screenshot(path=str(OUTPUT/('open-world-profile-'+engine+'.png')));pb.get_by_role('dialog').get_by_role('button',name='Report',exact=True).click();pb.get_by_role('dialog').locator('textarea').fill('Synthetic browser report; no real people.');pb.get_by_role('dialog').get_by_role('button',name='Submit report',exact=True).click();expect(pb.get_by_role('dialog')).to_contain_text('Report received');pb.get_by_role('dialog').get_by_role('button',name='Close',exact=True).click()
  admin=browser.new_context(viewport={'width':1280,'height':900});page=admin.new_page();page.on('pageerror',capture);page.goto(BASE+'/ops/solace');page.locator('[name=username]').fill('auditor-'+engine);page.locator('[name=password]').fill('Synthetic-Staff-Password-2026!');page.locator('[name=otp]').fill(totp(base64.b32encode(b'12345678901234567890').decode()));page.get_by_role('button',name='Unlock panel').click();page.locator('#safetyReports .safety-case').first.wait_for();assert admin.request.get(BASE+'/ops/solace/data').json()['visitors']==[];assert admin.request.get(BASE+'/ops/solace/safety/audit').json()['verified'];page.locator('#platformSafety').screenshot(path=str(OUTPUT/('admin-safety-'+engine+'.png')))
  page.get_by_role('button',name='Lock panel',exact=True).click();expect(page.get_by_role('button',name='Unlock panel')).to_be_visible();assert admin.request.get(BASE+'/ops/solace/safety/reports').status==401
  for context in [a,b]:post(context,'/api/me/discovery',dict(opted=False,visible=True,avatar=False,stats=False,bio='',interests=''))
  assert not errors,errors;browser.close();print(json.dumps(dict(engine=engine,passed=True,discovery_consent=True,connect_accept_shared_profile=True,report_submission=True,named_staff_mfa_login_logout=True,private_telemetry_redacted=True,portrait_landscape_desktop=True,physical_devices=False,navigation_unload_diagnostics=len(navigation_diagnostics))))
