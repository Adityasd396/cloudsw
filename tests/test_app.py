import tempfile
import unittest
from app import app, db, video_id


class WatchPartyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_instance = app.instance_path
        app.instance_path = self.temp.name
        app.config['TESTING'] = True
        with app.app_context():
            db().executescript('''
            CREATE TABLE presence(room TEXT,id TEXT,active INTEGER,PRIMARY KEY(room,id));
            CREATE TABLE profiles(id TEXT PRIMARY KEY,name TEXT,updated REAL);
            CREATE TABLE typing(room TEXT,id TEXT,updated REAL,PRIMARY KEY(room,id));
            CREATE TABLE rooms(id TEXT PRIMARY KEY,name TEXT,host TEXT,video TEXT,playing INTEGER DEFAULT 0,position REAL DEFAULT 0,updated REAL);
            CREATE TABLE members(room TEXT,id TEXT,name TEXT,seen REAL,PRIMARY KEY(room,id));
            CREATE TABLE messages(id INTEGER PRIMARY KEY AUTOINCREMENT,room TEXT,name TEXT,body TEXT,created REAL);
            CREATE TABLE queue(id INTEGER PRIMARY KEY AUTOINCREMENT,room TEXT,video TEXT,title TEXT,added_by TEXT,sort_order INTEGER NOT NULL DEFAULT 0);
            ''')
        self.host = app.test_client()
        self.guest = app.test_client()
        room = self.host.post('/api/rooms', json={'name': 'Test room'}).json['id']
        self.url = '/api/rooms/' + room
        self.host.post(self.url, json={'action': 'join', 'name': 'Host'})
        self.guest.post(self.url, json={'action': 'join', 'name': 'Guest'})

    def tearDown(self):
        app.instance_path = self.original_instance
        self.temp.cleanup()

    def test_shared_chat_queue_and_host_playback(self):
        result = self.guest.post(self.url, json={'action': 'chat', 'body': '<script>hello</script>'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.host.get(self.url).json['messages'][0]['body'], '<script>hello</script>')
        result = self.guest.post(self.url, json={'action': 'add', 'url': 'https://youtu.be/aqz-KE-bpKQ', 'title': 'Big Buck Bunny'})
        item = result.json['queue'][0]
        self.assertEqual(self.guest.post(self.url, json={'action': 'select', 'id': item['id']}).status_code, 200)
        self.host.post(self.url, json={'action': 'next'})
        self.host.post(self.url, json={'action': 'playback', 'position': 42, 'playing': True})
        state = self.guest.get(self.url).json
        self.assertEqual(state['video'], 'aqz-KE-bpKQ')
        self.assertEqual(state['position'], 42)
        self.assertEqual(state['playing'], 1)
        self.assertFalse(state['is_host'])
        self.assertEqual(len(state['members']), 2)
        self.assertEqual(state['queue'], [])

    def test_validation_and_access(self):
        self.assertEqual(self.guest.post(self.url, json={'action': 'playback', 'position': 99}).status_code, 200)
        self.assertEqual(self.host.post(self.url, json={'action': 'playback', 'position': 'bad'}).status_code, 400)
        self.assertEqual(self.guest.post(self.url, json={'action': 'add', 'url': 'https://evil.com/watch?v=aqz-KE-bpKQ'}).status_code, 400)
        self.assertEqual(app.test_client().post(self.url, json={'action': 'chat', 'body': 'no'}).status_code, 403)
        self.assertEqual(self.host.post(self.url, json={'action': 'chat', 'body': 'x'}, headers={'Origin': 'https://evil.com'}).status_code, 403)
        self.assertEqual(self.host.get('/api/rooms/missing').status_code, 404)

    def test_youtube_urls(self):
        for url in ['aqz-KE-bpKQ', 'https://www.youtube.com/watch?v=aqz-KE-bpKQ&t=10', 'https://youtube.com/shorts/aqz-KE-bpKQ', 'https://youtu.be/aqz-KE-bpKQ']:
            self.assertEqual(video_id(url), 'aqz-KE-bpKQ')
        self.assertIsNone(video_id('javascript:alert(1)'))

    def test_browse_and_watch(self):
        from unittest.mock import patch
        with patch.dict('os.environ', {'YOUTUBE_API_KEY': ''}):
            result = self.host.get('/api/videos?category=Films').json
            self.assertGreater(len(result['items']), 0)
            self.assertTrue(all(item['category'] == 'Films' for item in result['items']))
            self.assertFalse(result['search_enabled'])
            missing=self.host.get('/api/videos?q=nonexistent')
            self.assertEqual(missing.status_code,503)
            self.assertEqual(missing.json['code'],'search_not_configured')
        self.assertEqual(self.guest.post(self.url, json={'action': 'watch', 'url': 'aqz-KE-bpKQ'}).status_code, 200)
        result = self.host.post(self.url, json={'action': 'watch', 'url': 'aqz-KE-bpKQ'})
        self.assertEqual(result.json['video'], 'aqz-KE-bpKQ')
        self.assertEqual(result.json['playing'], 1)
        self.assertEqual(self.guest.get(self.url).json['video'], 'aqz-KE-bpKQ')

    def test_key_setup_and_search(self):
        from unittest.mock import patch
        from pathlib import Path
        result = {'items':[{'id':{'videoId':'aqz-KE-bpKQ'},'snippet':{'title':'A &amp; B','channelTitle':'Example'}}], 'nextPageToken':'next-token'}
        with patch('app.youtube_request', return_value=result) as youtube:
            key = 'test-key-for-configuration-12345'
            with patch.dict('os.environ', {}, clear=False):
                configured = self.host.post('/api/settings/youtube', json={'key':key})
                self.assertEqual(configured.status_code,200)
                self.assertEqual((Path(app.instance_path)/'youtube.key').read_text(), key)
                self.assertNotIn(key,configured.text)
                self.assertTrue(self.host.get('/api/settings').json['search_enabled'])
                found = self.host.get('/api/videos?q=unique-test-query').json
                self.assertEqual(found['source'],'youtube')
                self.assertEqual(found['items'][0]['title'],'A & B')
                self.assertEqual(found['next_page'],'next-token')
                self.assertNotIn(key,str(found))
                self.assertEqual(youtube.call_args.args[0]['videoEmbeddable'],'true')
        self.assertEqual(self.host.post('/api/settings/youtube',json={'key':'short'}).status_code,409)
        self.assertFalse(self.host.get('/api/settings').json['can_configure'])
        self.assertEqual(self.host.post('/api/settings/youtube',json={'key':key},environ_overrides={'REMOTE_ADDR':'192.168.0.2'}).status_code,403)

    def test_google_errors_are_actionable_and_hide_key(self):
        from app import YouTubeError
        from unittest.mock import patch
        with patch('app.youtube_request',side_effect=YouTubeError('Enable YouTube Data API v3.','api_disabled')):
            response=self.host.post('/api/settings/youtube',json={'key':'test-key-for-configuration-12345'})
            self.assertEqual(response.status_code,400)
            self.assertEqual(response.json['code'],'api_disabled')
            self.assertNotIn('test-key',response.text)

    def test_host_handover_and_recovery(self):
        state=self.host.get(self.url).json
        guest=next(member for member in state['members'] if not member['you'])
        response=self.host.post(self.url,json={'action':'transfer_host','member_id':guest['member_id']})
        self.assertFalse(response.json['is_host'])
        self.assertTrue(self.guest.get(self.url).json['is_host'])
        self.assertEqual(self.host.post(self.url,json={'action':'claim_host'}).status_code,409)
        with app.app_context():
            db().execute('UPDATE members SET seen=0 WHERE name=?',('Guest',))
            db().commit()
        self.assertTrue(self.host.post(self.url,json={'action':'claim_host'}).json['is_host'])

    def test_malformed_requests_and_nonfinite_positions(self):
        self.assertEqual(self.host.post(self.url,json=['not an object']).status_code,400)
        self.assertEqual(self.host.post(self.url,json={'action':'playback','position':'NaN'}).status_code,400)
        self.assertEqual(self.host.post(self.url,json={'action':'playback','position':'Infinity'}).status_code,400)
        self.assertIsNone(video_id('https://[invalid'))
        self.assertEqual(self.host.post(self.url,json={'action':'remove','id':99999}).status_code,404)

    def test_playlist_reordering_persists_and_changes_next(self):
        for video,title in [('aqz-KE-bpKQ','First'),('eRsGyueVLvQ','Second'),('R6MlUcmOul8','Third')]:
            response=self.host.post(self.url,json={'action':'add','url':video,'title':title})
        original=response.json['queue']
        self.assertTrue(self.guest.get(self.url).json['can_control'])
        moved=self.host.post(self.url,json={'action':'move','id':original[2]['id'],'direction':'up'})
        self.assertEqual([item['title'] for item in moved.json['queue']],['First','Third','Second'])
        self.host.post(self.url,json={'action':'move','id':original[2]['id'],'direction':'up'})
        self.assertEqual([item['title'] for item in self.guest.get(self.url).json['queue']],['Third','First','Second'])
        self.host.post(self.url,json={'action':'move','id':original[2]['id'],'direction':'up'})
        state=self.host.post(self.url,json={'action':'next'}).json
        self.assertEqual(state['video'],'R6MlUcmOul8')
        self.assertEqual([item['id'] for item in state['queue']],[original[0]['id'],original[1]['id']])
        self.assertEqual(self.host.post(self.url,json={'action':'move','id':original[0]['id'],'direction':'sideways'}).status_code,400)

    def test_simple_codes_profiles_and_typing(self):
        import re
        created=self.host.post('/api/rooms',json={'name':'Friends'}).json
        self.assertRegex(created['id'],r'^\d{6}$')
        self.assertEqual(self.host.get('/api/profile').json['name'],'Host')
        self.guest.post(self.url,json={'action':'typing','active':True})
        self.assertEqual(self.host.get(self.url).json['typing'],['Guest'])
        self.assertEqual(self.guest.get(self.url).json['typing'],[])
        self.guest.post(self.url,json={'action':'chat','body':'hello'})
        self.assertEqual(self.host.get(self.url).json['typing'],[])
        self.guest.post(self.url,json={'action':'typing','active':True})
        with app.app_context():
            db().execute('UPDATE typing SET updated=0')
            db().commit()
        self.assertEqual(self.host.get(self.url).json['typing'],[])
        with app.app_context():
            self.assertEqual(db().execute('SELECT name FROM profiles WHERE name=?',('Guest',)).fetchone()['name'],'Guest')
            self.assertEqual(db().execute('SELECT body FROM messages WHERE room=?',(self.url.rsplit('/',1)[1],)).fetchone()['body'],'hello')

    def test_compact_playback_update_excludes_chat_history(self):
        response=self.host.post(self.url,json={'action':'playback','position':25,'playing':True,'compact':True})
        self.assertEqual(response.json,{'ok':True})
        self.assertEqual(self.guest.get(self.url).json['position'],25)
        self.assertEqual(self.guest.post(self.url,json={'action':'playback','position':30,'compact':True}).status_code,200)

    def test_presence_inactive_resume_and_timeout(self):
        self.guest.post(self.url+'/presence',json={'active':False})
        self.guest.get(self.url)  # An in-flight poll cannot undo explicit inactivity.
        snapshot=self.host.get(self.url).json
        self.assertEqual(len(snapshot['members']),1)
        self.assertFalse(next(p for p in snapshot['participants'] if p['name']=='Guest')['active'])
        self.guest.post(self.url+'/presence',json={'active':True})
        self.assertEqual(len(self.host.get(self.url).json['members']),2)
        with app.app_context():
            db().execute('UPDATE members SET seen=0 WHERE name=?',('Guest',))
            db().commit()
        self.assertEqual(len(self.host.get(self.url).json['members']),1)
        self.assertEqual(app.test_client().post(self.url+'/presence',json={'active':False}).status_code,403)

    def test_every_participant_controls_and_stale_clock_cannot_override(self):
        previous=self.host.get(self.url).json['updated']
        paused=self.guest.post(self.url,json={'action':'playback','position':80,'playing':False})
        self.assertEqual(paused.status_code,200)
        self.assertFalse(paused.json['playing'])
        stale=self.host.post(self.url,json={'action':'playback','position':10,'playing':True,'expected_updated':previous,'compact':True})
        self.assertEqual(stale.status_code,409)
        state=self.host.get(self.url).json
        self.assertEqual(state['position'],80)
        self.assertFalse(state['playing'])
        item=self.guest.post(self.url,json={'action':'add','url':'eRsGyueVLvQ'}).json['queue'][0]
        self.assertEqual(self.guest.post(self.url,json={'action':'move','id':item['id'],'direction':'up'}).status_code,200)
        self.assertEqual(self.guest.post(self.url,json={'action':'remove','id':item['id']}).status_code,200)

    def test_presence_green_yellow_red_thresholds(self):
        import time
        from unittest.mock import patch
        start=time.time()
        with app.app_context():
            db().execute('UPDATE members SET seen=? WHERE name=?',(start,'Guest'))
            db().commit()
        for delay,status in [(1,'active'),(4,'reconnecting'),(9,'inactive')]:
            with patch('app.time.time',return_value=start+delay):
                people=self.host.get(self.url).json['participants']
                self.assertEqual(next(p for p in people if p['name']=='Guest')['status'],status)

    def test_simulated_three_hour_session_retains_controls_and_bounded_chat(self):
        import time
        from unittest.mock import patch
        start=time.time()
        for minute in range(181):
            with patch('app.time.time',return_value=start+minute*60):
                result=self.host.post(self.url,json={'action':'playback','position':minute*60,'playing':True,'compact':True})
                self.assertEqual(result.status_code,200)
                self.assertEqual(self.host.post(self.url,json={'action':'chat','body':f'Minute {minute}'}).status_code,200)
        with patch('app.time.time',return_value=start+10800):
            snapshot=self.host.get(self.url).json
            self.assertEqual(snapshot['position'],10800)
            self.assertEqual(len(snapshot['messages']),100)
            self.assertEqual(snapshot['messages'][-1]['body'],'Minute 180')
            self.assertEqual(self.guest.post(self.url,json={'action':'playback','position':10800,'playing':False}).status_code,200)
            with app.app_context():
                self.assertEqual(db().execute('SELECT count(*) FROM messages WHERE room=?',(snapshot['id'],)).fetchone()[0],181)


if __name__ == '__main__':
    unittest.main()
