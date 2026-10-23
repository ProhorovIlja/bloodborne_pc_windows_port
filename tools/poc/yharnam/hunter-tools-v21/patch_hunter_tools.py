#!/usr/bin/env python3
"""V21: put cheats and save editing in one locked Hunter Tools page.

UI-only host settings would not enforce anything. Actual save editor writes
are guarded separately on the game's execution thread.
"""
from pathlib import Path
OVERLAY="bbport/gpu/shim/bbport_overlay.cpp"
EDITOR="bbport/gpu/shim/bbport_save_editor.cpp"
HEADER="bbport/gpu/shim/bbport_save_editor.h"
COOP_API="bbport/gpu/bbcoop.h"
COOP_IMPL="bbport/gpu/bbcoop/coop.cpp"

def one(s,old,new,label):
    n=s.count(old)
    if n!=1:
        raise ValueError(f"V21 {label}: expected 1 anchor, found {n}")
    return s.replace(old,new,1)

def overlay(s):
    if "SH-HUNTER-TOOLS-V21" in s:
        raise ValueError("V21 overlay already applied")
    s=one(s,
      '''        const auto& effect = BbSettings::Effects[e];
        const char* hint =''',
      '''        const auto& effect = BbSettings::Effects[e];
        // Character cheats have their own opt-in page, not graphics settings.
        if (std::string_view(effect.key).starts_with("cheat_")) continue;
        const char* hint =''',"move game cheats out of effects")
    s=one(s,
      '''} // namespace Ui

void Menu() {''',
      '''// SH-HUNTER-TOOLS-V21: voluntary, offline-only character changes.
void HunterToolsTab() {
    if (!bbcoop_offline_character_edit_allowed()) {
        BbSaveEditor::SetEditorUnlocked(false);
        Note(T("Hunter Tools are locked in co-op. Previously enabled startup cheats "
               "can remain active until you restart the game. Disable them offline "
               "and restart before joining others.",
               "Инструменты заблокированы в кооперативе. Ранее включённые читы "
               "могут работать до перезапуска. Отключите их офлайн и "
               "перезапустите игру перед подключением к другим."),
             Dim());
        return;
    }
    if (!BbSaveEditor::Read()) {
        Note(T("Load a character before using Hunter Tools.",
               "Сначала загрузите персонажа для инструментов охотника."), Dim());
        return;
    }
    if (!BbSaveEditor::CanEdit()) {
        Note(T("Locked until explicitly enabled. These edits change your save "
               "and can affect game balance. Back up the character first.",
               "Инструменты заблокированы. Изменения затронут сохранение и баланс. "
               "Сначала сделайте резервную копию персонажа."),
             Dim());
        if (Row("hunter_unlock", T("Unlock for this session", "Разблокировать до выхода"),
                nullptr, T("Only available with co-op mode off. Never saves the unlock flag.",
                           "Только без кооператива. Разблокировка не сохраняется."), true)) {
            BbSaveEditor::SetEditorUnlocked(true);
        }
        return;
    }
    if (Row("hunter_lock", T("Lock Hunter Tools", "Заблокировать инструменты"),
            nullptr, nullptr, true)) {
        BbSaveEditor::SetEditorUnlocked(false);
        return;
    }
    Note(T("Gameplay cheats (restart required)", "Игровые читы (нужен перезапуск)"), Dim());
    auto& options = BbSettings::Get();
    for (int e = 0; e < BbSettings::EffectCount; ++e) {
        const auto& effect = BbSettings::Effects[e];
        if (!std::string_view(effect.key).starts_with("cheat_")) continue;
        Toggle(effect.key, T(effect.label, effect.label_ru), options.effects[e],
               T("Offline only. The game patch takes effect on restart; existing active "
                 "cheats can remain until restart. Not a host permission.",
                 "Только офлайн. Патч применяется после перезапуска; уже активный чит "
                 "может остаться до перезапуска. Это не разрешение хоста."));
    }
    ImGui::Spacing();
    Note(T("Character editor: echoes, insight, attributes, inventory",
           "Редактор персонажа: отголоски, озарение, характеристики, предметы"), Dim());
    SaveTab();
}

} // namespace Ui

void Menu() {''',"separate Hunter Tools page")
    s=one(s,
      '''static const char* tab_en[] = {"Display", "Upscaler", "Game effects", "Controls", "Advanced", "Save"};''',
      '''static const char* tab_en[] = {"Display", "Upscaler", "Game effects", "Controls", "Advanced", "Hunter Tools"};''',"English tab label")
    s=one(s,
      '''"Дополнительно", "Сохранение"};''',
      '''"Дополнительно", "Инструменты"};''',"Russian tab label")
    s=one(s,
      '''    const char* title = T("Settings", "Настройки");''',
      '''    const char* title = state.tab == 5
        ? T("Hunter Tools", "Инструменты охотника")
        : T("Settings", "Настройки");''',"separate tools page title")
    s=one(s,
      '''    default: SaveTab(); break;''',
      '''    default: HunterToolsTab(); break;''',"menu routing")
    return s

