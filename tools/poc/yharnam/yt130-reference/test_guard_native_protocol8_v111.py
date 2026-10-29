"""Release-blocking native YT1.3 client/Qt-server protocol compatibility tests."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

path = Path(__file__).with_name("guard_native_protocol8_v111.py")
spec = importlib.util.spec_from_file_location("yt130_protocol_guard", path)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def example():
    return (
        "void g() {\n"
        "  hello.mutable_hello()->set_protocol(CoopProtocol);\n"
        "  hello.mutable_lobby_hello()->set_protocol(CoopProtocol);\n}\n",
        "constexpr u32 CoopProtocol = bbcoop::PROTOCOL_CURRENT;\n",
        "enum Protocol { PROTOCOL_NONE = 0;\n PROTOCOL_CURRENT = 8; };\n"
        "message Hello {uint32 protocol = 1;}\n"
        "message LobbyHello {uint32 protocol = 1;}\n",
        "void game() {\n if (hello.protocol() != CoopProtocol) {\n"
        " notice = \"co-op protocol \" + std::to_string(hello.protocol());}\n}\n"
        "void lobby() {\n if (hello.protocol() != CoopProtocol || hello.member().empty()) {\n"
        " notice = \"co-op protocol \" + std::to_string(hello.protocol());}\n}\n",
    )


class NativeProtocol8Contract(unittest.TestCase):
    def test_protocol8_requires_both_game_hellos_and_server_refusals(self):
        guard.check_text(*example())
        self.assertEqual(len(guard.C_HELLOS), 2)
        self.assertEqual(len(guard.S_DENIALS), 2)

    def test_raw_version_number_flip_is_not_an_upgrade(self):
        originals = list(example())
        seven = originals.copy()
        seven[2] = seven[2].replace("PROTOCOL_CURRENT = 8;", "PROTOCOL_CURRENT = 7;")
        with self.assertRaisesRegex(ValueError, "Protocol 8"):
            guard.check_text(*seven)
        nine = originals.copy()
        nine[2] = nine[2].replace("PROTOCOL_CURRENT = 8;", "PROTOCOL_CURRENT = 9;")
        with self.assertRaisesRegex(ValueError, "Protocol 8"):
            guard.check_text(*nine)
        for n in (0, 1, 3):
            bad = originals.copy()
            bad[n] = "// protoc-only fake compatibility!"
            with self.subTest(source=n), self.assertRaises(ValueError):
                guard.check_text(*bad)

    def test_same_proto_number_but_different_schema_is_rejected(self):
        with TemporaryDirectory() as d:
            game = Path(d) / "game"
            server = Path(d) / "server"
            source = example()
            for root in (game, server):
                (root / Path(guard.CLIENT_SOURCE).parent).mkdir(parents=True, exist_ok=True)
                (root / Path(guard.COMMON_SOURCE).parent).mkdir(parents=True, exist_ok=True)
                (root / Path(guard.SERVER_SOURCE).parent).mkdir(parents=True, exist_ok=True)
                for name, content in zip(
                    (guard.CLIENT_SOURCE, guard.COMMON_SOURCE, guard.PROTO_SOURCE, guard.SERVER_SOURCE),
                    source,
                ):
                    (root / name).write_text(content, encoding="utf-8")
            guard.check_pair(game, server, pinned=False)
            # An independent client and server both say '8' but disagree on
            # field numbering: this must fail, not change a constant.
            (game / guard.PROTO_SOURCE).write_text(source[2] + "message NewField {}\n")
            with self.assertRaisesRegex(ValueError, "protobuf schemas differ"):
                guard.check_pair(game, server, pinned=False)

    def test_no_symlinked_unpinned_original_source(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            external = root / "content.txt"
            external.write_text("not original")
            link = root / "source.txt"
            link.symlink_to(external)
            with self.assertRaisesRegex(ValueError, "Missing pinned original"):
                guard.original(root, "source.txt", pinned=False)

    def test_git_blob_pins_are_distinct_and_unchanged(self):
        self.assertEqual(guard.blob(b"test"),
                         "30d74d258442c7c65512eafab474568dd706c430")
        self.assertEqual(len(set(guard.PIN_BLOBS.values())), 3)
        self.assertEqual(guard.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")


if __name__ == "__main__":
    unittest.main()
