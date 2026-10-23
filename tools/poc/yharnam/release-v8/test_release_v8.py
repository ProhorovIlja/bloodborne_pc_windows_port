import hashlib, importlib.util, json, pathlib, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parent
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+".py"))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
p=load("patch_update_channel")
g=load("release_gate")
class Tests(unittest.TestCase):
    def test_updater_from_original_anchors(self):
        source="""import re, json, urllib.request
RELEASES_API = 'https://api.github.com/repositories/1405692683/releases?per_page=100'
def newest_release(releases):
    for release in releases:
        version = release['tag_name'].lstrip('v')
        if not version_key(version)[0]:
            continue
        if not setup or not assets.get(setup + '.sha256'):
            continue
        return {'page':'', 'name': setup}
def release_notes(releases):
    for release in releases:
        version = release['tag_name'].lstrip('v')
        if not version_key(version)[0]:
            continue
def fetch_newest_release(timeout=15):
    return newest_release(fetch_releases(timeout))
def download_update(release):
    if digest.hexdigest() != want:
        return None
"""
        changed=p.patch_coop(source)
        self.assertIn("repositories/1429375055/releases",changed)
        self.assertEqual(changed.count("startswith(SH_RELEASE_PREFIX)"),2)
        self.assertIn("sh_compatibility_release(newest_release(",changed)
        self.assertIn("meta.get('server_deployed')",changed)
        self.assertIn("channel_manifest",changed)
        with self.assertRaises(ValueError):p.patch_coop(changed)
    def test_launcher_updates_are_separate(self):
        source="import sys\np=('bbport-launcher-coop' if COOP_TEST else 'bbport-launcher')\ndef fetch_update_release(beta=False):\n    pass\n"
        changed=p.patch_launcher(source)
        self.assertIn("bbport-launcher-coop-seamlesshunt",changed)
        self.assertIn("upstream native engine updates disabled",changed)
        with self.assertRaises(ValueError):p.patch_launcher(changed)
    def test_release_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            d=pathlib.Path(d)
            a=d/"SeamlessHunt-v1.0.0-setup.exe";b=d/"shadnet"
            a.write_bytes(b"not a real client");b.write_bytes(b"not a real server")
            proof={"source_sha":g.PIN,"client_protocol":8,"server_protocol":8,
                   "link_protocol":2,"installer_sha256":g.sha(a),"server_sha256":g.sha(b),
                   "checks":{}}
            with self.assertRaisesRegex(ValueError,"missing passed"):
                g.contract("1.0.0",a,b,proof)
            proof["checks"]={key:True for key in g.CHECKS}
            self.assertEqual(g.contract("1.0.0",a,b,proof)["release_tag"],"shyt-v1.0.0")
            proof["server_protocol"]=7
            with self.assertRaisesRegex(ValueError,"wrong source or protocol"):
                g.contract("1.0.0",a,b,proof)
            proof["server_protocol"]=8
            b.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError,"digest mismatch"):
                g.contract("1.0.0",a,b,proof)
if __name__=="__main__":
    unittest.main()
