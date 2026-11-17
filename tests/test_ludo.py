import json,random,unittest
from unittest.mock import patch
import test_app
from app import app,db
from ludo_game import legal

class LudoTests(unittest.TestCase):
    setUp=test_app.WatchPartyTests.setUp
    tearDown=test_app.WatchPartyTests.tearDown
    def start(self):
        self.endpoint=self.url+'/ludo';self.host.post(self.endpoint,json={'action':'join'})
        state=self.guest.post(self.endpoint,json={'action':'join'}).json
        return self.host.post(self.endpoint,json={'action':'start','revision':state['revision']}).json
    def seed(self,state):
        with app.app_context():
            row=db().execute('SELECT state FROM room_games WHERE room=?',(self.url.rsplit('/',1)[1],)).fetchone();all_games=json.loads(row['state'])
            original=all_games['ludo'];original.update({k:v for k,v in state.items() if k not in ('players','you','legal','storage_generation')})
            db().execute('UPDATE room_games SET state=? WHERE room=?',(json.dumps(all_games),self.url.rsplit('/',1)[1]));db().commit()
    def test_access_turns_server_dice_and_stale_roll(self):
        state=self.start();self.assertEqual(app.test_client().get(self.endpoint).status_code,403)
        self.assertEqual(self.guest.post(self.endpoint,json={'action':'roll','revision':state['revision']}).status_code,409)
        body={'action':'roll','revision':state['revision'],'dice':6}
        with patch('ludo_game.secrets.randbelow',return_value=0):result=self.host.post(self.endpoint,json=body).json
        self.assertEqual(result['event']['dice'],1);self.assertEqual(result['event']['kind'],'pass');self.assertEqual(result['turn'],'blue')
        self.assertEqual(self.host.post(self.endpoint,json=body).status_code,409)
    def test_capture_blockade_safe_and_exact_finish(self):
        state=self.start();state['pawns']['red']=[5,-1,-1,-1];state['pawns']['blue']=[50,-1,-1,-1];state['dice']=6;self.seed(state)
        captured=self.host.post(self.endpoint,json={'action':'move','token':0,'revision':state['revision']}).json
        self.assertEqual(captured['pawns']['blue'][0],-1);self.assertEqual(captured['turn'],'red');self.assertEqual(len(captured['event']['captured']),1)
        state['pawns']['blue']=[50,50,-1,-1];self.assertNotIn(0,legal(state,'red',6))
        state['pawns']['red']=[55,56,56,56];state['pawns']['blue']=[-1]*4;state['dice']=2;self.seed(state)
        self.assertEqual(self.host.post(self.endpoint,json={'action':'move','token':0,'revision':state['revision']}).status_code,400)
        state['dice']=1;self.seed(state);won=self.host.post(self.endpoint,json={'action':'move','token':0,'revision':state['revision']}).json
        self.assertEqual(won['winner'],'red');self.assertEqual(self.guest.get(self.endpoint).json['winner'],'red')
    def test_three_sixes_and_room_cleanup(self):
        state=self.start()
        for _ in range(2):
            with patch('ludo_game.secrets.randbelow',return_value=5):state=self.host.post(self.endpoint,json={'action':'roll','revision':state['revision']}).json
            state=self.host.post(self.endpoint,json={'action':'move','token':0,'revision':state['revision']}).json
        with patch('ludo_game.secrets.randbelow',return_value=5):state=self.host.post(self.endpoint,json={'action':'roll','revision':state['revision']}).json
        self.assertEqual(state['event']['kind'],'three_sixes');self.assertEqual(state['turn'],'blue')
        self.host.post(self.url+'/leave',json={});self.guest.post(self.url+'/leave',json={});self.assertEqual(self.host.get(self.endpoint).status_code,404)
    def test_four_players_and_complete_two_player_match(self):
        state=self.start();outsider=app.test_client();outsider.post(self.url,json={'action':'join','name':'Watcher'});self.assertEqual(outsider.post(self.endpoint,json={'action':'join'}).status_code,409)
        rng=random.Random(42);actions=0
        while not state['winner'] and actions<2000:
            client=self.host if state['turn']=='red' else self.guest
            if state['dice'] is None:
                with patch('ludo_game.secrets.randbelow',side_effect=lambda n:rng.randrange(n)):response=client.post(self.endpoint,json={'action':'roll','revision':state['revision']})
            else:
                legal_tokens=legal(state,state['turn'],state['dice']);token=max(legal_tokens,key=lambda t:state['pawns'][state['turn']][t]);response=client.post(self.endpoint,json={'action':'move','token':token,'revision':state['revision']})
            self.assertEqual(response.status_code,200,response.json);state=response.json;actions+=1
        self.assertIsNotNone(state['winner']);self.assertTrue(all(p==56 for p in state['pawns'][state['winner']]))
        self.assertEqual(self.guest.get(self.endpoint).json['winner'],state['winner'])
        self.assertEqual(self.host.post(self.endpoint,json={'action':'reset','revision':state['revision']}).status_code,200)
    def test_four_seats_and_other_games_coexist(self):
        self.endpoint=self.url+'/ludo';self.host.post(self.endpoint,json={'action':'join'});self.guest.post(self.endpoint,json={'action':'join'})
        for name in ['Third','Fourth']:
            client=app.test_client();client.post(self.url,json={'action':'join','name':name});self.assertEqual(client.post(self.endpoint,json={'action':'join'}).status_code,200)
        spectator=app.test_client();spectator.post(self.url,json={'action':'join','name':'Watcher'});self.assertEqual(spectator.post(self.endpoint,json={'action':'join'}).status_code,409)
        state=self.host.get(self.endpoint).json;self.assertEqual(len(state['players']),4)
        self.assertEqual(self.host.post(self.url+'/game',json={'action':'join'}).status_code,200)
        self.assertEqual(self.host.post(self.url+'/basketball',json={'action':'join'}).status_code,200)
        self.assertEqual(len(self.host.get(self.endpoint).json['players']),4)

if __name__=='__main__':unittest.main()
