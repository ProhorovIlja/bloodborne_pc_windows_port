// SPDX-License-Identifier: GPL-3.0-or-later
// D3 / D8: a guest's actions change the host's world (see party_worldact.h,
// docs/party/world_actions.md).
#include "party_worldact.h"

#include "party_progress.h"
#include "net/json.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace coop::worldact {

using progress::Category;

bool WorldActionAllowed(std::uint32_t id, bool clear, std::uint32_t host_map) {
    const int key = progress::PoolKeyOfId(id);
    if (key < 0 || !progress::WorldMirrorKey(key) || progress::NeverWritable(id) ||
        !progress::GetBit(progress::WorldMirrorMask(key).data(), id % progress::kBitsPerBlock)) {
        return false;
    }
    const Category c = progress::CategoryOf(id);
    // Elevator / two-state object flags (C2's state ids, e.g. 12410350/351 Central Yharnam's lift):
    // the lift's own network-synced events and the replicated ObjAct kick move it on the host; a
    // guest's value, arriving later, would fight the host's ride.
    if (c != Category::npc_quest &&
        progress::ModeFor(progress::Policy::Defaults(), id, c) == progress::SyncMode::State) {
        return false;
    }
    bool global_ok = false;
    switch (c) {
    case Category::shortcut_door:
    case Category::world_state:
        break;
    case Category::npc_quest:
        // NPC quests are state machines: a step clears the old state flag and sets the new one
        // (Iosefka live: 1141 off, 1143 on); both halves go to the host.
        global_ok = true;
        break;
    case Category::key_event:
    case Category::cutscene_seen:  // D10: a scene a guest's event played is seen in the host's world too
        if (clear) {
            return false;
        }
        global_ok = true;
        break;
    default:
        return false;
    }
    const std::uint32_t area = id >= 10000000u ? id / 100000u % 100u : 0u;
    if (area == 0) {
        return global_ok;  // 1000-1999 NPC state, 5000-5299 key items ...; never a door of no map
    }
    if (host_map == 0xffffffffu) {
        return false;
    }
    return area == (host_map >> 24);  // the guest acts in the host's world: the host's area
}

std::string RequestToJson(const Request& r) {
    json::Value v = json::Value::make_object();
    v.set("v", 1u);
    v.set("map", static_cast<unsigned>(r.map));
    json::Value s = json::Value::make_array(), c = json::Value::make_array();
    for (std::uint32_t id : r.set) {
        s.push(static_cast<unsigned>(id));
    }
    for (std::uint32_t id : r.clr) {
        c.push(static_cast<unsigned>(id));
    }
    v.set("set", std::move(s));
    v.set("clr", std::move(c));
    if (!r.kick.empty()) {
        json::Value k = json::Value::make_array();
        for (std::int32_t id : r.kick) {
            k.push(static_cast<unsigned>(id));
        }
        v.set("kick", std::move(k));
    }
    if (!r.fog.empty()) {
        json::Value f = json::Value::make_array();
        for (std::uint32_t id : r.fog) {
            f.push(static_cast<unsigned>(id));
        }
        v.set("fog", std::move(f));
    }
    return json::dump(v, 0);
}

bool RequestFromJson(const std::string& text, Request* out, std::string* error) {
    json::Value v;
    std::string err;
    if (text.size() > 4096 || !json::parse(text, v, err)) {
        if (error) {
            *error = err.empty() ? "too long" : err;
        }
        return false;
    }
    try {
        if (v.type != json::Value::Type::Object || json::u64(v, "v") != 1) {
            throw std::runtime_error("bad world_action body");
        }
        Request r;
        const std::uint64_t map = json::u64(v, "map");
        if (map > 0xffffffffull) {
            throw std::runtime_error("bad map");
        }
        r.map = std::uint32_t(map);
        const auto& set = json::arr(v, "set");
        const auto& clr = json::arr(v, "clr");
        const json::Value* kick = v.find("kick");
        if (kick) {
            if (kick->type != json::Value::Type::Array || kick->array.size() > kMaxKicks) {
                throw std::runtime_error("bad kick list");
            }
            for (const json::Value& x : kick->array) {
                const std::uint64_t id = json::as_u64(x, "kick");
                if (id == 0 || id > 99999999ull) {
                    throw std::runtime_error("bad kick event id");
                }
                if (std::find(r.kick.begin(), r.kick.end(), std::int32_t(id)) != r.kick.end()) {
                    throw std::runtime_error("duplicate kick");
                }
                r.kick.push_back(std::int32_t(id));
            }
        }
        if (const json::Value* fog = v.find("fog")) {
            if (fog->type != json::Value::Type::Array || fog->array.size() > kMaxFog) {
                throw std::runtime_error("bad fog list");
            }
            for (const json::Value& x : fog->array) {
                const std::uint64_t id = json::as_u64(x, "fog");
                if (id > 0xffffffffull || !BossGateByGuestFlag(std::uint32_t(id))) {
                    throw std::runtime_error("not a boss fog flag");
                }
                if (std::find(r.fog.begin(), r.fog.end(), std::uint32_t(id)) != r.fog.end()) {
                    throw std::runtime_error("duplicate fog");
                }
                r.fog.push_back(std::uint32_t(id));
            }
        }
        if (set.size() > kMaxSet || clr.size() > kMaxClear ||
            (set.empty() && clr.empty() && r.kick.empty() && r.fog.empty())) {
            throw std::runtime_error("bad world_action size");
        }
        auto take = [](const std::vector<json::Value>& a, bool clear, std::vector<std::uint32_t>* to) {
            for (const json::Value& x : a) {
                const std::uint64_t id = json::as_u64(x, "id");
                if (id > 0xffffffffull) {
                    throw std::runtime_error("bad id");
                }
                const std::uint32_t id32 = std::uint32_t(id);
                const std::uint32_t area = id32 >= 10000000u ? id32 / 100000u % 100u : 21u;
                if (!WorldActionAllowed(id32, clear, area << 24)) {
                    throw std::runtime_error("flag not allowed: " + std::to_string(id32));
                }
                if (std::find(to->begin(), to->end(), id32) != to->end()) {
                    throw std::runtime_error("duplicate id");
                }
                to->push_back(id32);
            }
        };
        take(set, false, &r.set);
        take(clr, true, &r.clr);
        for (std::uint32_t id : r.set) {
            if (std::find(r.clr.begin(), r.clr.end(), id) != r.clr.end()) {
                throw std::runtime_error("id both set and cleared");
            }
        }
        *out = std::move(r);
        return true;
    } catch (const std::exception& e) {
        if (error) {
            *error = e.what();
        }
        return false;
    }
}

bool RateLimit::Take(int slot, int n, double now) {
    if (slot < 0 || slot >= 8 || n < 0 || n > kRateFlags || !std::isfinite(now)) {
        return false;
    }
    Slot& s = slots_[slot];
    if (now - s.start >= kRateWindow || now < s.start) {
        s.start = now;
        s.used = 0;
    }
    if (s.used + n > kRateFlags) {
        return false;
    }
    s.used += n;
    return true;
}

bool WorldTalkAllowed(std::uint32_t talk) {
    if (talk < 100000 || talk > 999999) {
        return false;
    }
    const std::uint32_t map = talk / 1000;  // area * 10 + block
    if (map / 10 == 21) {
        return false;  // the Hunter's Dream: guest services' own list (Gehrman's ending is never a guest's)
    }
    if (map >= 210 && map <= 369 && map % 10 <= 2 && talk % 1000 <= 3) {
        return false;  // world lamps (LampTalk): lamp requests
    }
    return map >= 220 && map <= 369;  // the world maps' NPCs (Gilbert, Eileen, Alfred, Iosefka, ...)
}

const std::vector<GateRule>& GateRules() {
    // From every EMEVD boss-defeat event (2003[12]/[15]/[53]): its own flag and the 2000-3999
    // flags it sets (tools: flag_tool expand_all; 12411899 sets 2410 once both Central Yharnam
    // bosses are dead).
    static const std::vector<GateRule> rules = {
        {12201800, 2200}, {12301700, 2301}, {12301800, 2300}, {12401800, 2400}, {12401800, 2401},
        {12401800, 2402}, {12411700, 2411}, {12411800, 2412}, {12411800, 2410, 12411700},
        {12421700, 2420}, {12421800, 2421}, {12501800, 2500}, {12601800, 2601}, {12601850, 2600},
        {12701800, 2700}, {12701800, 2701}, {12801800, 2800}, {13201800, 3200}, {13301800, 3300},
        {13401800, 3400}, {13401800, 3401}, {13401800, 3402}, {13401800, 3403}, {13501800, 3510},
        {13501800, 3511}, {13501800, 3512}, {13501800, 3513}, {13501850, 3517}, {13601800, 3600},
    };
    return rules;
}

const std::vector<BossGate>& BossGates() {
    // flag_tool.py emevd --all-ops, every `ゲストがボス部屋入場` event: {event, its last 3[0] flag
    // (= the flag `ボスが動き出す` waits on), the flag it sets, its boss flag}.
    // intro_flag: the 3[0] ON condition before the host-entered one (the host's first-fight entry
    // event, an intro cutscene for most); fog_entity: the 3[24] action-button object (the fog).
    static const std::vector<BossGate> gates = {
        {12204891, 12204800, 12204801, 12201800, 12201802, 2201800},
        {12304811, 12304800, 12304801, 12301800, 12301802, 2301800},
        {12304731, 12304700, 12304701, 12301700, 12301702, 2301810},
        {12404841, 12404800, 12404801, 12401800, 12401802, 2401800},
        {12414731, 12414700, 12414701, 12411700, 12411702, 2411800},
        {12414811, 12414800, 12414801, 12411800, 12411802, 2411810},
        {12424811, 12424800, 12424801, 12421800, 12421802, 2421800},
        {12424711, 12424700, 12424701, 12421700, 0, 2421700},
        {12504811, 12504800, 12504801, 12501800, 12501802, 2501800},
        {12604846, 12604800, 12604801, 12601800, 12601802, 2601800},
        {12604861, 12604850, 12604851, 12601850, 12601852, 2601850},
        {12704841, 12704800, 12704801, 12701800, 12701802, 2701800},
        {12804881, 12804800, 12804801, 12801800, 12801802, 2801800},
        {13304871, 13304800, 13304801, 13301800, 13301802, 3301800},
        {13404801, 13404808, 13404809, 13401800, 13401801, 3401800},
        {13404851, 13404858, 13404859, 13401850, 13401851, 3401850},
        {13504801, 13504808, 13504809, 13501800, 13501801, 3501800},
        {13504851, 13504858, 13504859, 13501850, 13501851, 3501810},
        {13604801, 13604808, 13604809, 13601800, 13601801, 3601800},
    };
    return gates;
}

const BossGate* BossGateByEvent(std::int32_t guest_event) {
    for (const BossGate& g : BossGates()) {
        if (static_cast<std::int32_t>(g.guest_event) == guest_event) {
            return &g;
        }
    }
    return nullptr;
}

const BossGate* BossGateByGuestFlag(std::uint32_t guest_flag) {
    for (const BossGate& g : BossGates()) {
        if (g.guest_flag == guest_flag) {
            return &g;
        }
    }
    return nullptr;
}

bool BossGateSkipCondition(std::int32_t event_id, int bank, int id, std::uint32_t flag) {
    if (bank != 3 || id != 0) {
        return false;
    }
    const BossGate* g = BossGateByEvent(event_id);
    return g && g->host_flag == flag;
}

