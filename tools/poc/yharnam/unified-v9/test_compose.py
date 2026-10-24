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
sys.path.insert(0, str(HERE.parent/"hunter-tools-v21"))
from test_patch_hunter_tools import EDITOR as SAVE_EDITOR_FIXTURE, HEADER as SAVE_HEADER_FIXTURE
sys.path.insert(0, str(HERE.parent/"server-trust-v22"))
from test_patch_server_trust import B as SERVER_BOARDS_FIXTURE, W as SERVER_WORLD_FIXTURE, H as SERVER_HEADER_FIXTURE
sys.path.insert(0, str(HERE.parent/"stream-bounds-v24"))
from test_patch_stream import SOURCE as STREAM_FIXTURE
sys.path.insert(0, str(HERE.parent/"member-identity-v25"))
from test_patch_identity import LINK as LINK_ID_FIXTURE
sys.path.insert(0, str(HERE.parent/"ingress-quota-v26"))
from test_patch_ingress_quota import W as QUOTA_WORLD_FIXTURE, H as QUOTA_HEADER_FIXTURE
sys.path.insert(0, str(HERE.parent/"endpoint-rebind-v27"))
from test_patch_rebind import SOURCE as LINK_REBIND_FIXTURE
sys.path.insert(0, str(HERE.parent/"login-admission-v28"))
from test_patch_login_admission import CPP as LOGIN_CPP_FIXTURE, HEADER as LOGIN_H_FIXTURE
sys.path.insert(0, str(HERE.parent/"rpc-budget-v29"))
from test_patch_rpc_budget import CPP as RPC_CPP_FIXTURE, H as RPC_H_FIXTURE
sys.path.insert(0, str(HERE.parent/"auth-revocation-v30"))
from test_patch_auth_revocation import DBH as AUTH_DB_H, DBC as AUTH_DB_CPP, ACCOUNT as AUTH_ACCOUNT_TEST
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
        compose.SAVE_EDITOR: SAVE_EDITOR_FIXTURE,
        compose.SAVE_EDITOR_H: SAVE_HEADER_FIXTURE,
        compose.SERVER_BOARDS: SERVER_BOARDS_FIXTURE,
        compose.SERVER_WORLD: SERVER_WORLD_FIXTURE + (
            '    // The same run saying hello again (a guest whose game took the session host\'s role: phase 7).\n'
            '    const bool arrived = member.lobby.empty();\n'
            '    for (const std::vector<u8>& message : messages) {\n'
            '        if (const auto envelope = DecodeEnvelope(message)) {\n'),
        compose.SERVER_WORLD_H: '#include "bloodborne_party_boards.h"\n' + SERVER_HEADER_FIXTURE,
        compose.COOP_STREAM: STREAM_FIXTURE,
        compose.SERVER_LINK_CPP: LINK_ID_FIXTURE.replace(
            '#include "server_link.h"',
            '#include "server_link.h"\n' + LOGIN_CPP_FIXTURE
        ) + '''    const bool again = members.contains(from.Key());
    Link& link = members[from.Key()];
''',
        compose.SERVER_LINK_H: LOGIN_H_FIXTURE +
            '        QList<Endpoint> gone; // links forgotten\n',
        compose.LINK_SERVER_CPP: RPC_CPP_FIXTURE.replace(
            '    m_signedIn.insert(online_id, hash);',
            '''    const auto known = m_signedIn.constFind(online_id);
    if (known != m_signedIn.constEnd())
        return *known == hash;
    const bool make = !m_shared->config || m_shared->config->IsMakingAccountsAtSignIn();
    if (!user)
        return false;
    m_signedIn.insert(online_id, hash);''') + (
            "    // Phase 7: a linked game's address for the rooms and signaling is its virtual one, known from\n"
            "    // its hello.\n"
            "    for (const auto& linked : result.linked) {\n"),
        compose.LINK_SERVER_H: RPC_H_FIXTURE +
            '\n    QHash<QByteArray, QByteArray> m_signedIn; // player id -> its secret\'s hash, once signed in\n',
        compose.DATABASE_H: AUTH_DB_H,
        compose.DATABASE_CPP: AUTH_DB_CPP,
        compose.ACCOUNT_TEST_CPP: AUTH_ACCOUNT_TEST,
        compose.SERVER_LINK_TEST: """int Relays() {
  if (Contracts() != 0 || HelloAndBuilds() != 0 || Relays() != 0 ||
""",
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
        "bbport/gpu/bbcoop.h": "    uint32_t vials, bullets; /* Kaniel 2026-10-18: beside the name */\n    bbcoop_lobby_world worlds[BBCOOP_LOBBY_WORLDS];\n} bbcoop_lobby;\nvoid bbcoop_lobby_request(int action, const char *id);\n",
        "bbport/gpu/bbcoop/coop.cpp": "        out.bullets = member.bullets;\n        lobby->started = team.started();\nextern \"C\" int bbcoop_lobby_view(bbcoop_lobby* lobby) {\nextern \"C\" void bbcoop_lobby_request(int action, const char* id) {\n",
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
            '        const auto& effect = BbSettings::Effects[e];',
            '        const char* hint =',
            '} // namespace Ui',
            '',
            'void Menu() {',
            '    const char* title = T("Settings", "Настройки");',
            'static const char* tab_en[] = {"Display", "Upscaler", "Game effects", "Controls", "Advanced", "Save"};',
            '"Дополнительно", "Сохранение"};',
            '    default: SaveTab(); break;',
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
        # New server files first enter output when their initial source patch runs.
        # Fixed counts from UI-only composition are no longer valid.
        self.assertGreater(len(result),len(source))
        self.assertTrue(set(compose.ARCHIVES).issuperset({"dbno","ui"}))
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
        self.assertIn(b'SH-HUNTER-TOOLS-V21',result[compose.OVERLAY])
        self.assertIn(b'HunterToolsTab();',result[compose.OVERLAY])
        self.assertIn(b'if (!CanEdit()) return;',result[compose.SAVE_EDITOR])
        self.assertIn(b'sh_hunter_tools_policy.hpp',result[compose.SAVE_EDITOR_H])
        self.assertIn(b'AllowLocalEdit',result['bbport/gpu/shim/sh_hunter_tools_policy.hpp'])
        self.assertIn(b'bbcoop_offline_character_edit_allowed',
                      result['bbport/gpu/bbcoop.h'])
        self.assertIn(b'Coop::SessionMembers() <= 1',
                      result['bbport/gpu/bbcoop/coop.cpp'])
        self.assertIn(b'players >= 0 && players <= 1',
                      result['bbport/gpu/bbcoop/coop.cpp'])
        self.assertIn(b'SH-SERVER-TRUST-V22',result[compose.SERVER_WORLD])
        self.assertIn(b'SafeReviveHits(',result[compose.SERVER_WORLD])
        self.assertIn(b'AddReviveDamage',result[compose.SERVER_BOARDS])
        self.assertIn(b'rejected_vitals = 0',result[compose.SERVER_WORLD_H])
        self.assertIn(b'SafeVitalValues',result['server/src/sh_session_guard.hpp'])
        self.assertIn(b'SH-STREAM-BOUNDS-V24',result[compose.COOP_STREAM])
        self.assertIn(b'partial.Push(',result[compose.COOP_STREAM])
        self.assertIn(b'MaxMessageBytes',result['server/coop/sh_message_bounds.hpp'])
        self.assertIn(b'SH-MEMBER-ID-V25',result[compose.SERVER_WORLD])
        self.assertIn(b'Identity::Matches(',result[compose.SERVER_WORLD])
        self.assertIn(b'StrictMode() && !sign_in',result[compose.SERVER_LINK_CPP])
        self.assertIn(b'constexpr bool Matches',result['server/src/sh_member_identity.hpp'])
        self.assertIn(b'SH-INGRESS-QUOTA-V26',result[compose.SERVER_WORLD])
        self.assertIn(b'ingress.Accept(',result[compose.SERVER_WORLD])
        self.assertIn(b'Ingress::Budget ingress',result[compose.SERVER_WORLD_H])
        self.assertIn(b'BurstMessages',result['server/src/sh_ingress_quota.hpp'])
        self.assertIn(b'SH-ENDPOINT-REBIND-V27',result[compose.SERVER_LINK_CPP])
        self.assertIn(b'LinkRebind::MustRetire',result[compose.SERVER_LINK_CPP])
        self.assertIn(b'constexpr bool MustRetire',result['server/src/sh_endpoint_rebind.hpp'])
        self.assertIn(b'retired_online_ids',result[compose.SERVER_LINK_H])
        self.assertIn(b'udpExt.remove(',result[compose.LINK_SERVER_CPP])
        self.assertIn(b'SH-LOGIN-ADMISSION-V28',result[compose.SERVER_LINK_CPP])
        self.assertIn(b'hello_admission.Allow(',result[compose.SERVER_LINK_CPP])
        self.assertIn(b'LoginAdmission::Gate hello_admission',result[compose.SERVER_LINK_H])
        self.assertIn(b'HelloAdmissionLimitsDbCalls()',result[compose.SERVER_LINK_TEST])
        self.assertIn(b'class Gate',result['server/src/sh_login_admission.hpp'])
        self.assertIn(b'blocked = true',result[compose.LINK_SERVER_CPP])
        self.assertIn(b'MustEvictAuthCache(',result[compose.LINK_SERVER_CPP])
        self.assertIn(b'bool blocked = false',result[compose.LINK_SERVER_H])
        self.assertIn(b'MaxBufferedRpcBytes',result['server/src/sh_rpc_budget.hpp'])
        self.assertIn(b'CurrentCredentialStatus',result[compose.DATABASE_H])
        self.assertIn(b'CurrentCredentialStatus',result[compose.DATABASE_CPP])
        self.assertIn(b'db_hash_at_signin',result[compose.LINK_SERVER_H])
        self.assertIn(b'if (!user || user->banned)',result[compose.LINK_SERVER_CPP])
        self.assertIn(b'RevokedDatabaseCredentialsAreVisible()',result[compose.ACCOUNT_TEST_CPP])
        self.assertIn(b'CanTrustCache',result['server/src/sh_auth_revocation.hpp'])
        self.assertIn(b'ChangedAccountOnSameEndpoint()',result[compose.SERVER_LINK_TEST])
        self.assertIn(b'retired_online_ids.size() == 1',result[compose.SERVER_LINK_TEST])
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
        self.assertIn("V21 offline-only unlocked Hunter Tools", " ".join(manifest["applied"]))
        self.assertIn("V22 server ingress vitals bounds", " ".join(manifest["applied"]))
        self.assertIn("V24 bounded co-op protobuf reassembly", " ".join(manifest["applied"]))
        self.assertIn("V25 opt-in signed-in identity binding", " ".join(manifest["applied"]))
        self.assertIn("V26 opt-in co-op ingress quotas", " ".join(manifest["applied"]))
        self.assertIn("V27 stale virtual-address cleanup", " ".join(manifest["applied"]))
        self.assertIn("V28 opt-in bounded pre-database Hello admission", " ".join(manifest["applied"]))
        self.assertIn("V29 bounded local RPC backpressure", " ".join(manifest["applied"]))
        self.assertIn("V30 live DB verification", " ".join(manifest["applied"]))
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
    def test_v21_changed_editor_anchor_refused(self):
        source=originals()
        source[compose.SAVE_EDITOR]=source[compose.SAVE_EDITOR].replace(
            "void SetEchoes(std::int32_t echoes) {", "void SetEchoes(int echoes) {")
        with self.assertRaisesRegex(ValueError,"echoes"):
            compose.compose(source,ARCHIVES,v8)
    def test_v22_invalid_server_ingress_anchor_refused(self):
        source=originals()
        source[compose.SERVER_WORLD]=source[compose.SERVER_WORLD].replace(
            "case bbcoop::Envelope::kVitals: {", "case bbcoop::Envelope::kVitals3: {")
        with self.assertRaisesRegex(ValueError,"vitals ingress"):
            compose.compose(source,ARCHIVES,v8)
    def test_v24_changed_stream_reassembly_refused(self):
        source=originals()
        source[compose.COOP_STREAM]=source[compose.COOP_STREAM].replace(
            "partial.insert(partial.end()", "partial.insert(partial.begin()")
        with self.assertRaisesRegex(ValueError,"bounded reassembly"):
            compose.compose(source,ARCHIVES,v8)
    def test_v25_mismatched_server_link_source_rejected(self):
        source=originals()
        source[compose.SERVER_LINK_CPP]=source[compose.SERVER_LINK_CPP].replace(
            'if (refusal.isEmpty() && sign_in && !sign_in', 'if (refusal.isEmpty() && !sign_in')
        with self.assertRaisesRegex(ValueError,"strict auth prerequisite"):
            compose.compose(source,ARCHIVES,v8)
    def test_v26_modified_decode_loop_anchor_refused(self):
        source=originals()
        source[compose.SERVER_WORLD]=source[compose.SERVER_WORLD].replace(
            "DecodeEnvelope(message)", "DecodeEnvelope(raw)")
        with self.assertRaisesRegex(ValueError,"pre-decode budget"):
            compose.compose(source,ARCHIVES,v8)
    def test_v27_old_network_identity_cleanup_anchor_refused(self):
        source=originals()
        source[compose.SERVER_LINK_CPP]=source[compose.SERVER_LINK_CPP].replace(
            "members.contains(from.Key())", "members.find(from.Key())")
        with self.assertRaisesRegex(ValueError,"identity-rebind cleanup"):
            compose.compose(source,ARCHIVES,v8)
    def test_v28_changed_login_gate_anchor_refused(self):
        source=originals()
        source[compose.SERVER_LINK_CPP]=source[compose.SERVER_LINK_CPP].replace(
            "const auto hello = DecodeHello(datagram);",
            "const auto hello = DecodeHello(payload);")
        with self.assertRaisesRegex(ValueError,"before SignIn"):
            compose.compose(source,ARCHIVES,v8)
    def test_v29_broken_rpc_buffer_anchor_rejected(self):
        source=originals()
        source[compose.LINK_SERVER_CPP]=source[compose.LINK_SERVER_CPP].replace(
            "end.pending.append(data)", "end.pending.push_back(data)")
        with self.assertRaisesRegex(ValueError,"bounded rpc data and socket write"):
            compose.compose(source,ARCHIVES,v8)
    def test_v30_changed_cached_auth_anchor_rejected(self):
        source=originals()
        source[compose.LINK_SERVER_H]=source[compose.LINK_SERVER_H].replace(
            "QHash<QByteArray, QByteArray> m_signedIn", "QMap<QByteArray, QByteArray> m_signedIn")
        with self.assertRaisesRegex(ValueError,"cached credential representation"):
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
