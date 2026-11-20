"""Disposable local two-user dashboard, guest and room-control browser smoke."""
import json,os,time,re
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE=os.environ.get('SOLACE_TEST_BASE','http://127.0.0.1:8027')
def main():
 with sync_playwright() as p:
  for engine in ['chromium','webkit']:
   browser=getattr(p,engine).launch();a=browser.new_context(viewport={'width':390,'height':844});b=browser.new_context(viewport={'width':390,'height':844});pa=a.new_page();pb=b.new_page();errors=[];navigation_diagnostics=[];leaving=set()
   def capture(page,error):
    message=str(error)
    if page in leaving and '/api/rooms/' in message and 'due to access control checks.' in message:navigation_diagnostics.append(message)
    else:errors.append(message)
   for page in [pa,pb]:
    page.route('https://www.youtube.com/**',lambda route:route.abort());page.on('pageerror',lambda e,page=page:capture(page,e))
   def post(ctx,path,data):
    csrf=ctx.request.get(BASE+'/api/me').json()['csrf'];r=ctx.request.post(BASE+path,data=data,headers={'X-CSRF-Token':csrf});assert r.ok,(path,r.status,r.text());return r.json()
   pa.goto(BASE+'/home');pa.wait_for_url('**/welcome');pa.locator('#guestChoice').click();pa.locator('#guestForm input').fill('Peach');pa.locator('#guestForm button').click();pa.wait_for_url('**/home');pa.get_by_role('heading',name='Hi, Peach').wait_for();pa.reload();pa.get_by_role('heading',name='Hi, Peach').wait_for();assert not pa.locator('#guestChoice').count()
   post(b,'/api/me/profile',{'name':'Moon'});pb.goto(BASE+'/home');pb.get_by_role('heading',name='Hi, Moon').wait_for()
   c=b.request.get(BASE+'/api/me/connections').json()['friend_code'];post(a,'/api/me/connections',{'action':'request','code':c});c=a.request.get(BASE+'/api/me/connections').json()['friend_code'];post(b,'/api/me/connections',{'action':'accept','code':c})
   pa.locator('.home-primary a[href="/create"]').click();pa.locator('#setupSubmit').wait_for();assert pa.locator('#displayName').is_hidden();pa.locator('#newRoomName').fill('Moon garden');pa.locator('#setupSubmit').click();pa.wait_for_url('**/?room=*');room=pa.url.split('room=')[1];pa.locator('body.room-connected').wait_for();pa.evaluate("showScreen('room')");frame=pa.frame_locator('.inline-room-tools');
   try:frame.get_by_role('heading',name='Invite friends').wait_for(timeout=8000)
   except Exception:
    print({'engine':engine,'errors':errors,'active':pa.evaluate('activeScreen'),'frames':[(f.url,f.locator('body').inner_text()[:350]) for f in pa.frames],'src':pa.locator('.inline-room-tools').get_attribute('src')});raise
   frame.get_by_role('button',name='Invite',exact=True).click();frame.get_by_text('Invitation sent.',exact=True).wait_for()
   pb.reload();pb.locator('#homeInvitations').get_by_role('button',name='Accept',exact=True).click();
   pb.wait_for_url(re.compile(r'/(?:join)?\?room=\d+'),wait_until='domcontentloaded');pb.locator('body.room-connected').wait_for()
   assert pb.url.endswith('room='+room)
   frame.locator('[name=visibility]').select_option('public');assert frame.locator('#publicConfirmation').is_visible();frame.locator('[name=confirm_public]').check();frame.get_by_role('button',name='Save settings',exact=True).click();frame.get_by_text('Room updated.',exact=True).wait_for();assert a.request.get(BASE+'/api/public/rooms').json()['rooms']
   # Shared seek and play intent remains consistent while the separate tools screen is open.
   post(a,'/api/rooms/'+room,{'action':'playback','position':25,'playing':True});state=b.request.get(BASE+'/api/rooms/'+room).json();assert state['position']==25 and state['playing']==1
   post(b,'/api/rooms/'+room,{'action':'playback','position':12,'playing':False});assert a.request.get(BASE+'/api/rooms/'+room).json()['playing']==0
   for page in [pa,pb]:
    for w,h in [(390,844),(844,390),(1280,800)]:
     page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(150);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(engine,w)
   leaving.add(pa);pa.goto(BASE+'/home');pa.locator('#homeStats[aria-busy=false]').wait_for();pa.screenshot(path=str(Path('audit-results')/('home-'+engine+'.png')),full_page=True);pa.set_viewport_size({'width':390,'height':844});pa.screenshot(path=str(Path('audit-results')/('home-'+engine+'-portrait.png')),full_page=True)
   assert not errors,errors
   a.request.post(BASE+'/api/rooms/'+room+'/leave',data={});b.request.post(BASE+'/api/rooms/'+room+'/leave',data={});browser.close();print(json.dumps({'engine':engine,'passed':True,'guests_returning_friends_invitations_visibility':True,'portrait_landscape_desktop':True,'shared_controls':True,'physical_phones':False,'expected_navigation_cancellation_diagnostics':len(navigation_diagnostics)}))
if __name__=='__main__':main()
