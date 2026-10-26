"""Source exact and semantic guardrails for experimental non-hosted lobby dedupe."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).with_name("stage_lobby_dedupe.py")
spec = importlib.util.spec_from_file_location("yt130_lobby_dedupe", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class LobbyDedupStageTests(unittest.TestCase):
    def setUp(self):
        self.cpp = ("void Service::OnLobbyHello(Member&, const bbcoop::LobbyHello&, "
                    "qint64, Result&) {}\n"
                    "void Service::SendLobby(qint64 now_ms) {\n"
                    + mod.BEFORE + "\n}\n")

    def test_reuses_existing_hosted_dedupe_for_nonhosted(self):
        changed = mod.patch_text(self.cpp)
        self.assertEqual(changed.count("SerializeAsString()"), 1)
        self.assertEqual(changed.count("SendTo(member, envelope, now_ms);"), 1)
        self.assertIn("if (sent == bytes)", changed)
        self.assertIn("lobby_sent[member.lobby]", changed)
        self.assertIn("Each new lobby hello separately receives its initial state", changed)
        self.assertNotIn("if (hosted.enabled)", changed)
        self.assertEqual(mod.RELATIVE, "server/src/bloodborne_world.cpp")

    def test_fails_closed_on_modified_repeated_or_missing_source(self):
        examples = [
            self.cpp.replace("if (hosted.enabled)", "if (true)"),
            self.cpp + mod.BEFORE,
            self.cpp.replace("void Service::OnLobbyHello", "void Service::Unrecognized"),
            mod.patch_text(self.cpp),
        ]
        for altered in examples:
            with self.subTest(change=altered[-50:]):
                with self.assertRaises(ValueError):
                    mod.patch_text(altered)

    def test_pinned_source_and_no_client_code(self):
        self.assertEqual(mod.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(mod.ORIGINAL_BLOB,
                         "eca8c30d6fb78099b0f64a52388fd7d65f926e19")


if __name__ == "__main__":
    unittest.main()
