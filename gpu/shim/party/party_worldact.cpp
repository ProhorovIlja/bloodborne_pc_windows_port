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
        if (set.size() > kMaxSet || clr.size() > kMaxClear || (set.empty() && clr.empty() && r.kick.empty())) {
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

} // namespace coop::worldact

#ifndef BB_PARTY_WORLDACT_NO_GAME

#include "coop_hooks.h"
#include "game_state.h"
#include "party_director.h"
#include "party_link.h"
#include "party_guestsvc.h"

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
    std::printf("Party world: %s\n", line);
    std::fflush(stdout);
}

double Now() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
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
    bool pickups = false;           // D4 patches in: the guest sees and takes the host world's treasure
    Stats stats;
} g_st;

// Guest: kick event ids of the local player's ObjAct kicks (LocalKickEntry, main thread) for the
// next world_action. Host: remote kicks its game applied (NetKickEntry): kick event id -> time.
// MSB treasure spawns seen on this game (0x17DC300(MapItemMan, entity handle, MsbEvent, pos)):
// the fixture's pickup targets. Main thread.
std::mutex g_treasure_mu;
struct Treasure {
    std::array<float, 3> pos{};
    std::uint32_t flag = 0;  // 50000000 + item lot (the MSB event's lot; 0 = not found)
};
std::vector<Treasure> g_treasure;
std::mutex g_kick_mu;
std::vector<std::int32_t> g_kicks_out;
std::vector<std::pair<std::int32_t, double>> g_kicks_seen;

