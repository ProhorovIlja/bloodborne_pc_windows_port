"""Pinned native YT1.3 Win32 wall-clock rewrite/regression, no game data."""
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).with_name("stage_native_win32_clock_v153.py")
spec=importlib.util.spec_from_file_location("yt_native_winclock_v153",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class NativeClockOriginalSourceTests(unittest.TestCase):
    def original(self):
        return (m.OLD_INCLUDE+
                "typedef struct { int64_t seconds, microseconds; } GuestTimeval;\n"+
                "typedef struct { int32_t minuteswest, dsttime; } GuestTimezone;\n"+
                m.OLD_FN+
                'uintptr_t runtime_time_resolve(const char *name) {\n'
                ' if (!strcmp(name,"n88vx3C5nW8#I#J")) return (uintptr_t)guest_gettimeofday;\n'
                ' return 0;\n'
                '}\n')
    def test_native_windows_clock_is_real_winapi_and_guest_abi_preserved(self):
        result=m.rewrite(self.original())
        self.assertIn("#include <windows.h>",result)
        self.assertIn("GetSystemTimePreciseAsFileTime(&ft);",result)
        self.assertIn("INT64_C(116444736000000000)",result)
        self.assertIn("INT64_C(10000000)",result)
        self.assertIn("value->seconds=seconds; value->microseconds=micros",result)
        self.assertIn("GetTimeZoneInformation(&tz)",result)
        self.assertIn("zone->minuteswest=(int32_t)(-compat_utc_offset",result)
        self.assertIn('"n88vx3C5nW8#I#J"',result)
        self.assertIn("static ABI int guest_gettimeofday(",result)
        self.assertNotIn("if (gettimeofday(&t,NULL))",result)
        # Non-Windows original function semantics preserved, not rewritten.
        self.assertIn("gettimeofday(&t,&z)",result)
        self.assertIn("perror(\"STOP: host gettimeofday failed\")",result)
        self.assertEqual(result.count("GetSystemTimePreciseAsFileTime"),1)
    def test_fail_closed_on_already_patched_or_unpinned_file(self):
        src=self.original()
        with self.assertRaisesRegex(ValueError,"exact YT1.3"):
            m.transform(src.encode())
        with self.assertRaisesRegex(ValueError,"already staged"):
            m.rewrite(m.rewrite(src))
        for old in (m.OLD_INCLUDE,m.OLD_FN):
            with self.subTest(original=old[:44]):
                with self.assertRaisesRegex(ValueError,"drift"):
                    m.rewrite(src.replace(old,"BROKEN",1))
                with self.assertRaisesRegex(ValueError,"drift"):
                    m.rewrite(src+old)
        self.assertEqual(m.BLOB,"31f568e90ffa885e2814a2c6d08851befb681a77")
        self.assertEqual(m.PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.normalize(b"a\r\nb\r\n"),b"a\nb\n")
    def test_time_conversion_reference_vectors(self):
        # Windows FILETIME 1601 epoch to Unix signed timeval; test off-by-one
        # around 1970 and microsecond boundaries independently of the C test.
        ticks_per_second=10_000_000
        unix_epoch=116444736000000000
        def value(ticks):
            delta=ticks-unix_epoch
            seconds,micro=divmod(delta,ticks_per_second)
            return seconds,micro//10
        for ticks,expected in [
            (unix_epoch,(0,0)),
            (unix_epoch+1,(0,0)),
            (unix_epoch+10,(0,1)),
            (unix_epoch+9999990,(0,999999)),
            (unix_epoch+10000000,(1,0)),
            (unix_epoch-10,(-1,999999)),
        ]:
            with self.subTest(ticks=ticks):
                self.assertEqual(value(ticks),expected)

if __name__=="__main__":
    unittest.main()