bool BossGateWaitsForHost(const BossGate& g, bool intro_done, bool host_in, bool boss_dead) {
    return g.intro_flag != 0 && !intro_done && !host_in && !boss_dead;
}

bool BossFogNoticeDue(const BossGate& g, bool read, bool intro_done, bool host_in, bool boss_dead, float dist_m) {
    return read && BossGateWaitsForHost(g, intro_done, host_in, boss_dead) && dist_m >= 0.0f &&
           dist_m <= kBossFogNoticeRange;
}

const float* PickPlayerPos(bool physics_ok, const float* physics, bool drawn_ok, const float* drawn) {
    return physics_ok && physics ? physics : drawn_ok && drawn ? drawn : nullptr;
}

bool BossGateInBlock(const BossGate& g, std::uint32_t map) {
    const std::uint32_t area = g.host_flag / 100000 % 100, block = g.host_flag / 10000 % 10;
    return map != 0xffffffffu && (map >> 24) == area && ((map >> 16) & 0xff) == block;
}

bool BossGateHostOpens(const BossGate& g, bool guest_in, bool host_in, bool boss_dead, std::uint32_t host_map) {
    const std::uint32_t area = g.host_flag / 100000 % 100, block = g.host_flag / 10000 % 10;
    return guest_in && !host_in && !boss_dead && host_map != 0xffffffffu && (host_map >> 24) == area &&
           ((host_map >> 16) & 0xff) == block;
}

} // namespace coop::worldact

#ifndef BB_PARTY_WORLDACT_NO_GAME

#include "coop_hooks.h"
#include "party_b2.h"
#include "game_state.h"
#include "party_director.h"
#include "party_link.h"
#include "party_guestsvc.h"
#include "party_status.h"
#include "party_droproll.h"

#include <atomic>
#include <chrono>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <mutex>
#include <set>
#include <array>

extern "C" void runtime_pad_director_press(std::uint32_t buttons); // src/runtime_pad.c

