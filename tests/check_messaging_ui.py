"""Two isolated browser identities, private messaging, media and responsive UI."""
import io,json,os,time
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright,expect
BASE=os.environ.get('SOLACE_TEST_BASE','http://127.0.0.1:8027')
ROOT=Path(__file__).resolve().parents[1]
OUTPUT=Path(os.environ.get('SOLACE_SCREENSHOT_DIR',str(ROOT/'audit-results')));OUTPUT.mkdir(parents=True,exist_ok=True)
def main():
 with sync_playwright() as p:
  for engine in ['chromium','webkit']:
   browser=getattr(p,engine).launch();a=browser.new_context(viewport={'width':390,'height':844});b=browser.new_context(viewport={'width':390,'height':844});a.add_init_script("if(location.pathname==='/messages')Object.defineProperty(document,'hidden',{get:()=>false})");b.add_init_script("if(location.pathname==='/messages')Object.defineProperty(document,'hidden',{get:()=>false})");pa=a.new_page();pb=b.new_page();errors=[];navigation_diagnostics=[]
   def capture(error):
    message=str(error)
    if 'due to access control checks.' in message and message.startswith('/127.0.0.1:'):navigation_diagnostics.append(message)
    else:errors.append(message)
   for page in [pa,pb]:page.on('pageerror',capture);page.route('https://www.youtube.com/**',lambda r:r.abort())
   def post(ctx,path,data):
    me=ctx.request.get(BASE+'/api/me').json();r=ctx.request.post(BASE+path,data=data,headers={'X-CSRF-Token':me['csrf']});assert r.ok,(path,r.status,r.text());return r.json()
   post(a,'/api/me/profile',{'name':'Peach'});post(b,'/api/me/profile',{'name':'Moon'});code=b.request.get(BASE+'/api/me/connections').json()['friend_code']
   pa.goto(BASE+'/home');assert not pa.get_by_text('Open Solace',exact=True).count();pa.screenshot(path=str(OUTPUT/('moonlit-home-'+engine+'.png')),full_page=True)
   pa.goto(BASE+'/friends');pa.locator('#connectCode').fill(code[:4].lower()+'-'+code[4:].lower());pa.locator('#connectForm button').click();pa.locator('#friendPreview').get_by_text('Moon',exact=True).wait_for();assert not a.request.get(BASE+'/api/me/connections').json()['friends'];pa.get_by_role('button',name='Send friend request',exact=True).click();pa.get_by_text('Friend request sent.',exact=True).wait_for()
   pb.goto(BASE+'/friends');pb.locator('#homeRequests').get_by_role('button',name='Accept',exact=True).click();pb.locator('#homeFriends').get_by_role('button',name='Message',exact=True).wait_for();pa.reload();pa.locator('#homeFriends').get_by_role('button',name='Message',exact=True).click();pa.wait_for_url('**/messages?*');pa.locator('#dmName').get_by_text('Moon',exact=True).wait_for();pb.locator('#homeFriends').get_by_role('button',name='Message',exact=True).click();pb.wait_for_url('**/messages?*');pb.locator('#dmName').get_by_text('Peach',exact=True).wait_for()
   pa.locator('#dmText').fill('A little hello ♡');pa.locator('#dmSend').click();pb.locator('#dmMessages').get_by_text('A little hello ♡',exact=True).wait_for();pa.locator('#dmText').fill('typing a new thought');pb.locator('#dmTyping').get_by_text('Peach is typing…',exact=True).wait_for();pa.locator('#dmText').fill('')
   raw=io.BytesIO();Image.new('RGB',(180,120),'pink').save(raw,'PNG');expect(pa.locator('#dmSend')).to_be_enabled();pa.locator('#dmAttachment input[type=file]').set_input_files({'name':'picture.png','mimeType':'image/png','buffer':raw.getvalue()});pa.locator('.attachment-preview img').wait_for();assert pa.locator('.attachment-preview img').evaluate('(img)=>img.decode().then(()=>img.naturalWidth>0)');pa.locator('#dmSend').click();pb.locator('.shared-media img').wait_for();pb.locator('.picture-expand').click();pb.get_by_role('dialog',name='Expanded picture').wait_for();pb.get_by_role('button',name='Close ×').click()
   gif=io.BytesIO();Image.new('RGB',(90,60),'pink').save(gif,'GIF',save_all=True,append_images=[Image.new('RGB',(90,60),'purple')],duration=[120,140],loop=0);expect(pa.locator('#dmSend')).to_be_enabled();pa.locator('#dmAttachment input[type=file]').set_input_files({'name':'heart.gif','mimeType':'image/gif','buffer':gif.getvalue()});pa.locator('#dmSend').click();pb.get_by_role('button',name='Play GIF',exact=True).wait_for();pb.get_by_role('button',name='Play GIF',exact=True).click();pb.get_by_role('button',name='Pause GIF',exact=True).click()
   # Cancel a selected upload without sending or dropping the next draft.
   expect(pa.locator('#dmSend')).to_be_enabled();pa.locator('#dmAttachment input[type=file]').set_input_files({'name':'cancel.png','mimeType':'image/png','buffer':raw.getvalue()});pa.locator('.attachment-preview').get_by_role('button',name='Cancel',exact=True).click();assert pa.locator('.attachment-preview').is_hidden()
   for w,h in [(390,844),(844,390),(1280,800)]:
    for page in [pa,pb]:page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(120);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(engine,w)
   pa.screenshot(path=str(OUTPUT/('private-messages-'+engine+'.png')),full_page=True)
   # Room creation uses the same saved profile and no room title is required.
   pa.goto(BASE+'/create');assert pa.locator('#displayName').is_hidden();pa.locator('#setupSubmit').click();pa.locator('body.room-connected').wait_for();room=pa.url.split('room=')[1];pa.evaluate("showScreen('watch')");assert a.request.get(BASE+'/api/rooms/'+room).json()['name']=='Peach’s room'
   expect(pa.locator('.room-attach .attach-button')).to_be_enabled();pa.locator('.room-attach input[type=file]').set_input_files({'name':'room.png','mimeType':'image/png','buffer':raw.getvalue()});pa.locator('#message').fill('Moon picture');pa.locator('#chatForm').evaluate('(f)=>f.requestSubmit()');pa.locator('#messages .shared-media img').wait_for();expect(pa.locator('.room-attach .attach-button')).to_be_enabled();pa.locator('.room-attach input[type=file]').set_input_files({'name':'room.gif','mimeType':'image/gif','buffer':gif.getvalue()});pa.locator('#chatForm').evaluate('(f)=>f.requestSubmit()');
   try:pa.locator('#messages').get_by_role('button',name='Play GIF',exact=True).wait_for(timeout=7000)
   except Exception:
    print({'engine':engine,'toast':pa.locator('#toast').inner_text(),'preview':pa.locator('.room-attachment-preview').inner_text(),'room_media':a.request.get(BASE+'/api/rooms/'+room).json().get('media_items'),'messages':pa.locator('#messages').inner_text(),'errors':errors});raise
   pa.goto(BASE+'/settings');pa.locator('#spaceThemes .theme-landscape').first.wait_for();pa.screenshot(path=str(OUTPUT/('moonlit-settings-'+engine+'.png')),full_page=True)
   post(a,'/api/me/connections',{'action':'block','code':code});cid=b.request.get(BASE+'/api/me/conversations').json()['conversations'];assert not cid
   assert not errors,errors
   browser.close();print(json.dumps({'engine':engine,'passed':True,'friend_preview_explicit_request':True,'text_typing_images_gif_pause_viewer_cancel':True,'saved_identity_unnamed_room_media':True,'mobile_landscape_desktop':True,'physical_devices':False,'webkit_unload_diagnostics':len(navigation_diagnostics)}))
if __name__=='__main__':main()
