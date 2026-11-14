import json
import tempfile
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import test_app
from app import app,db
from tools.storage import backup,restore,verify

class ReliabilityTests(unittest.TestCase):
    setUp=test_app.WatchPartyTests.setUp
    tearDown=test_app.WatchPartyTests.tearDown

    def test_retry_chat_add_move_and_create_are_idempotent(self):
        for action in [{'action':'chat','body':'One delivery'},{'action':'add','url':'aqz-KE-bpKQ'}]:
            headers={'X-Request-ID':'retry-'+action['action']+'-0001'}
            for _ in range(2):self.assertEqual(self.host.post(self.url,json=action,headers=headers).status_code,200)
        state=self.host.get(self.url).json
        self.assertEqual(len(state['messages']),1);self.assertEqual(len(state['queue']),1)
        conflict=self.host.post(self.url,json={'action':'chat','body':'Different'},headers={'X-Request-ID':'retry-chat-0001'})
        self.assertEqual(conflict.status_code,409)
        one=self.host.post('/api/rooms',json={},headers={'X-Request-ID':'create-retry-0001'})
        two=self.host.post('/api/rooms',json={},headers={'X-Request-ID':'create-retry-0001'})
        self.assertEqual(one.json,two.json)

    def test_playback_revision_survives_same_timestamp_and_rejects_old_observations(self):
        state=self.host.get(self.url).json;revision=state['playback_revision']
        with patch('app.time.time',return_value=state['updated']):
            ack=self.guest.post(self.url,json={'action':'playback','position':42,'playing':True,'expected_revision':revision,'compact':True},headers={'X-Request-ID':'play-command-0001'}).json
            self.assertEqual(ack['playback_revision'],revision+1)
            old=self.host.post(self.url,json={'action':'playback','position':0,'playing':False,'source':'observation','expected_revision':revision})
            self.assertEqual(old.status_code,409)
            replay=self.guest.post(self.url,json={'action':'playback','position':42,'playing':True,'expected_revision':revision,'compact':True},headers={'X-Request-ID':'play-command-0001'})
            self.assertEqual(replay.json,ack)
        self.assertTrue(self.host.get(self.url).json['playing'])

    def test_concurrent_retries_have_one_effect(self):
        cookie=self.host.get_cookie('session').value
        def add(_):
            client=app.test_client();client.set_cookie('session',cookie)
            return client.post(self.url,json={'action':'add','url':'aqz-KE-bpKQ'},headers={'X-Request-ID':'parallel-add-001'}).status_code
        with ThreadPoolExecutor(max_workers=4) as pool:self.assertEqual(list(pool.map(add,range(4))),[200]*4)
        self.assertEqual(len(self.host.get(self.url).json['queue']),1)

    def test_snapshot_and_telemetry_require_membership(self):
        stranger=app.test_client();self.assertEqual(stranger.get(self.url).status_code,403)
        self.assertEqual(stranger.post(self.url+'/telemetry',json={'name':'reconnect'}).status_code,403)
        self.assertEqual(self.guest.post(self.url,json={'action':'playback','position':4,'playing':True,'source':'observation','expected_revision':0}).status_code,403)
        self.assertEqual(self.host.post(self.url+'/telemetry',json={'name':'playback_drift_ms','value':125}).status_code,200)
        self.assertEqual(self.host.post(self.url+'/telemetry',json={'name':'message_body','value':'private'}).status_code,400)

    def test_thirty_minute_recovery_grace_and_explicit_last_leave(self):
        import time
        start=time.time()
        with patch('app.time.time',return_value=start+900):
            self.host.get('/api/health')
            with app.app_context():self.assertEqual(db().execute('SELECT count(*) FROM rooms').fetchone()[0],1)
            self.host.post(self.url+'/leave',json={});self.assertTrue(self.guest.post(self.url+'/leave',json={}).json['room_deleted'])

    def test_backup_restore_preserves_chat_queue_revision_and_names(self):
        self.host.post(self.url,json={'action':'chat','body':'Restore me'})
        self.guest.post(self.url,json={'action':'add','url':'aqz-KE-bpKQ'})
        self.host.post(self.url,json={'action':'playback','position':37,'playing':False})
        with tempfile.TemporaryDirectory() as temporary:
            saved=Path(temporary)/'backup';target=Path(temporary)/'restored'
            backup(app.instance_path,saved);verify(saved);restore(saved,target)
            original=app.instance_path;app.instance_path=str(target)
            try:
                snapshot=self.host.get(self.url).json
                self.assertEqual(snapshot['messages'][0]['body'],'Restore me');self.assertEqual(len(snapshot['queue']),1);self.assertEqual(snapshot['position'],37);self.assertEqual(snapshot['playback_revision'],1)
                self.assertEqual(self.guest.get('/api/profile').json['name'],'Guest')
            finally:app.instance_path=original
            with self.assertRaises(ValueError):restore(saved,target)
            (saved/'afterglow.db').write_bytes(b'broken')
            with self.assertRaises(ValueError):verify(saved)

    def test_restored_generation_resets_an_old_chat_cursor(self):
        self.host.post(self.url,json={'action':'chat','body':'From restored history'})
        response=self.guest.get(self.url+'?after=999&generation=previous-backup')
        self.assertFalse(response.json['messages_delta']);self.assertEqual(response.json['messages'][-1]['body'],'From restored history')

    def test_user_command_rebases_over_observations_but_not_other_commands(self):
        state=self.host.get(self.url).json
        observed=self.host.post(self.url,json={'action':'playback','position':1,'playing':True,'source':'observation','expected_revision':state['playback_revision']})
        self.assertEqual(observed.status_code,200)
        command=self.guest.post(self.url,json={'action':'playback','position':1,'playing':False,'expected_revision':state['playback_revision']})
        self.assertEqual(command.status_code,200)
        stale=self.host.post(self.url,json={'action':'playback','position':0,'playing':True,'expected_revision':state['playback_revision']})
        self.assertEqual(stale.status_code,409)