def editor_header(s):
    if "SH-HUNTER-TOOLS-V21" in s: raise ValueError("V21 editor header already applied")
    s=one(s,
      '''#include <vector>''',
      '''#include <vector>
#include "sh_hunter_tools_policy.hpp"''',"policy include")
    s=one(s,
      '''void SetEchoes(std::int32_t echoes);''',
      '''// SH-HUNTER-TOOLS-V21: local offline save-editor gate; not host security.
bool CanEdit();
void SetEditorUnlocked(bool enabled);
void SetEchoes(std::int32_t echoes);''',"header API")
    s=one(s,
      '''    std::int32_t level = now.level;
    for (int i = 0; i < AttributeCount; ++i) {
        level += attributes[i] - now.attributes[i];
    }
    return level < 1 ? 1 : level;''',
      '''    return SeamlessHunt::HunterTools::LevelAfter(now.level, now.attributes,
                                                   attributes, AttributeCount);''',"stats level arithmetic")
    return s

def editor(s):
    if "SH-HUNTER-TOOLS-V21" in s: raise ValueError("V21 editor already applied")
    s=one(s,'''#include <cstdio>''','''#include <atomic>
#include <cstdio>''',"atomic")
    s=one(s,'''u64 image_base = 0;''','''u64 image_base = 0;
// SH-HUNTER-TOOLS-V21: fail closed and clear on entering any supported co-op
// team mode. The unlock is deliberately never persisted to disk.
std::atomic<bool> editor_unlocked{false};
bool OnlineSessionActive() {
    return bbcoop_offline_character_edit_allowed() == 0;
}''',"session gate")
    s=one(s,
      '''void SetImage(unsigned char* image) {
    image_base = reinterpret_cast<u64>(image);
}''',
      '''void SetImage(unsigned char* image) {
    image_base = reinterpret_cast<u64>(image);
    editor_unlocked.store(false);
}
bool CanEdit() {
    if (OnlineSessionActive()) {
        editor_unlocked.store(false);
        return false;
    }
    return SeamlessHunt::HunterTools::AllowLocalEdit(
        InWorld(), false, editor_unlocked.load());
}
void SetEditorUnlocked(bool enabled) {
    editor_unlocked.store(SeamlessHunt::HunterTools::AllowLocalEdit(
        InWorld(), OnlineSessionActive(), enabled));
}''',"public guard API")
    # Both at queue time and when executing (a connection can start between frames).
    for name,old,new in [
        ("echoes",'''void SetEchoes(std::int32_t echoes) {
    Queue([echoes] {''','''void SetEchoes(std::int32_t echoes) {
    if (!CanEdit()) return;
    Queue([echoes] {
        if (!CanEdit()) return;'''),
        ("insight",'''void SetInsight(std::int32_t insight) {
    Queue([insight] {''','''void SetInsight(std::int32_t insight) {
    if (!CanEdit()) return;
    Queue([insight] {
        if (!CanEdit()) return;'''),
        ("stats retry",'''void CommitStats(std::array<std::int32_t, AttributeCount> wanted, std::int32_t hp_max_before,
                 std::int32_t vitality_before, int tries) {
    const auto now = Read();''',
         '''void CommitStats(std::array<std::int32_t, AttributeCount> wanted, std::int32_t hp_max_before,
                 std::int32_t vitality_before, int tries) {
    if (!CanEdit()) return;
    const auto now = Read();'''),
        ("attributes",'''void SetAttributes(const std::int32_t attributes[AttributeCount]) {
    std::array<std::int32_t, AttributeCount> wanted;''',
         '''void SetAttributes(const std::int32_t attributes[AttributeCount]) {
    if (!CanEdit() || !attributes) return;
    std::array<std::int32_t, AttributeCount> wanted;'''),
        ("attributes job",'''    Queue([wanted] {
        const auto now = Read();''',
         '''    Queue([wanted] {
        if (!CanEdit()) return;
        const auto now = Read();'''),
        ("items",'''void GiveItem(std::uint32_t category, std::uint32_t id, std::int32_t quantity) {
    Queue([category, id, quantity] {''',
         '''void GiveItem(std::uint32_t category, std::uint32_t id, std::int32_t quantity) {
    // Invalid editor requests must not reach the game's inventory routine.
    if (!CanEdit() || quantity < 1 || quantity > 99 ||
        (category != GoodsCategory && category != WeaponCategory && category != ArmorCategory)) return;
    Queue([category, id, quantity] {
        if (!CanEdit()) return;'''),
        ("jobs",'''    if (!InWorld()) {
        return; // dropped: the character is not there (title screen, loading)
    }
    for (auto& job : jobs) {''',
         '''    if (!InWorld() || !CanEdit()) {
        return; // discard pending jobs after loading, locking or joining co-op
    }
    for (auto& job : jobs) {''')
    ]:
        s=one(s,old,new,name)
    return s

