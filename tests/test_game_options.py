import unittest
import test_app
from app import app,db

class MatchOptionsTests(unittest.TestCase):
    setUp=test_app.WatchPartyTests.setUp
    tearDown=test_app.WatchPartyTests.tearDown
    def join(self,kind):
        url=self.url+'/'+kind
        for client in [self.host,self.guest]:self.assertEqual(client.post(url,json={'action':'join'}).status_code,200)
        return url
    def configure(self,url,values):
        state=self.host.get(url).json
        a=self.host.post(url,json={'action':'configure','values':values,'revision':state['revision']});self.assertEqual(a.status_code,200,a.json)
        self.assertEqual(a.json['proposal']['votes'],[a.json['you']])
        b=self.guest.post(url,json={'action':'configure','values':values,'revision':a.json['revision']});self.assertEqual(b.status_code,200,b.json)
        self.assertNotIn('proposal',b.json);return b.json
    def test_together_goal_agreement_and_both_accept_rematch(self):
        url=self.join('basketball');before=self.host.get(self.url).json
        state=self.configure(url,{'mode':'together','difficulty':'challenging'})
        for i in range(8):
            client=self.host if state['turn']=='X' else self.guest
            state=client.post(url,json={'action':'shoot','revision':state['revision'],'aim':state['challenge']['target'],'power':state['challenge']['power']}).json
        self.assertEqual(state['winner'],'together');self.assertEqual(sum(state['scores'].values()),8)
        state=self.host.post(url,json={'action':'reset','revision':state['revision']}).json;self.assertEqual(state['winner'],'together')
        state=self.guest.post(url,json={'action':'reset','revision':state['revision']}).json;self.assertIsNone(state['winner']);self.assertEqual(state['mode'],'together')
        after=self.host.get(self.url).json
        for key in ['video','playing','position','playback_revision','playback_id']:self.assertEqual(before[key],after[key])
    def test_series_alternates_starter_and_requires_both_for_next_round(self):
        url=self.join('game');state=self.configure(url,{'best_of':3})
        for mark,cell in [('X',0),('O',3),('X',1),('O',4),('X',2)]:
            state=(self.host if mark=='X' else self.guest).post(url,json={'action':'move','cell':cell,'revision':state['revision']}).json
        self.assertEqual(state['wins']['X'],1);self.assertIsNone(state['series_winner'])
        state=self.host.post(url,json={'action':'reset','revision':state['revision']}).json;self.assertEqual(state['winner'],'X')
        state=self.guest.post(url,json={'action':'reset','revision':state['revision']}).json;self.assertEqual(state['turn'],'O');self.assertEqual(state['round'],2)
        for mark,cell in [('O',3),('X',0),('O',4),('X',1),('O',8),('X',2)]:
            state=(self.host if mark=='X' else self.guest).post(url,json={'action':'move','cell':cell,'revision':state['revision']}).json
        self.assertEqual(state['series_winner'],'X')
    def test_quick_ludo_preview_is_legal_and_does_not_advance_revision(self):
        from unittest.mock import patch
        url=self.join('ludo');state=self.configure(url,{'pawn_count':2})
        self.assertEqual(state['pawns']['red'][2:],[56,56])
        state=self.host.post(url,json={'action':'start','revision':state['revision']}).json
        with patch('ludo_game.secrets.randbelow',return_value=5):state=self.host.post(url,json={'action':'roll','revision':state['revision']}).json
        self.assertEqual(state['legal'],[0,1]);rev=state['revision']
        state=self.host.post(url,json={'action':'preview','token':0,'revision':rev}).json;self.assertEqual(state['revision'],rev)
        self.assertEqual(self.guest.get(url).json['selection']['token'],0)
        self.assertEqual(self.guest.post(url,json={'action':'preview','token':0,'revision':rev}).status_code,409)
        state=self.host.post(url,json={'action':'move','token':0,'revision':rev}).json;self.assertIsNone(state['selection'])
    def test_tic_tac_toe_departure_preserves_other_games(self):
        hoops=self.join('basketball');ttt=self.join('game');ludo=self.join('ludo')
        with app.app_context():
            db().execute("DELETE FROM members WHERE name='Guest'");db().commit()
        self.host.get(ttt)
        with app.app_context():
            import json
            state=json.loads(db().execute('SELECT state FROM room_games').fetchone()[0]);self.assertIn('basketball',state);self.assertIn('ludo',state)
    def test_cheers_reach_partner_without_changing_turn_revision(self):
        for kind in ['game','ludo']:
            url=self.join(kind);state=self.host.get(url).json
            response=self.host.post(url,json={'action':'cheer','emoji':'🫶','revision':state['revision']})
            self.assertEqual(response.status_code,200,response.json)
            other=self.guest.get(url).json
            self.assertEqual(other['revision'],state['revision']);self.assertEqual(other['cheer']['emoji'],'🫶')
