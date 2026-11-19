"""Local admin quota UI, recovery errors and public link checks."""
import json,time
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8017';NAME='Quota '+str(time.time_ns())[-10:]
with sync_playwright() as p:
 browser=p.chromium.launch();errors=[];console=[]
 admin=browser.new_page(viewport={'width':390,'height':844});user=browser.new_page(viewport={'width':390,'height':844})
 for page in [admin,user]:page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:console.append(m.text) if 'Content Security Policy' in m.text else None)
 user.goto(BASE+'/signup');user.locator('[name=name]').fill(NAME);user.locator('[name=email]').fill('quota-'+str(time.time_ns())+'@example.test');user.locator('[name=password]').fill('a unique quota test password');user.locator('[name=accept_terms]').check();user.locator('#authForm button').click();user.wait_for_url('**/account')
 admin.goto(BASE+'/ops/solace');admin.locator('[name=password]').fill('Disposable-Smoke-Only-2026!');admin.locator('form button').click();admin.locator('#defaultStorage').wait_for();admin.wait_for_function("()=>document.querySelector('#defaultStorage').value==='50'")
 admin.locator('#defaultStorage').fill('5');admin.locator('#saveDefaultStorage').click();admin.get_by_text('Storage limit saved. Existing data is preserved.',exact=True).wait_for()
 row=admin.locator('#userStorage tr').filter(has_text=NAME);row.locator('input').fill('7');row.get_by_role('button',name='Save',exact=True).click();admin.wait_for_function("()=>[...document.querySelectorAll('#userStorage tr')].some(r=>r.textContent.includes('"+NAME+"')&&r.querySelector('input').value==='7')")
 user.reload();user.wait_for_function("()=>document.querySelector('#storageUsage').textContent.includes('/ 7 MiB')")
 row=admin.locator('#userStorage tr').filter(has_text=NAME);row.get_by_role('button',name='Use default',exact=True).click();admin.wait_for_function("()=>[...document.querySelectorAll('#userStorage tr')].some(r=>r.textContent.includes('"+NAME+"')&&r.querySelector('input').value==='5')")
 admin.locator('#defaultStorage').fill('50');admin.locator('#saveDefaultStorage').click();admin.wait_for_function("()=>document.querySelector('#defaultStorage').value==='50'")
 user.goto(BASE+'/reset-password#token=invalid-token');user.wait_for_function("()=>location.hash===''");user.locator('#passwordReset [name=password]').fill('a new unique reset password');user.locator('#passwordReset button').click();user.get_by_text('This link is invalid or expired. Request a new one.',exact=True).wait_for()
 for path in ['/','/features','/how-it-works','/about','/faq','/contact','/privacy','/terms']:
  user.goto(BASE+path);assert user.get_by_role('heading',level=1).count()==1;assert user.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert not errors,errors;assert not console,console;browser.close();print(json.dumps({'passed':True,'admin_default_and_user_override':True,'reset_override':True,'profile_storage_visible':True,'fragment_not_retained':True,'expired_link_message':True,'public_pages_fit_mobile':True,'no_console_errors':True}))
