import unittest
import test_app
from app import app

class HoopsLiveTests(unittest.TestCase):
    setUp=test_app.WatchPartyTests.setUp
    tearDown=test_app.WatchPartyTests.tearDown
    def test_live_aim_power_scoring_and_stale_actions(self):
        route=self.url+'/basketball';self.host.post(route,json={'action':'join'});state=self.guest.post(route,json={'action':'join'}).json
        request={'action':'aim','revision':state['revision'],'phase':'charging','aim':.48,'power':.6}
        self.assertEqual(self.host.post(route,json=request).status_code,200)
        live=self.guest.get(route).json;self.assertEqual(live['live']['phase'],'charging');self.assertEqual(live['revision'],state['revision'])
        self.assertEqual(self.guest.post(route,json=request).status_code,409)
        miss=self.host.post(route,json={'action':'shoot','aim':.5,'power':0,'revision':state['revision']}).json;self.assertFalse(miss['shot']['goal']);self.assertIsNone(miss['live'])
        self.assertEqual(self.host.post(route,json=request).status_code,409)
        challenge=miss['challenge'];goal=self.guest.post(route,json={'action':'shoot','aim':challenge['target'],'power':challenge['power'],'revision':miss['revision']}).json
        self.assertTrue(goal['shot']['goal']);self.assertEqual(goal['shot']['rating'],'swish');self.assertEqual(goal['streaks']['O'],1)
        self.assertEqual(self.host.post(route,json={'action':'aim','revision':goal['revision'],'phase':'charging','aim':True,'power':.6}).status_code,400)

if __name__=='__main__':unittest.main()
