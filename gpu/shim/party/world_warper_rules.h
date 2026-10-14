// SPDX-License-Identifier: GPL-3.0-or-later
// The world warper (world_warper.h): the pure rules. Header only, no game dependency (unit tests:
// tests/test_world_warper.cpp).
//
//   Route    every ReturnPointParam row with a map and a spot (party_ids: kPartyReturnPoints /
//            ReturnSpot), the Chalice Dungeons (area 29, generated layouts) left out: the Hunter's
//            Dream first, then the lamps in the headstones' order (lamp_travel_rules.h kLamps), then
//            the other rows (boss-arena and event respawn points) by id. `lamps=A+B` replaces it.
//   Progress a text file (BB_WORLD_WARPER_STATE), one line per event, appended and flushed at once
//            so a crash keeps everything before it:
//              start <rp>                     the warp to <rp> began
//              done <rp> <new> <hitches> ...  the area's routine finished (the numbers for the log)
//              skip <rp> <reason>             no load / stuck: never tried again
//              finished                       the whole route is done (the launcher exports)
//            A row started `kMaxAttempts` times without a done (the game crashed or hung there
//            each time) is skipped on the next start: resume after a crash.
//   Options  BB_WORLD_WARPER = tour | replay | measure (replay, tour, replay again: the stutter
//            check in one session), then ",key=value" items: lamps=A+B (the tour's route),
//            replay=A+B (the replay's route), max=N (the first N rows of the route), noact (no
//            weapon / item actions), noenemy (no enemies), nokill.
#pragma once

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <set>
#include <string>
#include <vector>

#include "lamp_travel_rules.h"

namespace coop::warper {

enum class Mode : std::uint8_t { Off, Tour, Replay, Measure };

struct Options {
    Mode mode = Mode::Off;
    std::vector<std::uint32_t> lamps;   ///< lamps=: the tour's route (empty: every row)
    std::vector<std::uint32_t> replay;  ///< replay=: the replay route (empty: kDefaultReplay)
    int max = 0;                        ///< max=N: the first N rows only (0: all)
    bool act = true, enemies = true, kill = true;
};

/// The replay route (the stutter check): four lamps in four areas that a save past the first boss
/// usually has, each a different kind of scene (the Dream, streets, a cathedral, a forest).
inline constexpr std::uint32_t kDefaultReplay[] = {2102950, 2412950, 2402950, 2202950};

inline constexpr int kMaxAttempts = 2;

inline std::vector<std::uint32_t> ParseIds(const std::string& s) {
    std::vector<std::uint32_t> out;
    std::size_t at = 0;
    while (at < s.size()) {
        std::size_t end = s.find_first_of("+ /", at);
        if (end == std::string::npos) end = s.size();
        const std::string item = s.substr(at, end - at);
        at = end + 1;
        if (item.empty()) continue;
        char* e = nullptr;
        const unsigned long v = std::strtoul(item.c_str(), &e, 10);
        if (e && *e == 0 && v > 0 && v < 100000000ul) out.push_back(static_cast<std::uint32_t>(v));
    }
    return out;
}

inline Options ParseOptions(const char* env) {
    Options o;
    if (!env || !env[0]) return o;
    std::string s = env;
    for (char& c : s) {
        if (c == ';') c = ',';
    }
    std::size_t at = 0;
    bool first = true;
    while (at <= s.size()) {
        std::size_t end = s.find(',', at);
        if (end == std::string::npos) end = s.size();
        const std::string item = s.substr(at, end - at);
        at = end + 1;
        if (first) {
            first = false;
            if (item == "0" || item == "off" || item == "false" || item == "no") return Options{};
            if (item == "replay") o.mode = Mode::Replay;
            else if (item == "measure") o.mode = Mode::Measure;
            else o.mode = Mode::Tour;  // "1", "on", "tour" (or an option first: a tour)
            if (item.find('=') == std::string::npos && item != "noact" && item != "noenemy" && item != "nokill") continue;
        }
        if (item.rfind("lamps=", 0) == 0) o.lamps = ParseIds(item.substr(6));
        else if (item.rfind("replay=", 0) == 0) o.replay = ParseIds(item.substr(7));
        else if (item.rfind("max=", 0) == 0) o.max = std::max(0, std::atoi(item.c_str() + 4));
        else if (item == "noact") o.act = false;
        else if (item == "noenemy") o.enemies = false;
        else if (item == "nokill") o.kill = false;
    }
    return o;
}

/// Chalice Dungeon rows (area 29): generated layouts, no fixed spot, a ritual to enter.
constexpr bool ChaliceRow(std::uint32_t rp) {
    return rp / 100000 == 29;
}

/// The tour: `known` = every ReturnPointParam row (sorted or not); `has_spot(rp)`: the row has a
/// spot. Dream first, the lamps in the headstones' order, then the remaining rows by id; each once.
template <class SpotFn>
std::vector<std::uint32_t> BuildRoute(const std::vector<std::uint32_t>& known, SpotFn has_spot,
                                      const Options& o = Options{}) {
    std::vector<std::uint32_t> out;
    std::set<std::uint32_t> have(known.begin(), known.end()), used;
    auto add = [&](std::uint32_t rp) {
        if (!have.count(rp) || used.count(rp) || ChaliceRow(rp) || !has_spot(rp)) return;
        used.insert(rp);
        out.push_back(rp);
    };
    if (!o.lamps.empty()) {
        for (std::uint32_t rp : o.lamps) add(rp);
    } else {
        add(lamptravel::kDreamReturnPoint);
        for (const lamptravel::Lamp& l : lamptravel::kLamps) add(lamptravel::ReturnPoint(l));
        std::vector<std::uint32_t> rest(have.begin(), have.end());
        for (std::uint32_t rp : rest) add(rp);
    }
    if (o.max > 0 && out.size() > static_cast<std::size_t>(o.max)) out.resize(static_cast<std::size_t>(o.max));
    return out;
}

/// The packed map (AA << 24 | B << 16) of a ReturnPointParam row.
constexpr std::uint32_t MapOfRow(std::uint32_t rp) {
    return lamptravel::MapOf(rp);
}

struct Progress {
    std::map<std::uint32_t, int> starts;
    std::set<std::uint32_t> done, skipped;
    bool finished = false;
};

inline Progress ParseProgress(const std::string& text) {
    Progress p;
    std::size_t at = 0;
    while (at < text.size()) {
        std::size_t end = text.find('\n', at);
        if (end == std::string::npos) end = text.size();
        std::string line = text.substr(at, end - at);
        at = end + 1;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line == "finished") {
            p.finished = true;
            continue;
        }
        const std::size_t sp = line.find(' ');
        if (sp == std::string::npos) continue;
        const std::string word = line.substr(0, sp);
        const std::uint32_t rp = static_cast<std::uint32_t>(std::strtoul(line.c_str() + sp + 1, nullptr, 10));
        if (!rp) continue;
        if (word == "start") ++p.starts[rp];
        else if (word == "done") p.done.insert(rp);
        else if (word == "skip") p.skipped.insert(rp);
    }
    return p;
}

