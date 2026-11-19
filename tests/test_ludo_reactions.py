import unittest
from unittest.mock import patch
import test_app
from app import app

class LudoColorResultTests(unittest.TestCase):
    setUp=test_app.WatchPartyTests.setUp
    tearDown=test_app.WatchPartyTests.tearDown
    def test_color_claims_are_exclusive_and_lock_at_start(self):
        url=self.url+'/ludo'
        state=self.host.post(url,json={'action':'join','color':'green'}).json;self.assertEqual(state['you'],'green')
        self.assertEqual(self.guest.post(url,json={'action':'join','color':'green'}).status_code,409)
        state=self.guest.post(url,json={'action':'join','color':'yellow'}).json
        state=self.host.post(url,json={'action':'color','color':'red','revision':state['revision']}).json;self.assertEqual(state['you'],'red');self.assertNotIn('green',state['players'])
        state=self.host.post(url,json={'action':'start','revision':state['revision']}).json
        self.assertEqual(self.host.post(url,json={'action':'color','color':'blue','revision':state['revision']}).status_code,409)
    def test_roll_result_is_shared_without_exposing_member_ids_or_changing_video(self):
        url=self.url+'/ludo'
        for client in [self.host,self.guest]:state=client.post(url,json={'action':'join'}).json
        before=self.host.get(self.url).json
        state=self.host.post(url,json={'action':'start','revision':state['revision']}).json
        with patch('ludo_game.secrets.randbelow',return_value=4):state=self.host.post(url,json={'action':'roll','revision':state['revision']}).json
        result=self.guest.get(self.url).json['ludo_roll'];self.assertEqual(result['dice'],5);self.assertEqual(result['name'],'Host');self.assertEqual(set(result),{'id','dice','name','created'})
        after=self.host.get(self.url).json
        for key in ['video','playing','position','playback_revision','playback_id']:self.assertEqual(before[key],after[key])
        stranger=app.test_client();self.assertEqual(stranger.get(self.url).status_code,403)
