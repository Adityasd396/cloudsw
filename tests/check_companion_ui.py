"""Synthetic two-user social/game and portrait footer acceptance in browser engines."""
import io,json,os,uuid
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright,expect
from media_https_fixture import MediaFixture
ROOT=Path(__file__).resolve().parents[1];BASE=os.environ.get('SOLACE_TEST_BASE','http://127.0.0.1:8055');OUT=Path(os.environ.get('SOLACE_SCREENSHOT_DIR',str(ROOT/'audit-results')));OUT.mkdir(parents=True,exist_ok=True)
results=[]
with MediaFixture((ROOT/'.openai/stream-audit/media/soak.mp4').read_bytes()) as first,MediaFixture((ROOT/'.openai/stream-audit/media/soak.mp4').read_bytes()) as second,sync_playwright() as p:
 for engine in ['chromium','webkit']:
  browser=getattr(p,engine).launch(args=['--autoplay-policy=no-user-gesture-required'] if engine=='chromium' else []);contexts=[browser.new_context(viewport=dict(width=390,height=844),has_touch=True,ignore_https_errors=True) for _ in range(2)];pages=[];errors=[];diagnostics=[]
  for context in contexts:
   context.add_init_script("Object.defineProperty(document,'hidden',{get:()=>false});localStorage.setItem('solace-rotation','false');window.vibrations=[];navigator.vibrate=value=>{vibrations.push(value);return true}")
   page=context.new_page();page.on('pageerror',lambda e:(diagnostics if str(e).startswith('/127.0.0.1:') and 'due to access control checks.' in str(e) else errors).append(str(e)));page.route('https://www.youtube.com/**',lambda r:r.abort());pages.append(page)
  host,peer=pages
  def post(ctx,path,data):
   token=ctx.request.get(BASE+'/api/me').json()['csrf'];r=ctx.request.post(BASE+path,data=data,headers={'X-CSRF-Token':token});assert r.ok,(path,r.status,r.text());return r.json()
  codes=[]
  for c,name in zip(contexts,['Peach '+engine,'Moon '+engine]):
   post(c,'/api/me/profile',dict(name=name));codes.append(c.request.get(BASE+'/api/me/connections').json()['friend_code']);post(c,'/api/me/privacy',dict(share_read=True));post(c,'/api/me/discovery',dict(opted=True,visible=True,avatar=True,stats=False,bio='',interests=''))
   raw=io.BytesIO();Image.new('RGB',(36,36),'pink').save(raw,'PNG');r=c.request.post(BASE+'/api/me/avatar',multipart={'picture':{'name':'avatar.png','mimeType':'image/png','buffer':raw.getvalue()}},headers={'X-CSRF-Token':c.request.get(BASE+'/api/me').json()['csrf']});assert r.ok
  peer.goto(BASE+'/home');peer.locator('.home-greeting').click();post(contexts[0],'/api/me/connections',dict(action='request',code=codes[1]));expect(peer.locator('.in-app-notice')).to_contain_text('friend request',timeout=10000);post(contexts[1],'/api/me/connections',dict(action='accept',code=codes[0]))
  host.goto(BASE+'/settings');expect(host.locator('#prefHaptics')).to_be_enabled();host.locator('#prefHaptics').check();host.locator('#prefMusic').check();host.locator('#prefRotate').uncheck();host.locator('#spaceThemes').wait_for();expect(host.locator('#spaceThemes')).to_be_visible()
  for width,height in [(390,844),(844,390),(1280,800)]:
   host.set_viewport_size(dict(width=width,height=height));assert host.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
   for selector in ['#prefHaptics','#prefMusic']:
    box=host.locator(selector).evaluate("n=>{const r=n.getBoundingClientRect(),p=getComputedStyle(n,'::before');return {width:r.width,left:parseFloat(p.left),knob:parseFloat(p.width)}}");assert box['left']+box['knob']<=box['width'],box
  host.set_viewport_size(dict(width=390,height=844));host.screenshot(path=str(OUT/f'settings-professional-{engine}.png'));host.goto(BASE+'/friends');host.locator('#friendsSearch').fill('Moon');expect(host.locator('#homeFriends')).to_contain_text('Moon');host.locator('#homeFriends .profile-link').click();expect(host.get_by_role('dialog',name='Profile')).to_contain_text('Moon');host.screenshot(path=str(OUT/f'profile-professional-{engine}.png'));host.get_by_role('dialog').get_by_role('button',name='Close',exact=True).click();host.screenshot(path=str(OUT/f'friends-professional-{engine}.png'))
  for page in pages:page.goto(BASE+'/world');page.locator('#worldChoice').wait_for();page.locator('#worldJoin').click()
  text='World '+uuid.uuid4().hex;host.locator('#worldText').fill(text);host.locator('#worldSend').click();row=peer.locator('.world-message').filter(has_text=text);expect(row).to_be_visible();expect(row.locator('.chat-photo')).to_be_visible(timeout=10000);assert not row.get_by_role('button',name='Report',exact=True).count();row.dispatch_event('contextmenu');peer.get_by_role('toolbar',name='Message actions').get_by_role('button',name='React ❤️',exact=True).click();expect(host.locator('.world-message').filter(has_text=text).locator('.message-reactions')).to_contain_text('❤️',timeout=10000)
  expect(host.locator('.world-message').filter(has_text=text).locator('.shared-receipt')).to_have_text('✓✓',timeout=10000)
  gif=io.BytesIO();Image.new('RGB',(40,30),'pink').save(gif,'GIF',save_all=True,append_images=[Image.new('RGB',(40,30),'blue')],duration=120,loop=0);host.locator('#worldAttachment input').set_input_files(dict(name='hello.gif',mimeType='image/gif',buffer=gif.getvalue()));host.locator('#worldSend').click();expect(peer.locator('.shared-media').get_by_role('button',name='Play GIF',exact=True).last).to_be_visible();peer.locator('.shared-media').get_by_role('button',name='Play GIF',exact=True).last.click();peer.locator('.shared-media').get_by_role('button',name='Pause GIF',exact=True).last.click();peer.screenshot(path=str(OUT/f'world-professional-{engine}.png'))
  host.goto(BASE+'/messages?friend='+codes[1]);peer.goto(BASE+'/messages?friend='+codes[0]);host.locator('#dmText').fill('Direct '+text);host.locator('#dmSend').click();dm=peer.locator('.dm-message').filter(has_text='Direct '+text);expect(dm.locator('.chat-photo')).to_be_visible(timeout=10000);dm.dispatch_event('contextmenu');peer.get_by_role('toolbar').get_by_role('button',name='React 👏',exact=True).click();expect(host.locator('.dm-message').filter(has_text='Direct '+text).locator('.message-reactions')).to_contain_text('👏',timeout=10000);expect(host.locator('.dm-message').filter(has_text='Direct '+text).locator('.dm-receipt')).to_have_text('✓✓',timeout=10000)
  peer.goto(BASE+'/home');peer.locator('.home-greeting').click();host.locator('#dmText').fill('Notification '+text);host.locator('#dmSend').click();expect(peer.locator('.in-app-notice')).to_contain_text('sent a message',timeout=10000);assert peer.evaluate('vibrations.length')>0
  peer.locator('.in-app-notice').get_by_role('button',name='Open',exact=True).click();peer.locator('#dmText').wait_for();host.locator('#dmAttachment input').set_input_files(dict(name='direct.gif',mimeType='image/gif',buffer=gif.getvalue()));host.locator('#dmSend').click();expect(peer.locator('#dmMessages .shared-media').get_by_role('button',name='Play GIF',exact=True).last).to_be_visible(timeout=10000)
  peer.goto(BASE+'/home');created=[];host.on('request',lambda r:created.append(r.url) if r.method=='POST' and r.url==BASE+'/api/rooms' else None)
  for kind,join in [('hearts','#joinGame'),('hoops','#join'),('ludo','#join')]:
   host.goto(BASE+'/games');host.locator('[data-play-kind='+kind+']').click();host.wait_for_url('**/play/*');expect(host.locator('#playInvite')).to_be_visible();host.locator('#playInvite summary').click();host.locator('#playFriends button').filter(has_text='Moon').click()
   if kind=='hoops':
    post(contexts[1],'/api/me/preferences',dict(in_app_alerts=False));peer.goto(BASE+'/games');peer.locator('#gameInvitations').get_by_role('button',name='Play',exact=True).click();peer.wait_for_url('**/play/*');post(contexts[1],'/api/me/preferences',dict(in_app_alerts=True))
   else:
    notice=peer.locator('.in-app-notice');expect(notice).to_contain_text('invited you to play',timeout=10000);notice.get_by_role('button',name='Play',exact=True).click();peer.wait_for_url('**/play/*')
   assert host.url==peer.url
   for page in pages:page.frame_locator('.play-session iframe').locator(join).click()
   expect(host.locator('#playInvite')).to_be_hidden(timeout=10000)
   if kind=='hearts':
    host.frame_locator('.play-session iframe').locator('#board button').first.click();expect(peer.frame_locator('.play-session iframe').locator('#board button').first).to_have_attribute('data-mark','X')
   peer.goto(BASE+'/home')
  assert not created,created
  host.goto(BASE+'/home');bar=host.locator('.app-mobile-nav').bounding_box();assert bar and bar['height']<=60,bar;expect(host.locator('#momentsChart')).to_be_visible();host.locator('.home-primary a[href="/create"]').click();host.locator('#setupSubmit').click();host.locator('body.room-connected').wait_for();host.evaluate("showScreen('watch')");room=host.evaluate('roomId');peer.goto(BASE+'/?room='+room);peer.locator('body.room-connected').wait_for();peer.evaluate("showScreen('watch')")
  for url in [first.url,second.url]:
   host.evaluate('url=>action({action:"watch",url})',url)
   if engine=='chromium':host.wait_for_function('directElement&&directElement.currentTime>.1')
   for page in pages:
    expect(page.get_by_role('navigation',name='Room navigation')).to_be_visible();rect=page.get_by_role('navigation',name='Room navigation').bounding_box();assert rect and rect['y']+rect['height']<=845 and rect['height']<=64,rect
  host.evaluate("document.documentElement.requestFullscreen=()=>Promise.reject(Error('Test iPhone fallback'));toggleSolaceFullscreen(videoStage)");expect(host.get_by_role('navigation',name='Room navigation')).to_be_visible();host.evaluate('exitSolaceFullscreen()')
  host.locator('#message').fill('Room message '+engine);host.locator('.send').click();r=peer.locator('.chat-message').filter(has_text='Room message '+engine);expect(r).to_be_visible();expect(r.locator('.chat-photo')).to_be_visible(timeout=10000);r.dispatch_event('contextmenu');peer.get_by_role('toolbar').get_by_role('button',name='React ✨',exact=True).click();expect(host.locator('.chat-message').filter(has_text='Room message '+engine).locator('.message-reactions')).to_contain_text('✨',timeout=10000)
  host.locator('#message').focus();host.set_viewport_size(dict(width=390,height=540));expect(host.get_by_role('navigation',name='Room navigation')).to_be_visible();host.locator('#message').blur();host.set_viewport_size(dict(width=390,height=844));host.screenshot(path=str(OUT/f'portrait-footer-{engine}.png'));host.locator('.bottom-nav [data-target=room]').click();tools=host.frame_locator('.inline-room-tools');expect(tools.locator('#roomSettingsForm')).to_be_visible();assert not tools.locator('#spaceThemes').count();assert not host.locator('.room-detail-actions').get_by_role('button',name='Settings',exact=True).count();host.screenshot(path=str(OUT/f'room-management-{engine}.png'))
  assert not errors,errors
  for c in contexts:post(c,'/api/rooms/'+room+'/leave',{});post(c,'/api/me/preferences',dict(world_choice='skipped'))
  browser.close();results.append(dict(engine=engine,passed=True,personal_settings_and_room_management_separate=True,contained_toggles=True,profile_and_friend_search=True,world_gif_avatars_reactions_receipts=True,in_app_request_and_game_notifications=True,three_games_without_stream_room=True,portrait_footer_after_play_and_video_change=True,compact_mobile_navigation=True,physical_devices=False,actual_media=engine=='chromium',webkit_navigation_diagnostics=len(diagnostics)))
print(json.dumps(results));(OUT/'companion-browser-results.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
