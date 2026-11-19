import io
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from PIL import Image
import test_app
from app import app, db


class PublicLaunchTests(unittest.TestCase):
    setUp=test_app.WatchPartyTests.setUp
    tearDown=test_app.WatchPartyTests.tearDown

    def post(self,client,path,data=None,method='POST',**kw):
        token=client.get('/api/me').json['csrf']
        return client.open(path,method=method,json=data,headers={'X-CSRF-Token':token},**kw)

    def signup(self,client=None,email='peach@example.test',name='Peach'):
        return self.post(client or self.host,'/api/auth/signup',{'name':name,'email':email,'password':'a good unique password','accept_terms':'on'})

    def watch(self,client=None,active=True):
        return self.post(client or self.host,'/api/me/watch',{'room':self.url.split('/')[-1],'active':active,'title':'Synthetic test film'})

    def play(self):
        self.host.post(self.url,json={'action':'watch','url':'https://media.example/film.mp4?private_token=secret'})

    def test_public_pages_are_crawlable_and_seo_uses_configured_origin_only(self):
        with patch.dict(app.config,{'SOLACE_PUBLIC_URL':'https://watch.example.test','SOLACE_CONTACT_EMAIL':'support@example.test'}):
            for path in ['/','/features','/how-it-works','/about','/faq','/contact','/privacy','/terms']:
                page=app.test_client().get(path);self.assertEqual(page.status_code,200);self.assertIn(b'<h1>',page.data);self.assertIn(b'index,follow',page.data)
                self.assertIn(('https://watch.example.test'+path).encode(),page.data)
                self.assertNotIn(b'Jaanu',page.data)
            sitemap=self.host.get('/sitemap.xml').text
            for private in ['/account','/history','/ops/','/api/','/join','?room=']:self.assertNotIn(private,sitemap)
            self.assertIn('https://watch.example.test/sitemap.xml',self.host.get('/robots.txt').text)
            self.assertNotIn('evil.invalid',self.host.get('/',headers={'Host':'evil.invalid'}).text)
            page=self.host.get('/?room=123456');self.assertIn('noindex',page.headers['X-Robots-Tag']);self.assertNotIn(b'og:url',page.data)
        with patch.dict(app.config,{'SOLACE_PUBLIC_URL':''}):
            self.assertEqual(self.host.get('/sitemap.xml').status_code,503)
            self.assertIn('Disallow: /',self.host.get('/robots.txt').text)

    def test_secure_sessions_csrf_validation_signout_and_guest_upgrade(self):
        with self.host.session_transaction() as s:uid=s['uid']
        original_guest_cookie=self.host.get_cookie('session').value
        self.assertEqual(self.host.post('/api/auth/signup',json={}).status_code,403)
        self.assertEqual(self.signup().status_code,200)
        profile=self.host.get('/api/me').json;self.assertFalse(profile['guest']);self.assertEqual(profile['profile']['name'],'Peach')
        cookie=self.host.get_cookie('solace_account');self.assertTrue(cookie.http_only);self.assertEqual(cookie.same_site,'Lax')
        with app.app_context():
            account=db().execute('SELECT * FROM accounts').fetchone();self.assertEqual(account['id'],uid);self.assertNotEqual(account['password'],'a good unique password')
            self.assertNotEqual(db().execute('SELECT token FROM account_sessions').fetchone()[0],cookie.value)
        stolen=app.test_client();stolen.set_cookie('session',original_guest_cookie)
        self.assertTrue(stolen.get('/api/me').json['guest']);self.assertEqual(stolen.get(self.url).status_code,403)
        self.assertEqual(self.host.get(self.url).status_code,200)
        stale=self.host.get_cookie('solace_account').value;stale_session=self.host.get_cookie('session').value
        self.assertEqual(self.post(self.host,'/api/auth/signout',{}).status_code,200)
        other=app.test_client();other.set_cookie('solace_account',stale);other.set_cookie('session',stale_session)
        self.assertEqual(other.get('/api/me/history').status_code,401)

    def test_login_errors_validation_cookie_expiry_and_secure_https(self):
        self.assertEqual(self.signup().status_code,200)
        self.post(self.host,'/api/auth/signout',{})
        self.assertEqual(self.post(self.host,'/api/auth/signin',{'email':'peach@example.test','password':'incorrect long password'}).status_code,401)
        token=self.host.get('/api/me',base_url='https://localhost').json['csrf']
        result=self.host.post('/api/auth/signin',base_url='https://localhost',json={'email':'PEACH@example.test','password':'a good unique password'},headers={'X-CSRF-Token':token})
        self.assertEqual(result.status_code,200);self.assertTrue(self.host.get_cookie('solace_account').secure)
        with app.app_context():db().execute('UPDATE account_sessions SET expires=0');db().commit()
        self.assertTrue(self.host.get('/api/me').json['guest'])
        self.assertEqual(self.post(self.host,'/api/auth/signup',{'email':'bad','password':'x','name':''}).status_code,400)

    def test_profile_and_picture_authorization_validation_replacement_removal(self):
        self.signup();self.assertEqual(self.post(self.host,'/api/me/profile',{'name':'New Peach'}).status_code,200)
        self.assertEqual(self.host.get('/api/me').json['profile']['name'],'New Peach')
        self.assertEqual(self.guest.get('/api/me/avatar').status_code,302)
        self.assertEqual(self.post(self.guest,'/api/me/profile',{'name':'Steal'}).status_code,200)
        token=self.host.get('/api/me').json['csrf'];headers={'X-CSRF-Token':token}
        result=self.host.post('/api/me/avatar',data={'picture':(io.BytesIO(b'<svg onload=alert(1)>'),'x.png')},headers=headers)
        self.assertEqual(result.status_code,400)
        raw=io.BytesIO();Image.new('RGB',(400,300),'pink').save(raw,'JPEG',exif=b'Exif\x00\x00private-metadata')
        for color in ['pink','purple']:
            raw=io.BytesIO();exif=Image.Exif();exif[0x010E]='private upload metadata';Image.new('RGB',(400,300),color).save(raw,'JPEG',exif=exif);raw.seek(0)
            self.assertEqual(self.host.post('/api/me/avatar',data={'picture':(raw,'untrusted.any')},headers=headers).status_code,200)
            response=self.host.get('/api/me/avatar');self.assertEqual(response.mimetype,'image/png');self.assertIn('no-store',response.headers['Cache-Control'])
            with Image.open(io.BytesIO(response.data)) as image:self.assertEqual(image.size,(256,256));self.assertFalse(image.getexif())
        too_large=self.host.post('/api/me/avatar',data={'picture':(io.BytesIO(b'x'*(2*1024*1024+1)),'x.png')},headers=headers)
        self.assertEqual(too_large.status_code,413)
        too_large.request.close();too_large.request.environ['wsgi.input'].close();too_large.close()
        self.assertEqual(self.post(self.host,'/api/me/avatar',method='DELETE').status_code,200)
        self.assertEqual(self.host.get('/api/me').json['profile']['avatar'],'/static/default-avatar.svg')

    def test_real_history_events_reconnect_guest_upgrade_pause_and_deletion(self):
        self.play();start=time.time()
        with patch('launch.watch_time',return_value=start):self.assertEqual(self.watch().status_code,200)
        with patch('launch.watch_time',return_value=start+15):self.watch()
        self.signup()
        data=self.host.get('/api/me/history').json;entry=data['entries'][0]
        self.assertEqual(len(data['entries']),1);self.assertAlmostEqual(entry['seconds'],15,places=1);self.assertNotIn('secret',entry['video']);self.assertEqual(entry['people'],['Guest'])
        with patch('launch.watch_time',return_value=start+20):self.watch(active=False)
        with patch('launch.watch_time',return_value=start+22):self.watch()
        with patch('launch.watch_time',return_value=start+50):self.watch()
        self.assertEqual(self.host.get('/api/me/history').json['entries'][0]['seconds'],15)
        self.signup(self.guest,'berry@example.test','Berry')
        self.assertEqual(self.guest.get('/api/me/history').json['entries'],[])
        self.assertEqual(self.post(self.guest,'/api/me/history/'+str(entry['id']),method='DELETE').status_code,404)
        self.assertEqual(self.post(self.host,'/api/me/history/'+str(entry['id']),method='DELETE').status_code,200)
        self.watch();self.assertEqual(self.host.get('/api/me/history').json['entries'],[])

    def test_daily_activity_timezone_midnight_and_account_deletion_privacy(self):
        self.signup();self.signup(self.guest,'berry@example.test','Berry');self.play()
        start=datetime(2026,11,17,18,29,50,tzinfo=timezone.utc).timestamp()
        with app.app_context():db().execute('UPDATE members SET seen=?',(start,));db().commit()
        with patch('launch.watch_time',return_value=start):self.watch()
        with patch('launch.watch_time',return_value=start+20):self.watch();self.watch(self.guest)
        result=self.host.get('/api/me/history?start=2026-11-17&end=2026-11-18&timezone=Asia/Kolkata').json
        self.assertEqual([round(d['seconds']) for d in result['days']],[10,10]);self.assertEqual([d['sessions'] for d in result['days']],[1,0])
        self.assertEqual(self.host.get('/api/me/history?timezone=bad/zone').status_code,400)
        self.assertEqual(self.post(self.guest,'/api/me/delete-account',{'password':'wrong'}).status_code,403)
        self.assertEqual(self.post(self.guest,'/api/me/delete-account',{'password':'a good unique password'}).status_code,200)
        self.assertEqual(self.host.get('/api/me/history?start=2026-11-17&end=2026-11-18').json['entries'][0]['people'],['Former participant'])
        self.assertEqual(self.post(self.host,'/api/me/history',method='DELETE').status_code,200)
        self.assertEqual(self.post(self.host,'/api/me/delete-account',{'password':'a good unique password'}).status_code,200)
        self.assertTrue(self.host.get('/api/me').json['guest'])

    def test_private_routes_never_cache_and_unrelated_guest_cannot_record(self):
        for path in ['/account','/history','/signin','/api/me','/api/me/history','/love','/api/me/avatar']:
            response=self.host.get(path);self.assertIn('no-store',response.headers['Cache-Control']);self.assertIn('noindex',response.headers['X-Robots-Tag'])
        outsider=app.test_client();self.assertEqual(self.watch(outsider).status_code,403)
        self.assertEqual(self.host.get('/static/media/for-jaanu.mp4').status_code,404)
        self.assertEqual(self.host.get('/static/love.html').status_code,404)
        self.assertEqual(self.host.post(self.url,json={'action':'chat','body':'/iloveyou'}).status_code,409)

    def test_login_rate_limits_are_persistent(self):
        token=self.host.get('/api/me').json['csrf']
        for _ in range(20):self.host.post('/api/auth/signin',json={'email':'bad','password':'x'},headers={'X-CSRF-Token':token})
        self.assertEqual(self.host.post('/api/auth/signin',json={'email':'bad','password':'x'},headers={'X-CSRF-Token':token}).status_code,429)

    def test_concurrent_history_delete_and_heartbeat_cannot_recreate_entry(self):
        from concurrent.futures import ThreadPoolExecutor
        self.signup();self.play();self.watch()
        token=self.host.get('/api/me').json['csrf'];room=self.url.split('/')[-1]
        cookies={name:self.host.get_cookie(name).value for name in ['session','solace_account']}
        def act(index):
            client=app.test_client()
            for name,value in cookies.items():client.set_cookie(name,value)
            if index%2:return client.delete('/api/me/history',headers={'X-CSRF-Token':token}).status_code
            return client.post('/api/me/watch',json={'room':room,'active':True},headers={'X-CSRF-Token':token}).status_code
        with ThreadPoolExecutor(max_workers=4) as pool:self.assertEqual(set(pool.map(act,range(8))),{200})
        self.watch();self.assertEqual(self.host.get('/api/me/history').json['entries'],[])