namespace coop::worldact {
namespace {

void Log(const char* fmt, ...) __attribute__((format(printf, 1, 2)));
void Log(const char* fmt, ...) {
    char line[640];
    va_list ap;
    va_start(ap, fmt);
    std::vsnprintf(line, sizeof line, fmt, ap);
    va_end(ap);
    std::printf("Party: world: %s\n", line);  // "Party: ": the harness reaper counts it as activity
    std::fflush(stdout);
}

double Now() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

/// A tag that differs from step to step without digits: the harness reaper blanks numbers when it
/// counts distinct "Party:" lines, so a fixture's repeated steps need words to stay "active".
std::string StepTag(int n) {
    std::string t;
    n = n < 0 ? 0 : n;
    do {
        t.insert(t.begin(), char('a' + n % 26));
        n /= 26;
    } while (n > 0);
    return "step-" + t;
}

std::vector<std::uint32_t> ParseIds(const char* v) {
    std::vector<std::uint32_t> out;
    while (v && *v) {
        char* end = nullptr;
        const unsigned long x = std::strtoul(v, &end, 10);
        if (end == v) {
            break;
        }
        out.push_back(std::uint32_t(x));
        v = *end ? end + 1 : end;
    }
    return out;
}

struct State {
    std::once_flag once;
    bool enabled = false;
    std::vector<std::uint32_t> watch;  // BB_PARTY_WORLD_WATCH
    std::mutex mu;
    std::deque<std::pair<int, Request>> in;  // host: from guests (link thread -> tick)
    RateLimit rate;
    // guest (main thread)
    std::uint32_t map = 0xffffffffu;
    double steady_since = 0, last_scan = 0;
    bool steady = false, baselined = false;
    std::set<std::uint64_t> known;  // id * 2 + value: local changes already sent or held back
    std::set<std::uint32_t> fog_in;  // guest: boss fogs it went through (B2), reported once
    bool pickups = false;           // D4 patches in: the guest sees and takes the host world's treasure
    Stats stats;
} g_st;

// Guest: kick event ids of the local player's ObjAct kicks (LocalKickEntry, main thread) for the
// next world_action. Host: remote kicks its game applied (NetKickEntry): kick event id -> time.
// MSB treasure spawns seen on this game (0x17DC300(MapItemMan, entity handle, MsbEvent, pos)):
// the fixture's pickup targets. Main thread.
std::atomic<std::uint64_t> g_pickups{0};  // map item pickups on this game (PickupEntry)
std::atomic<double> g_pickup_at{-1e9};     // Now() of the last one
std::mutex g_treasure_mu;
struct Treasure {
    std::array<float, 3> pos{};
    std::uint32_t flag = 0;  // 50000000 + item lot (the MSB event's lot; 0 = not found)
};
std::vector<Treasure> g_treasure;
std::atomic<int> g_tgate[8];  // TreasureGate results (test fixture)
std::atomic<int> g_rec[4];     // record inserts by kind, [0] removes (test fixture)
std::atomic<std::uint64_t> g_rec_man{0};  // the MapItemMan the last insert went to
std::mutex g_kick_mu;
std::vector<std::int32_t> g_kicks_out;
std::vector<std::pair<std::int32_t, double>> g_kicks_seen;

/// A map treasure's pickup flag (5AABZnnn, a map's item lot): what a guest's pickup in the host's
/// world sets. Global item flags (5000-5999, 9042-9075 ...) are the guest game's own bookkeeping.
bool MapItemFlag(std::uint32_t id) {
    return id >= 50000000u && id < 60000000u && id / 100000u % 100u != 0 &&
           progress::CategoryOf(id) == Category::item_lot_picked;
}

State& S() {
    std::call_once(g_st.once, [] {
        const char* party = std::getenv("BB_PARTY");
        const char* on = std::getenv("BB_PARTY_WORLD_ACTIONS");
        g_st.enabled = party && party[0] && !(on && on[0] == '0');
        g_st.watch = ParseIds(std::getenv("BB_PARTY_WORLD_WATCH"));
        Log("guest world actions %s (levers, doors, shortcuts, elevators, NPC talk -> the host's world)",
            g_st.enabled ? "on" : "off");
        // On by default since 0.5.9 (live 2026-10-12: a guest and the host each took their own copy
        // of the same clinic treasure, docs/party/world_actions.md 4); BB_PARTY_GUEST_PICKUP=0 off.
        const char* pk = std::getenv("BB_PARTY_GUEST_PICKUP");
        if (g_st.enabled && !(pk && pk[0] == '0')) {
            // D4, instanced world items (items.md 2.4): MSB treasure is spawned on a client too
            // (0x17DC300: role 6 / session slot gates), and its pickup sets the pickup flag and runs
            // its Lua event there (0x17D6780: the "client in another world" skip) - into the
            // host-world overlay; GuestTick copies it into the guest's own save, the host's world
            // keeps its item. Treasure visibility follows the guest's own save (progress mirror).
            const bool a = PatchBytes(0x17DC3D6, {0x0f, 0x84, 0xa5, 0x0c, 0x00, 0x00},
                                      {0x66, 0x0f, 0x1f, 0x44, 0x00, 0x00}, "treasure spawn on a client (role 6)");
            const bool b = PatchBytes(0x17DC3E3, {0x0f, 0x85, 0x98, 0x0c, 0x00, 0x00},
                                      {0x66, 0x0f, 0x1f, 0x44, 0x00, 0x00}, "treasure spawn on a client (slot)");
            const bool c = PatchBytes(0x17D6838, {0x0f, 0x84, 0x2b, 0x02, 0x00, 0x00},
                                      {0x66, 0x0f, 0x1f, 0x44, 0x00, 0x00}, "pickup flag on a client in another world");
            // The host's map item sync (net handler 0x17D2F30: "clear kind 3" for -1 / 3) dropped every
            // treasure record a guest had just spawned (live 2026-10-12: 53 records -> 0 at the join
            // sync, no 0x17D6780 removal): the guest keeps its own treasure, the host never sends any.
            const bool d = PatchBytes(0x17D34A0, {0xe8, 0x9b, 0x26, 0x00, 0x00}, {0x0f, 0x1f, 0x44, 0x00, 0x00},
                                      "keep own treasure at the host's item sync (all kinds)");
            const bool e = PatchBytes(0x17D40AB, {0xe8, 0x90, 0x1a, 0x00, 0x00}, {0x0f, 0x1f, 0x44, 0x00, 0x00},
                                      "keep own treasure at the host's item sync (treasure)");
            // A client's treasure record gets no handle of its own (0x17D4FB0 numbers records only on
            // the host: role 6 / slot gates), so all of them kept handle 0x3 and a pickup's lookup
            // (0x17D81A0, first match) found another record: number them like the host does.
            const bool g = PatchBytes(0x17D52D9, {0x74, 0x26}, {0x66, 0x90}, "own treasure handles on a client (role 6)");
            const bool h = PatchBytes(0x17D52E6, {0x75, 0x1c}, {0x66, 0x90}, "own treasure handles on a client (slot)");
            // ... and the pickup flag itself (+0x28 of the record, the lot's getItemFlag) is set past a
            // second "client in another world" gate in 0x17D6780 (0x17D6AF6).
            const bool k = PatchBytes(0x17D6AF6, {0x0f, 0x84, 0x5c, 0x05, 0x00, 0x00},
                                      {0x66, 0x0f, 0x1f, 0x44, 0x00, 0x00}, "pickup flag on a client (lot flag)");
            g_st.pickups = a && b && c && d && e && g && h && k;
            progress::SetInstancedItems(g_st.pickups);
            Log("guest treasure pickups in the host's world: %s (instanced per player)",
                g_st.pickups ? "on" : "NOT installed");
        }
        // Enemy drops per player (user decision 2026-10-11): every player's game rolls each enemy's
        // drop itself (0x17DD0B0 on enemy death; live: the same enemy rolled on host and guest);
        // a client keeps only isGuestDrop items (vials, bullets) unless 0x17DD764 je -> jmp.
        // On by default (live 2026-10-12, fresh characters: the guest kept "Iosefka's Blood Vial" from
        // its own roll of a clinic enemy the host killed); BB_PARTY_GUEST_DROPS=0 turns it off.
        const char* dr = std::getenv("BB_PARTY_GUEST_DROPS");
        if (g_st.enabled && !(dr && dr[0] == '0')) {
            const bool d = PatchBytes(0x17DD764, {0x0f, 0x84, 0x3a, 0x02, 0x00, 0x00},
                                      {0xe9, 0x3b, 0x02, 0x00, 0x00, 0x90}, "full enemy drops on a client");
            Log("guest enemy drops: %s", d ? "full, own roll per player" : "NOT installed");
        }
    });
    return g_st;
}

void WatchTick(const GameSnapshot& s) {
    State& st = S();
    static double last = 0;
    static std::vector<int> prev;
    if (st.watch.empty() || !s.world_up || s.loading || Now() - last < 0.5) {
        return;
    }
    last = Now();
    prev.resize(st.watch.size(), -2);
    for (std::size_t i = 0; i < st.watch.size(); ++i) {
        bool vis = false, own = false, host = false;
        const bool hv = progress::ReadFlag(st.watch[i], &vis);
        const bool ho = progress::ReadFlagOwnSave(st.watch[i], &own);
        const bool hh = progress::HostWorldFlag(st.watch[i], &host);
        const int code = (hv ? (vis ? 1 : 0) : 2) | (ho ? (own ? 1 : 0) : 2) << 2 | (hh ? (host ? 1 : 0) : 2) << 4;
        if (code != prev[i]) {
            prev[i] = code;
            Log("watch %u: visible %s, own save %s, host image %s (load mode %d, role %d, %s)", st.watch[i],
                hv ? (vis ? "1" : "0") : "-", ho ? (own ? "1" : "0") : "-", hh ? (host ? "1" : "0") : "-",
                progress::FlagLoadMode(), s.session_role, MapName(s.map_id).c_str());
        }
    }
}

std::string IdList(const std::vector<std::uint32_t>& ids) {
    std::string out;
    for (std::uint32_t id : ids) {
        out += (out.empty() ? "" : " ") + std::to_string(id) + "(" +
               progress::CategoryName(progress::CategoryOf(id)) + ")";
    }
    return out;
}

/// BB_PARTY_GATE_CATCHUP=1 (opt-in for 0.5.2: not run live; 2410-style flags also gate bells).
bool GateCatchupOn() {
    static const bool on = [] {
        const char* v = std::getenv("BB_PARTY_GATE_CATCHUP");
        return v && v[0] == '1';
    }();
    return on;
}

/// The area gate flags of the bosses the guest's own save has killed, into the own save (pool in
/// load mode 1). Once per steady world; logged when something was written.
void GateCatchup() {
    std::string list;
    for (const GateRule& r : GateRules()) {
        bool boss = false, also = true, gate = false;
        if (!progress::ReadFlagOwnSave(r.boss, &boss) || !boss || (r.also && (!progress::ReadFlagOwnSave(r.also, &also) || !also)) ||
            !progress::ReadFlagOwnSave(r.gate, &gate) || gate) {
            continue;
        }
        if (progress::WriteFlagOwnSave(r.gate, true)) {
            list += " " + std::to_string(r.gate) + "(boss " + std::to_string(r.boss) + ")";
        }
    }
    if (!list.empty()) {
        Log("guest catch-up: area gate flags of its own bosses into the own save:%s", list.c_str());
        RequestGameSave("guest gate catch-up");
    }
}

void GuestTick(const GameSnapshot& s, party::PartyLink* link) {
    State& st = S();
    const double now = Now();
    const bool ok = s.session_role == 6 && s.world_up && !s.loading && progress::FlagLoadMode() == 1;
    if (!ok || s.map_id != st.map) {
        st.steady = false;
        st.baselined = false;
        st.map = s.map_id;
        st.fog_in.clear();
        return;
    }
    if (!st.steady) {
        st.steady = true;
        st.steady_since = now;
        st.known.clear();
    }
    if (now - st.last_scan < 0.25 || now - st.steady_since < 3.0) {
        return;
    }
    st.last_scan = now;
    std::vector<std::pair<std::uint32_t, bool>> changes;
    if (!progress::GuestLocalWorldChanges(&changes, 4096)) {
        st.steady = false;  // overlay rebuilt / no image: a new baseline once it settles
        st.baselined = false;
        return;
    }
    if (!st.baselined) {
        // What the guest's own game wrote while loading the map (client branches of events end
        // early and set their completion flags) stays local.
        for (const auto& [id, v] : changes) {
            // Item pickups never: the overlay's item bits are the own pool's (instanced items), so
            // a difference is always a pickup this guest made (also one during a map change).
            if (!(st.pickups && MapItemFlag(id))) {
                st.known.insert(std::uint64_t(id) * 2 + (v ? 1 : 0));
            }
        }
        st.baselined = true;
        Log("guest: %zu local flag difference(s) in the host's world held back as the baseline (%s)",
            changes.size(), MapName(s.map_id).c_str());
        if (GateCatchupOn()) {
            GateCatchup();
        }
        return;
    }
    Request r;
    r.map = s.map_id;
    std::vector<std::uint32_t> local, picked;
    for (const auto& [id, v] : changes) {
        if (v && st.pickups && MapItemFlag(id) && now - g_pickup_at.load() < 15.0) {
            // D4: the guest picked up the host world's treasure - instanced: its own save only.
            if (progress::WriteFlagOwnSave(id, true)) {
                ++st.stats.own_save;
                picked.push_back(id);
            }
            continue;
        }
        const std::uint64_t k = std::uint64_t(id) * 2 + (v ? 1 : 0);
        if (st.known.count(k)) {
            continue;
        }
        st.known.insert(k);
        // A map flag only of the block the guest stands in: a streamed-in neighbour block runs its
        // constructors (NPC states, live run 9: m24_00's 12400501.. while in m24_01) - not the
        // guest's doing; once the guest's map is that block, the new baseline holds them back.
        if (id >= 10000000u && id / 100000u % 100u != 0 &&
            (id / 100000u % 100u != (s.map_id >> 24) || id / 10000u % 10u != ((s.map_id >> 16) & 0xffu))) {
            local.push_back(id);
            continue;
        }
        if (!WorldActionAllowed(id, !v, s.map_id)) {
            local.push_back(id);
            continue;
        }
        std::vector<std::uint32_t>& to = v ? r.set : r.clr;
        if (to.size() < (v ? kMaxSet : kMaxClear)) {
            to.push_back(id);
        }
    }
    if (!picked.empty()) {
        RequestGameSave("guest pickup");
        std::string hv;
        for (std::uint32_t id : picked) {
            bool h = false;
            hv += (hv.empty() ? "" : " ") + std::to_string(id) + "=" +
                  (progress::HostWorldFlag(id, &h) ? (h ? "1" : "0") : "-");
        }
        Log("guest: picked up in the host's world (instanced, own save only): %s; the host's world: %s",
            IdList(picked).c_str(), hv.c_str());
    }
    if (!local.empty()) {
        Log("guest: local flag change(s) kept local (not a world action): %s", IdList(local).substr(0, 500).c_str());
    }
    {
        std::lock_guard<std::mutex> lk(g_kick_mu);
        for (std::int32_t k : g_kicks_out) {
            if (r.kick.size() < kMaxKicks && std::find(r.kick.begin(), r.kick.end(), k) == r.kick.end()) {
                r.kick.push_back(k);
            }
        }
        g_kicks_out.clear();
    }
    for (const BossGate& g : BossGates()) {
        // B2: a boss fog this guest went through (its guest-entry event set the flag in the
        // overlay; the host's game does not get it): the host opens the fight.
        if (g.guest_flag / 100000u % 100u != (s.map_id >> 24) || g.guest_flag / 10000u % 10u != ((s.map_id >> 16) & 0xffu)) {
            continue;
        }
        bool in = false;
        progress::ReadFlag(g.guest_flag, &in);
        const bool was = st.fog_in.count(g.guest_flag) != 0;
        if (in && !was && r.fog.size() < kMaxFog) {
            st.fog_in.insert(g.guest_flag);
            r.fog.push_back(g.guest_flag);
            Log("guest: went through boss fog (event %u, flag %u): the host opens the fight", g.guest_event, g.guest_flag);
        } else if (!in && was) {
            st.fog_in.erase(g.guest_flag);
        }
    }
    if (r.set.empty() && r.clr.empty() && r.kick.empty() && r.fog.empty()) {
        return;
    }
    // The guest's own save keeps what it did (its own world after the session).
    int own = 0;
    for (std::uint32_t id : r.set) {
        own += progress::WriteFlagOwnSave(id, true) ? 1 : 0;
    }
    for (std::uint32_t id : r.clr) {  // a quest step's old state, an elevator's other position
        own += progress::WriteFlagOwnSave(id, false) ? 1 : 0;
    }
    if (own) {
        st.stats.own_save += std::uint64_t(own);
        RequestGameSave("guest world action");
    }
    if (link) {
        link->send_event(0, kEventName, RequestToJson(r));
    }
    ++st.stats.sent;
    st.stats.sent_flags += r.set.size() + r.clr.size();
    std::string kicks;
    for (std::int32_t k : r.kick) {
        kicks += (kicks.empty() ? "" : " ") + std::to_string(k);
    }
    Log("guest: world action sent to the host (%s): set %s; clear %s; ObjAct kick %s; %d written to the own save",
        MapName(s.map_id).c_str(), r.set.empty() ? "-" : IdList(r.set).c_str(),
        r.clr.empty() ? "-" : IdList(r.clr).c_str(), kicks.empty() ? "-" : kicks.c_str(), own);
}

/// Host: the guest kicked ObjAct `kick_event` in its copy of the host's world. Unless the host's
/// game applied that kick itself (a remote kick in the last 15 s), replay it as a remote kick on
/// the host's own entry (0x13AF830(blockman, idx, -1, its current state), what the ObjAct
/// manager does for a network kick): the host's EMEVD sees "ObjAct executed" and the object
/// animates in the host's world.
void ReplayKick(int slot, std::int32_t kick_event, double now) {
    {
        std::lock_guard<std::mutex> lk(g_kick_mu);
        for (const auto& [id, at] : g_kicks_seen) {
            if (id == kick_event && now - at < 15.0) {
                Log("host: slot %d's ObjAct kick %d already reached the host's game (vanilla)", slot, kick_event);
                return;
            }
        }
    }
    std::uint64_t mgr = 0, blocks = 0;
    std::int32_t nblocks = 0;
    if (!SafeGet(Guest(0x553b0f0), &mgr) || !mgr || !SafeGet(mgr + 0x20, &nblocks) || !SafeGet(mgr + 0x28, &blocks) ||
        !blocks || nblocks <= 0 || nblocks > 64) {
        Log("host: slot %d's ObjAct kick %d: no ObjAct manager", slot, kick_event);
        return;
    }
    for (std::int32_t b = 0; b < nblocks; ++b) {
        const std::uint64_t bm = blocks + std::uint64_t(b) * 0xd8;
        std::uint64_t arr = 0;
        std::int32_t n = 0;
        if (!SafeGet(bm + 0x90, &arr) || !arr || !SafeGet(bm + 0x98, &n) || n <= 0 || n > 4096) {
            continue;
        }
        for (std::int32_t i = 0; i < n; ++i) {
            const std::uint64_t e = arr + std::uint64_t(i) * 0x140;
            std::int32_t ev = -1;
            std::uint64_t obj = 0, vt = 0, fn = 0;
            if (!SafeGet(e + 0xc, &ev) || ev != kick_event) {
                continue;
            }
            std::int32_t state = 0;
            if (SafeGet(e + 0x90, &obj) && obj && SafeGet(obj, &vt) && vt && SafeGet(vt + 0x38, &fn) && fn) {
                state = reinterpret_cast<std::int32_t(BB_COOP_SYSV*)(std::uint64_t)>(fn)(obj);
            }
            using RemoteKick = std::uint8_t(BB_COOP_SYSV*)(std::uint64_t, std::int32_t, std::int32_t, std::int32_t);
            const std::uint8_t ok = reinterpret_cast<RemoteKick>(Guest(0x13af830))(bm, i, -1, state);
            Log("host: slot %d's ObjAct kick %d replayed on the host's object (block %d entry %d, state %d): %s", slot,
                kick_event, b, i, state, ok ? "kicked" : "refused by the game");
            return;
        }
    }
    Log("host: slot %d's ObjAct kick %d: no such ObjAct in the host's loaded world", slot, kick_event);
}

void HostTick(const GameSnapshot& s) {
    State& st = S();
    std::deque<std::pair<int, Request>> in;
    {
        std::lock_guard<std::mutex> lk(st.mu);
        if (!s.world_up || s.loading || progress::FlagLoadMode() != 0) {
            return;  // kept until the host's world is steady
        }
        in.swap(st.in);
    }
    for (const auto& [slot, r] : in) {
        if (!st.rate.Take(slot, int(r.set.size() + r.clr.size()), Now())) {
            ++st.stats.refused;
            Log("host: world action from slot %d refused: rate limit", slot);
            continue;
        }
        std::string list;
        bool applied_any = false;
        // Split travel: a guest alone in a map the host is not in changes that map's flags; they
        // are checked against the map it stands in (docs/party/split_travel.md 6).
        const std::uint32_t check_map = b2::MemberApart(slot) ? b2::MemberMap(slot) : s.map_id;
        if (check_map != s.map_id) {
            Log("host: world action from slot %d, alone in %s: checked against its map", slot, MapName(check_map).c_str());
        }
        auto apply = [&](std::uint32_t id, bool v) {
            if (!WorldActionAllowed(id, !v, check_map)) {
                ++st.stats.refused;
                list += " " + std::to_string(id) + "(refused)";
                return;
            }
            bool before = false;
            progress::ReadFlag(id, &before);
            const bool ok = before == v || progress::WriteFlagOwnSave(id, v);
            st.stats.applied += ok && before != v ? 1 : 0;
            applied_any = applied_any || (ok && before != v);
            list += " " + std::to_string(id) + (v ? "=1" : "=0") + (before == v ? "(was)" : ok ? "" : "(NOT written)") +
                    "[" + progress::CategoryName(progress::CategoryOf(id)) + "]";
        };
        for (std::uint32_t id : r.set) {
            apply(id, true);
        }
        for (std::uint32_t id : r.clr) {
            apply(id, false);
        }
        for (std::int32_t k : r.kick) {
            ReplayKick(slot, k, Now());
        }
        for (std::uint32_t f : r.fog) {
            // B2: the guest went through a boss fog before the host: the host's game sets its
            // host-entered flag, which starts the boss (its `ボスが動き出す` waits on it). The
            // host still walks in through its own fog.
            const BossGate* g = BossGateByGuestFlag(f);
            bool host_in = false, dead = false;
            if (!g) {
                continue;
            }
            progress::ReadFlag(g->host_flag, &host_in);
            progress::ReadFlag(g->boss_flag, &dead);
            if (!BossGateHostOpens(*g, true, host_in, dead, s.map_id)) {
                Log("host: boss fog: slot %d went in (flag %u); nothing to open (host in %d, boss dead %d, host in %s)",
                    slot, f, host_in ? 1 : 0, dead ? 1 : 0, MapName(s.map_id).c_str());
                continue;
            }
            const bool ok = progress::WriteFlagOwnSave(g->host_flag, true);
            bool after = false;
            progress::ReadFlag(g->host_flag, &after);
            Log("host: boss fog: slot %d went in first (event %u): host-entered flag %u%s -> %d; the boss starts, "
                "the host's own fog stays", slot, g->guest_event, g->host_flag, ok ? "" : " NOT written", after ? 1 : 0);
        }
        if (applied_any) {
            // The host's own save holds the host's world: without a request the change waited for
            // the game's next autosave, and a quit soon after lost it (NPC quest flags read 0 on the
            // host's Continue while the guest's own save had them).
            RequestGameSave("guest world action (host's world)");
        }
        if (!list.empty()) {
            Log("host: slot %d changed the host's world (guest in %s, host in %s):%s", slot, MapName(r.map).c_str(),
                MapName(s.map_id).c_str(), list.c_str());
        }
    }
}

bool PutLocal(const float target[3], float px, float pz, float dist, float angle_deg, std::string* what) {
    const std::uint64_t wcm = Guest(0x553e878);
    std::uint64_t man = 0, player = 0, vt = 0, fn = 0;
    if (!wcm || !SafeGet(wcm, &man) || !man || !SafeGet(man + 0x60, &player) || !player ||
        !SafeGet(player, &vt) || !SafeGet(vt + 0x5f8, &fn) || !fn) {
        return false;
    }
    float h = std::sqrt(px * px + pz * pz);
    if (h < 1e-3f) {
        px = 0, pz = 1, h = 1;
    }
    px /= h, pz /= h;
    const float a = angle_deg * 3.14159265f / 180.0f;
    const float dx = px * std::cos(a) + pz * std::sin(a), dz = -px * std::sin(a) + pz * std::cos(a);
    alignas(16) float pos[4] = {target[0] + dx * dist, target[1], target[2] + dz * dist, 1.0f};
    // forward(yaw) = (-sin yaw, -cos yaw) (party_guestsvc StandAt): face the target.
    const float yaw = std::atan2(-(target[0] - pos[0]), -(target[2] - pos[2]));
    alignas(16) float rot[4] = {0, yaw, 0, 0};
    using WarpFn = void(BB_COOP_SYSV*)(std::uint64_t, const float*, const float*, std::uint64_t);
    reinterpret_cast<WarpFn>(fn)(player, pos, rot, 0);
    char b[160];
    std::snprintf(b, sizeof b, "target (%.2f, %.2f, %.2f), standing at (%.2f, %.2f, %.2f) yaw %.2f", target[0],
                  target[1], target[2], pos[0], pos[1], pos[2], yaw);
    if (what) {
        *what = b;
    }
    return true;
}


// BB_PARTY_WORLDACT_TEST (live tests, the guest): "obj=E[/E...];chr=E[/E...];after=S": S s
// (default 8) after the guest's world became steady in the host's world, for each map object
// (lever, door) and then each character (NPC): stand around it (8 directions x 1.0 / 1.6 m) until
// an action prompt shows, press Cross (then three more for a talk: the dialogue lines; "talk=N": N
// presses in all), wait, next.
struct Fixture {
    bool parsed = false;
    std::vector<std::int32_t> objs, chrs;
    int pickups = 0;  // "pickup=N": the N treasures nearest the guest, one try each
    std::string map;  // "map=NAME": only while the current map's name contains NAME
    int kills = 0;    // "kill=N": N times the nearest live map enemy: ForceDead, then pick up its drop
    std::int32_t loot = 0;  // "loot=ENTITY": wait until that enemy is dead (killed anywhere), then pick up its drop
    std::uint32_t grab = 0;  // "grab=FLAG": the treasure with that pickup flag, picked up through the game's own
                             // pickup function 0x17D8570 (what Cross on it calls) - no standing spot needed
    bool lootall = false;    // "lootall": every enemy whose drop this game rolls: stand on it, Cross x5
    std::size_t lootall_idx = 0;
    int lootall_stage = 0;
    int loot_stage = 0;
    double loot_since = 0;
    bool attack = false;  // "attack": kill with the weapon (R1 taps) instead of ForceDead
    bool has_near = false;  // "near=X:Y:Z": the treasure nearest that point, not the player
    float near[3] = {};
    int kill_stage = 0;
    float kill_pos[3] = {};
    std::int32_t kill_id = 0;
    double after = 8;
    int talk = 4;  // "talk=N": Cross presses at a character (the first opens the talk), default 4
    std::size_t idx = 0;
    int tries = 0, presses = 0;
    double next = 0, release = 0;
    bool done = false;
} g_fx;

void FixtureList(const std::string& v, const char* key, std::vector<std::int32_t>* out) {
    const std::size_t at = v.find(key);
    if (at == std::string::npos) {
        return;
    }
    const std::size_t from = at + std::strlen(key), end = v.find(';', at);
    std::string part = v.substr(from, end == std::string::npos ? std::string::npos : end - from);
    for (char& c : part) {
        c = c == '/' ? ',' : c;
    }
    for (std::uint32_t id : ParseIds(part.c_str())) {
        out->push_back(std::int32_t(id));
    }
}

// The local player's position.
bool MyPos(float out[3]) {
    std::uint64_t man = 0, player = 0;
    if (!SafeGet(Guest(0x553e878), &man) || !man || !SafeGet(man + 0x60, &player) || !player) {
        return false;
    }
    // The physics position first (PickPlayerPos: +0xC0 goes stale on a guest in the host's world).
    std::uint64_t a = 0, b = 0, c = 0, d = 0;
    float phys[3] = {}, drawn[4] = {};
    const bool phys_ok = SafeGet(player + 0x58, &a) && a && SafeGet(a + 8, &b) && b && SafeGet(b + 0x3b0, &c) && c &&
                         SafeGet(c + 0x68, &d) && d && SafeRead(d + 0x1e0, phys, sizeof phys);
    const bool drawn_ok = SafeRead(player + 0xc0, drawn, sizeof drawn);
    const float* p = PickPlayerPos(phys_ok, phys, drawn_ok, drawn);
    if (!p) {
        return false;
    }
    std::memcpy(out, p, 12);
    return true;
}

// The nearest live map character (WorldChrMan block lists: +0x28 blocks of 0x160, count +0x20;
// block +0xC0 list of 0x38-byte entries, count +0xB8; entry +0 the ChrIns) within 45 m that is not
// a player (PlayerIns +0x78 chr type is only meaningful for players: skip the local player and
// chrs whose entity +0x3B8 is negative).
std::uint64_t NearestEnemy(const float me[3], float pos[3], const std::vector<std::uint64_t>& skip) {
    std::uint64_t wcm = 0, blocks = 0, local = 0;
    std::int32_t nb = 0;
    if (!SafeGet(Guest(0x553e878), &wcm) || !wcm || !SafeGet(wcm + 0x20, &nb) || !SafeGet(wcm + 0x28, &blocks) ||
        !blocks || nb <= 0 || nb > 64) {
        return 0;
    }
    SafeGet(wcm + 0x60, &local);
    std::uint64_t best = 0;
    float bd = 45.0f * 45.0f;
    int seen = 0, dead = 0, logged = 0;
    for (std::int32_t b = 0; b < nb; ++b) {
        std::uint64_t list = 0;
        std::int32_t n = 0;
        if (!SafeGet(blocks + std::uint64_t(b) * 0x160 + 0xb8, &n) || n <= 0 || n > 4096 ||
            !SafeGet(blocks + std::uint64_t(b) * 0x160 + 0xc0, &list) || !list) {
            continue;
        }
        for (std::int32_t k = 0; k < n; ++k) {
            std::uint64_t chr = 0, cm = 0, dm = 0;
            std::int32_t hp = 0;
            float p[4] = {};
            if (!SafeGet(list + std::uint64_t(k) * 0x38, &chr) || !chr || chr == local ||
                std::find(skip.begin(), skip.end(), chr) != skip.end() || !SafeRead(chr + 0xc0, p, sizeof p)) {
                continue;
            }
            ++seen;
            if (!SafeGet(chr + 0x3b0, &cm) || !cm || !SafeGet(cm + 0x20, &dm) || !dm || !SafeGet(dm + 0xf8, &hp) ||
                hp <= 0) {
                ++dead;
                continue;
            }
            const float dx = p[0] - me[0], dy = p[1] - me[1], dz = p[2] - me[2];
            const float d = dx * dx + dy * dy + dz * dz;
            std::int32_t ent = 0, type = -1;
            SafeGet(chr + 0x3b8, &ent);
            SafeGet(chr + 0x78, &type);
            if ((ent >= 10000000 && ent <= 10000010) || type == 0 || type == 1 || type == 2 || type == 8 || type == 12) {
                continue;  // a player (the host or another guest: chr type 0/1/2/8/12), not an enemy
            }
            if (type == 4) {
                continue;  // live (Central Yharnam lamp): a type-4 chr at the lamp took no damage - not hostile
            }
            if (hp >= 999) {
                continue;  // live: an untouchable 999-HP chr stands on the lamp (the lamp's own chr)
            }
            if (d < 30.0f * 30.0f && logged < 6) {
                ++logged;
                Log("test: fixture: candidate chr %p +0x3B8 %d +0x78 %d HP %d at %.1f m", reinterpret_cast<void*>(chr),
                    ent, type, hp, std::sqrt(d));
            }
            if (d < bd) {
                bd = d;
                best = chr;
                std::memcpy(pos, p, 12);
            }
        }
    }
    if (!best) {
        Log("test: fixture: map characters seen: %d (%d dead / unreadable), none alive within 45 m", seen, dead);
    }
    return best;
}

void KillTick(Fixture& f, double now) {
    static std::vector<std::uint64_t> done_ids;
    static std::uint64_t kill_chr = 0;
    float me[3] = {};
    if (!MyPos(me)) {
        return;
    }
    if (f.kill_stage == 0) {
        kill_chr = NearestEnemy(me, f.kill_pos, done_ids);
        f.kill_id = 0;
        if (kill_chr) {
            SafeGet(kill_chr + 0x3b8, &f.kill_id);
        }
        if (!kill_chr) {
            Log("test: fixture: no live enemy within 45 m");
            f.kills = 0;
            return;
        }
        done_ids.push_back(kill_chr);
        if (f.attack) {
            f.kill_stage = 10;  // weapon: R1 taps facing it (stages 10..)
            Log("test: fixture: attacking enemy (chr +0x3B8 %d) at (%.1f, %.1f, %.1f) with the weapon", f.kill_id,
                f.kill_pos[0], f.kill_pos[1], f.kill_pos[2]);
            return;
        }
        // What Lua ForceDead (0x13320C0) does with the chr: clear +0x1E3 bit 5, then 0x18BF9A0(chr)
        // (HP 0 and the dead flag): the enemy's normal death on this game.
        std::uint8_t b = 0;
        if (SafeGet(kill_chr + 0x1e3, &b)) {
            b = std::uint8_t(b & 0xdf);
            SafeWrite(kill_chr + 0x1e3, &b, 1);
        }
        reinterpret_cast<void(BB_COOP_SYSV*)(std::uint64_t)>(Guest(0x18bf9a0))(kill_chr);
        Log("test: fixture: enemy (chr +0x3B8 %d) at (%.1f, %.1f, %.1f) killed by this player (ForceDead)", f.kill_id,
            f.kill_pos[0], f.kill_pos[1], f.kill_pos[2]);
        f.kill_stage = 1;
        f.next = now + 6.0;  // death animation; the drop appears
        return;
    }
    if (f.kill_stage >= 10) {
        // Stand 1.3 m in front of it, facing it, R1; until its HP is 0 (60 taps at most).
        std::uint64_t cm = 0, dm = 0;
        std::int32_t hp = 1;
        float p[4] = {};
        if (SafeRead(kill_chr + 0xc0, p, sizeof p)) {
            std::memcpy(f.kill_pos, p, 12);
        }
        const bool read = SafeGet(kill_chr + 0x3b0, &cm) && cm && SafeGet(cm + 0x20, &dm) && dm && SafeGet(dm + 0xf8, &hp);
        if ((read && hp <= 0) || f.kill_stage >= 70) {
            Log("test: fixture: enemy (chr +0x3B8 %d) %s after %d weapon tap(s)", f.kill_id,
                read && hp <= 0 ? "killed by this player's weapon" : "still alive", f.kill_stage - 10);
            f.kill_stage = 1;
            f.next = now + 6.0;
            return;
        }
        if ((f.kill_stage - 10) % 6 == 0) {
            std::string what;
            PutLocal(f.kill_pos, 0.0f, 1.0f, 1.3f, 0.0f, &what);
        }
        runtime_pad_director_press(0x800);  // R1
        f.release = now + 0.12;
        ++f.kill_stage;
        f.next = now + 0.7;
        Log("test: fixture: R1 %s, enemy HP %d", StepTag(f.kill_stage - 10).c_str(), read ? hp : -1);
        return;
    }
    if (f.kill_stage >= 1 && f.kill_stage <= 3 && std::getenv("BB_PARTY_WORLDACT_NOWALK")) {
        f.kill_stage = 4;  // no walk to the corpse: the drop is taken through the pickup function (lootall)
    }
    if (f.kill_stage >= 1 && f.kill_stage <= 3) {
        std::string what;
        if (f.kill_stage == 1) {
            PutLocal(f.kill_pos, 0.0f, 1.0f, 0.3f, 0.0f, &what);
            Log("test: fixture: at enemy %d's spot: %s", f.kill_id, what.c_str());
        }
        std::uint32_t pp = 0;
        const bool up = GuestSvcPromptUp(&pp);
        runtime_pad_director_press(0x4000);
        f.release = now + 0.15;
        Log("test: fixture: drop of enemy %d: prompt %s %u; Cross", f.kill_id, up ? "up" : "not seen", pp);
        ++f.kill_stage;
        f.next = now + 2.0;
        return;
    }
    f.kill_stage = 0;
    --f.kills;
    f.next = now + 2.0;
}

void FixtureTick(double now) {
    Fixture& f = g_fx;
    if (const std::uint64_t m = g_rec_man.load()) {
        // Test diagnostics: the treasure record count on this game, logged when it changes.
        static int last = -1;
        std::uint64_t node = 0;
        int c = 0;
        SafeGet(m + 0x28, &node);
        for (; node && c < 4096; ++c) {
            if (!SafeGet(node, &node)) {
                break;
            }
        }
        if (c != last) {
            Log("test: treasure records on this game: %d -> %d (inserts %d, removes %d, role %d)", last, c,
                g_rec[3].load(), g_rec[0].load(), LocalSessionRole());
            last = c;
        }
    }
    if (!f.parsed) {
        f.parsed = true;
        const char* t = std::getenv("BB_PARTY_WORLDACT_TEST");
        if (!t || !t[0]) {
            f.done = true;
            return;
        }
        const std::string v(t);
        FixtureList(v, "obj=", &f.objs);
        FixtureList(v, "chr=", &f.chrs);
        if (const std::size_t a = v.find("after="); a != std::string::npos) {
            f.after = std::atof(v.c_str() + a + 6);
        }
        if (const std::size_t a = v.find("pickup="); a != std::string::npos) {
            f.pickups = std::atoi(v.c_str() + a + 7);
        }
        if (const std::size_t a = v.find("map="); a != std::string::npos) {
            f.map = v.substr(a + 4, v.find(';', a) == std::string::npos ? std::string::npos : v.find(';', a) - a - 4);
        }
        f.attack = v.find("attack") != std::string::npos;
        if (const std::size_t a = v.find("near="); a != std::string::npos) {
            f.has_near = std::sscanf(v.c_str() + a + 5, "%f:%f:%f", &f.near[0], &f.near[1], &f.near[2]) == 3;
        }
        if (const std::size_t a = v.find("grab="); a != std::string::npos) {
            f.grab = std::uint32_t(std::strtoul(v.c_str() + a + 5, nullptr, 10));
        }
        f.lootall = v.find("lootall") != std::string::npos;
        if (const std::size_t a = v.find("loot="); a != std::string::npos) {
            f.loot = std::atoi(v.c_str() + a + 5);
        }
        if (const std::size_t a = v.find("talk="); a != std::string::npos) {
            f.talk = std::clamp(std::atoi(v.c_str() + a + 5), 1, 12);
        }
        if (const std::size_t a = v.find("kill="); a != std::string::npos) {
            f.kills = std::atoi(v.c_str() + a + 5);
        }
        Log("test: fixture: %zu object(s), %zu character(s), %.0f s after a steady world", f.objs.size(),
            f.chrs.size(), f.after);
    }
    if (f.release > 0 && now >= f.release) {
        runtime_pad_director_press(0);
        f.release = 0;
    }
    State& st = S();
    if (f.done || !st.steady || now - st.steady_since < f.after || now < f.next ||
        (!f.map.empty() && MapName(st.map).find(f.map) == std::string::npos)) {
        return;
    }
    const std::size_t total = f.objs.size() + f.chrs.size();
    if (f.idx >= total && (f.grab || f.lootall)) {
        // MapItemMan (*0x553D6E0) record lists (0x17D81A0): kind 3 (treasure) at +0x28, kind 2 (enemy
        // drops) at +0x38; node +0 next, +0x20 handle, +0x28 pickup flag, +0x54 item count, items from
        // +0x58 (16 bytes: +0 id with category bits, +4 count). The pickup 0x17D8570(man, &handle) is
        // what Cross on the item calls.
        std::uint64_t man = 0;
        if (!SafeGet(Guest(0x553d6e0), &man) || !man) {
            return;
        }
        auto items = [](std::uint64_t node) {
            std::int32_t n = 0;
            SafeGet(node + 0x54, &n);
            std::string out;
            for (std::int32_t i = 0; i < n && i < 8; ++i) {
                std::uint32_t id = 0, cnt = 0;
                SafeGet(node + 0x58 + std::uint64_t(i) * 16, &id);
                SafeGet(node + 0x58 + std::uint64_t(i) * 16 + 4, &cnt);
                char b[48];
                std::snprintf(b, sizeof b, " %#x x%u", id, cnt);
                out += b;
            }
            return out.empty() ? std::string(" (none)") : out;
        };
        using Pick = void(BB_COOP_SYSV*)(std::uint64_t, std::int32_t*);
        const Pick pick = reinterpret_cast<Pick>(Guest(0x17d8570));
        if (f.grab) {
            std::uint64_t node = 0;
            SafeGet(man + 0x28, &node);
            std::uint64_t hit = 0;
            int count = 0;
            std::string seen;
            for (int guard = 0; node && guard < 4096; ++guard, ++count) {
                std::uint32_t flag = 0;
                SafeGet(node + 0x28, &flag);
                if (flag == f.grab) {
                    hit = node;
                }
                if (count < 6) {
                    seen += " " + std::to_string(flag);
                }
                if (!SafeGet(node, &node)) {
                    break;
                }
            }
            if (!hit) {
                int n18 = 0, n38 = 0;
                for (std::uint64_t list : {man + 0x18, man + 0x38}) {
                    std::uint64_t q = 0;
                    SafeGet(list, &q);
                    int c = 0;
                    for (; q && c < 4096; ++c) {
                        if (!SafeGet(q, &q)) {
                            break;
                        }
                    }
                    (list == man + 0x18 ? n18 : n38) = c;
                }
                Log("test: fixture: grab: no treasure record with flag %u (%d kind-3 records, first flags%s; kind-1 %d, "
                    "kind-2 %d; MapItemMan %p, inserts went to %p); inserts k1 %d k2 %d k3 %d, removes %d; spawn gates: pass %d, no gd %d, role %d, slot %d, chr type %d, handle %d, entity %d",
                    f.grab, count, seen.c_str(), n18, n38, reinterpret_cast<void*>(man), reinterpret_cast<void*>(g_rec_man.load()), g_rec[1].load(), g_rec[2].load(), g_rec[3].load(), g_rec[0].load(),
                    g_tgate[0].load(), g_tgate[1].load(), g_tgate[2].load(),
                    g_tgate[3].load(), g_tgate[4].load(), g_tgate[5].load(), g_tgate[6].load());
            } else {
                bool vis = false, own = false, host = false;
                progress::ReadFlag(f.grab, &vis);
                progress::ReadFlagOwnSave(f.grab, &own);
                progress::HostWorldFlag(f.grab, &host);
                std::int32_t handle = 0;
                SafeGet(hit + 0x20, &handle);
                const std::uint64_t picks0 = g_pickups.load();
                const std::string what = items(hit);
                std::uint16_t f48 = 0;
                SafeGet(hit + 0x48, &f48);
                std::int32_t f24 = 0;
                SafeGet(hit + 0x24, &f24);
                Log("test: fixture: grab: record flags +0x48 %#x (0x40 live, 0x80 host-owned), +0x24 %d", unsigned(f48), f24);
                using Find = std::uint64_t(BB_COOP_SYSV*)(std::uint64_t, std::int32_t);
                const std::uint64_t found = reinterpret_cast<Find>(Guest(0x17d81a0))(man, handle);
                std::string hs;
                {
                    std::uint64_t q = 0;
                    SafeGet(man + 0x28, &q);
                    for (int g = 0; q && g < 12; ++g) {
                        std::int32_t hh = 0, ff = 0;
                        std::uint16_t fl = 0;
                        SafeGet(q + 0x20, &hh);
                        SafeGet(q + 0x28, &ff);
                        SafeGet(q + 0x48, &fl);
                        char b[64];
                        std::snprintf(b, sizeof b, " [%#x %d %#x]", unsigned(hh), ff, unsigned(fl));
                        hs += b;
                        if (!SafeGet(q, &q)) {
                            break;
                        }
                    }
                }
                Log("test: fixture: grab: lookup 0x17D81A0(%#x) -> %p (record %p); list [handle flag bits]:%s, next handle %#x",
                    unsigned(handle), reinterpret_cast<void*>(found), reinterpret_cast<void*>(hit), hs.c_str(),
                    [&] { std::uint32_t c = 0; SafeGet(man + 0xc, &c); return c; }());
                const int rm0 = g_rec[0].load();
                pick(man, &handle);
                {
                    bool still = false;
                    std::uint64_t q = 0;
                    SafeGet(man + 0x28, &q);
                    for (int g = 0; q && g < 4096; ++g) {
                        still = still || q == hit;
                        if (!SafeGet(q, &q)) {
                            break;
                        }
                    }
                    std::uint16_t f2 = 0;
                    SafeGet(hit + 0x48, &f2);
                    Log("test: fixture: grab: after the pickup: record %s, removes %d -> %d, flags %#x", still ? "still listed" : "gone",
                        rm0, g_rec[0].load(), unsigned(f2));
                }
                Log("test: fixture: grab: treasure flag %u (handle %#x, items%s) picked up through 0x17D8570: %s; "
                    "before: visible %d, own save %d, host %d", f.grab, unsigned(handle), what.c_str(),
                    g_pickups.load() > picks0 ? "pickup ran" : "pickup did NOT run", int(vis), int(own), int(host));
            }
            f.grab = 0;
            f.next = now + 3.0;
            return;
        }
        // lootall: every enemy drop record this game holds, once.
        static std::vector<std::int32_t> done;
        std::uint64_t node = 0;
        SafeGet(man + 0x38, &node);
        for (int guard = 0; node && guard < 4096; ++guard) {
            std::int32_t handle = 0;
            SafeGet(node + 0x20, &handle);
            if (std::find(done.begin(), done.end(), handle) == done.end()) {
                done.push_back(handle);
                const std::string what = items(node);
                const std::uint64_t picks0 = g_pickups.load();
                std::int32_t h = handle;
                pick(man, &h);
                Log("test: fixture: lootall: enemy drop record %#x (items%s) picked up through 0x17D8570: %s", unsigned(handle),
                    what.c_str(), g_pickups.load() > picks0 ? "pickup ran" : "pickup did NOT run");
                f.next = now + 2.0;
                return;
            }
            if (!SafeGet(node, &node)) {
                break;
            }
        }
        // Same text while waiting (the reaper sees an idle run); a hard 25 s timeout.
        static double since = 0;
        if (!since) {
            since = now;
        }
        if (now - since > 25.0) {
            Log("test: fixture: lootall: FAILED / done: no new drop record for 25 s; stopping");
            f.lootall = false;
            f.done = true;
            return;
        }
        Log("test: fixture: lootall: no new drop record yet");
        f.next = now + 5.0;
        return;
    }
    if (f.idx >= total && f.pickups <= 0 && f.loot > 0) {
        // The enemy's chr (0x13C97A0(entity)); its HP from the data module +0xF8 (max +0xFC).
        using Find = std::uint64_t(BB_COOP_SYSV*)(std::int32_t, std::int32_t, std::uint64_t);
        const std::uint64_t chr = reinterpret_cast<Find>(Guest(0x13c97a0))(f.loot, f.loot, 0);
        std::uint64_t cm = 0, dm = 0;
        std::int32_t hp = -1;
        float p[4] = {};
        const bool ok = chr && SafeRead(chr + 0xc0, p, sizeof p) && SafeGet(chr + 0x3b0, &cm) && cm &&
                        SafeGet(cm + 0x20, &dm) && dm && SafeGet(dm + 0xf8, &hp);
        if (f.loot_stage == 0) {
            if (!f.loot_since) {
                f.loot_since = now;
                Log("test: fixture: loot: waiting for enemy %d to die (%s, HP %d)", f.loot, ok ? "here" : "not found", hp);
            }
            if (ok && hp <= 0) {
                std::memcpy(f.kill_pos, p, 12);
                Log("test: fixture: loot: enemy %d is dead at (%.1f, %.1f, %.1f); its drop next", f.loot, p[0], p[1], p[2]);
                f.loot_stage = 1;
                f.next = now + 5.0;  // death animation, the drop appears
            } else if (now - f.loot_since > 30) {
                Log("test: fixture: loot: enemy %d did not die", f.loot);
                f.loot = 0;
            } else {
                Log("test: fixture: loot: waiting for the enemy to die");  // same text: the reaper sees idleness
                f.next = now + 5.0;
            }
            return;
        }
        if (f.loot_stage <= 10) {
            static std::uint64_t picks0 = 0;
            if (f.loot_stage == 1) {
                picks0 = g_pickups.load();
            } else if (g_pickups.load() > picks0) {
                Log("test: fixture: loot: enemy %d's drop picked up after %d spot(s)", f.loot, f.loot_stage - 1);
                f.loot = 0;
                f.next = now + 3.0;
                return;
            }
            std::string what;
            PutLocal(f.kill_pos, 0.0f, 1.0f, f.loot_stage <= 5 ? 0.5f : 1.0f, float(f.loot_stage % 5) * 72.0f, &what);
            runtime_pad_director_press(0x4000);
            f.release = now + 0.15;
            Log("test: fixture: loot %s: Cross at the drop", StepTag(f.loot_stage).c_str());
            ++f.loot_stage;
            f.next = now + 1.2;
            return;
        }
        Log("test: fixture: loot: no pickup at enemy %d's spot", f.loot);
        f.loot = 0;
        return;
    }
    if (f.idx >= total && f.pickups <= 0 && f.kills > 0) {
        KillTick(f, now);
        return;
    }
    if (f.idx >= total && f.pickups > 0) {
        // The nearest treasure not tried yet: stand on it, Cross (pick up), next one 5 s later.
        static std::array<float, 3> cur{};
        static std::uint64_t picks_before = 0;
        if (f.presses >= 1) {
            // Around the treasure (8 directions x 0.6 / 1.1 m, facing it), Cross at each spot until
            // the game's pickup function ran (PickupEntry).
            if (g_pickups.load() > picks_before || f.presses > 16) {
                Log("test: fixture: treasure: %s after %d spot(s)",
                    g_pickups.load() > picks_before ? "picked up" : "no pickup", f.presses);
                f.presses = 0;
                f.next = now + 4.0;
                --f.pickups;
                return;
            }
            if (f.release > 0) {
                return;
            }
            std::string what;
            // 0.0 / 0.3 m first (the item glow is often off the MSB point), then 0.6 / 1.1 m around it.
            const float dd = f.presses <= 2 ? 0.3f * float(f.presses - 1) : f.presses <= 9 ? 0.6f : 1.1f;
            PutLocal(cur.data(), 0.0f, 1.0f, dd, float(f.presses % 8) * 45.0f, &what);
            Log("test: fixture: treasure %s: Cross", StepTag(f.presses).c_str());
            runtime_pad_director_press(0x4000);
            f.release = now + 0.15;
            ++f.presses;
            f.next = now + 1.0;
            return;
        }
        static std::vector<std::array<float, 3>> tried;
        const char* only = std::getenv("BB_PARTY_WORLDACT_TEST");
        const char* fl = only ? std::strstr(only, "flag=") : nullptr;
        const std::uint32_t want = fl ? std::uint32_t(std::strtoul(fl + 5, nullptr, 10)) : 0;
        float me[4] = {};
        std::uint64_t wcm = 0, man = 0, player = 0;
        if (!SafeGet(Guest(0x553e878), &man) || !man || !SafeGet(man + 0x60, &player) || !player ||
            !SafeRead(player + 0xc0, me, sizeof me)) {
            return;
        }
        (void)wcm;
        std::array<float, 3> best{};
        float bd = 1e9f;
        {
            std::lock_guard<std::mutex> lk(g_treasure_mu);
            for (const Treasure& tr : g_treasure) {
                const auto& t = tr.pos;
                if (std::find(tried.begin(), tried.end(), t) != tried.end() || (want && tr.flag != want)) {
                    continue;
                }
                bool taken = false;
                if (!want && tr.flag && progress::ReadFlag(tr.flag, &taken) && taken) {
                    continue;  // taken in this guest's view (its own pickups, instanced)
                }
                const float* from = f.has_near ? f.near : me;
                const float dx = t[0] - from[0], dy = t[1] - from[1], dz = t[2] - from[2];
                const float d = dx * dx + dy * dy + dz * dz;
                if (d < bd) {
                    bd = d;
                    best = t;
                }
            }
            if (f.tries == 0) {
                // The nearest treasures with their pickup flag and this player's view (taken or not).
                std::vector<std::pair<float, const Treasure*>> near;
                const float* from = f.has_near ? f.near : me;
                for (const Treasure& tr : g_treasure) {
                    const float dx = tr.pos[0] - from[0], dy = tr.pos[1] - from[1], dz = tr.pos[2] - from[2];
                    near.emplace_back(std::sqrt(dx * dx + dy * dy + dz * dz), &tr);
                }
                std::sort(near.begin(), near.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
                for (std::size_t i = 0; i < near.size() && i < 8; ++i) {
                    bool taken = false;
                    const bool known = near[i].second->flag && progress::ReadFlag(near[i].second->flag, &taken);
                    Log("test: fixture: treasure %zu: (%.1f, %.1f, %.1f) %.1f m, flag %u %s", i, near[i].second->pos[0],
                        near[i].second->pos[1], near[i].second->pos[2], near[i].first, near[i].second->flag,
                        !known ? "?" : taken ? "taken" : "NOT taken");
                }
                std::size_t with = 0;
                for (const Treasure& tr : g_treasure) {
                    with += tr.flag ? 1 : 0;
                }
                Log("test: fixture: %zu treasure spawn(s) seen on this game (%zu with a pickup flag)", g_treasure.size(),
                    with);
            }
        }
        if (bd > 60.0f * 60.0f) {
            f.pickups = 0;
            Log("test: fixture: no untaken treasure within 60 m (nearest %.0f m)", std::sqrt(bd));
            return;
        }
        if (f.presses == 0) {
            tried.push_back(best);
            std::string what;
            cur = best;
            picks_before = g_pickups.load();
            PutLocal(best.data(), 0.0f, 1.0f, 0.6f, 0.0f, &what);
            Log("test: fixture: treasure at (%.1f, %.1f, %.1f), %.1f m away: %s", best[0], best[1], best[2],
                std::sqrt(bd), what.c_str());
            f.presses = 1;
            f.next = now + 1.2;
            ++f.tries;
            return;
        }
        std::uint32_t pp = 0;
        const bool up = GuestSvcPromptUp(&pp);
        Log("test: fixture: treasure: prompt %s %u; Cross", up ? "up" : "not seen", pp);
        runtime_pad_director_press(0x4000);
        f.release = now + 0.15;
        f.presses = 0;
        f.next = now + 5.0;
        --f.pickups;
        return;
    }
    if (f.idx >= total) {
        f.done = true;
        Log("test: fixture done");
        return;
    }
    const bool obj = f.idx < f.objs.size();
    const char* kind = obj ? "object" : "character";
    const std::int32_t ent = obj ? f.objs[f.idx] : f.chrs[f.idx - f.objs.size()];
    std::uint32_t prompt = 0;
    if (f.presses > 0) {
        if (!obj && f.presses < f.talk) {
            runtime_pad_director_press(0x4000);  // talk: the next dialogue lines
            f.release = now + 0.15;
            ++f.presses;
            f.next = now + 1.5;
            Log("test: fixture: character %d: Cross #%d", ent, f.presses);
            return;
        }
        Log("test: fixture: %s %d done", kind, ent);
        if (obj) {
            runtime_pad_director_press(0x2000);  // Circle: back out of a menu the object opened
            f.release = now + 0.15;
        }
        ++f.idx;
        f.tries = 0;
        f.presses = 0;
        f.next = now + 1.0;
        return;
    }
    if (f.tries > 0 && GuestSvcPromptUp(&prompt)) {
        Log("test: fixture: %s %d: prompt %u up after %d spot(s); Cross", kind, ent, prompt, f.tries);
        runtime_pad_director_press(0x4000);
        f.release = now + 0.15;
        f.presses = 1;
        f.next = now + (obj ? 8.0 : 1.5);
        return;
    }
    if (f.tries >= 16) {
        Log("test: fixture: %s %d: no prompt at 16 spots; next", kind, ent);
        ++f.idx;
        f.tries = 0;
        return;
    }
    const float angle = float(f.tries % 8) * 45.0f, dist = f.tries < 8 ? 1.0f : 1.6f;
    std::string what;
    const bool ok = obj ? StandAtObject(ent, dist, angle, &what) : StandAtChr(ent, dist, angle, &what);
    ++f.tries;
    f.next = now + 1.0;
    if (!ok) {
        Log("test: fixture: %s %d not loaded", kind, ent);
        f.tries = 16;
        return;
    }
    if (f.tries == 1 || f.tries == 9) {
        Log("test: fixture: %s %d: %s", kind, ent, what.c_str());
    }
}


// ObjAct kicks (levers, doors, elevators): the per-block ObjAct manager (0xD8 bytes; entries at
// +0x90, 0x140 each, count +0x98; entry +0x8 list index, +0xC kick event id, +0x58 object handle,
// +0x5C trigger state). 0x13AE370(blockman, idx, chr) = the local player's kick (the action button
// update 0x13ADCC0); 0x13AF830(blockman, idx, chr, state) = a kick another player made, applied
// by the ObjAct manager update 0x13B2790 from its network queue (0x13B2F90). Logged both ways.
std::atomic<std::uint64_t> g_kicks_local{0}, g_kicks_net{0};
void LogKick(const char* who, std::uint64_t man, std::uint64_t idx, std::uint64_t a3, std::uint64_t a4) {
    std::int32_t n = 0, list = -1, ev = -1, handle = -1, trig = -1;
    std::uint64_t arr = 0;
    if (SafeGet(man + 0x98, &n) && SafeGet(man + 0x90, &arr) && arr && std::int32_t(idx) >= 0 &&
        std::int32_t(idx) < n) {
        const std::uint64_t e = arr + (idx & 0xffffffffu) * 0x140;
        SafeGet(e + 0x8, &list);
        SafeGet(e + 0xc, &ev);
        SafeGet(e + 0x58, &handle);
        SafeGet(e + 0x5c, &trig);
    }
    Log("ObjAct kick (%s): block man %p entry %d: list %d, kick event %d, object handle %#x, trigger state %d; "
        "arg %d / %d", who, reinterpret_cast<void*>(man), std::int32_t(idx), list, ev, unsigned(handle), trig,
        std::int32_t(a3), std::int32_t(a4));
}
BB_COOP_SYSV void LocalKickEntry(std::uint64_t man, std::uint64_t idx, std::uint64_t chr, std::uint64_t, std::uint64_t,
                                 std::uint64_t) {
    g_kicks_local.fetch_add(1);
    LogKick("local player", man, idx, chr, 0);
    std::int32_t n = 0, ev = -1;
    std::uint64_t arr = 0;
    if (LocalSessionRole() == 6 && SafeGet(man + 0x98, &n) && SafeGet(man + 0x90, &arr) && arr &&
        std::int32_t(idx) >= 0 && std::int32_t(idx) < n && SafeGet(arr + (idx & 0xffffffffu) * 0x140 + 0xc, &ev) &&
        ev > 0) {
        std::lock_guard<std::mutex> lk(g_kick_mu);
        if (g_kicks_out.size() < 16) {
            g_kicks_out.push_back(ev);
        }
    }
}
// The gates of 0x17DC300 before its lot roll, evaluated like the game does (test fixture diagnostics):
// 0 passes, 1 no player GameData, 2 role 6, 3 session slot, 4 chr-type byte [2], 5 handle -1,
// 6 handle's map block / entity index out of range.
int TreasureGate(std::uint64_t handle, std::int32_t* role_out, std::int32_t* type_out) {
    std::uint64_t holder = 0, gd = 0, rolep = 0, gp = 0, slotp = 0, tab = 0;
    if (!SafeGet(Guest(0x553b130), &holder) || !holder || !SafeGet(holder + 8, &gd) || !gd) {
        return 1;
    }
    std::int32_t role = -1, slot = 0;
    std::uint32_t type = 0;
    if (SafeGet(Guest(0x5540290), &rolep) && rolep) {
        SafeGet(rolep + 0x124, &role);
    }
    *role_out = role;
    SafeGet(gd + 0xa4, &type);
    *type_out = std::int32_t(type);
    if (role == 6 && !S().pickups) {
        return 2;
    }
    if (SafeGet(Guest(0x5556678), &gp) && gp && SafeGet(gp + 0x16f8, &slotp) && slotp) {
        SafeGet(slotp + 0x98, &slot);
        if (slot != -1 && !S().pickups) {
            return 3;
        }
    }
    std::uint8_t may = 0;
    SafeGet(Guest(type <= 13 ? 0x47348a0 + std::uint64_t(type) * 12 + 2 : 0x47348a0 + 0xa8 + 2), &may);
    if (!may) {
        return 4;
    }
    const std::uint32_t h = std::uint32_t(handle);
    if (h == 0xffffffffu) {
        return 5;
    }
    std::int32_t nb = 0, cnt = 0;
    std::uint64_t blocks = 0, data = 0;
    const std::uint32_t b = (h >> 20) & 0xff, i = h & 0xfffff;
    if (!SafeGet(Guest(0x553b168), &tab) || !tab || !SafeGet(tab + 0x20, &nb) || std::int32_t(b) >= nb ||
        !SafeGet(tab + 0x28, &blocks) || !SafeGet(blocks + b * 0x1f8ull + 0xc8, &cnt) || cnt <= std::int32_t(i) ||
        !SafeGet(blocks + b * 0x1f8ull + 0xd0, &data) || !data) {
        return 6;
    }
    return 0;
}
BB_COOP_SYSV void TreasureSpawnEntry(std::uint64_t, std::uint64_t handle, std::uint64_t ev, std::uint64_t pos,
                                     std::uint64_t, std::uint64_t) {
    std::int32_t type = -1;
    float p[3] = {};
    if (!ev || !SafeGet(ev + 0xc, &type) || type != 4 || !pos || !SafeRead(pos, p, sizeof p)) {
        return;
    }
    {
        std::int32_t role = -1, ctype = -1;
        const int g = TreasureGate(handle, &role, &ctype);
        if (g_tgate[g].fetch_add(1) < 2) {
            Log("test: treasure spawn: handle %#x role %d chr type %d -> gate %d (0 = all gates pass)", unsigned(handle),
                role, ctype, g);
        }
    }
    // The treasure's item lot: an int of the MSB event whose 50000000 + lot is an item pickup flag
    // (lot 2410180 -> flag 52410180, as the C3 log shows).
    Treasure t;
    t.pos = {p[0], p[1], p[2]};
    std::int32_t words[48] = {};
    if (SafeRead(ev, words, sizeof words)) {
        for (std::int32_t w : words) {
            if (w >= 1000000 && w < 50000000 &&
                progress::CategoryOf(50000000u + std::uint32_t(w)) == Category::item_lot_picked) {
                t.flag = 50000000u + std::uint32_t(w);
                break;
            }
        }
    }
    std::lock_guard<std::mutex> lk(g_treasure_mu);
    if (g_treasure.size() < 512) {
        g_treasure.push_back(t);
    }
}

// Test fixture diagnostics: MapItemMan record inserts by kind (0x17DC300's tail) and removals.
template <int K>
BB_COOP_SYSV void RecordInsertEntry(std::uint64_t man, std::uint64_t a1, std::uint64_t, std::uint64_t, std::uint64_t,
                                    std::uint64_t) {
    g_rec_man.store(man);
    if (K == 2) {
        droproll::FixtureInsert(a1);  // the drop insert: the shared roll's result log
    }
    if (g_rec[K].fetch_add(1) < 2) {
        Log("test: MapItemMan record insert kind %d (MapItemMan %p, role %d)", K, reinterpret_cast<void*>(man),
            LocalSessionRole());
    }
}
template <int K>
BB_COOP_SYSV void RecordClearEntry(std::uint64_t man, std::uint64_t a1, std::uint64_t a2, std::uint64_t, std::uint64_t,
                                   std::uint64_t) {
    Log("test: MapItemMan treasure clear %s (MapItemMan %p, args %#llx %#llx, role %d)",
        K == 0 ? "all 0x17D57C0" : "0x17D5B40 (net handler 0x17D2F30)", reinterpret_cast<void*>(man),
        static_cast<unsigned long long>(a1), static_cast<unsigned long long>(a2), LocalSessionRole());
}
BB_COOP_SYSV void RecordRemoveEntry(std::uint64_t, std::uint64_t handle_ptr, std::uint64_t set_flag, std::uint64_t,
                                    std::uint64_t, std::uint64_t) {
    std::int32_t h = -1;
    SafeGet(handle_ptr, &h);
    if (g_rec[0].fetch_add(1) < 4) {
        Log("test: MapItemMan record remove: handle %#x, set flag %d (role %d)", unsigned(h), int(set_flag & 0xff),
            LocalSessionRole());
    }
}

BB_COOP_SYSV void PickupEntry(std::uint64_t, std::uint64_t handle_ptr, std::uint64_t, std::uint64_t, std::uint64_t,
                              std::uint64_t) {
    std::int32_t h = -1;
    SafeGet(handle_ptr, &h);
    g_pickups.fetch_add(1);
    g_pickup_at.store(Now());
    Log("map item pickup on this game (role %d): item handle %#x", LocalSessionRole(), unsigned(h));
}

BB_COOP_SYSV void NetKickEntry(std::uint64_t man, std::uint64_t idx, std::uint64_t chr, std::uint64_t state,
                               std::uint64_t, std::uint64_t) {
    g_kicks_net.fetch_add(1);
    LogKick("another player", man, idx, chr, state);
    std::int32_t n = 0, ev = -1;
    std::uint64_t arr = 0;
    if ((chr & 0xffffffffu) != 0xffffffffu && SafeGet(man + 0x98, &n) && SafeGet(man + 0x90, &arr) && arr && std::int32_t(idx) >= 0 &&
        std::int32_t(idx) < n && SafeGet(arr + (idx & 0xffffffffu) * 0x140 + 0xc, &ev)) {
        std::lock_guard<std::mutex> lk(g_kick_mu);
        if (g_kicks_seen.size() >= 32) {
            g_kicks_seen.erase(g_kicks_seen.begin());
        }
        g_kicks_seen.emplace_back(ev, Now());
    }
}

} // namespace

bool StandAtObject(std::int32_t entity, float dist, float angle_deg, std::string* what) {
    std::uint32_t idx = 0xffffffffu;
    using Find = std::uint64_t(BB_COOP_SYSV*)(std::int32_t, std::uint32_t*);
    const std::uint64_t fn = Guest(0x13c9af0);
    const std::uint64_t rec = fn ? reinterpret_cast<Find>(fn)(entity, &idx) : 0;
    float m[16] = {};
    if (!rec || !SafeRead(rec + 0x230, m, sizeof m)) {
        return false;
    }
    // 3x4 rows at +0x240 (m[4..15]): translation in column 3, the local z axis in column 2.
    const float t[3] = {m[7], m[11], m[15]};
    return PutLocal(t, m[6], m[14], dist, angle_deg, what);
}

bool ObjectPoint(std::int32_t entity, float dist, float angle_deg, float out[3]) {
    std::uint32_t idx = 0xffffffffu;
    using Find = std::uint64_t(BB_COOP_SYSV*)(std::int32_t, std::uint32_t*);
    const std::uint64_t fn = Guest(0x13c9af0);
    const std::uint64_t rec = fn ? reinterpret_cast<Find>(fn)(entity, &idx) : 0;
    float m[16] = {};
    if (!rec || !SafeRead(rec + 0x230, m, sizeof m)) {
        return false;
    }
    // The same point StandAtObject puts the player on (PutLocal's geometry), without the warp.
    float px = m[6], pz = m[14];
    float h = std::sqrt(px * px + pz * pz);
    if (h < 1e-3f) {
        px = 0, pz = 1, h = 1;
    }
    px /= h, pz /= h;
    const float a = angle_deg * 3.14159265f / 180.0f;
    out[0] = m[7] + (px * std::cos(a) + pz * std::sin(a)) * dist;
    out[1] = m[11];
    out[2] = m[15] + (-px * std::sin(a) + pz * std::cos(a)) * dist;
    return true;
}

bool StandAtChr(std::int32_t entity, float dist, float angle_deg, std::string* what) {
    using Find = std::uint64_t(BB_COOP_SYSV*)(std::int32_t, std::int32_t, std::uint64_t);
    const std::uint64_t fn = Guest(0x13c97a0);
    const std::uint64_t chr = fn ? reinterpret_cast<Find>(fn)(entity, entity, 0) : 0;
    float p[4] = {}, r[4] = {};
    const std::uint64_t c = chr ? chr : GuestSvcFindChr(std::uint32_t(entity));
    if (!c || !SafeRead(c + 0xc0, p, sizeof p) || !SafeRead(c + 0xd0, r, sizeof r)) {
        return false;
    }
    // The chr's front: forward(yaw) = (-sin, -cos), yaw = +0xd0 [1].
    return PutLocal(p, -std::sin(r[1]), -std::cos(r[1]), dist, angle_deg, what);
}

void Init() {
    State& st = S();
    if (!st.enabled) {
        return;
    }
    // push rbp; mov rbp, rsp; push r15; push r14; push r13; push r12; push rbx (13 bytes, both).
    const bool a = HookPrologue(0x13AE370, {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54, 0x53},
                                &LocalKickEntry, "ObjAct local kick (log)");
    const bool b = HookPrologue(0x13AF830, {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54, 0x53},
                                &NetKickEntry, "ObjAct remote kick (log)");
    Log("ObjAct kick log %s", a && b ? "on" : "partly off");
    // Enemy drop rolls and map item pickups: logged (the D4 evidence) - only with D4 on or a test.
    const bool d4 = st.pickups || std::getenv("BB_PARTY_WORLDACT_TEST");
    // The enemy drop roll (0x17DD0B0): one shared roll per kill for the party (party_droproll.h),
    // logged with D4 on or a test.
    droproll::Init(d4);
    if (d4) {
    HookPrologue(0x17D8570, {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54, 0x53},
                 &PickupEntry, "map item pickup (log)");
    }
    if (std::getenv("BB_PARTY_WORLDACT_TEST")) {
        HookPrologue(0x17DC300, {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54, 0x53},
                     &TreasureSpawnEntry, "MSB treasure spawn (test fixture)");
        const std::initializer_list<std::uint8_t> pro = {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56,
                                                         0x41, 0x55, 0x41, 0x54, 0x53};
        HookPrologue(0x17D4C40, pro, &RecordInsertEntry<1>, "MapItemMan insert kind 1 (test)");
        HookPrologue(0x17D5320, pro, &RecordInsertEntry<2>, "MapItemMan insert kind 2 (test)");
        HookPrologue(0x17D4FB0, pro, &RecordInsertEntry<3>, "MapItemMan insert kind 3 (test)");
        HookPrologue(0x17D6780, pro, &RecordRemoveEntry, "MapItemMan remove (test)");
        HookPrologue(0x17D57C0, pro, &RecordClearEntry<0>, "MapItemMan clear treasure (test)");
        HookPrologue(0x17D5B40, pro, &RecordClearEntry<1>, "MapItemMan clear treasure, net (test)");
    }
}

bool Enabled() {
    return S().enabled;
}

bool OnHostEvent(int slot, const std::string& body, std::string* why) {
    State& st = S();
    if (!st.enabled || PartyDirector::Get().Role() != PartyRole::Host) {
        if (why) {
            *why = "world actions are off on the host";
        }
        return false;
    }
    Request r;
    if (!RequestFromJson(body, &r, why)) {
        std::lock_guard<std::mutex> lk(st.mu);
        ++st.stats.refused;
        return false;
    }
    std::lock_guard<std::mutex> lk(st.mu);
    ++st.stats.received;
    if (st.in.size() >= 32) {
        if (why) {
            *why = "queue full";
        }
        return false;
    }
    st.in.emplace_back(slot, std::move(r));
    return true;
}

namespace {
// Guest (playtest 1 bug 8): standing at a boss fog of the host's world that has no prompt yet
// because the host has not had its first fight there (the intro condition stays, BossGate): a
// notice says why, at most once a minute per fog, and a log line.
void FogWaitTick(const GameSnapshot& s) {
    static double last_scan = 0;
    static std::uint32_t last_gate = 0;
    static double last_notice = -1e9;
    const double now = Now();
    if (s.session_role != 6 || !s.world_up || s.loading || now - last_scan < 1.0) {
        return;
    }
    last_scan = now;
    float me[3] = {};
    const bool have_me = MyPos(me);
    static std::string last_state;
    std::string state;
    const BossGate* hit = nullptr;
    float hit_d = 0;
    for (const BossGate& g : BossGates()) {
        if (!g.fog_entity || !BossGateInBlock(g, s.map_id)) {
            continue;
        }
        bool intro = false, host_in = false, dead = false;
        const bool read = progress::ReadFlag(g.intro_flag ? g.intro_flag : g.host_flag, &intro) &&
                          progress::ReadFlag(g.host_flag, &host_in) && progress::ReadFlag(g.boss_flag, &dead);
        float fog[3] = {};
        const bool found = ObjectPoint(g.fog_entity, 0.0f, 0.0f, fog);
        float d = -1;
        if (found && have_me) {
            const float dx = fog[0] - me[0], dy = fog[1] - me[1], dz = fog[2] - me[2];
            d = std::sqrt(dx * dx + dy * dy + dz * dz);
        }
        // Diagnostics: the gate's state whenever it changes (distance bucket: near / 20 m / far).
        char buf[160];
        std::snprintf(buf, sizeof buf, " [%u: read %d intro %d host %d dead %d fog %s%s]", g.guest_event, read ? 1 : 0,
                      intro ? 1 : 0, host_in ? 1 : 0, dead ? 1 : 0, !found ? "not loaded" : !have_me ? "?" : "",
                      !found || !have_me ? "" : d <= kBossFogNoticeRange ? "near" : d <= 20.0f ? "within 20 m" : "far");
        state += buf;
        if (BossFogNoticeDue(g, read, intro, host_in, dead, found && have_me ? d : -1.0f) && !hit) {
            hit = &g;
            hit_d = d;
        }
    }
    if (state != last_state) {
        last_state = state;
        Log("guest: boss fogs of this block:%s", state.empty() ? " none" : state.c_str());
    }
    if (hit) {
        const BossGate& g = *hit;
        const double d = hit_d;
        if (last_gate == g.guest_event && now - last_notice < 60.0) {
            return;
        }
        last_gate = g.guest_event;
        last_notice = now;
        party::status::SetLastEvent(kBossFogWaitNotice);
        Log("guest: at boss fog %d (event %u, %.1f m): first fight here - the host goes in first (host's first-fight "
            "flag %u off); notice shown", g.fog_entity, g.guest_event, d, g.intro_flag);
    }
}
} // namespace

void Tick(const GameSnapshot& s, party::PartyLink* link) {
    State& st = S();
    WatchTick(s);
    FixtureTick(Now());
    if (!st.enabled) {
        return;
    }
    const PartyRole role = PartyDirector::Get().Role();
    droproll::Tick(s, link, role == PartyRole::Host);
    if (role == PartyRole::Guest) {
        FogWaitTick(s);
        GuestTick(s, link);
    } else if (role == PartyRole::Host) {
        // The fixture's clock on the host (kill=N: the host's own kill, each player rolls its drop).
        const bool steady = s.world_up && !s.loading && s.cooperators > 0;
        if (!steady || s.map_id != st.map) {
            st.steady = false;
            st.map = s.map_id;
        } else if (!st.steady) {
            st.steady = true;
            st.steady_since = Now();
        }
        HostTick(s);
    }
}

Stats GetStats() {
    std::lock_guard<std::mutex> lk(S().mu);
    return S().stats;
}

} // namespace coop::worldact

#endif // BB_PARTY_WORLDACT_NO_GAME
