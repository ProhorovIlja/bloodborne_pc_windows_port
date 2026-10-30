"""V158 exact original Qt receive-path diagnostics; private-data-free fixtures."""
import importlib.util
import unittest
from pathlib import Path

path=Path(__file__).with_name("stage_qt_receive_v158.py")
spec=importlib.util.spec_from_file_location("qt_v158",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def bbload_fixture():
    return ("struct Totals {\n"+m.TOTAL_OLD+"\n};\n"+
            "void Game::OnReadyRead() {\n"+m.READ_OLD+"\n"+m.DATA_OLD+"\n}\n"+
            "void Game::TakeData() {\n"+m.FRAME_OLD+"\n}\n"+
            "void Finish() {\n"+m.OUTPUT_OLD+"\n}\n"+
            "// V156 marker SHYT_V156_ANONYMOUS_LOBBY_NOTICE_CATEGORIES\n")

def shards_fixture():
    return ("# SHYT-V155-ORIGINAL-QT-ANONYMOUS-DATA-WIRE\n"+
            '{"team_total_notices": sum(r["team_total_notices"] for r in results)}\n'+
            m.AGG_OLD+"\n")

class QtLoadReceiverV158Tests(unittest.TestCase):
    def test_source_scope_and_expected_exact_qt_fields(self):
        self.assertEqual(m.PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.PATH,"server/loadtest/bbload.cpp")
        self.assertIn("socket.readDatagram(datagram.data()",m.READ_NEW)
        self.assertIn("bytes_read < 0",m.READ_NEW)
        self.assertIn("bytes_read != datagram.size()",m.READ_NEW)
        self.assertIn("++load.totals.game_data_datagrams_received",m.DATA_NEW)
        self.assertIn("++load.totals.game_data_decode_failed",m.DATA_NEW)
        self.assertIn("++load.totals.game_frame_bad_header",m.FRAME_NEW)
        self.assertIn("++load.totals.game_frame_decode_failed",m.FRAME_NEW)
        self.assertIn("++load.totals.game_frame_short_entries",m.FRAME_NEW)
        self.assertIn("++load.totals.game_frame_decoded",m.FRAME_NEW)
        self.assertNotIn("printf(",m.DATA_NEW+m.FRAME_NEW+m.READ_NEW)
        self.assertNotIn("qInfo(",m.DATA_NEW+m.FRAME_NEW+m.READ_NEW)
        self.assertNotIn("name.c_str()",m.DATA_NEW+m.FRAME_NEW+m.READ_NEW)
        self.assertNotIn("from.toString()",m.DATA_NEW+m.FRAME_NEW+m.READ_NEW)
    def test_exact_staging_preserves_core_frame_decoder(self):
        s=m.patch_load(bbload_fixture())
        self.assertIn(m.MARKER,s)
        self.assertIn("for (const GameFrameEntry &entry : game_frame->entries)",s)
        self.assertIn("GameLinkDetail::Get",m.FRAME_NEW if "GameLinkDetail::Get" in m.FRAME_NEW else "GameLinkDetail::Get")
        for field in ("udp_read_failed","udp_read_short",
                      "game_data_datagrams_received","game_data_decode_failed",
                      "game_frame_decode_failed","game_frame_bad_header",
                      "game_frame_short_entries","game_frame_decoded"):
            self.assertIn(f'{{"{field}", static_cast<double>(totals.{field})}}',s)
            self.assertIn(f'{{"{field}": sum(r["{field}"] for r in results)}}'.replace("{","").replace("}",""),m.AGG_NEW)
        self.assertEqual(s.count("socket.readDatagram"),1)
        self.assertEqual(s.count("game_frame_bad_header"),3) # totals, receive and JSON
        with self.assertRaisesRegex(ValueError,"drift"):
            m.patch_load(s)
    def test_fail_closed_on_original_source_or_order_drift(self):
        with self.assertRaisesRegex(ValueError,"V141\\+V156"):
            m.patch_load(bbload_fixture().replace(
                "SHYT_V156_ANONYMOUS_LOBBY_NOTICE_CATEGORIES","MISSING"))
        with self.assertRaisesRegex(ValueError,"V155\\+V156"):
            m.patch_shards(shards_fixture().replace(
                "SHYT-V155-ORIGINAL-QT-ANONYMOUS-DATA-WIRE","MISSING"))
        for a in (m.TOTAL_OLD,m.READ_OLD,m.DATA_OLD,m.FRAME_OLD,m.OUTPUT_OLD):
            with self.subTest(label=a[:24]):
                with self.assertRaisesRegex(ValueError,"drift"):
                    m.patch_load(bbload_fixture().replace(a,"DIFFERENT"))
                with self.assertRaisesRegex(ValueError,"drift"):
                    m.patch_load(bbload_fixture()+a)
    def test_shard_totals_preserve_existing_reports_and_no_identifiers(self):
        s=m.patch_shards(shards_fixture())
        self.assertIn(m.AGG_NEW,s)
        self.assertIn('"team_total_notices": sum(',s)
        self.assertNotIn("name",m.AGG_NEW)
        self.assertNotIn("token",m.AGG_NEW)
        self.assertNotIn("user",m.AGG_NEW)
        with self.assertRaisesRegex(ValueError,"drift"):
            m.patch_shards(s)

if __name__=="__main__":
    unittest.main()