/// Why the row is not visited again (nullptr: it is still to do).
inline const char* SkipReason(const Progress& p, std::uint32_t rp) {
    if (p.done.count(rp)) return "done";
    if (p.skipped.count(rp)) return "skipped";
    const auto it = p.starts.find(rp);
    if (it != p.starts.end() && it->second >= kMaxAttempts) return "crashed there";
    return nullptr;
}

/// The next route index to visit at or after `from` (route.size(): nothing left).
inline std::size_t NextIndex(const std::vector<std::uint32_t>& route, const Progress& p, std::size_t from) {
    for (std::size_t i = from; i < route.size(); ++i) {
        if (!SkipReason(p, route[i])) return i;
    }
    return route.size();
}

/// Rows of the route already handled (done, skipped or given up).
inline std::size_t HandledCount(const std::vector<std::uint32_t>& route, const Progress& p) {
    std::size_t n = 0;
    for (std::uint32_t rp : route) n += SkipReason(p, rp) ? 1 : 0;
    return n;
}

/// One step of a scripted input sequence: buttons and sticks held for `seconds`.
struct PadStep {
    float seconds = 0;
    std::uint32_t buttons = 0;
    int lx = -1, ly = -1, rx = -1, ry = -1;  ///< 0..255, -1 = released (the player's own)
    const char* what = "";                   ///< the action's name for the per-action counts
};

// PS4 pad bits (src/runtime_pad.c).
inline constexpr std::uint32_t kL3 = 0x2, kR3 = 0x4, kUp = 0x10, kRight = 0x20, kDown = 0x40, kLeft = 0x80,
                               kL2 = 0x100, kR2 = 0x200, kL1 = 0x400, kR1 = 0x800, kTriangle = 0x1000,
                               kCircle = 0x2000, kSquare = 0x8000;

/// The camera sweep: a full turn right, then up and down (the sky, the ground), then back.
inline std::vector<PadStep> LookSteps() {
    return {
        {5.0f, 0, -1, -1, 255, 128, "look"}, {0.2f, 0, -1, -1, 128, 128, "look"},
        {1.2f, 0, -1, -1, 128, 0, "look"},   {2.0f, 0, -1, -1, 128, 255, "look"},
        {1.0f, 0, -1, -1, 128, 0, "look"},   {0.3f, 0, -1, -1, -1, -1, "look"},
    };
}

/// The walk loop: a circle forward while the camera turns, a dash (Circle held), back, sideways.
inline std::vector<PadStep> WalkSteps() {
    return {
        {3.0f, 0, 128, 0, 200, 128, "walk"},       {2.5f, kCircle, 128, 0, 60, 128, "walk"},
        {0.3f, 0, -1, -1, -1, -1, "walk"},        {2.0f, 0, 128, 255, -1, -1, "walk"},
        {1.5f, 0, 0, 128, -1, -1, "walk"},        {1.5f, 0, 255, 128, -1, -1, "walk"},
        {0.3f, 0, -1, -1, -1, -1, "walk"},
    };
}

