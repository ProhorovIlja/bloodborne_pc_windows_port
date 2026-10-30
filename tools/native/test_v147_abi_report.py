"""V147 privacy-safe original YT native PE/PS4 ABI import census tests."""
from contextlib import redirect_stderr,redirect_stdout
from io import StringIO
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

p=Path(__file__).with_name("v147_abi_report.py")
spec=importlib.util.spec_from_file_location("v147_abi_report",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def analysis():
    return {"source_sha256":"TOP_SECRET_GAME_HASH", "sfo":{"TITLE":"SECRET_GAME_TITLE"},
            "import_count":3,"imports":["a#libSceNet#x","b#libSceLibcInternal#y",
                                        "PRIVATE_NID#libSceFoo#z"],
            "needed":["libc.prx","libSceFios2.prx"],"entry":"0x12345"}

def link():
    return {"imports":5,"bindings":2,
            "modules":[{"file":"private/path/libc.prx"},{"file":"secret/location/libSceFios2.prx"}],
            "unresolved_imports":["PRIVATE_NID#libSceFoo#z",
                                 "SECRET_NETWORK_NID#libSceNet#b",
                                 "secretlibc#libSceLibcInternal#c"]}


class NativeAbiTests(unittest.TestCase):
    def test_output_contains_only_aggregate_no_raw_symbols_or_host_paths(self):
        out=m.summarize(analysis(),link())
        raw=json.dumps(out)
        self.assertEqual(out["schema"],"SHYT_NATIVE_ABI_AGGREGATE_V147")
        self.assertEqual(out["original_executable_imports"],3)
        self.assertEqual(out["linked_total_import_slots"],5)
        self.assertEqual(out["native_module_bound_symbols"],2)
        self.assertEqual(out["unresolved_linker_imports"],3)
        self.assertEqual(out["linked_module_count"],2)
        self.assertEqual(out["unresolved_by_host_library_class"],
                         {"native_libc":1,"sce_network":1,"sce_platform":1})
        for forbidden in ("PRIVATE_NID","SECRET","TOP_SECRET","libSceFoo",
                          "private/path","0x12345","libc.prx"):
            self.assertNotIn(forbidden,raw)
        self.assertFalse(out["runtime_proven"])
        self.assertTrue(out["link_stage_proven"])
        self.assertFalse(out["privacy"]["symbol_names_included"])
    def test_no_link_is_explicitly_not_linked(self):
        out=m.summarize(analysis())
        self.assertFalse(out["link_stage_proven"])
        self.assertEqual(out["linked_import_census"],"not_provided")
        self.assertNotIn("unresolved_linker_imports",out)
    def test_invalid_shapes_and_counts_fail_closed(self):
        a=analysis()
        for broken in (
            {**a,"import_count":"3"},
            {**a,"import_count":2},
            {**a,"imports":["a"]},
            {**a,"needed":None},
            {**a,"import_count":True},
        ):
            with self.subTest(broken=broken):
                with self.assertRaises(m.AbiReportError): m.summarize(broken)
        l=link()
        for broken in (
            {**l,"imports":2},
            {**l,"bindings":9},
            {**l,"bindings":True},
            {**l,"unresolved_imports":["x",5]},
            {**l,"modules":["secret"]},
        ):
            with self.subTest(broken=broken):
                with self.assertRaises(m.AbiReportError): m.summarize(a,broken)
    def test_unknown_symbol_format_does_not_leak(self):
        output=m.summarize(analysis(),{**link(),"unresolved_imports":["sensitive",
                       "SECRETPATH#WEIRD_LIB_VALUE","NID#libSceNetX#x"]})
        self.assertEqual(output["unresolved_by_host_library_class"],
                         {"other_host_library":1,"sce_network":1,"unknown_symbol_format":1})
        self.assertNotIn("sensitive",str(output))
        self.assertNotIn("SECRETPATH",str(output))
    def test_cli_does_not_modify_original_reports_or_reveal_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            a=root/"analysis.json"
            b=root/"link.json"
            output=root/"safe-aggregate.json"
            a.write_text(json.dumps(analysis()),encoding="utf-8")
            b.write_text(json.dumps(link()),encoding="utf-8")
            before=(a.read_bytes(),b.read_bytes())
            stdout=StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(m.main(["--analysis",str(a),"--link",str(b),
                                         "--output",str(output)]),0)
            self.assertTrue(output.is_file())
            aggregate=output.read_text()
            self.assertNotIn(str(root),aggregate)
            self.assertNotIn("PRIVATE_NID",aggregate)
            self.assertEqual((a.read_bytes(),b.read_bytes()),before)
            with redirect_stderr(StringIO()):
                self.assertEqual(m.main(["--analysis",str(a),"--link",str(b),
                                         "--output",str(output)]),2)
                self.assertEqual(m.main(["--analysis",str(a),"--link",str(b),
                                         "--output",str(a)]),2)
            self.assertEqual((a.read_bytes(),b.read_bytes()),before)
    def test_error_redaction_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"PRIVATE_REPORT.json"
            path.write_text("{bad JSON",encoding="utf-8")
            stderr=StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(m.main(["--analysis",str(path)]),2)
            self.assertNotIn("PRIVATE_REPORT",stderr.getvalue())
            self.assertNotIn(str(directory),stderr.getvalue())


if __name__=="__main__":
    unittest.main()
