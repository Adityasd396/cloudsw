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
            CREATE TABLE room_games(room TEXT PRIMARY KEY,state TEXT);
            CREATE TABLE presence(room TEXT,id TEXT,active INTEGER,PRIMARY KEY(room,id));
            CREATE TABLE participant_ads(room TEXT,id TEXT,active INTEGER,updated REAL,started REAL,PRIMARY KEY(room,id));
            CREATE TABLE room_ads(room TEXT PRIMARY KEY,active INTEGER,updated REAL);
            CREATE TABLE profiles(id TEXT PRIMARY KEY,name TEXT,updated REAL);
            CREATE TABLE typing(room TEXT,id TEXT,updated REAL,PRIMARY KEY(room,id));
            CREATE TABLE rooms(id TEXT PRIMARY KEY,name TEXT,host TEXT,video TEXT,playing INTEGER DEFAULT 0,position REAL DEFAULT 0,updated REAL,playback_id TEXT NOT NULL DEFAULT 'initial');
            CREATE TABLE members(room TEXT,id TEXT,name TEXT,seen REAL,PRIMARY KEY(room,id));
            CREATE TABLE messages(id INTEGER PRIMARY KEY AUTOINCREMENT,room TEXT,name TEXT,body TEXT,created REAL,sender TEXT,reply_to INTEGER);
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
        self.assertTrue(self.guest.get(self.url).json['can_control'])
        self.host.post(self.url, json={'action': 'next'})
        self.host.post(self.url, json={'action': 'playback', 'position': 42, 'playing': True})
        state = self.guest.get(self.url).json
        self.assertEqual(state['video'], 'aqz-KE-bpKQ')
        self.assertEqual(state['position'], 42)
        self.assertEqual(state['playing'], 1)
        self.assertFalse(state['is_host'])
        self.assertEqual(len(state['members']), 2)
        self.assertEqual(state['queue'], [])

    def test_shared_queue_end_is_atomic_even_for_repeated_videos(self):
        import concurrent.futures
        for title in ['A','B','C']:
            self.host.post(self.url,json={'action':'add','url':'aqz-KE-bpKQ','title':title})
        before=self.host.get(self.url).json
        cookies=[c.get_cookie('session').value for c in (self.host,self.guest)]
        def finish(cookie):
            client=app.test_client();client.set_cookie('session',cookie)
            return client.post(self.url,json={'action':'next','expected_playback_id':before['playback_id']}).status_code
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(finish,cookies)),[200,409])
        after=self.guest.get(self.url).json
        self.assertEqual([item['title'] for item in after['queue']],['B','C'])
        self.assertNotEqual(before['playback_id'],after['playback_id'])
        self.assertTrue(after['playing'])
        self.assertEqual(self.guest.post(self.url,json={'action':'playback','position':90,'playing':False}).status_code,200)
        self.assertEqual(self.host.get(self.url).json['position'],90)

    def test_chat_identity_does_not_confuse_matching_names(self):
        self.host.post(self.url,json={'action':'join','name':'Same'})
        self.guest.post(self.url,json={'action':'join','name':'Same'})
        self.assertEqual(self.host.post(self.url,json={'action':'chat','body':'mine'}).status_code,200)
        self.assertEqual(self.guest.post(self.url,json={'action':'chat','body':'theirs'}).status_code,200)
        host=self.host.get(self.url).json['messages'];guest=self.guest.get(self.url).json['messages']
        self.assertEqual([m['you'] for m in host],[True,False])
        self.assertEqual([m['you'] for m in guest],[False,True])
        self.assertNotEqual(host[0]['sender_id'],host[1]['sender_id'])
        self.assertNotIn('sender',host[0])

    def test_reply_is_shared_and_cannot_quote_another_room(self):
        sent=self.host.post(self.url,json={'action':'chat','body':'A message to reply to'}).json['messages'][-1]
        response=self.guest.post(self.url,json={'action':'chat','body':'My reply','reply_to':sent['id']})
        self.assertEqual(response.status_code,200)
        quoted=self.host.get(self.url).json['messages'][-1]
        self.assertEqual(quoted['reply'],{'id':sent['id'],'name':'Host','body':'A message to reply to'})
        self.assertTrue(self.host.get(self.url).json['messages'][0]['is_host'])
        other=self.host.post('/api/rooms',json={}).json['id']
        endpoint='/api/rooms/'+other
        self.host.post(endpoint,json={'action':'join','name':'Host'})
        self.assertEqual(self.host.post(endpoint,json={'action':'chat','body':'Bad quote','reply_to':sent['id']}).status_code,400)

    def test_any_participant_reports_ads_with_stable_notification_identity(self):
        response=self.guest.post(self.url,json={'action':'ad_status','active':True})
        self.assertEqual(response.status_code,200)
        alert=self.host.get(self.url).json['ad_alerts'][0]
        self.assertEqual(alert['name'],'Guest');self.assertFalse(alert['you'])
        self.assertTrue(self.guest.get(self.url).json['ad_alerts'][0]['you'])
        self.guest.post(self.url,json={'action':'ad_status','active':True})
        self.assertEqual(self.host.get(self.url).json['ad_alerts'][0]['started'],alert['started'])
        self.guest.post(self.url,json={'action':'ad_status','active':False})
        self.assertEqual(self.host.get(self.url).json['ad_alerts'],[])
        self.guest.post(self.url,json={'action':'ad_status','active':True})
        self.assertGreater(self.host.get(self.url).json['ad_alerts'][0]['started'],alert['started'])

    def test_game_two_players_turns_winner_and_room_cleanup(self):
        endpoint=self.url+'/game'
        self.assertEqual(app.test_client().get(endpoint).status_code,403)
        self.assertEqual(self.host.post(endpoint,json={'action':'join'}).json['you'],'X')
        game=self.guest.post(endpoint,json={'action':'join'}).json
        self.assertEqual(game['you'],'O')
        spectator=app.test_client();spectator.post(self.url,json={'action':'join','name':'Spectator'})
        self.assertEqual(spectator.post(endpoint,json={'action':'join'}).status_code,409)
        self.assertEqual(self.guest.post(endpoint,json={'action':'move','cell':4,'revision':game['revision']}).status_code,409)
        self.assertEqual(self.host.post(endpoint,json={'action':'move','cell':True,'revision':game['revision']}).status_code,400)
        for client,cell in [(self.host,0),(self.guest,3),(self.host,1),(self.guest,4),(self.host,2)]:
            response=client.post(endpoint,json={'action':'move','cell':cell,'revision':game['revision']})
            self.assertEqual(response.status_code,200);game=response.json
        self.assertEqual(game['winner'],'X')
        self.assertEqual(self.guest.get(endpoint).json['board'],game['board'])
        stale=self.host.post(endpoint,json={'action':'reset','revision':0})
        self.assertEqual(stale.status_code,409)
        game=self.host.post(endpoint,json={'action':'reset','revision':game['revision']}).json
        self.assertEqual(game['board'],['']*9)
        self.assertIsNone(game['winner'])
        for client in (self.host,self.guest,spectator):client.post(self.url+'/leave',json={})
        self.assertEqual(self.host.get(endpoint).status_code,404)
        with app.app_context():self.assertEqual(db().execute('SELECT count(*) FROM room_games').fetchone()[0],0)

    def test_game_stale_duplicate_move_is_rejected(self):
        endpoint=self.url+'/game'
        self.host.post(endpoint,json={'action':'join'})
        game=self.guest.post(endpoint,json={'action':'join'}).json
        move={'action':'move','cell':0,'revision':game['revision']}
        self.assertEqual(self.host.post(endpoint,json=move).status_code,200)
        self.assertEqual(self.host.post(endpoint,json=move).status_code,409)
        self.assertEqual(self.host.get(endpoint).json['board'],['X','','','','','','','',''])

    def test_love_command_is_shared_and_video_supports_phone_seeking(self):
        sent=self.host.post(self.url,json={'action':'chat','body':'/iloveyou'})
        self.assertEqual(sent.status_code,200)
        messages=self.guest.get(self.url).json['messages']
        self.assertEqual(messages[-1]['body'],'/iloveyou')
        page=self.guest.get('/static/love.html')
        self.assertEqual(page.status_code,200)
        self.assertIn(b'You are my solace.',page.data)
        self.assertIn(b'/static/media/for-jaanu.mp4',page.data)
        page.close()
        response=self.guest.get('/static/media/for-jaanu.mp4',headers={'Range':'bytes=0-1023'})
        try:
            self.assertEqual(response.status_code,206)
            self.assertEqual(response.mimetype,'video/mp4')
            self.assertEqual(len(response.data),1024)
            self.assertTrue(response.headers['Content-Range'].startswith('bytes 0-1023/'))
        finally:response.close()

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
        self.assertTrue(response.json['ok']);self.assertIn('updated',response.json);self.assertNotIn('messages',response.json)
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

    def test_creator_host_controls_transfer_and_ads(self):
        self.assertTrue(self.host.get(self.url).json['can_control'])
        self.assertTrue(self.guest.get(self.url).json['can_control'])
        self.assertEqual(self.guest.post(self.url,json={'action':'playback','position':0,'playing':False}).status_code,200)
        self.host.post(self.url,json={'action':'ad_status','active':True})
        self.assertTrue(self.guest.get(self.url).json['host_ad'])
        self.host.post(self.url,json={'action':'ad_status','active':False})
        self.assertFalse(self.guest.get(self.url).json['host_ad'])
        self.host.post(self.url,json={'action':'playback','position':40,'playing':False})
        self.host.post(self.url,json={'action':'playback','position':40,'playing':True})
        self.assertTrue(self.guest.get(self.url).json['playing'])
        target=next(p for p in self.host.get(self.url).json['members'] if not p['you'])
        self.host.post(self.url,json={'action':'transfer_host','member_id':target['member_id']})
        self.assertTrue(self.guest.get(self.url).json['can_control'])
        self.assertTrue(self.host.get(self.url).json['can_control'])

    def test_old_pause_sample_cannot_override_confirmed_resume(self):
        paused=self.host.post(self.url,json={'action':'playback','position':50,'playing':False}).json
        self.host.post(self.url,json={'action':'playback','position':50,'playing':True})
        old=self.host.post(self.url,json={'action':'playback','position':50,'playing':False,'expected_updated':paused['updated'],'compact':True})
        self.assertEqual(old.status_code,409)
        state=self.guest.get(self.url).json
        self.assertEqual(state['playing'],1)
        self.assertEqual(state['position'],50)

    def test_last_leave_deletes_room_and_room_data_but_keeps_names(self):
        self.host.post(self.url,json={'action':'chat','body':'Room history'})
        self.guest.post(self.url,json={'action':'add','url':'aqz-KE-bpKQ'})
        first=self.host.post(self.url+'/leave',json={})
        self.assertFalse(first.json['room_deleted'])
        self.assertTrue(self.guest.get(self.url).json['is_host'])
        last=self.guest.post(self.url+'/leave',json={})
        self.assertTrue(last.json['room_deleted'])
        self.assertEqual(self.guest.get(self.url).status_code,404)
        self.assertEqual(self.guest.get('/api/profile').json['name'],'Guest')
        with app.app_context():
            for table in ['messages','queue','typing','presence','room_ads','members']:
                self.assertEqual(db().execute(f'SELECT count(*) FROM {table}').fetchone()[0],0)

    def test_disconnect_grace_and_expiry(self):
        import time
        from unittest.mock import patch
        start=time.time()
        self.host.post(self.url+'/presence',json={'active':False})
        self.guest.post(self.url+'/presence',json={'active':False})
        with patch('app.time.time',return_value=start+90):
            self.host.get('/api/health')
            with app.app_context():self.assertEqual(db().execute('SELECT count(*) FROM rooms').fetchone()[0],1)
        with patch('app.time.time',return_value=start+130):
            self.host.get('/api/health')
            with app.app_context():self.assertEqual(db().execute('SELECT count(*) FROM rooms').fetchone()[0],0)

    def test_leave_retry_is_safe_and_cannot_remove_other_members(self):
        outsider=app.test_client()
        response=outsider.post(self.url+'/leave',json={})
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.json['room_deleted'])
        self.assertEqual(len(self.host.get(self.url).json['members']),2)
        self.host.post(self.url+'/leave',json={})
        retry=self.host.post(self.url+'/leave',json={})
        self.assertEqual(retry.status_code,200)
        self.assertFalse(retry.json['room_deleted'])
        self.assertTrue(self.guest.get(self.url).json['is_host'])
        self.guest.post(self.url+'/leave',json={})
        for client in (self.host,self.guest):
            retry=client.post(self.url+'/leave',json={})
            self.assertEqual(retry.status_code,200)
            self.assertTrue(retry.json['room_deleted'])
        self.assertEqual(self.guest.get(self.url).status_code,404)

    def test_simultaneous_final_leaves_delete_room(self):
        import concurrent.futures
        cookies=[c.get_cookie('session').value for c in (self.host,self.guest)]
        def leave(cookie):
            client=app.test_client();client.set_cookie('session',cookie)
            response=client.post(self.url+'/leave',json={})
            return response.status_code,response.json['room_deleted']
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(leave,cookies))
        self.assertEqual(sorted(responses),[(200,False),(200,True)])
        self.assertEqual(self.host.get(self.url).status_code,404)

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
