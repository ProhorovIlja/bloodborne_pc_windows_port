import unittest
from presence import Presence, Observation, MAX_PEERS

class TestPresence(unittest.TestCase):
    def setUp(self):
        self.p = Presence()
    def test_absent_is_unknown_not_fake_zero(self):
        self.assertEqual(self.p.snapshot(100)["state"],"unavailable")
        self.assertIsNone(self.p.snapshot(100)["online"])
    def test_known_empty_server_really_zero(self):
        self.p.mark_server_alive(100)
        self.assertEqual(self.p.snapshot(100)["online"],0)
        self.assertEqual(self.p.snapshot(136)["state"],"stale")
        self.assertEqual(self.p.snapshot(251)["state"],"unavailable")
    def test_area_privacy_and_pvp(self):
        self.p.mark_server_alive(100)
        for i in range(3):
            self.assertTrue(self.p.observe(Observation(f"i-{i}","central_yharnam",100,True,False),100))
        self.assertTrue(self.p.observe(Observation("pvp","old_yharnam",100,True,True),100))
        self.assertTrue(self.p.observe(Observation("hidden","old_yharnam",100,False,False),100))
        s=self.p.snapshot(100)
        self.assertEqual(s["online"],5)
        self.assertEqual(s["areas"],[{"key":"central_yharnam","hunters":3,"suppressed":False}])
        self.assertNotIn("account_key",str(s))
        self.assertNotIn("pvp",str(s))
    def test_lone_hunter_cannot_be_publicly_tracked(self):
        self.p.mark_server_alive(10)
        self.p.observe(Observation("only","fishing_hamlet",10,True),10)
        snapshot = self.p.snapshot(10)
        self.assertEqual(snapshot["areas"], [])
        self.assertNotIn("fishing_hamlet", str(snapshot))
    def test_two_hunters_location_stays_private_until_threshold(self):
        self.p.mark_server_alive(10)
        for i in range(2):
            self.assertTrue(self.p.observe(
                Observation(f"single-{i}", "old_yharnam", 10, True), 10))
        before = self.p.snapshot(10)
        self.assertEqual(before["online"], 2)
        self.assertEqual(before["areas"], [])
        self.assertNotIn("old_yharnam", str(before))
        self.assertTrue(self.p.observe(
            Observation("third", "old_yharnam", 10, True), 10))
        after = self.p.snapshot(10)
        self.assertEqual(after["areas"], [
            {"key": "old_yharnam", "hunters": 3, "suppressed": False}
        ])
    def test_expiration_departure_and_reordered_updates(self):
        self.p.mark_server_alive(0)
        self.assertTrue(self.p.observe(Observation("a","cathedral_ward",0),0))
        self.p.mark_server_alive(20)
        self.assertTrue(self.p.observe(Observation("a","old_yharnam",20),20))
        self.assertFalse(self.p.observe(Observation("a","cathedral_ward",0),20))
        self.assertEqual(self.p.snapshot(20)["online"],1)
        self.p.depart("a")
        self.assertEqual(self.p.snapshot(20)["online"],0)
        self.p.mark_server_alive(100)
        self.assertEqual(self.p.snapshot(100)["online"],0)
    def test_reject_fabricated_unverified_heartbeat(self):
        self.assertFalse(self.p.observe(Observation("fake","central_yharnam",10,True),10))
    def test_reject_invalid_and_stale_inputs(self):
        self.p.mark_server_alive(100)
        for obs in [Observation("x","javascript:alert(1)",100,True),
                    Observation("x","central_yharnam",float("nan"),True),
                    Observation("x","central_yharnam",1,True),
                    Observation("","old_yharnam",100,True),
                    Observation("x","old_yharnam",100,1)]:
            self.assertFalse(self.p.observe(obs,100))
    def test_bounded_memory_and_stale_eviction(self):
        self.p.mark_server_alive(0)
        for i in range(MAX_PEERS):
            self.assertTrue(self.p.observe(Observation(str(i),"central_yharnam",0),0))
        self.assertFalse(self.p.observe(Observation("overflow","central_yharnam",0),0))
        self.p.mark_server_alive(100)
        self.assertTrue(self.p.observe(Observation("new","old_yharnam",100),100))
        self.assertEqual(self.p.snapshot(100)["online"],1)
    def test_nonmonotonic_server_time_rejected(self):
        self.p.mark_server_alive(100)
        with self.assertRaisesRegex(ValueError,"nonmonotonic"):
            self.p.mark_server_alive(99)
if __name__=="__main__":
    unittest.main()