/// Weapon actions, both forms: R1 combo, R2 (charged: held), the transform (L1) and its attacks,
/// the firearm (L2), a dodge (Circle) and a backstep, then the transform back.
inline std::vector<PadStep> ActionSteps() {
    auto tap = [](std::uint32_t b, const char* w, float hold = 0.15f, float after = 0.9f) {
        return std::vector<PadStep>{{hold, b, -1, -1, -1, -1, w}, {after, 0, -1, -1, -1, -1, w}};
    };
    std::vector<PadStep> v;
    auto add = [&](std::vector<PadStep> s) { v.insert(v.end(), s.begin(), s.end()); };
    add(tap(kR1, "r1"));
    add(tap(kR1, "r1"));
    add(tap(kR1, "r1", 0.15f, 1.3f));
    add(tap(kR2, "r2", 0.15f, 1.6f));
    add(tap(kR2, "r2 charged", 1.6f, 1.6f));
    add(tap(kL2, "firearm", 0.15f, 1.3f));
    add(tap(kL1, "transform", 0.15f, 1.6f));
    add(tap(kR1, "r1 transformed"));
    add(tap(kR1, "r1 transformed", 0.15f, 1.3f));
    add(tap(kR2, "r2 transformed", 0.15f, 1.8f));
    add(tap(kL1, "transform back", 0.15f, 1.6f));
    v.push_back({0.25f, kCircle, 128, 0, -1, -1, "dodge"});
    v.push_back({1.0f, 0, -1, -1, -1, -1, "dodge"});
    add(tap(kCircle, "backstep", 0.15f, 1.0f));
    return v;
}

/// Once per tour (the first area): the other weapons and items. Left / Right on the d-pad switch
/// the left-hand (firearm / torch / shield) and right-hand weapons, each followed by its attacks;
/// Up / Down cycle the quick items (and tools), Square uses one, Triangle a blood vial.
inline std::vector<PadStep> LoadoutSteps() {
    auto tap = [](std::uint32_t b, const char* w, float hold = 0.15f, float after = 0.9f) {
        return std::vector<PadStep>{{hold, b, -1, -1, -1, -1, w}, {after, 0, -1, -1, -1, -1, w}};
    };
    std::vector<PadStep> v;
    auto add = [&](std::vector<PadStep> s) { v.insert(v.end(), s.begin(), s.end()); };
    for (int i = 0; i < 2; ++i) {
        add(tap(kRight, "weapon switch", 0.15f, 1.8f));
        add(tap(kR1, "r1 (other weapon)", 0.15f, 1.2f));
        add(tap(kL1, "transform (other weapon)", 0.15f, 1.6f));
        add(tap(kR1, "r1 (other weapon)", 0.15f, 1.2f));
        add(tap(kL1, "transform (other weapon)", 0.15f, 1.6f));
        add(tap(kLeft, "left-hand switch", 0.15f, 1.8f));
        add(tap(kL2, "left-hand weapon", 0.15f, 1.4f));
    }
    for (int i = 0; i < 4; ++i) {
        add(tap(kUp, "quick item", 0.15f, 0.6f));
        add(tap(kSquare, "quick item", 0.15f, 2.6f));
    }
    for (int i = 0; i < 3; ++i) {
        add(tap(kDown, "tool / item", 0.15f, 0.6f));
        add(tap(kSquare, "tool / item", 0.15f, 2.6f));
    }
    add(tap(kTriangle, "blood vial", 0.15f, 2.0f));
    return v;
}

inline float Seconds(const std::vector<PadStep>& steps) {
    float s = 0;
    for (const PadStep& p : steps) s += p.seconds;
    return s;
}

/// The area's name for the progress display (English, the map's usual name; "" unknown).
inline const char* AreaName(std::uint32_t rp) {
    switch (rp / 10000) {
    case 210: return "Hunter's Dream";
    case 211: return "Abandoned Old Workshop";
    case 220: return "Hemwick Charnel Lane";
    case 230: return "Old Yharnam";
    case 240: return "Cathedral Ward";
    case 241: return "Central Yharnam";
    case 242: return "Upper Cathedral Ward";
    case 250: return "Cainhurst";
    case 260: return "Nightmare of Mensis";
    case 270: return "Forbidden Woods";
    case 280: return "Yahar'gul";
    case 320: return "Byrgenwerth / Lecture Building";
    case 330: return "Nightmare Frontier";
    case 340: return "Hunter's Nightmare";
    case 350: return "Research Hall";
    case 360: return "Fishing Hamlet";
    default: return "";
    }
}

/// One area's line in the progress file: "done <rp> <new> <hitches> <worst ms> <seconds> <map>".
inline std::string DoneLine(std::uint32_t rp, std::uint64_t created, std::uint64_t hitches, double worst_ms,
                            double seconds, const std::string& map) {
    char b[160];
    std::snprintf(b, sizeof b, "done %u %llu %llu %.0f %.0f %s", rp, static_cast<unsigned long long>(created),
                  static_cast<unsigned long long>(hitches), worst_ms, seconds, map.c_str());
    return b;
}

} // namespace coop::warper
