import json
import re
import sqlite3
import time
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from werkzeug.security import generate_password_hash
from app import app,db
import test_app as fixtures


class PrivatePanelTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.WatchPartyTests('test_validation_and_access');self.fixture.setUp()
        self.old_hash=app.config.get('OPS_PASSWORD_HASH')
        self.password='isolated-test-password-only'
        app.config['OPS_PASSWORD_HASH']=generate_password_hash(self.password,method='pbkdf2:sha256:1000')
        self.admin=app.test_client()

    def tearDown(self):
        if self.old_hash is None:app.config.pop('OPS_PASSWORD_HASH',None)
        else:app.config['OPS_PASSWORD_HASH']=self.old_hash
        self.fixture.tearDown()

    def login(self):
        page=self.admin.get('/ops/solace')
        token=re.search(r'name="csrf" value="([^"]+)"',page.text).group(1)
        return self.admin.post('/ops/solace',data={'csrf':token,'password':self.password})

    def test_private_data_and_backup_require_auth_and_panel_has_no_public_link(self):
        for route in ['/ops/solace/data','/ops/solace/chat-backup.json']:
            response=self.admin.get(route)
            self.assertEqual(response.status_code,401)
            self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.assertNotIn('/ops/solace',self.fixture.host.get('/').text)
        self.assertEqual(self.login().status_code,303)
        response=self.admin.get('/ops/solace/data')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['retention_days'],30)
        self.assertEqual(response.headers['X-Frame-Options'],'DENY')
        self.assertIn('visitors',response.json)
        self.assertNotIn(self.password,response.text)
        self.assertEqual(self.admin.post('/ops/solace/logout',data={}).status_code,403)
        with self.admin.session_transaction() as session:token=session['ops_csrf']
        self.assertEqual(self.admin.post('/ops/solace/logout',data={'csrf':token}).status_code,303)
        self.assertEqual(self.admin.get('/ops/solace/data').status_code,401)

    def test_local_admin_forms_preserve_origin_for_login_and_logout(self):
        base='http://127.0.0.1:8000'
        page=self.admin.get('/ops/solace',base_url=base)
        self.assertEqual(page.headers['Referrer-Policy'],'same-origin')
        token=re.search(r'name="csrf" value="([^"]+)"',page.text).group(1)
        data={'csrf':token,'password':self.password}
        # Opaque and foreign origins remain rejected even with a valid CSRF token.
        for origin in ['null','http://evil.test:8000','http://127.0.0.1:8001']:
            rejected=self.admin.post('/ops/solace',base_url=base,data=data,headers={'Origin':origin})
            self.assertEqual(rejected.status_code,403)
        response=self.admin.post('/ops/solace',base_url=base,data=data,headers={'Origin':base})
        self.assertEqual(response.status_code,303)
        self.assertEqual(self.admin.get('/ops/solace/data',base_url=base).status_code,200)
        page=self.admin.get('/ops/solace',base_url=base)
        self.assertEqual(page.headers['Referrer-Policy'],'same-origin')
        with self.admin.session_transaction(base_url=base) as session:token=session['ops_csrf']
        response=self.admin.post('/ops/solace/logout',base_url=base,data={'csrf':token},headers={'Origin':base})
        self.assertEqual(response.status_code,303)
        self.assertEqual(self.admin.get('/ops/solace/data',base_url=base).status_code,401)

    def test_login_requires_csrf_limits_attempts_and_expires(self):
        self.assertEqual(self.admin.post('/ops/solace',data={'password':self.password}).status_code,403)
        self.admin.get('/ops/solace')
        with self.admin.session_transaction() as session:token=session['ops_csrf']
        for _ in range(5):
            self.assertEqual(self.admin.post('/ops/solace',data={'csrf':token,'password':'wrong'}).status_code,401)
        self.assertEqual(self.admin.post('/ops/solace',data={'csrf':token,'password':self.password}).status_code,429)
        other=app.test_client();page=other.get('/ops/solace');token=re.search(r'name="csrf" value="([^"]+)"',page.text).group(1)
        self.assertEqual(other.post('/ops/solace',data={'csrf':token,'password':self.password},environ_overrides={'REMOTE_ADDR':'192.0.2.17'}).status_code,303)
        with closing(sqlite3.connect(Path(app.instance_path)/'solace-admin.db')) as connection:
            connection.execute('UPDATE admin_sessions SET expires=?',(time.time()-1,));connection.commit()
        self.assertEqual(other.get('/ops/solace/data').status_code,401)

    def test_logout_cannot_be_undone_by_replaying_inflight_cookies(self):
        self.assertEqual(self.login().status_code,303)
        old_room=self.admin.get_cookie('session').value
        old_ops=self.admin.get_cookie('solace_ops',path='/ops/solace').value
        with self.admin.session_transaction() as saved:csrf=saved['ops_csrf']
        self.assertEqual(self.admin.post('/ops/solace/logout',data={'csrf':csrf}).status_code,303)
        self.admin.set_cookie('session',old_room)
        self.admin.set_cookie('solace_ops',old_ops,path='/ops/solace')
        self.assertEqual(self.admin.get('/ops/solace/data').status_code,401)
        self.assertEqual(self.admin.get('/ops/solace/chat-backup.json').status_code,401)
        # Room responses cannot erase a newly established, path-scoped admin login.
        self.admin.delete_cookie('solace_ops',path='/ops/solace')
        self.assertEqual(self.login().status_code,303)
        self.admin.delete_cookie('session')
        self.assertEqual(self.admin.get('/ops/solace/data').status_code,200)

    def test_backup_survives_room_deletion_and_ip_matches_are_private(self):
        f=self.fixture
        f.host.post(f.url,json={'action':'chat','body':'Private backup test'})
        public=f.guest.get(f.url)
        self.assertNotIn('127.0.0.1',public.text)
        self.assertNotIn('visitor_ips',public.text)
        f.host.post(f.url+'/leave',json={});f.guest.post(f.url+'/leave',json={})
        self.assertEqual(self.login().status_code,303)
        data=self.admin.get('/ops/solace/data').json
        self.assertEqual(data['rooms'],0)
        self.assertGreaterEqual(data['chat_backup_count'],1)
        self.assertTrue(any(match['ip']=='127.0.0.1' and match['devices']>=2 for match in data['ip_matches']))
        self.assertIn('left_room',[event['event'] for event in data['events']])
        response=self.admin.get('/ops/solace/chat-backup.json')
        self.assertEqual(response.status_code,200)
        self.assertIn('attachment',response.headers['Content-Disposition'])
        backup=json.loads(response.data);response.close()
        self.assertEqual(backup['messages'][0]['body'],'Private backup test')

    def test_retention_removes_old_private_records(self):
        self.login();self.admin.get('/ops/solace/data')
        now=time.time();path=Path(app.instance_path)/'solace-admin.db'
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.execute('INSERT INTO chat_archive VALUES(?,?,?,?,?,?,?)',('old-room',999,'old','Old','expired','null',now-31*86400))
        with patch('admin_panel.time.time',return_value=now+3601):
            self.assertEqual(self.login().status_code,303)
            data=self.admin.get('/ops/solace/data').json
            self.assertEqual(data['chat_backup_count'],0)
        with closing(sqlite3.connect(path)) as connection:self.assertEqual(connection.execute('SELECT count(*) FROM chat_archive').fetchone()[0],0)

    def test_panel_is_disabled_until_password_is_configured(self):
        app.config.pop('OPS_PASSWORD_HASH',None)
        with patch.dict('os.environ',{'SOLACE_ADMIN_PASSWORD_HASH':''}):
            self.assertEqual(self.admin.get('/ops/solace').status_code,404)

    def test_private_panel_rejects_plain_http_from_remote_devices(self):
        previous=app.config['TESTING'];app.config['TESTING']=False
        try:
            self.assertEqual(self.admin.get('/ops/solace',environ_overrides={'REMOTE_ADDR':'192.0.2.7'}).status_code,403)
        finally:app.config['TESTING']=previous
        response=self.admin.get('/api/profile',base_url='https://localhost')
        self.assertIn('Secure',response.headers.get('Set-Cookie',''))

    def test_ip_headers_are_ignored_unless_proxy_trust_is_explicit(self):
        f=self.fixture;self.login()
        f.host.get('/api/profile',headers={'X-Real-IP':'192.0.2.99'})
        data=self.admin.get('/ops/solace/data').json
        self.assertFalse(any(v['ip']=='192.0.2.99' for v in data['visitors']))
        previous=app.config.get('OPS_TRUST_X_REAL_IP')
        app.config['OPS_TRUST_X_REAL_IP']=True
        try:
            f.host.get('/api/profile',headers={'X-Real-IP':'192.0.2.99'})
            f.guest.get('/api/profile',headers={'X-Real-IP':'192.0.2.99'})
            data=self.admin.get('/ops/solace/data').json
            self.assertTrue(any(m['ip']=='192.0.2.99' and m['devices']==2 for m in data['ip_matches']))
        finally:
            if previous is None:app.config.pop('OPS_TRUST_X_REAL_IP',None)
            else:app.config['OPS_TRUST_X_REAL_IP']=previous

    def test_owner_setup_copies_existing_history_without_duplicates(self):
        room=self.fixture.url.rsplit('/',1)[1]
        with app.app_context():
            db().execute('INSERT INTO messages(room,name,body,created) VALUES(?,?,?,?)',(room,'Before update','Existing history',time.time()))
            db().commit()
        self.assertEqual(app.extensions['solace_ops']['seed_archive'](),1)
        self.assertEqual(app.extensions['solace_ops']['seed_archive'](),0)
        self.login();response=self.admin.get('/ops/solace/chat-backup.json')
        self.assertEqual(json.loads(response.data)['messages'][0]['body'],'Existing history');response.close()


    def test_diagnostics_are_member_only_private_and_server_assigns_roles(self):
        f=self.fixture;route=f.url+'/diagnostics'
        self.assertEqual(app.test_client().post(route,json={}).status_code,403)
        before=f.host.get(f.url).json['playback_revision']
        payload={'client':'web','platform':'iPhone','playback':'playing','position':12,'drift_ms':21,'keyboard':True,'typing':True,'role':'host','ip':'secret-fake-ip','password':'never-store-this','draft':'never-store-this','width':390,'height':504,'volume':50,'screen':'watch','visibility':'visible','request_rtt_ms':18}
        for client in [f.host,f.guest]:self.assertEqual(client.post(route,json=payload).status_code,202)
        self.assertEqual(f.host.get(f.url).json['playback_revision'],before)
        self.assertEqual(self.admin.get('/ops/solace/data').status_code,401)
        self.login();data=self.admin.get('/ops/solace/data').json
        reports=data['client_diagnostics'];self.assertEqual({r['role'] for r in reports},{'host','peer'})
        self.assertEqual(len(data['diagnostic_history']),2)
        self.assertNotIn('never-store-this',json.dumps(reports));self.assertNotIn('secret-fake-ip',json.dumps(reports))
        for report in reports:self.assertTrue(report['details']['typing']);self.assertEqual(report['details']['width'],390)

    def test_diagnostics_validation_rate_bound_and_logging_failure_do_not_break_room(self):
        f=self.fixture;route=f.url+'/diagnostics'
        self.assertEqual(f.host.post(route,json=[]).status_code,400)
        first=f.host.post(route,json={'client':'web','position':-1,'duration':True,'drift_ms':700000,'width':999999,'playback':'invented','platform':'<script>alert(1)</script>'})
        self.assertTrue(first.json['saved']);self.assertFalse(f.host.post(route,json={'position':20}).json['saved'])
        self.login();details=self.admin.get('/ops/solace/data').json['client_diagnostics'][0]['details']
        for key in ('position','duration','drift_ms','width','playback'):self.assertNotIn(key,details)
        self.assertNotIn('<',details['platform'])
        with closing(sqlite3.connect(Path(app.instance_path)/'solace-admin.db')) as connection:
            connection.execute('DROP TABLE client_diagnostics');connection.commit()
        response=f.host.post(route,json={'client':'web'});self.assertEqual(response.status_code,202);self.assertFalse(response.json['saved'])
        self.assertEqual(f.host.get(f.url).status_code,200)

    def test_diagnostics_retention_purges_snapshots_and_history(self):
        self.fixture.host.post(self.fixture.url+'/diagnostics',json={'client':'web'})
        self.login();now=time.time()
        with closing(sqlite3.connect(Path(app.instance_path)/'solace-admin.db')) as connection:
            connection.execute('UPDATE client_diagnostics SET received=?',(now-31*86400,))
            connection.execute('UPDATE diagnostic_events SET created=?',(now-31*86400,))
            connection.execute('UPDATE admin_sessions SET expires=?',(now+7200,));connection.commit()
        with patch('admin_panel.time.time',return_value=now+3601):data=self.admin.get('/ops/solace/data').json
        self.assertEqual(data['client_diagnostics'],[]);self.assertEqual(data['diagnostic_history'],[])

if __name__=='__main__':unittest.main()
