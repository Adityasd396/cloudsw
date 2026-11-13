import unittest
import test_app
from app import app,db


class BasketballTests(unittest.TestCase):
    setUp=test_app.WatchPartyTests.setUp
    tearDown=test_app.WatchPartyTests.tearDown

    def join(self):
        self.endpoint=self.url+'/basketball'
        self.assertEqual(self.host.post(self.endpoint,json={'action':'join'}).status_code,200)
        response=self.guest.post(self.endpoint,json={'action':'join'})
        self.assertEqual(response.status_code,200)
        return response.json

    def test_two_players_score_miss_and_exactly_once_shots(self):
        state=self.join()
        body={'action':'shoot','aim':.5,'revision':state['revision']}
        goal=self.host.post(self.endpoint,json=body)
        self.assertTrue(goal.json['shot']['goal'])
        self.assertEqual(goal.json['scores'],{'X':1,'O':0})
        self.assertEqual(self.host.post(self.endpoint,json=body).status_code,409)
        self.assertEqual(self.host.post(self.endpoint,json={**body,'revision':goal.json['revision']}).status_code,409)
        miss=self.guest.post(self.endpoint,json={'action':'shoot','aim':0,'revision':goal.json['revision']})
        self.assertFalse(miss.json['shot']['goal'])
        self.assertEqual(self.host.get(self.endpoint).json['scores'],miss.json['scores'])
        self.assertEqual(miss.json['turn'],'X')

    def test_first_to_five_reset_and_other_game_preserved(self):
        state=self.join()
        self.host.post(self.url+'/game',json={'action':'join'})
        for turn in range(9):
            client=self.host if turn%2==0 else self.guest
            result=client.post(self.endpoint,json={'action':'shoot','aim':.5,'revision':state['revision']})
            self.assertEqual(result.status_code,200);state=result.json
        self.assertEqual(state['winner'],'X')
        self.assertEqual(state['scores'],{'X':5,'O':4})
        self.assertEqual(self.guest.get(self.endpoint).json['winner'],'X')
        self.assertEqual(self.guest.post(self.endpoint,json={'action':'shoot','aim':.5,'revision':state['revision']}).status_code,409)
        again=self.guest.post(self.endpoint,json={'action':'reset','revision':state['revision']}).json
        self.assertEqual(again['scores'],{'X':0,'O':0});self.assertIsNone(again['shot'])
        self.assertEqual(self.host.get(self.url+'/game').json['players'],{'X':'Host'})

    def test_access_validation_and_room_deletion(self):
        state=self.join()
        self.assertEqual(app.test_client().get(self.endpoint).status_code,403)
        outsider=app.test_client();outsider.post(self.url,json={'action':'join','name':'Watcher'})
        self.assertEqual(outsider.post(self.endpoint,json={'action':'join'}).status_code,409)
        for aim in [True,None,-1,2,'0.5',float('nan'),float('inf')]:
            self.assertEqual(self.host.post(self.endpoint,json={'action':'shoot','aim':aim,'revision':state['revision']}).status_code,400)
        self.assertEqual(self.host.post(self.endpoint,json=[]).status_code,400)
        outsider.post(self.url+'/leave',json={});self.host.post(self.url+'/leave',json={});self.guest.post(self.url+'/leave',json={})
        self.assertEqual(self.host.get(self.endpoint).status_code,404)
        with app.app_context():self.assertEqual(db().execute('SELECT count(*) FROM room_games').fetchone()[0],0)

    def test_both_users_play_pause_seek_independently_of_game(self):
        state=self.join()
        for client,other,playing,position in [(self.host,self.guest,True,12),(self.guest,self.host,False,12),(self.host,self.guest,False,42),(self.guest,self.host,True,42),(self.guest,self.host,True,32)]:
            response=client.post(self.url,json={'action':'playback','position':position,'playing':playing})
            self.assertEqual(response.status_code,200)
            seen=other.get(self.url).json
            self.assertEqual(bool(seen['playing']),playing);self.assertEqual(seen['position'],position)
        self.host.post(self.endpoint,json={'action':'shoot','aim':.5,'revision':state['revision']})
        self.assertEqual(self.guest.get(self.url).json['position'],32)
        self.assertTrue(self.guest.get(self.url).json['playing'])

    def test_concurrent_duplicate_shot_scores_once(self):
        from concurrent.futures import ThreadPoolExecutor
        state=self.join();cookie=self.host.get_cookie('session').value
        def shoot(_):
            client=app.test_client();client.set_cookie('session',cookie)
            return client.post(self.endpoint,json={'action':'shoot','aim':.5,'revision':state['revision']}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(shoot,range(2)))
        self.assertEqual(sorted(statuses),[200,409])
        self.assertEqual(self.guest.get(self.endpoint).json['scores']['X'],1)
