#!/usr/bin/env python3
"""Synthetic-only source/guard regression for V194 YT v1.3.1 migration.

Real, exact pinned upstream test_team_lobby is compiled separately in CI.
"""
from pathlib import Path
import importlib.util
from unittest import TestCase, main, mock
import tempfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("v194",HERE/"stage_yt131_five_seat_v194.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Yt131FiveSeatStageTests(TestCase):
    def test_reviewed_proto_actions_are_explicit(self):
        self.assertEqual(len(m.PINNED_BLOBS),4)
        self.assertEqual(len(set(m.PINNED_BLOBS)),4)
        self.assertIn("PROTOCOL_CURRENT = 8;",m.PROTO_GATES)
        self.assertIn("ASK_JOIN = 24;",m.PROTO_GATES)
        self.assertIn("uint32 team_size = 14;",m.PROTO_GATES)
        self.assertEqual(len(m.UPSTREAM_131),40)

    def test_fails_closed_before_patching_when_proto_missing(self):
        # Pure synthetic placeholder, no game code or retail data. Ensure that
        # the validation fails BEFORE patch() can edit any C++.
        fake={p:"not-a-proto" for p in m.PINNED_BLOBS}
        with mock.patch.object(m,"patch",side_effect=AssertionError("called too early")) as patch:
            with self.assertRaisesRegex(ValueError,"proto gate"):
                m.transform(fake)
            patch.assert_not_called()

    def test_rejects_partial_duplicate_or_reapplied_change(self):
        with self.assertRaisesRegex(ValueError,"incomplete"):
            m.transform({"server/coop/coop.proto":"PROTOCOL_CURRENT = 8;"})
        proto="\n".join(m.PROTO_GATES)
        fake={p:proto for p in m.PINNED_BLOBS}
        fake["server/coop/coop.proto"] += "\nPROTOCOL_CURRENT = 8;"
        with self.assertRaisesRegex(ValueError,"proto gate"):
            m.transform(fake)
        fake["server/coop/coop.proto"]=proto
        fake["server/coop/team_lobby.cpp"]=m.MARK
        with self.assertRaisesRegex(ValueError,"already applied"):
            m.transform(fake)

    def test_stage_rejects_wrong_git_revision_without_writing(self):
        with tempfile.TemporaryDirectory(prefix="v194-gate-") as tmp:
            root=Path(tmp)
            # Never trust a valid-looking directory without an exact checkout.
            with self.assertRaises((OSError,ValueError)):
                m.stage(root)
            self.assertEqual(list(root.iterdir()),[])

    def test_one_replace_checks_repeated_anchor(self):
        with self.assertRaisesRegex(ValueError,"source drift"):
            m.replace_one("a\na\n","a","b","repeated")
        with self.assertRaisesRegex(ValueError,"source drift"):
            m.replace_one("a","missing","b","absent")
        self.assertEqual(m.replace_one("A","A","B","once"),"B")

if __name__=="__main__":
    main()
