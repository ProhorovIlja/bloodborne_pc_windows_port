// SPDX-License-Identifier: GPL-3.0-or-later
// Party balance, the game side (see party_balance.h, docs/party/balance.md). Offsets are ours
// (raw ELF VA of out/eboot.elf, 1.09), each read in the eboot (capstone / Ghidra):
//   0x17e46e0 float MaxHpRate(SpEffect list, bool independent): the product of the active
//             effects' maxHpRate (node +0x48 -> param row +0x10, read live), NG+ table, 9200 sync.
//             Called by the per-frame HP update 0x1a0d7d0 (max = base * rate; current HP grows
//             with the "independent" rate) and the boss-bar refresh (EMEVD 2004[53]).
//   0x17e1d90 RemoveSpEffect(list, node, 1) (EMEVD 2004[21]): NOT used - removing 7503 from a boss
//             mid-fight killed it (live); bosses are kept out by entity (0x13c97a0) instead
//   chr vfunc +0x3f0 ApplySpEffect(chr, id, chr, 0, 1, 0, 0, 1.0 x5) (party_director / party_b2)
//   ChrIns +0x1c8 SpEffect list (+8 first node; node +0x40 id, +0x48 row, +0x58 next)
//   ChrIns +0x3c8 -> +8 NpcParam row (0x18e4fa6): teamType +0x12f, isSoulGetByBoss 0x149 bit 4
//   WorldChrMan 0x553e878: +0x60 local player, +0x30 / +0x38 player set (stride 0x38),
//             +0x850 + set * 8 chr set tables ({int count, pad, entries}; entries 0x38 apart,
//             chr at +0); sets < *(*(+8) + 0x18) + 2 (party_b2 ChrOfHandle, the game's 0x15bdc20)
//   ChrIns +0x3b0 -> +0x20 data module: HP +0xf8, max HP +0xfc, base max +0x100 (0x18bf9a0, the
//             kill, writes HP +0xf8 = 0; 0x1a0d7d0 is the HP struct at +0xf0)
#include "party_balance.h"

#include "../../party_env.h"
#include "../bbport_settings.h"
#include "../net/bbnet_internal.h"
#include "coop_hooks.h"
#include "game_state.h"
#include "party_async_io.h"
#include "party_link.h"
#include "party_status.h"
#include "party_travel.h"
#include "seamless_rules.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <string>

