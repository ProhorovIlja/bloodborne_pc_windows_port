#!/usr/bin/env python3
"""Offline integration fixtures: V5 and V3 alter one overlay; V7 uses the real socket anchors."""
import importlib.util
from pathlib import Path
import shutil
import sys
import subprocess
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ARCHIVES=HERE.parent/"pinned-archives"
V8=HERE.parent/"release-v8/patch_update_channel.py"
sys.path.insert(0, str(HERE.parent/"map-safety-v16"))
from test_patch_map import SOURCE as MAP_FIXTURE
sys.path.insert(0, str(HERE.parent/"gc-safety-v17"))
from test_patch_texture_gc import SOURCE as GC_FIXTURE
sys.path.insert(0, str(HERE.parent/"map-cache-v18"))
from test_patch_chart_cache import SOURCE as CHART_CACHE_FIXTURE
sys.path.insert(0, str(HERE.parent/"map-data-v19"))
from test_patch_map_data import SOURCE as MAP_DATA_FIXTURE
sys.path.insert(0, str(HERE.parent/"map-range-v20"))
from test_patch_map_range import SOURCE as MAP_RANGE_FIXTURE
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
        compose.MAP3D: MAP_FIXTURE,
        compose.TEXTURE_GC: GC_FIXTURE,
        compose.MAPCHARTS: CHART_CACHE_FIXTURE.replace(
            '#include "bbport_settings.h"', MAP_RANGE_FIXTURE),
        compose.MAPART: MAP_DATA_FIXTURE,
        "server/coop/coop.proto": "    PROTOCOL_CURRENT = 7;\n        FORGET_WORLD = 11;\n    }\n    string world = 6;\n}\n\nmessage LobbyPlayer {\n    string party = 7;\n}\n\nmessage TeamInvite {\n",
        "server/coop/team_lobby.cpp": "    switch (request.action()) {\n    case Action::CREATE: {\n        team.set_leader(member);\n        bbcoop::TeamMember& m = *team.add_members();\n",
        "emulator/src/core/bloodborne_re_internal.h": "void TeamLobbyRequest(bbcoop::TeamRequest::Action action, const std::string& id);\n",
        "emulator/src/core/bloodborne_server_world.cpp": """#include "core/bloodborne_team.h"
TeamGate team_gate;
        if (decision.step == TeamGate::Step::Hold) {
            return true;
        }
void TeamChoose(TeamGate::Choice choice) {
    std::scoped_lock lock{team_mutex};
void TeamBackAtTitle() {
    if (!team_switch) {
    if (lobby_playing || team_gate.Holding()) {
        team_gate.Reset();
std::optional<bbcoop::LobbyState> TeamLobbyState() {
std::string TeamLobbyMember() {
void TeamLobbyRequest(bbcoop::TeamRequest::Action action, const std::string& id) {
""",
        "emulator/src/core/bloodborne_party_death.cpp": "void TickPartyDeath() {\n    if (!party_death_hook_installed) {\n",
        "bbport/gpu/bbcoop.h": "    bbcoop_lobby_world worlds[BBCOOP_LOBBY_WORLDS];\n} bbcoop_lobby;\nvoid bbcoop_lobby_request(int action, const char *id);\n",
        "bbport/gpu/bbcoop/coop.cpp": "        lobby->started = team.started();\nextern \"C\" int bbcoop_lobby_view(bbcoop_lobby* lobby) {\nextern \"C\" void bbcoop_lobby_request(int action, const char* id) {\n",
        compose.OVERLAY: "\n".join([
            '#include "bbport_settings.h"',v3.OLD_SUBTITLE,
            'status = std::to_string(lobby.member_count) + T(" of 4", " из 4");',
            v3.OLD_HEADER,v3.OLD_CARD,
            '    if (lobby.leader) {\n        ImGui::PushFont(MenuArt::Font(), 19.0f);\n        const ImVec2 remove_size(S(170.0f), S(38.0f));',
            '        bbcoop_team_choose(lobby.in_team ? BBCOOP_TEAM_GO_START : BBCOOP_TEAM_GO_ALONE);',
            '} // namespace Party',
            '',
            '/// Kaniel 2026-10-17: the teammate compass',
            '    if (Party::shown && !menu_open) {',
            '        Party::game = {float(game.offset.x), float(game.offset.y), float(game.extent.width),',
            '                       float(game.extent.height)};',
            '        Party::Draw();',
            '    }',
            "// Hold L3 + R3, or the menu's Quit row:",
            '        const bool down = event.type == SDL_EVENT_KEY_DOWN;',
            '        // bbport: numpad 0',
            'if (Team::open && !menu_open) {',
            '        Team::Screen();',
            'return initialized && (menu_open || quit_open || prompt_active || BbSettings::Get().show_fps || party || compass ||',
            '    if (BbSettings::Get().show_fps && !menu_open) {',
            '        FpsCounter();',
            '    }',
        ]),
        "bbport/src/runtime_camhook.c": """static float *field(unsigned char *camera, unsigned offset) { return (float *)(camera+offset); }
static float camhook_frame(unsigned char *camera,float pitch) {
    return pitch;
}

#ifdef _WIN32
""",
        "bbport/src/runtime_pad.c": 'if (!kbm.mouse_camera) { puts("Runtime: Mouse camera: off (mouse_camera=0)"); return; }',
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
        self.assertEqual(len(result),len(source)+10)  # V18 and V20 add two policy headers
        self.assertIn(b'DirectSafeGameFrame',result['emulator/src/core/libraries/network/native_shlk_adapter.hpp'])
        self.assertIn(b'IsStaticallyDirectSafe',result['emulator/src/core/libraries/network/native_direct_filter.hpp'])
        self.assertIn(b'sh-resume-mode',result[compose.OVERLAY])
        self.assertIn(b'ShResumeMode()',result['emulator/src/core/bloodborne_server_world.cpp'])
        self.assertIn(b'SeamlessHunt::Resume::Mode',result['emulator/src/core/last_session_policy.hpp'])
        self.assertIn(b'sh_spectator_frame(camera)',result['bbport/src/runtime_camhook.c'])
        self.assertIn(b'runtime_camhook_spectator',result[compose.OVERLAY])
        self.assertIn(b'sh-quit-desktop',result[compose.OVERLAY])
        self.assertIn(b'ShPerformance::Draw',result[compose.OVERLAY])
        self.assertIn(b'class Watch',result['bbport/gpu/shim/sh_perf_watch.hpp'])
        self.assertIn(b'SH-MAP-V16',result[compose.MAP3D])
        self.assertIn(b'texture != VK_NULL_HANDLE',result[compose.MAP3D])
        self.assertIn(b'SH-GC-V17',result[compose.TEXTURE_GC])
        self.assertIn(b'image.binding.is_bound',result[compose.TEXTURE_GC])
        self.assertIn(b'SH_GC_RECLAIM_DEPTH',result[compose.TEXTURE_GC])
        self.assertIn(b'SH-MAP-CACHE-V18',result[compose.MAPCHARTS])
        self.assertIn(b'SH-MAP-RANGE-V20',result[compose.MAPCHARTS])
        self.assertIn(b'MaxRangeBytes',result['bbport/gpu/shim/sh_map_range_io.hpp'])
        self.assertIn(b'std::jthread worker;',result[compose.MAPCHARTS])
        self.assertIn(b'class Budget',result['bbport/gpu/shim/sh_map_cache.hpp'])
        self.assertIn(b'SH-MAP-DATA-V19',result[compose.MAPART])
        self.assertIn(b'MaxFloorCells',result[compose.MAPART])
        self.assertIn(b'vmaDestroyBuffer(allocator, out.buffer, out.allocation);',result[compose.MAP3D])
        self.assertIn(b'SeamlessHunt::Spectate::State',result['bbport/gpu/shim/spectator_policy.hpp'])
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
        self.assertIn("V16 defensive Vulkan map allocation", " ".join(manifest["applied"]))
        self.assertIn("V17 active GPU resource GC protection", " ".join(manifest["applied"]))
        self.assertIn("V18 bounded CPU map cache", " ".join(manifest["applied"]))
        self.assertIn("V19 bounded compressed map/mesh decoding", " ".join(manifest["applied"]))
        self.assertIn("V20 bounded and exact game archive", " ".join(manifest["applied"]))
        self.assertEqual(set(manifest["sha256"]),set(result))
        self.assertEqual(source,originals())
    def test_missing_anchor_rejected(self):
        source=originals()
        source[compose.OVERLAY]=source[compose.OVERLAY].replace("The four places","not pinned")
        with self.assertRaises(ValueError):
            compose.compose(source,ARCHIVES,v8)
    def test_v16_source_anchor_drift_refused(self):
        source=originals()
        source[compose.MAP3D]=source[compose.MAP3D].replace("info.pMappedData == nullptr",
                                                              "info.pMappedData == NULL",1)
        with self.assertRaisesRegex(ValueError,"VMA buffers"):
            compose.compose(source,ARCHIVES,v8)
    def test_v17_source_anchor_drift_refused(self):
        source=originals()
        source[compose.TEXTURE_GC]=source[compose.TEXTURE_GC].replace("const auto image_id",
                                                                           "auto image_id",1)
        with self.assertRaisesRegex(ValueError,"anchor drift"):
            compose.compose(source,ARCHIVES,v8)
    def test_v18_changed_worker_rejected(self):
        source=originals()
        source[compose.MAPCHARTS]=source[compose.MAPCHARTS].replace(
            "std::condition_variable wake;", "std::condition_variable wakeX;")
        with self.assertRaisesRegex(ValueError,"stop-aware condition"):
            compose.compose(source,ARCHIVES,v8)
    def test_v19_invalid_cache_parser_anchor_refused(self):
        source=originals()
        source[compose.MAPART]=source[compose.MAPART].replace(
            'raw_size > (1u << 31)', 'raw_size > 100000000')
        with self.assertRaisesRegex(ValueError,"mesh decompression bound"):
            compose.compose(source,ARCHIVES,v8)
    def test_v20_invalid_range_reader_anchor_refused(self):
        source=originals()
        source[compose.MAPCHARTS]=source[compose.MAPCHARTS].replace(
            'std::vector<std::uint8_t> bytes(size);', 'std::vector<std::uint8_t> bytes(len);', 1)
        with self.assertRaisesRegex(ValueError,"runtime game archive read"):
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
