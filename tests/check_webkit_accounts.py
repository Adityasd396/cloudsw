"""WebKit account/profile/history UX without assuming a trusted media fixture."""
import io,json,time
from PIL import Image
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8019'
with sync_playwright() as p:
 browser=p.webkit.launch();page=browser.new_page(viewport={'width':390,'height':844});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(BASE+'/signup');page.locator('[name=name]').fill('WebKit Peach');page.locator('[name=email]').fill('webkit-'+str(time.time_ns())+'@example.test');page.locator('[name=password]').fill('a webkit account password');page.locator('[name=accept_terms]').check();page.locator('#authForm button').click();page.wait_for_url('**/home');page.goto(BASE+'/account')
 image=io.BytesIO();Image.new('RGB',(40,40),'purple').save(image,'PNG');page.locator('[name=picture]').set_input_files({'name':'profile.png','mimeType':'image/png','buffer':image.getvalue()});page.locator('#pictureForm button').click();page.get_by_text('Picture updated.',exact=True).wait_for();page.locator('#removePicture').click();page.get_by_text('Picture removed.',exact=True).wait_for()
 for w,h in [(390,844),(844,390)]:page.set_viewport_size({'width':w,'height':h});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.goto(BASE+'/history');page.get_by_text('No viewing sessions in these dates.',exact=False).wait_for();page.goto(BASE+'/account');page.locator('#signout').click();page.wait_for_url('**/signin');assert page.request.get(BASE+'/api/me/history').status==401
 assert not errors,errors;browser.close();print(json.dumps({'passed':True,'engine':'webkit','signup_profile_picture_history_empty_and_signout':True,'portrait_landscape':True,'media':'Not covered by this account-only check','physical_phones':False}))
