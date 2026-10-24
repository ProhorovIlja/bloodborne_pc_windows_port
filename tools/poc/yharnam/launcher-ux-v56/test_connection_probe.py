"""V57 TCP-only, user-triggered network diagnostic regression."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
def load(path, name):
    spec=importlib.util.spec_from_file_location(name, HERE/path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

v56=load("patch_onboarding.py", "shyt_v56_onboarding_test")
v57=load("patch_connection_probe.py", "shyt_v57_probe_test")
SOURCE=(HERE/"pinned_coop_onboarding_fixture.py").read_text("utf-8")


class FakeCoop:
    def __init__(self):
        self.calls=[]
    def shyt_remote_ports(self, install, ip):
        self.calls.append(("profile",install,ip))
        return {"backend_tcp_port":21443, "webapi_tcp_port":32315}
    def port_open(self, port, ip, timeout=0.3):
        self.calls.append(("tcp",port,ip,timeout))
        return port==21443


class ProbeTests(unittest.TestCase):
    def test_compose_real_launcher_popup_and_compile(self):
        result=v57.transform(v56.transform(SOURCE))
        compile(result,"pinned-blauncher-v57.py","exec")
        for required in (
            "SHYT_LAUNCHER_TCP_DIAG_V57",
            "self.coop_probe_button",
            "self.coop_probe_line",
            "self.coop_probe_server",
            "shyt_tcp_backend_probe(bbport_coop, PORT_DIR, ip)",
            "Server changed. Test again.",
            "UDP matchmaking and Direct P2P not tested.",
            "self.coop_import_saves",
        ):
            self.assertIn(required,result)
        self.assertNotIn("password_entry",result)

    def test_bounded_tcp_probe_respects_staging_ports_and_no_credentials(self):
        mod={}
        exec(v57.HELPER,mod)
        fake=FakeCoop()
        self.assertEqual(mod["shyt_tcp_backend_probe"](fake,"/install","198.51.100.4"),
                         (True,False))
        self.assertEqual(fake.calls,[
            ("profile","/install","198.51.100.4"),
            ("tcp",21443,"198.51.100.4",1.0),
            ("tcp",32315,"198.51.100.4",1.0),
        ])
        self.assertNotIn("password",v57.HELPER.lower())
        self.assertNotIn("token",v57.HELPER.lower())

    def test_no_second_application_or_missing_v56(self):
        with self.assertRaisesRegex(ValueError, "must follow V56"):
            v57.transform(SOURCE)
        first=v57.transform(v56.transform(SOURCE))
        with self.assertRaisesRegex(ValueError, "already present"):
            v57.transform(first)
        with self.assertRaisesRegex(ValueError,"source drift"):
            v57.transform(v56.transform(SOURCE).replace(
                "def coop_changed(self):",
                "def moved_changed(self):"))

if __name__=="__main__":
    unittest.main()