namespace coop::balance {

namespace {

using u8 = std::uint8_t;
using u16 = std::uint16_t;
using u32 = std::uint32_t;
using Clock = std::chrono::steady_clock;

constexpr u64 kSlotWorldChrMan = 0x553e878;
constexpr u64 kMaxHpRate = 0x17e46e0;
constexpr u64 kMaxStaminaRate = 0x17e4a20;  // float(list): the SpEffects' maxStaminaRate (+0x18)
constexpr u32 kBossRow0 = 7500;   // 7500 + k: k + 1 cooperators
constexpr u32 kEnemyRow = 7503;   // unused in 1.09
constexpr float kVanillaRowHp[4] = {1.5f, 2.0f, 2.5f, 3.0f};
constexpr int kEnemyTeam = 23;
constexpr int kMaxSets = 64;
constexpr int kMaxPerSet = 4096;
constexpr int kMaxAppliesPerPass = 256;

void Log(const char* fmt, ...) __attribute__((format(printf, 1, 2)));
void Log(const char* fmt, ...) {
    char line[768];
    va_list ap;
    va_start(ap, fmt);
    std::vsnprintf(line, sizeof line, fmt, ap);
    va_end(ap);
    coop::asyncio::Print(std::string("Party balance: ") + line + "\n");
}

template <class T>
T Field(u64 base, u64 off, T fallback = T{}) {
    T v{};
    return base && SafeGet(base + off, &v) ? v : fallback;
}

u64 Slot(u64 off) {
    u64 v = 0;
    const u64 at = Guest(off);
    return at && SafeGet(at, &v) ? v : 0;
}

bool EnvIsZero(const char* name) {
    const char* v = std::getenv(name);
    return v && v[0] == '0' && !v[1];
}

bool On() {
    static const bool on = bb_party_enabled() && !EnvIsZero("BB_PARTY_BALANCE");
    return on;
}

// ---- State ----
std::mutex g_mu;  // the received rules
bool g_have_host = false;
Rules g_host;

std::atomic<u64> g_rot_list{0};         // the local player's SpEffect list (rate hook)
std::atomic<float> g_rot_factor{1.0f};  // max HP: 1 - 0.1 * health stacks while rot is on
std::atomic<float> g_rot_st_factor{1.0f};  // max stamina: 1 - 0.1 * stamina stacks
std::atomic<int> g_stacks{0}, g_deaths{0};  // all stacks (health + stamina)
std::atomic<int> g_st_stacks{0};            // of them: stamina rot
void* g_st_rate_orig = nullptr;
bool g_st_hooked = false;
std::atomic<bool> g_rest_pending{false};
std::atomic<bool> g_hooked{false};
using RateFn = float(BB_COOP_SYSV*)(u64, u64);
void* g_rate_orig = nullptr;

struct TickState {
    bool loaded = false;
    Clock::time_point next_params{}, next_enemies{}, next_send{}, last_death{};
    std::string last_sent;
    int last_n = 0;
    u64 last_player = 0;
    int last_hp = -1;
    bool log = false;
    bool row_refused[4]{};
    bool rows_logged = false;
    Doping written[4];
    bool have_written[4]{};
    int hp_logged_factor = -1, hp_logged_max = -1;
    int hits = 0;
    std::string toast;            // a rot notice waiting for the respawn
    Clock::time_point toast_at{};  // alive in the world since  // rot factor (percent) of the last "max HP now" line
    Clock::time_point factor_since{};
    int last_factor = 100;
};
TickState& S() {
    static TickState s;
    return s;
}

// ---- Rot persistence ----
std::filesystem::path RotPath() {
    std::string dir = bbnet::settings().user_dir;
    if (dir.empty()) {
        if (const char* u = std::getenv("BB_GPU_USER_DIR")) dir = u;
        else if (const char* u2 = std::getenv("BB_USER_DIR")) dir = u2;
        else dir = std::string(std::getenv("BB_DATA_DIR") ? std::getenv("BB_DATA_DIR") : ".") + "/user";
    }
    return std::filesystem::path(dir) / "party_rot.txt";
}

void LoadRot() {
    std::ifstream f(RotPath());
    std::string key;
    int v = 0;
    if (f >> key >> v && key == "stacks") g_stacks = std::clamp(v, 0, kRotMaxStacks);
    int st = 0;
    if (f >> key >> st && key == "stamina") g_st_stacks = std::clamp(st, 0, g_stacks.load());
}

void SaveRot() {
    std::error_code ec;
    const auto p = RotPath();
    std::filesystem::create_directories(p.parent_path(), ec);
    std::ofstream f(p, std::ios::trunc);
    f << "stacks " << g_stacks.load() << "\n";
}

void UpdateRotFactor(const Rules& r) {
    g_rot_factor = r.rot ? RotHpFactor(g_stacks.load() - g_st_stacks.load()) : 1.0f;
    g_rot_st_factor = r.rot ? RotHpFactor(g_st_stacks.load()) : 1.0f;
}

// ---- Hooks ----
BB_COOP_SYSV float RateHook(u64 list, u64 independent) {
    float r = reinterpret_cast<RateFn>(g_rate_orig)(list, independent);
    if (list && list == g_rot_list.load(std::memory_order_relaxed)) r *= g_rot_factor.load(std::memory_order_relaxed);
    return r;
}

BB_COOP_SYSV float StaminaRateHook(u64 list) {
    float r = reinterpret_cast<float(BB_COOP_SYSV*)(u64)>(g_st_rate_orig)(list);
    if (list && list == g_rot_list.load(std::memory_order_relaxed)) r *= g_rot_st_factor.load(std::memory_order_relaxed);
    return r;
}

void OnLampUse(u32 id) {
    g_rest_pending = true;
    (void)id;
}

// ---- SpEffects ----
bool HasEffect(u64 chr, int id, u64* node_out = nullptr) {
    u64 node = Field<u64>(Field<u64>(chr, 0x1c8), 8);
    for (int guard = 0; node && guard < 256; ++guard) {
        if (Field<int>(node, 0x40, -1) == id) {
            if (node_out) *node_out = node;
            return true;
        }
        node = Field<u64>(node, 0x58);
    }
    return false;
}

bool ApplyEffect(u64 chr, int id) {
    u64 vt = 0, fn = 0;
    if (!chr || !SafeGet(chr, &vt) || !vt || !SafeGet(vt + 0x3f0, &fn) || !fn) return false;
    using Fn = void(BB_COOP_SYSV*)(u64, u64, u64, u64, u64, u64, u64, float, float, float, float, float);
    reinterpret_cast<Fn>(fn)(chr, u64(id), chr, 0, 1, 0, 0, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f);
    return true;
}


// ---- Param rows ----
Doping ReadRow(u64 row) {
    Doping d;
    d.hp_rate = Field<float>(row, 0x10, -1.0f);
    d.attack_rate = Field<float>(row, 0x48, -1.0f);
    d.resist_rate = Field<float>(row, 0x108, -1.0f);
    d.super_armor = Field<std::int16_t>(row, 0x13a, 0);
    return d;
}

void WriteRow(u64 row, const Doping& d) {
    for (u64 off : {0x10ull}) SafeWrite(row + off, &d.hp_rate, 4);
    for (u64 off : {0x48ull, 0x4cull, 0x50ull, 0x54ull}) SafeWrite(row + off, &d.attack_rate, 4);
    for (u64 off : {0x108ull, 0x10cull, 0x110ull, 0x114ull}) SafeWrite(row + off, &d.resist_rate, 4);
    const std::int16_t sa = static_cast<std::int16_t>(std::clamp(d.super_armor, -30000, 30000));
    SafeWrite(row + 0x13a, &sa, 2);
}

void WriteParams(const Rules& r, int n) {
    TickState& st = S();
    for (int k = 0; k < 4; ++k) {
        const u32 id = kBossRow0 + u32(k);
        const u64 row = GameParamRow("SpEffectParam", "SP_EFFECT_PARAM_ST", id);
        if (!row) {
            st.have_written[k] = false;  // params not loaded (or reloaded): the next pass writes again
            continue;
        }
        const Doping want = k < 3 ? Boss(r, k + 1) : Enemy(r, n);
        const Doping now = ReadRow(row);
        if (now == want) {
            st.have_written[k] = true;
            st.written[k] = want;
            continue;
        }
        // Only a row that still holds the 1.09 value or what we wrote last.
        const bool vanilla = now.hp_rate == kVanillaRowHp[k] && now.attack_rate == 1.0f;
        const bool ours = st.have_written[k] && now == st.written[k];
        if (!vanilla && !ours) {
            if (!st.row_refused[k]) {
                st.row_refused[k] = true;
                Log("SpEffect %u: maxHpRate %.3f attack %.3f is neither 1.09's nor ours; left alone", id, now.hp_rate,
                    now.attack_rate);
            }
            continue;
        }
        WriteRow(row, want);
        st.written[k] = want;
        st.have_written[k] = true;
        Log("SpEffect %u (%s): HP x%.3f, resist x%.3f, damage x%.3f, poise %+d", id,
            k < 3 ? (k == 0 ? "boss, 1 cooperator" : k == 1 ? "boss, 2 cooperators" : "boss, 3 cooperators")
                  : "normal enemies",
            want.hp_rate, want.resist_rate, want.attack_rate, want.super_armor);
    }
}

// ---- Enemies ----
// Every entity the boss events dope (EMEVD 2004[8] SpEffect 7500 / 7501 in the 1.09 maps;
// the chalice bosses in m29 take theirs from event parameters / Lua_MultiDoping: isSoulGetByBoss).
constexpr int kBossEntities[] = {2100800, 2100810, 2200800, 2200801, 2300800, 2300810, 2400800, 2410800, 2410810,
                                 2410811, 2420800, 2500800, 2500801, 2500802, 2600800, 2600801, 2600802, 2600850,
                                 2700800, 2700801, 2700802, 2800800, 2800801, 2800802, 2800803, 3200800, 3300800,
                                 3400800, 3400801, 3400850, 3500800, 3500850, 3600800, 3600801};
constexpr u64 kGetChrByEntityId = 0x13c97a0;

u64 ChrByEntity(int entity) {
    static const bool code_ok = MatchesOriginal(kGetChrByEntityId, {0x55, 0x48, 0x89, 0xe5});
    if (!code_ok) return 0;
    using Fn = u64(BB_COOP_SYSV*)(int, u64, u64);
    return reinterpret_cast<Fn>(Guest(kGetChrByEntityId))(entity, u64(unsigned(entity)), 0);
}

std::string g_boss_line;  // the last boss line logged (only changes are logged)
u64 g_sample = 0;
u32 g_sample_handle = ~0u;
int g_sample_logs = 0;

bool IsPlayer(u64 wcm, u64 chr) {
    const int n = Field<int>(wcm, 0x30, 0);
    const u64 entries = Field<u64>(wcm, 0x38);
    for (int i = 0; entries && n > 0 && n <= 8 && i < n; ++i)
        if (Field<u64>(entries + u64(i) * 0x38, 0) == chr) return true;
    return chr == Field<u64>(wcm, 0x60);
}

void EnemyPass(const GameSnapshot& s, bool scale) {
    const u64 wcm = Slot(kSlotWorldChrMan);
    if (!wcm || !s.player) return;
    const int sets = std::min(Field<int>(Field<u64>(wcm, 8), 0x18, -2) + 2, kMaxSets);
    int seen = 0, enemies = 0, applied = 0, removed = 0, bosses = 0, carrying = 0, counted = 0;
    // The bosses of the loaded maps, by the entity ids the boss events dope (EMEVD 2004[8] with
    // SpEffect 7500 / 7501, every map; GetChrByEntityId 0x13c97a0, as the events resolve them).
    u64 boss_chrs[sizeof kBossEntities / sizeof kBossEntities[0]];
    int n_boss = 0;
    for (int e : kBossEntities)
        if (const u64 c = ChrByEntity(e)) boss_chrs[n_boss++] = c;
    for (int set = 0; set < sets; ++set) {
        const u64 tab = Field<u64>(wcm, 0x850 + u64(set) * 8);
        const int count = Field<int>(tab, 0, 0);
        const u64 entries = Field<u64>(tab, 8);
        if (!tab || !entries || count <= 0 || count > kMaxPerSet) continue;
        for (int i = 0; i < count; ++i) {
            const u64 chr = Field<u64>(entries + u64(i) * 0x38, 0);
            if (!chr) continue;
            ++seen;
            if (IsPlayer(wcm, chr)) continue;
            const u64 npc = Field<u64>(Field<u64>(chr, 0x3c8), 8);
            if (!npc) continue;
            const int team = Field<u8>(npc, 0x12f, 0xff);
            const bool boss_soul = (Field<u8>(npc, 0x149, 0) & 0x10) != 0;
            if (team != kEnemyTeam) continue;
            ++enemies;
            const bool doped = HasEffect(chr, 7500) || HasEffect(chr, 7501) || HasEffect(chr, 7502);
            const bool boss_entity = std::find(boss_chrs, boss_chrs + n_boss, chr) != boss_chrs + n_boss;
            if (doped || boss_soul || boss_entity) {
                ++bosses;
                if (doped) {  // evidence: the boss's HP with the party's doping row (same on every peer)
                    const u64 dm = Field<u64>(Field<u64>(chr, 0x3b0), 0x20);
                    const int dope = HasEffect(chr, 7502) ? 7502 : HasEffect(chr, 7501) ? 7501 : 7500;
                    u64 node = 0;
                    HasEffect(chr, dope, &node);
                    const u64 list = Field<u64>(chr, 0x1c8);
                    char b[200];
                    std::snprintf(b, sizeof b, "boss chr %x: SpEffect %d (flags %x): HP %d / %d base %d, rate %.3f",
                                  Field<u32>(chr, 8, ~0u), dope, Field<u32>(node, 0x1c), Field<int>(dm, 0xf8, -1),
                                  Field<int>(dm, 0xfc, -1), Field<int>(dm, 0x100, -1),
                                  double(list && g_rate_orig ? reinterpret_cast<RateFn>(g_rate_orig)(list, 0) : -1.0f));
                    if (g_boss_line != b) {
                        g_boss_line = b;
                        Log("%s", b);
                    }
                }
                // No removal: taking 7503 off a boss mid-fight (0x17e1d90, EMEVD 2004[21]'s remove) killed
                // the Cleric Beast outright (live 2026-10-11, HP 6597 -> 0). Bosses never get it now
                // (the boss entity table below); one that still carries it is only counted.
                if (HasEffect(chr, int(kEnemyRow))) ++removed;
                continue;
            }
            if (scale && applied < kMaxAppliesPerPass && !HasEffect(chr, int(kEnemyRow))) {
                const u64 dm = Field<u64>(Field<u64>(chr, 0x3b0), 0x20);
                const int hp_before = Field<int>(dm, 0xf8, -1), max_before = Field<int>(dm, 0xfc, -1);
                if (ApplyEffect(chr, int(kEnemyRow))) {
                    if (!applied) {  // one sample, followed in the log (evidence: max HP before / after)
                        g_sample = chr;
                        g_sample_handle = Field<u32>(chr, 8, ~0u);
                        Log("sample chr %x before SpEffect %u: HP %d / %d", g_sample_handle, kEnemyRow, hp_before,
                            max_before);
                    }
                    ++applied;
                }
            }
            u64 node = 0;
            if (HasEffect(chr, int(kEnemyRow), &node)) {
                ++carrying;
                if ((Field<u32>(node, 0x1c) & 0x800c0003u) == 0) ++counted;
            }
        }
    }
    char sample[480] = "";
    if (g_sample && Field<u32>(g_sample, 8, ~0u) == g_sample_handle) {
        const u64 dm = Field<u64>(Field<u64>(g_sample, 0x3b0), 0x20);
        const u64 npc = Field<u64>(Field<u64>(g_sample, 0x3c8), 8);
        u64 node = 0;
        const bool on = HasEffect(g_sample, int(kEnemyRow), &node);
        const u64 list = Field<u64>(g_sample, 0x1c8);
        const float rate = list && g_rate_orig ? reinterpret_cast<RateFn>(g_rate_orig)(list, 0) : -1.0f;
        std::string effects;
        for (u64 n = Field<u64>(list, 8); n && effects.size() < 120; n = Field<u64>(n, 0x58)) {
            char e[24];
            std::snprintf(e, sizeof e, " %d/%x", Field<int>(n, 0x40, -1), Field<u32>(n, 0x1c));
            effects += e;
        }
        std::snprintf(sample, sizeof sample,
                      "; sample chr %x (NpcParam HP %u): HP %d / %d base %d, rate %.3f, 7503 %s (flags %x, row %s); effects%s",
                      g_sample_handle, Field<u32>(npc, 0x20), Field<int>(dm, 0xf8, -1), Field<int>(dm, 0xfc, -1),
                      Field<int>(dm, 0x100, -1), double(rate), on ? "on" : "off", Field<u32>(node, 0x1c),
                      !node ? "-" : Field<u64>(node, 0x48) == GameParamRow("SpEffectParam", "SP_EFFECT_PARAM_ST", kEnemyRow) ? "7503" : "other", effects.c_str());
    } else {
        g_sample = 0;
    }
    const bool any = applied || removed;
    if (S().log || any || (sample[0] && ++g_sample_logs <= 3))
        Log("enemy pass: %d chrs, %d enemies (%d bosses), SpEffect %u applied to %d, on %d boss(es) from before, carried by %d "
            "(%d counted)%s",
            seen, enemies, bosses, kEnemyRow, applied, removed, carrying, counted, sample);
}

}  // namespace

Rules FromSettings() {
    const auto& v = BbSettings::Get();
    Rules r;
    r.rot = v.party_rot;
    r.boss_hp = v.party_boss_hp;
    r.boss_damage = v.party_boss_damage;
    r.boss_poise = v.party_boss_poise;
    r.enemy_hp = v.party_enemy_hp;
    r.enemy_damage = v.party_enemy_damage;
    r.enemy_poise = v.party_enemy_poise;
    return Clamped(r);
}

Rules InForce() {
    {
        std::lock_guard<std::mutex> lk(g_mu);
        if (g_have_host) return g_host;
    }
    return FromSettings();
}

bool OnHostRules(const std::string& json, std::string* error) {
    Rules r;
    if (!FromJson(json, &r, error)) return false;
    bool changed;
    {
        std::lock_guard<std::mutex> lk(g_mu);
        changed = !g_have_host || g_host != r;
        g_host = r;
        g_have_host = true;
    }
    if (changed) Log("the host's rules: %s", ToJson(r).c_str());
    return true;
}

int LocalDeaths() {
    return g_deaths.load();
}

int LocalRotStacks() {
    return InForce().rot ? g_stacks.load() : 0;
}

void Init() {
    if (!On()) {
        Log("off (BB_PARTY_BALANCE=0 or no party)");
        return;
    }
    LoadRot();
    S().log = std::getenv("BB_PARTY_BALANCE_LOG") && std::getenv("BB_PARTY_BALANCE_LOG")[0] == '1';
    if (ReplacePrologue(kMaxHpRate, {0x55, 0x48, 0x89, 0xe5, 0x53, 0x50}, reinterpret_cast<const void*>(&RateHook),
                        &g_rate_orig, "balance: max HP rate (rot)")) {
        g_hooked = true;
    }
    // The second rot kind (ERSC has five): max stamina, through the stamina rate 0x17e4a20.
    if (ReplacePrologue(kMaxStaminaRate, {0x55, 0x48, 0x89, 0xe5, 0x48, 0x83, 0xec, 0x10},
                        reinterpret_cast<const void*>(&StaminaRateHook), &g_st_rate_orig,
                        "balance: max stamina rate (rot)")) {
        g_st_hooked = true;
    }
    SetLampUseObserver(&OnLampUse);
    Log("on: rot hooks HP %s, stamina %s; %d rot stack(s) (%d stamina) kept from the last game",
        g_hooked ? "in" : "NOT in", g_st_hooked ? "in" : "NOT in", g_stacks.load(), g_st_stacks.load());
}

void Tick(const GameSnapshot& s, party::PartyLink* link, bool host) {
    if (!On()) return;
    TickState& st = S();
    const auto now = Clock::now();
    const Rules r = host ? FromSettings() : InForce();
    if (host) {
        std::lock_guard<std::mutex> lk(g_mu);
        g_have_host = false;  // a host's own settings count
    }
    // The host's rules to the party (on change, and every 15 s for late joiners).
    if (host && link) {
        const std::string j = ToJson(r);
        if (j != st.last_sent || now >= st.next_send) {
            link->post_event(party::kBroadcast, kEventName, j);
            if (j != st.last_sent) Log("rules sent to the party: %s", j.c_str());
            st.last_sent = j;
            st.next_send = now + std::chrono::seconds(15);
        }
    }

    const bool in_world = s.world_up && !s.loading && s.player;
    // C4: the local player's death, the lamp rest, the rate factor.
    const u64 dm = in_world ? Field<u64>(Field<u64>(s.player, 0x3b0), 0x20) : 0;
    const int hp = dm ? Field<int>(dm, 0xf8, -1) : -1;
    const int max_hp = dm ? Field<int>(dm, 0xfc, -1) : -1;
    if (in_world && s.player == st.last_player && st.last_hp > 0 && hp == 0 && max_hp > 1) {
        ++g_deaths;
        st.last_death = now;
        bool stamina_kind = false;
        if (r.rot && g_stacks.load() < kRotMaxStacks) {
            // One kind picked at random per death (ERSC): max HP or, with the hook in, max stamina.
            stamina_kind = g_st_hooked && (std::chrono::steady_clock::now().time_since_epoch().count() >> 10) % 2 == 1;
            ++g_stacks;
            if (stamina_kind) ++g_st_stacks;
            SaveRot();
        }
        const int k = g_stacks.load(), ks = g_st_stacks.load(), kh = k - ks;
        Log("death %d; rot %s, %d stack(s) (this one %s): max HP x%.2f, max stamina x%.2f", g_deaths.load(),
            r.rot ? "on" : "off", k, stamina_kind ? "stamina" : "health", double(RotHpFactor(kh)), double(RotHpFactor(ks)));
        if (r.rot) {
            char b[160];
            std::snprintf(b, sizeof b, "Rot %d/%d: max HP -%d %%, stamina -%d %% until you rest at a lamp", k,
                          kRotMaxStacks, kh * kRotHpPercentPerStack, ks * kRotHpPercentPerStack);
            st.toast = b;  // shown once the player is back on its feet (the death's travel notice comes first)
            st.toast_at = Clock::time_point{};
        }
    }
    // Evidence for damage scaling: the local player's hits (first 40 per game).
    if (in_world && s.player == st.last_player && st.last_hp > 0 && hp >= 0 && hp < st.last_hp && st.hits < 40) {
        ++st.hits;
        Log("hit: HP %d -> %d (-%d), max %d", st.last_hp, hp, st.last_hp - hp, max_hp);
    }
    if (!st.toast.empty()) {
        if (!(in_world && hp > 0)) {
            st.toast_at = Clock::time_point{};
        } else if (st.toast_at == Clock::time_point{}) {
            st.toast_at = now;
        } else if (std::chrono::duration<double>(now - st.toast_at).count() >= 2.0) {
            party::status::SetLastEvent(st.toast);
            Log("notice: %s", st.toast.c_str());
            st.toast.clear();
        }
    }
    st.last_player = in_world ? s.player : 0;
    st.last_hp = in_world ? hp : -1;
    if (g_rest_pending.exchange(false)) {
        const double since_death = std::chrono::duration<double>(now - st.last_death).count();
        if (st.last_death != Clock::time_point{} && since_death < 20.0) {
            Log("lamp warp %.0f s after a death: the respawn, not a rest", since_death);
        } else if (g_stacks.load() > 0) {
            Log("lamp rest: rot cleansed (%d stack(s), %d stamina)", g_stacks.load(), g_st_stacks.load());
            g_stacks = 0;
            g_st_stacks = 0;
            SaveRot();
            if (r.rot) party::status::SetLastEvent("The rot is cleansed");
        }
    }
    UpdateRotFactor(r);
    // Evidence: the local max HP once a rot change has settled (3 s, in the world).
    {
        const int f = static_cast<int>(std::lround(g_rot_factor.load() * 100.0f)) +
                      1000 * static_cast<int>(std::lround(g_rot_st_factor.load() * 100.0f));
        if (f != st.last_factor) {
            st.last_factor = f;
            st.factor_since = now;
        }
        if (in_world && max_hp > 0 && hp > 0 && (f != st.hp_logged_factor || max_hp != st.hp_logged_max) &&
            std::chrono::duration<double>(now - st.factor_since).count() >= 3.0) {
            st.hp_logged_factor = f;
            st.hp_logged_max = max_hp;
            Log("max HP now %d (HP %d), max stamina %d, rot factor HP %d %% stamina %d %% (%d stack(s))", max_hp, hp,
                Field<int>(dm, 0x138, -1), f % 1000, f / 1000, g_stacks.load());
        }
    }
    g_rot_list.store(in_world ? Field<u64>(s.player, 0x1c8) : 0, std::memory_order_relaxed);

    // D7: the rows (every second) and the enemies (every 2 s).
    if (s.cooperators >= 0) st.last_n = std::clamp(s.cooperators, 0, 3);
    if (now >= st.next_params) {
        st.next_params = now + std::chrono::seconds(1);
        WriteParams(r, st.last_n);
    }
    if (in_world && now >= st.next_enemies) {
        st.next_enemies = now + std::chrono::seconds(2);
        const bool scale = st.last_n > 0 && EnemyScalingActive(r);
        if (scale || st.log) EnemyPass(s, scale);
    }
}

}  // namespace coop::balance
