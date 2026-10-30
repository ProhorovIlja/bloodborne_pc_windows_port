"""V132 game world exact byte/reliability-preserving fan-out static regression."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

sp=importlib.util.spec_from_file_location(
    "yt130_encode_once",Path(__file__).with_name("stage_world_encode_once_v132.py"))
assert sp and sp.loader
v=importlib.util.module_from_spec(sp)
sp.loader.exec_module(v)


class WorldBroadcastTests(unittest.TestCase):
    def setUp(self):
        self.cpp="\n".join([p[1] for p in v.PATCHES]) + "\n// SHYT-V108-ALLIED-HOSTILE-VITALS\nSendTo(visitor->second, safe, now_ms);"
        self.header=v.HEADER_INCLUDE+v.HEADER_SENDTO

    def test_all_fanout_serialized_once_without_touching_reliable_chunks(self):
        cpp,h=v.rewrite(self.cpp,self.header)
        self.assertIn("const auto encoded = EncodeEnvelope(board)",cpp)
        self.assertIn("const auto encoded = EncodeEnvelope(envelope)",cpp)
        self.assertEqual(cpp.count("member.stream.Send(encoded, now_ms)"),1)
        self.assertIn("SendEncodedTo(invader->second, envelope, encoded, now_ms)",cpp)
        self.assertIn("SendTo(*only, board, now_ms)",cpp)
        self.assertIn("if (!member.to_flush)",cpp)
        self.assertIn("flush_now.push_back(&member)",cpp)
        self.assertIn("std::span<const u8>",h)
        self.assertIn("++m_diagEnvelopes[static_cast<int>(envelope.body_case())]",cpp)
        self.assertIn("#include <span>",h)
        self.assertEqual(cpp.count("void Service::SendTo("),1)
        self.assertEqual(cpp.count("void Service::SendEncodedTo("),1)

    def test_five_hunter_and_invader_delivery_filters_unchanged(self):
        cpp,_=v.rewrite(self.cpp,self.header)
        self.assertIn("member.party == world.name && &member != &from",cpp)
        self.assertIn("if (member.party == world.name)",cpp)
        self.assertIn("if (!invasion.joined) continue;",cpp)
        self.assertIn("const auto invader = members.find(invasion.invader)",cpp)
        self.assertIn("SendTo(visitor->second, safe, now_ms);",cpp)
        self.assertNotIn("SendEncodedTo(visitor->second, board, encoded",cpp)
        self.assertIn("member.stream.Send(encoded, now_ms);",cpp)
        for phrase in ("Drop(", "PacketClass::Unreliable", "Skip(","DirectP2P"):
            self.assertNotIn(phrase,cpp)

    def test_missing_source_or_repeat_patch_fails_closed(self):
        cpp,h=v.rewrite(self.cpp,self.header)
        with self.assertRaises(ValueError):v.rewrite(cpp,h)
        with self.assertRaises(ValueError):v.rewrite(self.cpp.replace(v.SENDTO_OLD,"BROKEN"),self.header)
        with self.assertRaises(ValueError):v.rewrite(self.cpp,self.header.replace(v.HEADER_SENDTO,"BROKEN"))

    def test_original_exact_source_pin(self):
        self.assertEqual(v.PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(v.CPP,"server/src/bloodborne_world.cpp")
        self.assertEqual(v.HEADER,"server/src/bloodborne_world.h")


if __name__=="__main__":unittest.main()
