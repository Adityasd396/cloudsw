import io,json,re,tempfile,unittest,os
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from werkzeug.security import generate_password_hash
import test_app
import test_launch as launch_tests
from app import app,db

class LaunchHardeningTests(unittest.TestCase):
    setUp=test_app.WatchPartyTests.setUp
    tearDown=test_app.WatchPartyTests.tearDown
    post=launch_tests.PublicLaunchTests.post
    signup=launch_tests.PublicLaunchTests.signup
    watch=launch_tests.PublicLaunchTests.watch
    play=launch_tests.PublicLaunchTests.play

    def admin(self):
        app.config['OPS_PASSWORD_HASH']=generate_password_hash('isolated-admin-only')
        self.addCleanup(app.config.pop,'OPS_PASSWORD_HASH',None)
        client=app.test_client();page=client.get('/ops/solace');token=re.search(r'name="csrf" value="([^"]+)"',page.text).group(1)
        client.post('/ops/solace',data={'csrf':token,'password':'isolated-admin-only'});page=client.get('/ops/solace');token=re.search(r'name="csrf" value="([^"]+)"',page.text).group(1)
        return client,{'X-CSRF-Token':token}

    def test_quota_default_override_validation_and_no_stream_interruption(self):
        self.signup();self.play();self.watch();admin,headers=self.admin()
        self.assertEqual(self.guest.get('/ops/solace/storage').status_code,401)
        self.assertEqual(admin.post('/ops/solace/storage',json={'limit_mib':2}).status_code,403)
        self.assertEqual(admin.post('/ops/solace/storage',json={'limit_mib':0},headers=headers).status_code,400)
        self.assertEqual(admin.post('/ops/solace/storage',json={'limit_mib':2},headers=headers).json['default_mib'],2)
        user=next(row for row in admin.get('/ops/solace/storage').json['users'] if row['registered'])
        self.assertEqual(admin.post('/ops/solace/storage',json={'user':user['user'],'limit_mib':1},headers=headers).status_code,200)
        self.assertEqual(self.host.get('/api/me').json['storage']['limit_bytes'],1048576)
        with self.host.session_transaction() as s:owner=s['uid']
        with app.app_context():db().execute('UPDATE watch_history SET title=? WHERE owner=?',('x'*1048576,owner));db().commit()
        before=self.host.get(self.url).json
        sample=self.watch();self.assertEqual(sample.status_code,202);self.assertTrue(sample.json['history_paused'])
        image=io.BytesIO();Image.new('RGB',(30,30),'red').save(image,'PNG');image.seek(0)
        token=self.host.get('/api/me').json['csrf']
        self.assertEqual(self.host.post('/api/me/avatar',data={'picture':(image,'a.png')},headers={'X-CSRF-Token':token}).status_code,413)
        after=self.host.get(self.url).json
        for key in ['video','playback_id','playing','playback_revision']:self.assertEqual(before[key],after[key])
        self.post(self.host,'/api/me/history',method='DELETE');self.assertFalse(self.host.get('/api/me').json['storage']['full'])
        self.assertEqual(admin.post('/ops/solace/storage',json={'user':user['user'],'limit_mib':None},headers=headers).status_code,200)
        self.assertEqual(self.host.get('/api/me').json['storage']['limit_bytes'],2097152)

    def test_password_recovery_verification_one_use_expiry_and_revocation(self):
        sent=[]
        class Mail:
            def __init__(self,*a,**kw):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def starttls(self,**kw):pass
            def login(self,*args):pass
            def send_message(self,message):sent.append(message)
        settings={'SOLACE_PUBLIC_URL':'https://watch.example.test','SOLACE_SMTP_HOST':'smtp.example.test','SOLACE_MAIL_FROM':'hello@example.test'}
        with patch.dict(app.config,settings),patch('account_mail.smtplib.SMTP',Mail):
            self.assertEqual(self.signup().status_code,200);self.assertEqual(len(sent),1)
            token=re.search(r'#token=([\w-]+)',sent[-1].get_content()).group(1)
            with app.app_context():self.assertNotEqual(db().execute('SELECT token FROM account_tokens').fetchone()[0],token)
            self.assertEqual(self.post(self.guest,'/api/auth/verify',{'token':token}).status_code,200)
            self.assertTrue(self.host.get('/api/me').json['profile']['verified'])
            self.assertEqual(self.post(self.guest,'/api/auth/verify',{'token':token}).status_code,400)
            unknown=self.post(self.guest,'/api/auth/recovery',{'email':'missing@example.test'})
            known=self.post(self.guest,'/api/auth/recovery',{'email':'peach@example.test'})
            self.assertEqual(known.json,unknown.json);token=re.search(r'#token=([\w-]+)',sent[-1].get_content()).group(1)
            self.assertEqual(self.post(self.guest,'/api/auth/reset',{'token':token,'password':'new strong unique password'}).status_code,200)
            self.assertTrue(self.host.get('/api/me').json['guest'])
            self.assertEqual(self.post(self.guest,'/api/auth/reset',{'token':token,'password':'new strong unique password'}).status_code,400)
            self.post(self.host,'/api/auth/recovery',{'email':'peach@example.test'});token=re.search(r'#token=([\w-]+)',sent[-1].get_content()).group(1)
            with app.app_context():db().execute('UPDATE account_tokens SET expires=0');db().commit()
            self.assertEqual(self.post(self.guest,'/api/auth/reset',{'token':token,'password':'new strong unique password'}).status_code,400)

    def test_readiness_identifiers_and_csp_and_unconfigured_mail(self):
        self.assertEqual(self.host.get('/api/ready').status_code,200)
        result=self.host.get('/',headers={'X-Request-ID':'not-a-valid-private-token'})
        self.assertRegex(result.headers['X-Request-ID'],r'^[0-9a-f]{32}$');self.assertIn("script-src 'self'",result.headers['Content-Security-Policy'])
        app.extensions['solace_draining']=True
        try:self.assertEqual(self.host.get('/api/ready').status_code,503);self.assertEqual(self.host.get(self.url).headers['Retry-After'],'2')
        finally:app.extensions['solace_draining']=False
        with patch.dict(app.config,{'SOLACE_ENV':'production','SOLACE_PUBLIC_URL':'','SOLACE_CONTACT_EMAIL':''}):self.assertEqual(self.host.get('/api/ready').status_code,503)
        with patch.dict(app.config,{'SOLACE_SMTP_HOST':''}):self.assertEqual(self.post(self.host,'/api/auth/recovery',{'email':'p@example.test'}).status_code,503)

    def test_player_exit_preserves_an_unrelated_ludo_match(self):
        third=app.test_client();fourth=app.test_client()
        for client,name in [(third,'C'),(fourth,'D')]:client.post(self.url,json={'action':'join','name':name});client.post(self.url+'/ludo',json={'action':'join'})
        state=third.get(self.url+'/ludo').json;third.post(self.url+'/ludo',json={'action':'start','revision':state['revision']})
        self.host.post(self.url+'/game',json={'action':'join'});self.guest.post(self.url+'/game',json={'action':'join'})
        before=third.get(self.url+'/ludo').json;self.host.post(self.url+'/leave',json={});after=third.get(self.url+'/ludo').json
        for key in ['started','players','pawns','revision']:self.assertEqual(before[key],after[key])
        self.assertEqual(self.guest.get(self.url+'/game').json['players'],{})

    def test_production_http_redirects_to_configured_https_and_rejects_credentials(self):
        with patch.dict(os.environ,{'SOLACE_ENV':'production'}),patch.dict(app.config,{'SOLACE_PUBLIC_URL':'https://watch.example.test'}):
            response=self.host.get('/',headers={'Host':'untrusted.invalid'})
            self.assertEqual(response.status_code,308);self.assertEqual(response.headers['Location'],'https://watch.example.test/')
            self.assertEqual(self.host.post('/api/auth/signin',json={'password':'never-process-on-http'}).status_code,426)