def coop_header(s):
    if "SH-HUNTER-TOOLS-V21" in s: raise ValueError("V21 coop API already applied")
    return one(s,
        '''void bbcoop_lobby_request(int action, const char *id);''',
        '''void bbcoop_lobby_request(int action, const char *id);
// SH-HUNTER-TOOLS-V21: conservative local edit gate covering both Team Lobby
// and legacy live player sessions. Not a remote anti-cheat mechanism.
int bbcoop_offline_character_edit_allowed(void);''',"coop API")

def coop_impl(s):
    if "SH-HUNTER-TOOLS-V21" in s: raise ValueError("V21 coop implementation already applied")
    return one(s,
        '''extern "C" int bbcoop_lobby_view(bbcoop_lobby* lobby) {''',
        '''// SH-HUNTER-TOOLS-V21: when any party or another live player is present,
// never allow this untrusted client to edit its local character through the UI.
extern "C" int bbcoop_offline_character_edit_allowed(void) {
    namespace Coop = Core::Bloodborne::Coop;
    const auto players = Coop::SessionPlayers();
    return !Coop::TeamModeOn() && !Coop::InPartySession() &&
           Coop::SessionMembers() <= 1 && players >= 0 && players <= 1;
}

extern "C" int bbcoop_lobby_view(bbcoop_lobby* lobby) {''',"coop runtime bridge")

def transform(sources):
    return {OVERLAY: overlay(sources[OVERLAY]), EDITOR: editor(sources[EDITOR]),
            HEADER: editor_header(sources[HEADER]),
            COOP_API: coop_header(sources[COOP_API]),
            COOP_IMPL: coop_impl(sources[COOP_IMPL])}