State& S() {
    std::call_once(g_st.once, [] {
        const char* party = std::getenv("BB_PARTY");
        const char* on = std::getenv("BB_PARTY_WORLD_ACTIONS");
        g_st.enabled = party && party[0] && !(on && on[0] == '0');
        g_st.watch = ParseIds(std::getenv("BB_PARTY_WORLD_WATCH"));
        Log("guest world actions %s (levers, doors, shortcuts, elevators, NPC talk -> the host's world)",
            g_st.enabled ? "on" : "off");
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
            // Enemy drops are per player too (user decision 2026-10-11): every player's game rolls
            // each enemy's drop itself (0x17DD0B0 on enemy death); a client kept only isGuestDrop
            // items (vials, bullets): 0x17DD764 je (not a client: no filter) -> jmp.
            const char* dr = std::getenv("BB_PARTY_GUEST_DROPS");
            const bool d = (dr && dr[0] == '0') ||
                           PatchBytes(0x17DD764, {0x0f, 0x84, 0x3a, 0x02, 0x00, 0x00}, {0xe9, 0x3b, 0x02, 0x00, 0x00, 0x90},
                                      "full enemy drops on a client");
            Log("guest enemy drops: %s", dr && dr[0] == '0' ? "vanilla (vials / bullets only)" : d ? "full, own roll per player"
                                                                                                   : "NOT installed");
            g_st.pickups = a && b && c;
            progress::SetInstancedItems(g_st.pickups);
            Log("guest treasure pickups in the host's world: %s (instanced per player)",
                g_st.pickups ? "on" : "NOT installed");
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

void GuestTick(const GameSnapshot& s, party::PartyLink* link) {
    State& st = S();
    const double now = Now();
    const bool ok = s.session_role == 6 && s.world_up && !s.loading && progress::FlagLoadMode() == 1;
    if (!ok || s.map_id != st.map) {
        st.steady = false;
        st.baselined = false;
        st.map = s.map_id;
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
            st.known.insert(std::uint64_t(id) * 2 + (v ? 1 : 0));
        }
        st.baselined = true;
        Log("guest: %zu local flag difference(s) in the host's world held back as the baseline (%s)",
            changes.size(), MapName(s.map_id).c_str());
        return;
    }
    Request r;
    r.map = s.map_id;
    std::vector<std::uint32_t> local, picked;
    for (const auto& [id, v] : changes) {
        const std::uint64_t k = std::uint64_t(id) * 2 + (v ? 1 : 0);
        if (st.known.count(k)) {
            continue;
        }
        st.known.insert(k);
        if (v && progress::CategoryOf(id) == Category::item_lot_picked && st.pickups) {
            // D4: the guest picked up the host world's treasure - instanced: its own save only.
            if (progress::WriteFlagOwnSave(id, true)) {
                ++st.stats.own_save;
                picked.push_back(id);
            }
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
    if (r.set.empty() && r.clr.empty() && r.kick.empty()) {
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
        auto apply = [&](std::uint32_t id, bool v) {
            if (!WorldActionAllowed(id, !v, s.map_id)) {
                ++st.stats.refused;
                list += " " + std::to_string(id) + "(refused)";
                return;
            }
            bool before = false;
            progress::ReadFlag(id, &before);
            const bool ok = before == v || progress::WriteFlagOwnSave(id, v);
            st.stats.applied += ok && before != v ? 1 : 0;
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
// an action prompt shows, press Cross (then three more for a talk: the dialogue lines), wait,
// next.
struct Fixture {
    bool parsed = false;
    std::vector<std::int32_t> objs, chrs;
    int pickups = 0;  // "pickup=N": the N treasures nearest the guest, one try each
    int kills = 0;    // "kill=N": N times the nearest live map enemy: ForceDead, then pick up its drop
    int kill_stage = 0;
    float kill_pos[3] = {};
    std::int32_t kill_id = 0;
    double after = 8;
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
    float me[4] = {};
    if (!SafeGet(Guest(0x553e878), &man) || !man || !SafeGet(man + 0x60, &player) || !player ||
        !SafeRead(player + 0xc0, me, sizeof me)) {
        return false;
    }
    std::memcpy(out, me, 12);
    return true;
}

// The nearest live map character of the current map's entity range (AABnnnn) within 25 m, by the
// WorldChrMan id sets (party_guestsvc FindChr's walk) and 0x13C97A0(id).
std::int32_t NearestEnemy(const float me[3], float pos[3], const std::vector<std::int32_t>& skip) {
    std::uint64_t wcm = 0;
    std::int32_t sets = 0;
    if (!SafeGet(Guest(0x553e878), &wcm) || !wcm || !SafeGet(wcm + 0x90, &sets) || sets <= 0 || sets > 4096) {
        return 0;
    }
    using Find = std::uint64_t(BB_COOP_SYSV*)(std::int32_t, std::int32_t, std::uint64_t);
    const Find find = reinterpret_cast<Find>(Guest(0x13c97a0));
    std::int32_t best = 0;
    float bd = 25.0f * 25.0f;
    for (std::int32_t i = 0; i < sets; ++i) {
        std::uint64_t set = 0, arr = 0;
        std::int32_t n = 0;
        if (!SafeGet(wcm + 0x98 + 8 * std::uint64_t(i), &set) || !set || !SafeGet(set + 0xf0, &n) ||
            !SafeGet(set + 0xf8, &arr) || n <= 0 || n > 100000) {
            continue;
        }
        for (std::int32_t k = 0; k < n; ++k) {
            std::int32_t id = 0;
            if (!SafeGet(arr + 8 * std::uint64_t(k), &id) || id < 1000000 || id > 9999999 ||
                std::find(skip.begin(), skip.end(), id) != skip.end() || id % 10000 >= 700) {
                continue;  // AAB0000-AAB0699: enemies (NPCs from 700 up)
            }
            const std::uint64_t chr = find(id, id, 0);
            std::uint64_t cm = 0, dm = 0;
            std::int32_t hp = 0;
            float p[4] = {};
            if (!chr || !SafeRead(chr + 0xc0, p, sizeof p) || !SafeGet(chr + 0x3b0, &cm) || !cm ||
                !SafeGet(cm + 0x20, &dm) || !dm || !SafeGet(dm + 0x128, &hp) || hp <= 0) {
                continue;
            }
            const float dx = p[0] - me[0], dy = p[1] - me[1], dz = p[2] - me[2];
            const float d = dx * dx + dy * dy + dz * dz;
            if (d < bd) {
                bd = d;
                best = id;
                std::memcpy(pos, p, 12);
            }
        }
    }
    return best;
}

void KillTick(Fixture& f, double now) {
    static std::vector<std::int32_t> done_ids;
    float me[3] = {};
    if (!MyPos(me)) {
        return;
    }
    if (f.kill_stage == 0) {
        f.kill_id = NearestEnemy(me, f.kill_pos, done_ids);
        if (!f.kill_id) {
            Log("test: fixture: no live enemy within 25 m");
            f.kills = 0;
            return;
        }
        done_ids.push_back(f.kill_id);
        // Lua ForceDead (0x13320C0(ctx, entity)): the enemy's normal death on this game.
        reinterpret_cast<void(BB_COOP_SYSV*)(std::uint64_t, std::uint32_t)>(Guest(0x13320c0))(0, std::uint32_t(f.kill_id));
        Log("test: fixture: enemy %d at (%.1f, %.1f, %.1f) killed by this player (ForceDead)", f.kill_id,
            f.kill_pos[0], f.kill_pos[1], f.kill_pos[2]);
        f.kill_stage = 1;
        f.next = now + 6.0;  // death animation; the drop appears
        return;
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
    if (f.done || !st.steady || now - st.steady_since < f.after || now < f.next) {
        return;
    }
    const std::size_t total = f.objs.size() + f.chrs.size();
    if (f.idx >= total && f.pickups <= 0 && f.kills > 0) {
        KillTick(f, now);
        return;
    }
    if (f.idx >= total && f.pickups > 0) {
        // The nearest treasure not tried yet: stand on it, Cross (pick up), next one 5 s later.
        if (f.presses == 1) {
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
                const float dx = t[0] - me[0], dy = t[1] - me[1], dz = t[2] - me[2];
                const float d = dx * dx + dy * dy + dz * dz;
                if (d < bd) {
                    bd = d;
                    best = t;
                }
            }
            if (f.tries == 0) {
                std::size_t with = 0;
                for (const Treasure& tr : g_treasure) {
                    with += tr.flag ? 1 : 0;
                }
                Log("test: fixture: %zu treasure spawn(s) seen on this game (%zu with a pickup flag)", g_treasure.size(),
                    with);
            }
        }
        if (bd > 1e8f) {
            f.pickups = 0;
            Log("test: fixture: no treasure left to try");
            return;
        }
        if (f.presses == 0) {
            tried.push_back(best);
            std::string what;
            PutLocal(best.data(), 0.0f, 1.0f, 0.4f, 0.0f, &what);
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
        if (!obj && f.presses < 4) {
            runtime_pad_director_press(0x4000);  // talk: the next dialogue lines
            f.release = now + 0.15;
            ++f.presses;
            f.next = now + 1.5;
            Log("test: fixture: character %d: Cross #%d", ent, f.presses);
            return;
        }
        Log("test: fixture: %s %d done", kind, ent);
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
BB_COOP_SYSV void TreasureSpawnEntry(std::uint64_t, std::uint64_t, std::uint64_t ev, std::uint64_t pos, std::uint64_t,
                                     std::uint64_t) {
    std::int32_t type = -1;
    float p[3] = {};
    if (!ev || !SafeGet(ev + 0xc, &type) || type != 4 || !pos || !SafeRead(pos, p, sizeof p)) {
        return;
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

BB_COOP_SYSV void EnemyDropEntry(std::uint64_t, std::uint64_t chr_handle, std::uint64_t npc, std::uint64_t,
                                 std::uint64_t, std::uint64_t) {
    Log("enemy drop roll on this game (role %d): chr handle %#x, npc param %p", LocalSessionRole(),
        unsigned(chr_handle), reinterpret_cast<void*>(npc));
}
BB_COOP_SYSV void PickupEntry(std::uint64_t, std::uint64_t handle_ptr, std::uint64_t, std::uint64_t, std::uint64_t,
                              std::uint64_t) {
    std::int32_t h = -1;
    SafeGet(handle_ptr, &h);
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
    // Enemy drop rolls and map item pickups: logged (rare events; the D4 evidence).
    HookPrologue(0x17DD0B0, {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54, 0x53},
                 &EnemyDropEntry, "enemy drop roll (log)");
    HookPrologue(0x17D8570, {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54, 0x53},
                 &PickupEntry, "map item pickup (log)");
    if (std::getenv("BB_PARTY_WORLDACT_TEST")) {
        HookPrologue(0x17DC300, {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54, 0x53},
                     &TreasureSpawnEntry, "MSB treasure spawn (test fixture)");
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

void Tick(const GameSnapshot& s, party::PartyLink* link) {
    State& st = S();
    WatchTick(s);
    FixtureTick(Now());
    if (!st.enabled) {
        return;
    }
    const PartyRole role = PartyDirector::Get().Role();
    if (role == PartyRole::Guest) {
        GuestTick(s, link);
    } else if (role == PartyRole::Host) {
        HostTick(s);
    }
}

Stats GetStats() {
    std::lock_guard<std::mutex> lk(S().mu);
    return S().stats;
}

} // namespace coop::worldact

#endif // BB_PARTY_WORLDACT_NO_GAME
