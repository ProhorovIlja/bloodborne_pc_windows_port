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


    def test_ui_recovers_after_worker_error_and_thread_start_failure(self):
        # Execute the real injected method without opening Tk or making sockets.
        import ast
        import queue
        import types

        patched = v57.transform(v56.transform(SOURCE))
        defs = [node for node in ast.walk(ast.parse(patched))
                if isinstance(node, ast.FunctionDef)
                and node.name == "coop_probe_server"]
        self.assertEqual(len(defs), 1)
        method = ast.fix_missing_locations(
            ast.Module(body=[defs[0]], type_ignores=[]))

        class Widget:
            def __init__(self):
                self.state = {}
            def configure(self, **kwargs):
                self.state.update(kwargs)
            def get(self):
                return "198.51.100.4"

        class BrokenCoop:
            def valid_ip(self, ip):
                return True
            def shyt_remote_ports(self, install, ip):
                raise RuntimeError("private local path must not appear")

        class SynchronousThread:
            def __init__(self, target, daemon):
                self.target = target
            def start(self):
                self.target()

        class NoThread(SynchronousThread):
            def start(self):
                raise RuntimeError("worker creation failed")

        def make_self():
            return types.SimpleNamespace(
                coop_probe_pending=False,
                coop_probe_button=Widget(),
                coop_probe_line=Widget(),
                coop_vars={"host_ip": Widget()},
                ui_calls=queue.Queue(),
            )

        base = {
            "bbport_coop": BrokenCoop(),
            "PORT_DIR": "/private/installation",
            "_": lambda en, ru: en,
            "OK": "green",
            "CAUTION": "orange",
            "MUTED": "gray",
            "shyt_tcp_backend_probe": lambda *a: (_ for _ in ()).throw(
                RuntimeError("private diagnostic failure")),
        }
        for thread_type in (SynchronousThread, NoThread):
            env = dict(base, threading=types.SimpleNamespace(Thread=thread_type))
            exec(compile(method, "injected_coop_probe_server.py", "exec"), env)
            gui = make_self()
            env["coop_probe_server"](gui)
            if thread_type is SynchronousThread:
                gui.ui_calls.get_nowait()()
            self.assertFalse(gui.coop_probe_pending)
            self.assertEqual(gui.coop_probe_button.state.get("state"), "normal")
            self.assertNotIn("private", gui.coop_probe_line.state["text"])
            self.assertEqual(gui.coop_probe_line.state.get("fg"), "orange")

if __name__=="__main__":
    unittest.main()
