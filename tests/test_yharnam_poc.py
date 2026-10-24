"""Game-free tests of isolated Yharnam Together staging utilities."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]/'tools'/'yharnam_poc'

def load(name, filename):
    spec=importlib.util.spec_from_file_location(name, ROOT/filename)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

stage=load('yt_stage','prepare_staging.py')
patch=load('yt_patch','patch_launcher_ports.py')

class TestIsolatedYharnamPoC(unittest.TestCase):
    def test_port_isolation(self):
        self.assertFalse(set(stage.PORTS.values()) & stage.PROD)
        self.assertEqual(stage.PORTS['udp'], 32314)

    def test_reject_wrong_git_revision(self):
        with tempfile.TemporaryDirectory() as d:
            checkout=Path(d)/'checkout'
            (checkout/'server'/'coop').mkdir(parents=True)
            (checkout/'server'/'coop'/'team_lobby.h').write_text('fixture')
            subprocess.run(['git','init','-q',str(checkout)],check=True)
            subprocess.run(['git','-C',str(checkout),'config','user.email','test@example.org'],check=True)
            subprocess.run(['git','-C',str(checkout),'config','user.name','Test'],check=True)
            subprocess.run(['git','-C',str(checkout),'add','.'],check=True)
            subprocess.run(['git','-C',str(checkout),'commit','-qm','fixture'],check=True)
            with self.assertRaisesRegex(ValueError,'revision'):
                stage.ensure_stage(Path(d)/'output',checkout,None)

    def test_local_stage_isolated(self):
        with tempfile.TemporaryDirectory() as d:
            checkout=Path(d)/'checkout'
            (checkout/'server'/'coop').mkdir(parents=True)
            (checkout/'server'/'coop'/'team_lobby.h').write_text('fixture')
            (checkout/'server'/'worlds.cfg').write_text('world fixture')
            (checkout/'server'/'scoreboards.cfg').write_text('score fixture')
            target=Path(d)/'stage'
            with mock.patch.object(stage,'ensure_stage',return_value=(target,stage.PIN)):
                m=stage.stage_server(checkout,target,'127.0.0.1','')
            self.assertTrue(m['staging_only'])
            self.assertFalse(m['binary_staged'])
            cfg=(target/'state'/'shadnet.cfg').read_text()
            self.assertIn('Host=127.0.0.1',cfg)
            self.assertIn('MatchingUdpPort=32314',cfg)
            self.assertIn('TcpLocalOnly=true',cfg)
            self.assertIn('MakeAccountsAtSignIn=true',cfg)
            self.assertFalse((target/'bin'/'shadnet').exists())

    def test_reject_invalid_bind(self):
        with tempfile.TemporaryDirectory() as d:
            c=Path(d)/'checkout'
            with mock.patch.object(stage,'ensure_stage',return_value=(Path(d)/'stage',stage.PIN)):
                with self.assertRaises(ValueError):
                    stage.stage_server(c,Path(d)/'stage','999.0.0.1','')

    def test_launcher_patch_defaults_and_overrides(self):
        original='import os\n'+patch.SOURCE_LINE+'\n'
        patched,changed=patch.patch_content(original)
        self.assertTrue(changed)
        self.assertFalse(patch.patch_content(patched)[1])
        with mock.patch.dict('os.environ',{},clear=True):
            ns={}
            exec(compile(patched,'fixture','exec'),ns)
            self.assertEqual((ns['SHADNET_PORT'],ns['WEBAPI_PORT'],ns['MATCHING_PORT'],ns['BACKEND_PORT']),patch.PROD)
        with mock.patch.dict('os.environ',{'SH_YT_TCP_PORT':'32313','SH_YT_WEBAPI_PORT':'32315',
                                           'SH_YT_UDP_PORT':'32314','SH_YT_BACKEND_PORT':'21443'}):
            ns={}
            exec(compile(patched,'fixture','exec'),ns)
            self.assertEqual((ns['SHADNET_PORT'],ns['WEBAPI_PORT'],ns['MATCHING_PORT'],ns['BACKEND_PORT']),
                             (32313,32315,32314,21443))

    def test_invalid_staging_port(self):
        text='import os\n'+patch.SOURCE_LINE+'\n'
        code=patch.patch_content(text)[0]
        with mock.patch.dict('os.environ',{'SH_YT_UDP_PORT':'invalid'}):
            with self.assertRaises(ValueError):
                exec(compile(code,'fixture','exec'),{})

if __name__=='__main__':
    unittest.main()
