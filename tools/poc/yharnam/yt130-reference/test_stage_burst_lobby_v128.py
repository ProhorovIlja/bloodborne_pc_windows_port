"""V128 original YT1.3 lobby burst tests; no synthetic performance claims."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "yt130_lobby128", Path(__file__).with_name("stage_burst_lobby_v128.py"))
assert spec is not None and spec.loader is not None
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class LobbyBurstTests(unittest.TestCase):
    def setUp(self):
        self.source = stage.STAGED_TICK + "\n" + stage.HELLO + "\n" + stage.START

    def test_small_lobbies_unmodified_and_burst_threshold_explicit(self):
        patched = stage.rewrite(self.source)
        self.assertIn("!hosted.enabled && members.size() > 32 ? 250 : 0;", patched)
        self.assertIn("hosted.enabled ? now_ms - lobby_sent_ms >= hosted.lobby_interval_ms", patched)
        self.assertIn("now_ms - lobby_sent_ms >= nonhosted_lobby_wait_ms", patched)
        self.assertIn(stage.HELLO, patched)
        self.assertIn(stage.START, patched)
        self.assertNotIn(stage.STAGED_TICK, patched)

    def test_every_pending_change_will_eventually_flush(self):
        patched = stage.rewrite(self.source)
        self.assertEqual(patched.count("SendLobby(now_ms);"), 1)
        self.assertEqual(patched.count("if (lobby_changed &&"), 1)
        self.assertEqual(patched.count("lobby_sent_ms >= nonhosted_lobby_wait_ms"), 1)
        self.assertEqual(patched.count("members.size() > 32"), 1)

    def test_source_drift_and_double_stage_fail_closed(self):
        patched = stage.rewrite(self.source)
        with self.assertRaises(ValueError):
            stage.rewrite(patched)
        with self.assertRaises(ValueError):
            stage.rewrite(self.source.replace(stage.HELLO, "unsafe-newcomer-route"))
        with self.assertRaises(ValueError):
            stage.rewrite(self.source.replace(stage.START, "unsafe-team-start"))

    def test_not_an_unsafe_early_drop_or_production_direct_p2p(self):
        self.assertTrue(stage.PATH.startswith("server/src/"))
        self.assertEqual(stage.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertNotIn("m_socket", stage.BATCH_TICK)
        self.assertNotIn("drop", stage.BATCH_TICK.lower())
        self.assertNotIn("direct", stage.BATCH_TICK.lower())


if __name__ == "__main__":
    unittest.main()
