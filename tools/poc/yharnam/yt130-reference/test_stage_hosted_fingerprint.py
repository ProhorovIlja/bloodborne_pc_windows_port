"""Prevent false 0/1000 Hosted test from bare bbload default fingerprint."""
import importlib.util
from pathlib import Path
import shlex
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "yt_hosted_fingerprint", HERE / "stage_hosted_fingerprint.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class HostedFingerprintTests(unittest.TestCase):
    def test_original_build_verification_exactly_matches_nonhosted_fixture(self):
        self.assertEqual(m.BUILD, "bb-build 1;version=dev;protocol=9;")
        self.assertEqual(m.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOB, "9a8e6a1dd866f9ef996ed544e3b781953e154230")
        m.verify()
        parsed = shlex.split(f"--build '{m.BUILD}' --owner-fps 30 --follower-fps 8")
        self.assertEqual(parsed[1], m.BUILD)
        self.assertEqual(parsed[-4:], ["--owner-fps", "30", "--follower-fps", "8"])
        self.assertEqual(f"--build '{m.BUILD}'".split()[1], "'bb-build")

    def test_fail_closed_on_drift_bad_source_or_double_application(self):
        for data in (b"", b"import argparse\nargs.extra.split()\n",
                     b"import argparse\nshlex.split(args.extra)\n"):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    m.rewrite(data)


if __name__ == "__main__":
    unittest.main()
