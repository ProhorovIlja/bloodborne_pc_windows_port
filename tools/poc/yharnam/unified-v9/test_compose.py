#!/usr/bin/env python3
"""Offline integration fixtures: V5 and V3 alter one overlay; V7 uses the real socket anchors."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ARCHIVES=HERE.parent/"pinned-archives"
V8=HERE.parent/"release-v8/patch_update_channel.py"
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
v8=load(V8,"sh_v8")
compose=load(HERE/"compose_sources.py","sh_compose")

def originals():
    v3=compose.load_zip_module(ARCHIVES/compose.ARCHIVES["ui"],"PATCH-YHARNAM-TEAM-UI.py","sh_ui_test")
    v7=compose.load_zip_module(ARCHIVES/compose.ARCHIVES["direct"],"PATCH-BBPORT-NATIVE-DIRECT-V7.py","sh_direct_test")
    return {
        "server/coop/coop.proto": "    PROTOCOL_CURRENT = 7;\n        FORGET_WORLD = 11;\n    }\n    string world = 6;\n}\n\nmessage LobbyPlayer {\n    string party = 7;\n}\n\nmessage TeamInvite {\n",
        "server/coop/team_lobby.cpp": "    switch (request.action()) {\n    case Action::CREATE: {\n        team.set_leader(member);\n        bbcoop::TeamMember& m = *team.add_members();\n",
        "emulator/src/core/bloodborne_re_internal.h": "void TeamLobbyRequest(bbcoop::TeamRequest::Action action, const std::string& id);\n",
        "emulator/src/core/bloodborne_server_world.cpp": "std::string TeamLobbyMember() {\nvoid TeamLobbyRequest(bbcoop::TeamRequest::Action action, const std::string& id) {\n",
        "emulator/src/core/bloodborne_party_death.cpp": "void TickPartyDeath() {\n    if (!party_death_hook_installed) {\n",
        "bbport/gpu/bbcoop.h": "    bbcoop_lobby_world worlds[BBCOOP_LOBBY_WORLDS];\n} bbcoop_lobby;\nvoid bbcoop_lobby_request(int action, const char *id);\n",
        "bbport/gpu/bbcoop/coop.cpp": "        lobby->started = team.started();\nextern \"C\" void bbcoop_lobby_request(int action, const char* id) {\n",
        compose.OVERLAY: "\n".join([
            '#include "bbport_settings.h"',v3.OLD_SUBTITLE,
            'status = std::to_string(lobby.member_count) + T(" of 4", " из 4");',
            v3.OLD_HEADER,v3.OLD_CARD,
            '    if (lobby.leader) {\n        ImGui::PushFont(MenuArt::Font(), 19.0f);\n        const ImVec2 remove_size(S(170.0f), S(38.0f));',
        ]),
        compose.NETWORK: "\n".join([v7.INSERT_INCLUDE,v7.INSERT_SEND,v7.INSERT_RECEIVE,
                                    v7.INSERT_TICK,v7.INSERT_FIELD,v7.INSERT_RESET]),
        compose.COOP: """import re, json, urllib.request
RELEASES_API = 'https://api.github.com/repositories/1405692683/releases?per_page=100'
def newest_release(releases):
    for release in releases:
        version = release['tag_name'].lstrip('v')
        if not version_key(version)[0]:
            continue
        if not setup or not assets.get(setup + '.sha256'):
            continue
        return {'page': '',
                    'name': setup}
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
""",
        compose.LAUNCHER: """CONFIG=('bbport-launcher-coop' if COOP_TEST else 'bbport-launcher')
def fetch_update_release(beta=False):
    pass
""",
    }

class AllPatches(unittest.TestCase):
    def test_real_v3_v5_v7_v8_functions_combine(self):
        source=originals()
        result,manifest=compose.compose(source,ARCHIVES,v8)
        self.assertEqual(len(result),len(source)+5)
        self.assertIn(b'DirectSafeGameFrame',result['emulator/src/core/libraries/network/native_shlk_adapter.hpp'])
        self.assertIn(b'IsStaticallyDirectSafe',result['emulator/src/core/libraries/network/native_direct_filter.hpp'])
        for path,needle in [
            ("server/coop/coop.proto",b"PROTOCOL_CURRENT = 8"),
            ("server/coop/team_lobby.cpp",b"SET_DBNO"),
            (compose.OVERLAY,b"sh-scale-plus"),
            (compose.OVERLAY,b'"sh-dbno"'),
            (compose.NETWORK,b"native_direct.TryGame("),
            (compose.COOP,b"1429375055"),
        ]:
            self.assertIn(needle,result[path])
        self.assertFalse(manifest["public_release_ready"])
        self.assertEqual(set(manifest["sha256"]),set(result))
        self.assertEqual(source,originals())
    def test_missing_anchor_rejected(self):
        source=originals()
        source[compose.OVERLAY]=source[compose.OVERLAY].replace("The four places","not pinned")
        with self.assertRaises(ValueError):
            compose.compose(source,ARCHIVES,v8)
    def test_tampered_archive_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            newdir=Path(d)
            for filename in compose.ARCHIVES.values():
                shutil.copy2(ARCHIVES/filename,newdir/filename)
            bad=newdir/compose.ARCHIVES["direct"]
            bad.write_bytes(bad.read_bytes()+b"tampered")
            with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):
                compose.compose(originals(),newdir,v8)
    def test_wrong_source_commit_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            upstream=root/"upstream";upstream.mkdir()
            subprocess.run(["git","init","-q",str(upstream)],check=True)
            out=root/"out"
            with self.assertRaises(ValueError):
                compose.run(upstream,root,out)
            self.assertFalse(out.exists())
    def test_cannot_mutate_upstream(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);upstream=root/"upstream";upstream.mkdir()
            with self.assertRaises(ValueError):
                compose.run(upstream,root,upstream/"out")

if __name__=="__main__":
    unittest.main(verbosity=2)
