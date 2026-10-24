import unittest
from patch_hunter_tools import overlay,editor,editor_header,coop_header,coop_impl

UI='''        const auto& effect = BbSettings::Effects[e];
        const char* hint =
} // namespace Ui

void Menu() {
    const char* title = T("Settings", "Настройки");
static const char* tab_en[] = {"Display", "Upscaler", "Game effects", "Controls", "Advanced", "Save"};
"Дополнительно", "Сохранение"};
    default: SaveTab(); break;
'''
HEADER='''#include <vector>
    std::int32_t level = now.level;
    for (int i = 0; i < AttributeCount; ++i) {
        level += attributes[i] - now.attributes[i];
    }
    return level < 1 ? 1 : level;
void SetEchoes(std::int32_t echoes);'''
EDITOR='''#include <cstdio>
u64 image_base = 0;
void SetImage(unsigned char* image) {
    image_base = reinterpret_cast<u64>(image);
}
void SetEchoes(std::int32_t echoes) {
    Queue([echoes] {
void SetInsight(std::int32_t insight) {
    Queue([insight] {
void CommitStats(std::array<std::int32_t, AttributeCount> wanted, std::int32_t hp_max_before,
                 std::int32_t vitality_before, int tries) {
    const auto now = Read();
void SetAttributes(const std::int32_t attributes[AttributeCount]) {
    std::array<std::int32_t, AttributeCount> wanted;
    Queue([wanted] {
        const auto now = Read();
void GiveItem(std::uint32_t category, std::uint32_t id, std::int32_t quantity) {
    Queue([category, id, quantity] {
    if (!InWorld()) {
        return; // dropped: the character is not there (title screen, loading)
    }
    for (auto& job : jobs) {
'''
class Tests(unittest.TestCase):
    def test_cheats_no_longer_mixed_with_graphics(self):
        result=overlay(UI)
        self.assertIn('if (std::string_view(effect.key).starts_with("cheat_")) continue;',result)
        self.assertIn('HunterToolsTab();',result)
        self.assertIn('state.tab == 5',result)
        self.assertIn('SaveTab();',result)
        self.assertIn('Unlock for this session',result)
        self.assertIn('bbcoop_offline_character_edit_allowed()',result)
    def test_backend_lock_at_enqueue_and_dispatch(self):
        s=editor(EDITOR)
        self.assertIn('editor_unlocked.store(false)',s)
        self.assertIn('OnlineSessionActive()',s)
        self.assertIn('bbcoop_offline_character_edit_allowed()',s)
        self.assertIn('!InWorld() || !CanEdit()',s)
        self.assertGreaterEqual(s.count('if (!CanEdit()) return;'),6)
        self.assertIn('!CanEdit() || !attributes',s)
        self.assertIn('quantity < 1 || quantity > 99',s)
        self.assertIn('category != GoodsCategory',s)
    def test_legacy_coop_runtime_guard(self):
        header=coop_header('void bbcoop_lobby_request(int action, const char *id);')
        impl=coop_impl('extern "C" int bbcoop_lobby_view(bbcoop_lobby* lobby) {')
        self.assertIn('int bbcoop_offline_character_edit_allowed(void);',header)
        for term in ['Coop::TeamLobbyState()', 'lobby && lobby->has_team()',
                     'Coop::TeamPlaying(&in_hunt)', 'Coop::InPartySession()',
                     'Coop::SessionMembers() <= 1','players >= 0 && players <= 1']:
            self.assertIn(term,impl)
        with self.assertRaisesRegex(ValueError,'coop runtime bridge'):
            coop_impl('unrecognized legacy server build')
        with self.assertRaisesRegex(ValueError,'already applied'):
            coop_impl(impl)
    def test_level_overflow_guard(self):
        s=editor_header(HEADER)
        self.assertIn('#include "sh_hunter_tools_policy.hpp"',s)
        self.assertIn('SeamlessHunt::HunterTools::LevelAfter',s)
    def test_drift_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"menu routing"):
            overlay(UI.replace('default: SaveTab();','default: FakeTab();'))
        with self.assertRaisesRegex(ValueError,"stats level arithmetic"):
            editor_header(HEADER.replace('level += attributes[i]', 'level -= attributes[i]'))
    def test_double_apply_rejected(self):
        with self.assertRaisesRegex(ValueError,"already applied"):
            overlay(overlay(UI))
        with self.assertRaisesRegex(ValueError,"already applied"):
            editor(editor(EDITOR))
        with self.assertRaisesRegex(ValueError,"already applied"):
            editor_header(editor_header(HEADER))

if __name__=='__main__': unittest.main()
