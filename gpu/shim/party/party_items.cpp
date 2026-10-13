// SPDX-License-Identifier: GPL-3.0-or-later
// Party items, phase C3 (see party_items.h; the RE is docs/party/items.md).
//
// Every site below was disassembled from smoketest/out/eboot.elf (1.09) and is compared byte for
// byte before anything is written. Offsets are ours (raw ELF VA). The game's code is System V:
// every call into it goes through a BB_COOP_SYSV pointer at Guest(off).
#include "party_items.h"
#include "party_async_io.h"
#include "party_perf.h"

#include "../../party_env.h"

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <unordered_map>

#ifndef BB_PARTY_ITEMS_NO_GAME
#include "coop_hooks.h"
#include "game_state.h"
#include "party_director.h"
#include "party_progress.h"
#include "party_status.h"
#include "seamless_rules.h"

#include <atomic>
#include <chrono>
#include <cstdarg>
#include <cstdlib>
#include <mutex>
#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#endif
#endif

namespace coop {

// ---------------------------------------------------------------------------------------------
// Pure part (unit-tested)
// ---------------------------------------------------------------------------------------------

namespace {

struct LotFlag {
    std::int32_t lot;
    std::int32_t flag;
};
constexpr LotFlag kLotFlags[] = {
#define ITEM_LOT_FLAG(lot, flag) {lot, flag},
#include "party_items.inc"
#undef ITEM_LOT_FLAG
};

struct LedgerRow {
    std::int32_t idx;
    std::int32_t lot;
    std::int32_t done_flag;
    const char* note;
};
constexpr LedgerRow kLedger[] = {
#define ITEM_LEDGER(idx, lot, done, note) {idx, lot, done, note},
#include "party_items.inc"
#undef ITEM_LEDGER
};

struct SourceName {
    ItemSource source;
    const char* name;
};
constexpr SourceName kSourceNames[] = {
    {ItemSource::Unknown, "unknown"}, {ItemSource::Award, "award"}, {ItemSource::Flag, "flag"},
    {ItemSource::Full, "full"},       {ItemSource::Mark, "mark"},   {ItemSource::Test, "test"},
};

const std::unordered_map<std::int32_t, std::int32_t>& FlagToLot() {
    // The lowest lot per flag: the table is sorted by lot, so the first row wins (a chain head
    // before its continuation rows, the NG variant 34000 before 34030).
    static const std::unordered_map<std::int32_t, std::int32_t> m = [] {
        std::unordered_map<std::int32_t, std::int32_t> r;
        for (const LotFlag& e : kLotFlags) {
            r.emplace(e.flag, e.lot);
        }
        return r;
    }();
    return m;
}

constexpr std::int32_t kTreasureBase = 50000000;

bool InRange(std::int32_t v, std::int32_t lo, std::int32_t hi) {
    return v >= lo && v <= hi;
}

} // namespace

const char* ItemSourceName(ItemSource s) {
    for (const SourceName& n : kSourceNames) {
        if (n.source == s) {
            return n.name;
        }
    }
    return "unknown";
}

ItemSource ItemSourceFromName(const std::string& name) {
    for (const SourceName& n : kSourceNames) {
        if (name == n.name) {
            return n.source;
        }
    }
    return ItemSource::Unknown;
}

std::int64_t ItemGrant::DoneFlag() const {
    if (flag >= 0) {
        return flag;
    }
    if (ledger >= 0 && ledger < kItemLedgerSize) {
        return std::int64_t(kItemLedgerBase) + ledger;
    }
    return -1;
}

std::string DescribeItem(const ItemGrant& g) {
    char text[160];
    if (g.flag >= 0) {
        std::snprintf(text, sizeof text, "#%llu lot %d (flag %d, %s)", static_cast<unsigned long long>(g.seq), g.lot,
                      g.flag, ItemSourceName(g.source));
    } else {
        std::snprintf(text, sizeof text, "#%llu lot %d (ledger %d = flag %lld, %s)",
                      static_cast<unsigned long long>(g.seq), g.lot, g.ledger, static_cast<long long>(g.DoneFlag()),
                      ItemSourceName(g.source));
    }
    return text;
}

std::int32_t ItemLotFlag(std::int32_t lot) {
    const LotFlag* b = std::begin(kLotFlags);
    const LotFlag* e = std::end(kLotFlags);
    const LotFlag* it = std::lower_bound(b, e, lot, [](const LotFlag& x, std::int32_t v) { return x.lot < v; });
    return it != e && it->lot == lot ? it->flag : kItemNone;
}

std::int32_t ItemLotForFlag(std::int32_t flag) {
    if (flag <= 0) {
        return kItemNone;
    }
    if (flag >= kTreasureBase && ItemLotFlag(flag - kTreasureBase) == flag) {
        return flag - kTreasureBase;
    }
    const auto& m = FlagToLot();
    const auto it = m.find(flag);
    return it != m.end() ? it->second : kItemNone;
}

std::int32_t ItemLedgerIndex(std::int32_t lot) {
    for (const LedgerRow& r : kLedger) {
        if (r.lot == lot) {
            return r.idx;
        }
    }
    return kItemNone;
}

std::int32_t ItemLedgerDoneFlag(std::int32_t idx) {
    for (const LedgerRow& r : kLedger) {
        if (r.idx == idx) {
            return r.done_flag;
        }
    }
    return kItemNone;
}

std::vector<std::uint32_t> LedgerBitsToSeed(const std::function<bool(std::uint32_t)>& is_set) {
    std::vector<std::uint32_t> out;
    if (is_set(kItemLedgerSeeded)) {
        return out;
    }
    for (const LedgerRow& r : kLedger) {
        const std::uint32_t bit = kItemLedgerBase + static_cast<std::uint32_t>(r.idx);
        if (r.done_flag > 0 && is_set(static_cast<std::uint32_t>(r.done_flag)) && !is_set(bit) &&
            std::find(out.begin(), out.end(), bit) == out.end()) {
            out.push_back(bit);
        }
    }
    return out;
}

std::int32_t ItemLedgerLot(std::int32_t idx) {
    for (const LedgerRow& r : kLedger) {
        if (r.idx == idx) {
            return r.lot;
        }
    }
    return kItemNone;
}

std::size_t ItemLotFlagCount() {
    return std::size(kLotFlags);
}

std::size_t ItemLedgerCount() {
    return std::size(kLedger);
}

bool ItemLotDenied(std::int32_t lot, std::int32_t flag) {
    if (lot <= 0 || lot >= 100000000) {
        return true; // unresolved; Chalice Dungeon lots (1100xxxxx, 2001xxxxx)
    }
    if (lot / 100000 == 29) {
        return true; // area 29 treasure (Chalice Dungeons)
    }
    if (flag > 0 && (flag / 10000000 == 1 || flag / 10000000 == 5) && (flag / 100000) % 100 == 29) {
        return true; // area 29 flags
    }
    // DLC boss rewards whose flags live in the personal block 6000-8999 (Ludwig 3401800 -> 6674,
    // Laurence 3401850 -> 6673): a phantom never gets them (2003[4] is skipped on clients) and
    // the flag is the guest's own, so a replay is exact. Every other lot with a personal flag is
    // a per-player gift (Messenger 10000/10010/10050, DLC NPCs 43120/43130, 43800).
    if (lot == 3401800 || lot == 3401850) {
        return false;
    }
    if (InRange(flag, 6000, 8999)) {
        return true;
    }
    switch (lot) {
    case 10000: case 10010: case 10011: case 10040: case 10050: // Messenger gifts (per player)
    case 10500: case 11500: case 12500:                         // covenant gems (common 9440)
    case 17010: case 24060: case 28000: case 32020:             // common 9100 (repeatable)
    case 43000:                                                 // 13501940 (repeatable)
    case 2100900: case 2100910: case 2100920:                   // 12105064 DLC messenger hats
    case 43802:                                                 // cycle variant of 43800
    case 5020: case 16581:                                      // PvP / NPC kill texts
        return true;
    default:
        break;
    }
    if (InRange(lot, 100000, 101999)) {
        return true; // rune / gem use (common 9500)
    }
    if (InRange(lot, 5500, 5959)) {
        return true; // covenant / PvP lots 5500-5950 and their rows
    }
    return false;
}

std::optional<ItemGrant> ClassifyAward(std::int32_t lot, bool host_only) {
    if (!host_only) {
        return std::nullopt; // clients get it in vanilla (2003[36], GetRateItem_IgnoreMultiPlay)
    }
    ItemGrant g;
    g.lot = lot;
    g.flag = ItemLotFlag(lot);
    g.source = ItemSource::Award;
    if (ItemLotDenied(lot, g.flag)) {
        return std::nullopt;
    }
    if (g.flag < 0) {
        g.ledger = ItemLedgerIndex(lot);
        if (g.ledger < 0) {
            return std::nullopt; // flagless and not in the ledger: no way to give it exactly once
        }
    }
    return g;
}

std::optional<ItemGrant> ClassifyFlag(std::int32_t flag, const std::map<std::int32_t, std::int32_t>& captured) {
    ItemGrant g;
    const auto it = captured.find(flag);
    g.lot = it != captured.end() ? it->second : ItemLotForFlag(flag);
    if (g.lot < 0) {
        return std::nullopt;
    }
    g.flag = flag;
    g.source = ItemSource::Flag;
    if (ItemLotDenied(g.lot, flag)) {
        return std::nullopt;
    }
    return g;
}

bool InstancedTreasureFlag(std::int32_t flag, bool instanced, bool captured) {
    return instanced && !captured && flag >= 50000000 && flag < 60000000 && flag / 100000 % 100 != 0;
}

json::Value ItemsToJson(const std::vector<ItemGrant>& items) {
    json::Value v = json::Value::make_object();
    json::Value a = json::Value::make_array();
    for (const ItemGrant& g : items) {
        json::Value row = json::Value::make_array();
        row.push(static_cast<unsigned long long>(g.seq)); // < 2^53: exact as a double
        row.push(g.lot);
        row.push(g.flag);
        row.push(g.ledger);
        row.push(ItemSourceName(g.source));
        if (!g.items.empty()) {
            json::Value list = json::Value::make_array();
            for (const GrantItem& it : g.items) {
                json::Value e = json::Value::make_array();
                e.push(static_cast<unsigned long long>(it.category));
                e.push(it.id);
                e.push(it.count);
                if (it.has_gem) {
                    json::Value gem = json::Value::make_array();
                    for (const std::int32_t x : it.gem) {
                        gem.push(x);
                    }
                    e.push(gem);
                }
                list.push(e);
            }
            row.push(list);
        }
        a.push(row);
    }
    v.set("items", a);
    return v;
}

bool ItemsFromJson(const json::Value& v, std::vector<ItemGrant>* out, std::string* error) {
    try {
        if (v.type != json::Value::Type::Object) {
            throw std::runtime_error("not an object");
        }
        std::vector<ItemGrant> r;
        if (json::arr(v, "items").size() > kMaxItemsPerEvent) {
            throw std::runtime_error("items: too many rows");
        }
        for (const json::Value& row : json::arr(v, "items")) {
            if (row.type != json::Value::Type::Array || (row.array.size() != 5 && row.array.size() != 6)) {
                throw std::runtime_error("items: a row needs [seq, lot, flag, ledger, source(, items)]");
            }
            auto integer = [](const json::Value& x, const char* what) -> double {
                // Range first: converting 1e300 to an integer is undefined.
                if (x.type != json::Value::Type::Number || !(x.number > -9.0e15 && x.number < 9.0e15) ||
                    x.number != static_cast<double>(static_cast<long long>(x.number))) {
                    throw std::runtime_error(std::string("items: ") + what + " is not an integer");
                }
                return x.number;
            };
            ItemGrant g;
            const double seq = integer(row.array[0], "seq");
            if (seq < 0) {
                throw std::runtime_error("items: seq is negative");
            }
            g.seq = static_cast<std::uint64_t>(seq);
            const double lot = integer(row.array[1], "lot"), flag = integer(row.array[2], "flag"),
                         ledger = integer(row.array[3], "ledger");
            if (lot <= 0 || lot > 2147483647.0 || flag < -1 || flag > 2147483647.0 || ledger < -1 ||
                ledger >= kItemLedgerSize) {
                throw std::runtime_error("items: value out of range");
            }
            g.lot = static_cast<std::int32_t>(lot);
            g.flag = static_cast<std::int32_t>(flag);
            g.ledger = static_cast<std::int32_t>(ledger);
            if (row.array[4].type != json::Value::Type::String) {
                throw std::runtime_error("items: source is not a string");
            }
            g.source = ItemSourceFromName(row.array[4].string);
            if (g.DoneFlag() < 0) {
                throw std::runtime_error("items: a row needs a flag or a ledger index");
            }
            if (row.array.size() == 6) {
                const json::Value& list = row.array[5];
                if (list.type != json::Value::Type::Array || list.array.size() > kMaxGrantItems) {
                    throw std::runtime_error("items: the item list is not an array of at most 16");
                }
                for (const json::Value& e : list.array) {
                    if (e.type != json::Value::Type::Array || (e.array.size() != 3 && e.array.size() != 4)) {
                        throw std::runtime_error("items: an item needs [category, id, count(, gem)]");
                    }
                    const double cat = integer(e.array[0], "category"), id = integer(e.array[1], "item id"),
                                 count = integer(e.array[2], "count");
                    if (cat < 0 || cat > 15 || id <= 0 || id > 2147483647.0 || count < 1 || count > 255) {
                        throw std::runtime_error("items: item value out of range");
                    }
                    GrantItem it;
                    it.category = static_cast<std::uint32_t>(cat);
                    it.id = static_cast<std::int32_t>(id);
                    it.count = static_cast<std::int32_t>(count);
                    if (e.array.size() == 4) {
                        const json::Value& gem = e.array[3];
                        if (gem.type != json::Value::Type::Array || gem.array.size() != kGemFields) {
                            throw std::runtime_error("items: gem data needs 8 integers");
                        }
                        for (std::size_t k = 0; k < kGemFields; ++k) {
                            const double x = integer(gem.array[k], "gem field");
                            if (x < -1 || x > 2147483647.0) {
                                throw std::runtime_error("items: gem field out of range");
                            }
                            it.gem[k] = static_cast<std::int32_t>(x);
                        }
                        it.has_gem = true;
                    }
                    if (!GrantItemSupported(it)) {
                        throw std::runtime_error("items: item category / gem data not accepted");
                    }
                    g.items.push_back(it);
                }
            }
            r.push_back(g);
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

bool ItemGrantFromPeerAllowed(const ItemGrant& g, std::string* why) {
    auto no = [&](const char* w) {
        if (why) {
            *why = w;
        }
        return false;
    };
    if (g.source != ItemSource::Award && g.source != ItemSource::Flag && g.source != ItemSource::Full) {
        return no("not a host source (mark / test rows are guest-local)");
    }
    if (ItemLotDenied(g.lot, g.flag)) {
        return no("lot denied");
    }
    if (g.flag < 0) {
        if (g.ledger < 0 || ItemLedgerLot(g.ledger) != g.lot) {
            return no("ledger row does not match the lot");
        }
        return true;
    }
    const std::int32_t table_flag = ItemLotFlag(g.lot);
    if (table_flag == g.flag || ItemLotForFlag(g.flag) == g.lot) {
        return true;
    }
    if (table_flag != kItemNone) {
        return no("the lot has another flag");
    }
    if (ItemLotForFlag(g.flag) != kItemNone) {
        return no("the flag belongs to another lot");
    }
    // A lot / flag pair outside the tables. An honest host of the same game version never sends
    // one: ClassifyAward takes the flag from ITEM_LOT_FLAG and ClassifyFlag only maps flags the
    // table (or a capture of a table lot) gives, so this would be an arbitrary event flag write
    // plus an arbitrary lot award in the guest's own save. Refused (docs/party/items.md 6.5).
    return no("lot / flag pair outside the tables");
}

std::vector<ItemGrant> FilterPeerItems(const std::vector<ItemGrant>& in, std::size_t* rejected) {
    std::vector<ItemGrant> out;
    std::size_t bad = 0;
    for (const ItemGrant& g : in) {
        if (ItemGrantFromPeerAllowed(g)) {
            out.push_back(g);
        } else {
            ++bad;
        }
    }
    if (rejected) {
        *rejected = bad;
    }
    return out;
}

bool GuestGiftShareable(std::int32_t lot, std::int32_t flag) {
    return flag > 0 && ItemLotFlag(lot) == flag && !ItemLotDenied(lot, flag) &&
           !InstancedTreasureFlag(flag, true, false);
}

std::string GiftUpToJsonText(std::int32_t lot, std::int32_t flag) {
    json::Value v = json::Value::make_object();
    v.set("lot", lot);
    v.set("flag", flag);
    return json::dump(v, 0);
}

bool GiftUpFromJsonText(const std::string& text, std::int32_t* lot, std::int32_t* flag, std::string* error) {
    auto fail = [&](const char* why) {
        if (error) {
            *error = why;
        }
        return false;
    };
    json::Value v;
    std::string err;
    if (!json::parse(text, v, err) || v.type != json::Value::Type::Object) {
        return fail("gift_up: not a JSON object");
    }
    const json::Value* l = v.find("lot");
    const json::Value* f = v.find("flag");
    auto integer = [](const json::Value* x, std::int32_t* out) {
        // Range first: converting 1e300 to an integer is undefined.
        if (!x || x->type != json::Value::Type::Number || !(x->number >= -2147483648.0 && x->number <= 2147483647.0) ||
            x->number != static_cast<double>(static_cast<long long>(x->number))) {
            return false;
        }
        *out = static_cast<std::int32_t>(x->number);
        return true;
    };
    std::int32_t a = 0, b = 0;
    if (!integer(l, &a) || !integer(f, &b)) {
        return fail("gift_up: lot / flag must be 32-bit integers");
    }
    if (!GuestGiftShareable(a, b)) {
        return fail("gift_up: not a shareable gift (unknown lot / flag pair, denied, or map treasure)");
    }
    *lot = a;
    *flag = b;
    return true;
}

bool GiftRateLimit::Take(int slot, double now) {
    if (slot < 0 || slot >= 8) {
        return false;
    }
    if (now - start_[slot] >= kWindow) {
        start_[slot] = now;
        used_[slot] = 0;
    }
    if (used_[slot] >= kPerWindow) {
        return false;
    }
    ++used_[slot];
    return true;
}

std::string ItemsToJsonText(const std::vector<ItemGrant>& items) {
    return json::dump(ItemsToJson(items), 0);
}

bool ItemsFromJsonText(const std::string& text, std::vector<ItemGrant>* out, std::string* error) {
    json::Value v;
    std::string err;
    if (!json::parse(text, v, err)) {
        if (error) {
            *error = err;
        }
        return false;
    }
    return ItemsFromJson(v, out, error);
}

bool HostItems::Offer(ItemGrant g) {
    const std::int64_t key = g.Key();
    if (key < 0 || !sent_.insert(key).second) {
        return false;
    }
    g.seq = NextSeq();
    if (q_.size() >= kMaxQueue) {
        q_.pop_front();
    }
    q_.push_back(g);
    return true;
}

bool HostItems::Pop(ItemGrant* out) {
    if (q_.empty()) {
        return false;
    }
    *out = q_.front();
    q_.pop_front();
    return true;
}

bool ItemApplyAllowedNow(const ItemApplyState& s) {
    return s.world_up && !s.loading && s.load_mode == 0 && s.own_world == 1 && s.game_data &&
           (s.session_role == 0 /* idle */ || s.session_role == 3 /* hosting in the own world */);
}

bool ItemSummonedApplyAllowedNow(const ItemApplyState& s) {
    return s.world_up && !s.loading && s.load_mode == 1 && s.own_world == 0 && s.game_data &&
           s.session_role == 6 /* client in the host's world */;
}

ItemApplyMode ItemApplyModeNow(const ItemApplyState& s) {
    if (ItemApplyAllowedNow(s)) {
        return ItemApplyMode::Home;
    }
    return ItemSummonedApplyAllowedNow(s) ? ItemApplyMode::Summoned : ItemApplyMode::None;
}

bool GrantCategorySupported(std::uint32_t category) {
    return category == 0 || category == 1 || category == 2 || category == 4;
}

bool GemDataPlausible(const std::int32_t (&gem)[kGemFields]) {
    if (gem[0] < 0 || gem[0] > 3 || gem[1] < 0 || gem[1] > 1000) {
        return false;
    }
    for (std::size_t k = 2; k < kGemFields; ++k) {
        if (gem[k] < -1 || gem[k] > 99999999) {
            return false;
        }
    }
    return true;
}

bool GrantItemSupported(const GrantItem& it) {
    if (it.category == 8) {
        return it.has_gem && it.count == 1 && it.id > 0 && GemDataPlausible(it.gem);
    }
    return !it.has_gem && GrantCategorySupported(it.category);
}

const char* LotPlanResultName(LotPlanResult r) {
    switch (r) {
    case LotPlanResult::Give: return "give";
    case LotPlanResult::Random: return "random lot without the host's item list";
    case LotPlanResult::Unsupported: return "blood gem without the host's gem data / unsupported category";
    case LotPlanResult::Missing: return "no ItemLotParam row";
    }
    return "?";
}

namespace {

bool SlotWeighted(const LotRowData& r, int i) {
    return r.base[i] > 0 || r.cumulate[i] > 0;
}

bool SlotHasItem(const LotRowData& r, int i) {
    return r.id[i] > 0 && r.category[i] != 0xffffffffu;
}

int WeightedSlots(const LotRowData& r, int* only) {
    int n = 0;
    for (int i = 0; i < 8; ++i) {
        if (SlotWeighted(r, i)) {
            if (only) {
                *only = i;
            }
            ++n;
        }
    }
    return n;
}

int SlotCount(const LotRowData& r, int i) {
    return r.num[i] > 0 ? r.num[i] : 1;
}

} // namespace

bool LotChainHasGem(const std::vector<LotRowData>& chain) {
    for (const LotRowData& r : chain) {
        for (int i = 0; i < 8; ++i) {
            if (SlotWeighted(r, i) && SlotHasItem(r, i) && r.category[i] == 8) {
                return true;
            }
        }
    }
    return false;
}

bool LotChainRandom(const std::vector<LotRowData>& chain) {
    for (const LotRowData& r : chain) {
        if (WeightedSlots(r, nullptr) > 1) {
            return true;
        }
    }
    return false;
}

std::vector<GrantItem> RollLotChain(const std::vector<LotRowData>& chain, std::uint64_t seed) {
    std::vector<GrantItem> out;
    std::uint64_t x = seed ? seed : 0x9e3779b97f4a7c15ull;
    for (const LotRowData& r : chain) {
        std::uint32_t total = 0;
        for (int i = 0; i < 8; ++i) {
            total += r.base[i];
        }
        if (total == 0) {
            int only = -1;
            if (WeightedSlots(r, &only) == 1 && SlotHasItem(r, only) && GrantCategorySupported(r.category[only])) {
                out.push_back({r.category[only], r.id[only], SlotCount(r, only)}); // a cumulate-only slot
            }
            continue;
        }
        x ^= x << 13; // xorshift64
        x ^= x >> 7;
        x ^= x << 17;
        std::uint32_t pick = static_cast<std::uint32_t>(x % total);
        for (int i = 0; i < 8; ++i) {
            if (pick < r.base[i]) {
                if (SlotHasItem(r, i) && GrantCategorySupported(r.category[i])) {
                    out.push_back({r.category[i], r.id[i], SlotCount(r, i)});
                }
                break;
            }
            pick -= r.base[i];
        }
    }
    return out;
}

LotPlan PlanSummonedLot(const std::vector<LotRowData>& chain, const std::vector<GrantItem>& host_items,
                        const std::function<bool(std::int32_t)>& row_done) {
    LotPlan p;
    if (chain.empty()) {
        p.result = LotPlanResult::Missing;
        p.why = "no ItemLotParam row";
        return p;
    }
    auto done = [&](const LotRowData& r) { return r.flag > 0 && row_done && row_done(r.flag); };
    auto add_flag = [&](const LotRowData& r) {
        if (r.flag > 0 && std::find(p.row_flags.begin(), p.row_flags.end(), r.flag) == p.row_flags.end()) {
            p.row_flags.push_back(r.flag);
        }
    };
    if (!host_items.empty()) {
        // The host's list: every item must be a weighted slot of a different row (what one roll
        // of the chain can give), else it is ignored and the rows decide.
        std::vector<bool> used(chain.size(), false);
        std::vector<int> row_of(host_items.size(), -1);
        bool ok = host_items.size() <= chain.size();
        for (std::size_t k = 0; k < host_items.size() && ok; ++k) {
            const GrantItem& it = host_items[k];
            ok = false;
            for (std::size_t r = 0; r < chain.size() && !ok; ++r) {
                if (used[r]) {
                    continue;
                }
                for (int i = 0; i < 8; ++i) {
                    // A blood gem: the generated id is the slot's plus the area's rank offset.
                    const bool id_ok = it.category == 8
                                           ? it.has_gem && it.count == 1 && it.id >= chain[r].id[i] &&
                                                 it.id - chain[r].id[i] <= kMaxGemIdOffset
                                           : chain[r].id[i] == it.id;
                    if (SlotWeighted(chain[r], i) && SlotHasItem(chain[r], i) && chain[r].category[i] == it.category &&
                        id_ok && it.count >= 1 && it.count <= SlotCount(chain[r], i)) {
                        used[r] = true;
                        row_of[k] = static_cast<int>(r);
                        ok = true;
                        break;
                    }
                }
            }
        }
        if (ok) {
            for (std::size_t k = 0; k < host_items.size(); ++k) {
                const LotRowData& r = chain[static_cast<std::size_t>(row_of[k])];
                if (done(r)) {
                    continue;
                }
                if (!GrantItemSupported(host_items[k])) {
                    p.result = LotPlanResult::Unsupported;
                    p.why = "category " + std::to_string(host_items[k].category);
                    p.items.clear();
                    p.row_flags.clear();
                    return p;
                }
                p.items.push_back(host_items[k]);
                add_flag(r);
            }
            // Rows the host's roll left empty are done as well (vanilla sets every record's flag).
            for (std::size_t r = 0; r < chain.size(); ++r) {
                if (!used[r] && !done(chain[r])) {
                    add_flag(chain[r]);
                }
            }
            p.result = LotPlanResult::Give;
            p.why = "host's item list";
            return p;
        }
        p.why = "host's item list does not match the rows; ";
    }
    for (const LotRowData& r : chain) {
        if (done(r)) {
            continue;
        }
        int only = -1;
        const int n = WeightedSlots(r, &only);
        if (n > 1) {
            p.result = LotPlanResult::Random;
            p.why += "row " + std::to_string(r.lot) + " has " + std::to_string(n) + " weighted slots";
            p.items.clear();
            p.row_flags.clear();
            return p;
        }
        add_flag(r);
        if (n == 0 || !SlotHasItem(r, only)) {
            continue; // an empty row gives nothing
        }
        if (!GrantCategorySupported(r.category[only])) {
            p.result = LotPlanResult::Unsupported;
            p.why += "row " + std::to_string(r.lot) + " gives category " + std::to_string(r.category[only]);
            p.items.clear();
            p.row_flags.clear();
            return p;
        }
        p.items.push_back({r.category[only], r.id[only], SlotCount(r, only)});
    }
    p.result = LotPlanResult::Give;
    p.why += "deterministic rows";
    return p;
}

const char* LotFitName(LotFit f) {
    switch (f) {
    case LotFit::Give: return "fits";
    case LotFit::Owned: return "unique item held already";
    case LotFit::Full: return "would exceed the item's max";
    }
    return "?";
}

LotFit ClassifyLotFit(const std::vector<LotSlotState>& slots, std::string* why) {
    LotFit fit = LotFit::Give;
    for (const LotSlotState& s : slots) {
        // Goods only: weapons / armor / runes have no count limit the award can hit.
        if (s.category != 4 || s.id <= 0 || s.owned < 0 || s.max_num <= 0) {
            continue;
        }
        const int num = s.num > 0 ? s.num : 1;
        if (s.owned + num <= s.max_num || s.max_storage > 0) {
            continue; // fits, or the overflow goes to the storage
        }
        const LotFit f = s.max_num == 1 && s.owned >= 1 ? LotFit::Owned : LotFit::Full;
        if (fit == LotFit::Give || f == LotFit::Owned) {
            fit = f;
            if (why) {
                char b[160];
                std::snprintf(b, sizeof b, "goods %d: held %d + %d > max %d, no storage", s.id, s.owned, num,
                              s.max_num);
                *why = b;
            }
        }
    }
    return fit;
}

std::size_t GuestItems::Offer(const std::vector<ItemGrant>& items) {
    std::size_t taken = 0;
    for (const ItemGrant& g : items) {
        const std::int64_t key = g.Key();
        if (key < 0 || done_.count(key)) {
            continue;
        }
        if (g.source == ItemSource::Mark) {
            if (q_.size() >= kMaxQueue) {
                continue;
            }
            q_.push_front(g); // before any replay of the same flag
            ++taken;
            continue;
        }
        if (q_.size() >= kMaxQueue || queued_.count(key)) {
            continue;
        }
        // A lot outside the tables comes once, whatever flags it is paired with.
        if (g.flag >= 0 && ItemLotFlag(g.lot) != g.flag && ItemLotForFlag(g.flag) != g.lot &&
            !adhoc_lots_.insert(g.lot).second) {
            continue;
        }
        queued_.insert(key);
        if (q_.size() >= kMaxQueue) {
            continue; // the host's next full list brings it again
        }
        q_.push_back(g);
        ++taken;
    }
    return taken;
}

std::optional<ItemGrant> GuestItems::Step(const ItemApplyState& s, double now) {
    const ItemApplyMode mode = ItemApplyModeNow(s);
    if (mode == ItemApplyMode::None) {
        stable_ = 0;
    } else {
        stable_ = mode == stable_mode_ ? stable_ + 1 : 1;
    }
    stable_mode_ = mode;
    if (q_.empty() || stable_ < kStableTicks) {
        return std::nullopt;
    }
    // Home: the queue in order. Summoned: the first grant not deferred to the own world (random
    // lots without the host's list, blood gems).
    auto it = q_.begin();
    if (mode == ItemApplyMode::Summoned) {
        while (it != q_.end() && it->source != ItemSource::Mark && home_only_.count(it->Key())) {
            ++it;
        }
        if (it == q_.end()) {
            return std::nullopt;
        }
    }
    // Marks only set a flag (no popup / notice): no spacing for them.
    if (it->source != ItemSource::Mark && (now - last_apply_ < kSpacing || !s.calm)) {
        return std::nullopt; // one popup / notice at a time, and none in a fight
    }
    ItemGrant g = *it;
    q_.erase(it);
    if (g.source != ItemSource::Mark) {
        queued_.erase(g.Key());
    }
    last_mode_ = mode;
    return g;
}

void GuestItems::Defer(const ItemGrant& g) {
    const std::int64_t key = g.Key();
    if (key < 0 || done_.count(key) || queued_.count(key)) {
        return;
    }
    home_only_.insert(key);
    queued_.insert(key);
    q_.push_front(g); // keeps its place for the own world
}

// ---------------------------------------------------------------------------------------------
// Game part
// ---------------------------------------------------------------------------------------------
#ifndef BB_PARTY_ITEMS_NO_GAME

namespace {

using u8 = std::uint8_t;
using u32 = std::uint32_t;
using u64 = std::uint64_t;
using ull = unsigned long long;
using Clock = std::chrono::steady_clock;

constexpr u64 kAwardLot = 0x17ddc50;   // (MapItemMan*, int lot, char hostOnly)
constexpr u64 kGiveList = 0x17d89f0;   // (MapItemMan*, ItemList*): inventory add + popup
constexpr u64 kMapItemMan = 0x553d6e0; // slot: *(u64*)slot is the first argument of every lot call
constexpr u64 kFlagMan = 0x553b100;    // SprjEventFlagMan slot (+0x80 load mode)
constexpr u64 kIsFlag = 0x13cfc00;     // u8 (man, u32 id, u8* exists)
constexpr u64 kSetFlag = 0x13cfcc0;    // void (man, u32 id, u32 on)
constexpr u64 kWts = 0x5556678;        // WorldTransitionState / GameStateMan slot
constexpr u64 kWtsOwnWorld = 0x1592;   // 1 in the own world, 0 summoned into another

// Blood gems (docs/party/items.md 10.1).
constexpr u64 kSprjGaitem = 0x553e990;    // slot: +8 + (handle & 0xffff) * 8 = instance (+8 handle, +0xC item id)
constexpr u64 kGaitemCreate = 0x1a87590;  // u32* (u32* out, SprjGaitem*, u32 gem id): a new gem instance
constexpr u64 kGaitemRelease = 0x1a8bc00; // void (u32* handle): reference -1 (frees at 0)
constexpr u64 kItemGetList = 0x553b1c0;   // the item-get dialog's entries (+8 live list, +0x10 free nodes)
constexpr u64 kMenuState = 0x5562878;     // +0x130: the item-get dialog is up (0x16D86E0)

using AwardFn = void(BB_COOP_SYSV*)(u64, u32, u32);
using GiveListFn = void(BB_COOP_SYSV*)(u64, void*);
using GaitemCreateFn = u32*(BB_COOP_SYSV*)(u32*, u64, u32);
using GaitemReleaseFn = void(BB_COOP_SYSV*)(u32*);
using IsFlagFn = u8(BB_COOP_SYSV*)(u64, u32, u8*);
using SetFlagFn = void(BB_COOP_SYSV*)(u64, u32, u32);

void Log(const char* fmt, ...) __attribute__((format(printf, 1, 2)));
void Log(const char* fmt, ...) {
    char line[768];
    va_list ap;
    va_start(ap, fmt);
    std::vsnprintf(line, sizeof line, fmt, ap);
    va_end(ap);
    perf::Scope z(perf::Zone::Log);
    coop::asyncio::Print(std::string("Party items: ") + line + "\n"); // never blocks the caller (party_async_io.h)
}

bool EnvOff(const char* name) {
    const char* v = std::getenv(name);
    return v && v[0] == '0' && !v[1];
}

double Now() {
    return std::chrono::duration<double>(Clock::now().time_since_epoch()).count();
}

std::atomic<bool> g_on{false};
std::atomic<bool> g_in_apply{false}; // our own 0x17DDC50 call: the hook stands aside
std::atomic<u32> g_added{0};         // items 0x17D89F0 added during our own award

std::mutex g_host_mu;
HostItems g_host;            // under g_host_mu
std::deque<int> g_full_due;  // under g_host_mu
std::mutex g_guest_mu;
GuestItems g_guest;          // under g_guest_mu
std::vector<ItemGrant> g_test; // BB_PARTY_ITEMS_TEST lots, offered once the tick runs
bool g_test_offered = false;
// BB_PARTY_ITEMS_HOST_TEST (live check of the summoned give): the host awards these lots through
// the game's own 0x17DDC50 (hostOnly 1, as EMEVD 2003[4]) once a cooperator has been in its world
// for 20 s, 10 s apart; BB_PARTY_ITEMS_HOST_TEST_FLAGS: flags it sets (SetEventFlag) with the first.
std::vector<std::int32_t> g_host_test;
std::vector<std::uint32_t> g_host_test_flags;
std::size_t g_host_test_next = 0;
double g_host_test_coop = 0, g_host_test_poll = 0, g_host_test_last = 0;

// D5 gifts (party_items.h GuestGiftShareable): guest reports to post, host awards to take.
struct GiftDue {
    int slot = -1;
    std::int32_t lot = 0, flag = 0;
};
std::mutex g_gift_mu;
std::deque<std::string> g_gift_up;  // guest: EVENT gift_up bodies (under g_gift_mu)
std::deque<GiftDue> g_gift_due;     // host: under g_gift_mu
GiftRateLimit g_gift_rate;          // host: under g_gift_mu
double g_gift_last = 0;             // host, main thread: the last gift award
// BB_PARTY_GIFT_TEST=<lot> (live check): a summoned guest awards the lot through the game's own
// 0x17DDC50 (hostOnly 0, as a talk gift) once its world has been steady for 20 s.
std::int32_t g_gift_test = 0;
double g_gift_test_since = 0;
bool g_gift_test_done = false;

u64 Ptr(u64 slot_off) {
    u64 p = 0;
    return SafeGet(Guest(slot_off), &p) ? p : 0;
}

int OwnWorld() {
    const u64 wts = Ptr(kWts);
    u8 v = 0xff;
    return wts && SafeGet(wts + kWtsOwnWorld, &v) ? v : -1;
}

int LoadMode(u64 man) {
    std::int32_t m = -1;
    return man && SafeGet(man + 0x80, &m) ? m : -1;
}

PartyRole Role() {
    return PartyDirector::Get().Role();
}

bool IsFlag(u64 man, std::int64_t id) {
    if (!man || id < 0) {
        return false;
    }
    u8 exists = 0;
    return reinterpret_cast<IsFlagFn>(Guest(kIsFlag))(man, static_cast<u32>(id), &exists) != 0;
}

void SetFlag(u64 man, std::int64_t id, bool on = true) {
    if (man && id >= 0) {
        reinterpret_cast<SetFlagFn>(Guest(kSetFlag))(man, static_cast<u32>(id), on ? 1 : 0);
    }
}

void SeedHostSeq() {
    // Wall-clock seeded like travel: a restarted host keeps counting upward.
    const u64 seed = static_cast<u64>(
        std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch())
            .count());
    std::lock_guard<std::mutex> lk(g_host_mu);
    g_host.SeedSeq(seed);
}

// ---- Blood gems ----

/// A gem's gaitem instance (SprjGaitem +8 + index * 8; the handle at +8 must match), else 0.
u64 GemInstance(u32 handle) {
    const u64 gi = Ptr(kSprjGaitem);
    if (!gi || !handle || !(handle & 0x800000u) || (handle & 0xffffu) == 0xffffu) {
        return 0;
    }
    u64 inst = 0;
    u32 h = 0, type = 0;
    if (!SafeGet(gi + 8 + 8ull * (handle & 0xffffu), &inst) || !inst || !SafeGet(inst + 8, &h) || h != handle ||
        !SafeGet(inst + 0xc, &type) || (type >> 28) != 8) {
        return 0;
    }
    return inst;
}

/// Host: the gem behind a give-list handle (id + instance data), as 0x1A87E20 wrote it.
bool ReadGem(u32 handle, GrantItem* it) {
    const u64 inst = GemInstance(handle);
    u32 type = 0;
    if (!inst || !SafeGet(inst + 0xc, &type) || !SafeRead(inst + 0x18, it->gem, sizeof it->gem)) {
        return false;
    }
    it->category = 8;
    it->id = static_cast<std::int32_t>(type & 0x0fffffffu);
    it->count = 1;
    it->has_gem = true;
    return GemDataPlausible(it->gem);
}

std::string GemText(const GrantItem& it) {
    char b[160];
    std::snprintf(b, sizeof b, "gem %d (flags %d, rank %d, effects %d %d %d %d %d %d)", it.id, it.gem[0], it.gem[1],
                  it.gem[2], it.gem[3], it.gem[4], it.gem[5], it.gem[6], it.gem[7]);
    return b;
}

/// Guest: the host's gem recreated - a new gaitem instance with the host's id and instance data,
/// handed to the lot award's own give list 0x17D89F0 (inventory, else storage / the ground, and
/// the native item-get dialog with its sound, as the host's award showed it). The gem's
/// GemGenParam row and every effect's GemeffectParam row must exist first.
bool GiveGem(const GrantItem& it, std::string* why) {
    if (!it.has_gem || it.category != 8 || it.count != 1) {
        *why = "no gem data";
        return false;
    }
    if (!GameParamRow("GemGenParam", "GEM_GEN_PARAM_ST", static_cast<u32>(it.id))) {
        *why = "no GemGenParam row " + std::to_string(it.id);
        return false;
    }
    for (std::size_t k = 2; k < kGemFields; ++k) {
        if (it.gem[k] != -1 && !GameParamRow("GemeffectParam", "GEMEFFECT_PARAM_ST", static_cast<u32>(it.gem[k]))) {
            *why = "no GemeffectParam row " + std::to_string(it.gem[k]);
            return false;
        }
    }
    static const u8 kCreate[] = {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54,
                                 0x53, 0x48, 0x83, 0xec, 0x28, 0x41, 0x89, 0xd6, 0x48, 0x89, 0xf3};
    static const u8 kRelease[] = {0x55, 0x48, 0x89, 0xe5, 0x41, 0x56, 0x53, 0x48, 0x89, 0xfb, 0x8b, 0x33};
    static const u8 kGive[] = {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54,
                               0x53, 0x48, 0x81, 0xec, 0xb8, 0x01, 0x00, 0x00, 0x49, 0x89, 0xf7};
    if (!MatchesOriginal(kGaitemCreate, kCreate, sizeof kCreate) ||
        !MatchesOriginal(kGaitemRelease, kRelease, sizeof kRelease) || !MatchesOriginal(kGiveList, kGive, sizeof kGive)) {
        *why = "gaitem / give-list code differs from 1.09";
        return false;
    }
    const u64 gi = Ptr(kSprjGaitem), mim = Ptr(kMapItemMan);
    if (!gi || !mim) {
        *why = "no SprjGaitem / MapItemMan";
        return false;
    }
    u32 handle = 0;
    reinterpret_cast<GaitemCreateFn>(Guest(kGaitemCreate))(&handle, gi, static_cast<u32>(it.id));
    const u64 inst = GemInstance(handle);
    u32 type = 0;
    if (!inst || !SafeGet(inst + 0xc, &type) || type != (0x80000000u | static_cast<u32>(it.id))) {
        if (handle) {
            reinterpret_cast<GaitemReleaseFn>(Guest(kGaitemRelease))(&handle);
        }
        *why = "no gaitem instance (table full?)";
        return false;
    }
    std::memcpy(reinterpret_cast<void*>(inst + 0x18), it.gem, sizeof it.gem);
    // ItemList {u32 n; n x {u32 gaitem, u32 id | category << 28, u32 count, u32 -1}} like 0x17DDC50's.
    u32 list[16] = {};
    list[0] = 1;
    list[1] = handle;
    list[2] = type;
    list[3] = 1;
    list[4] = 0xffffffffu;
    g_in_apply = true;
    reinterpret_cast<GiveListFn>(Guest(kGiveList))(mim, list);
    g_in_apply = false;
    reinterpret_cast<GaitemReleaseFn>(Guest(kGaitemRelease))(&handle); // the inventory keeps its own reference
    return true;
}

/// Host: the last give lists with a blood gem that came from a pickup (0x17D8570 -> 0x17D89F0,
/// not through 0x17DDC50). The treasure's flag reaches OnHostFlagSet a little later (C2's scan),
/// and the gem the host really got rides along. Main thread only.
struct RecentGive {
    double at = 0;
    std::vector<GrantItem> items;
};
std::deque<RecentGive> g_recent_gem_gives;

// ---- The award hook (main thread: EMEVD, Lua) ----

AwardFn g_award_original = nullptr; // the trampoline (ReplacePrologue)
bool g_capturing = false;           // main thread: the host's own award runs, GiveListEntry records
std::vector<GrantItem> g_captured;  // its items (category, id, count)
bool g_captured_bad = false;        // an item that could not be read (the guest resolves the lot itself)

/// Host side of an award, before the game runs it: the grant to offer once the call returned
/// (its items captured), else nothing. Guest side: the mark for a lot received while summoned.
std::optional<ItemGrant> AwardEntry(u64 lot_arg, u64 host_only_arg) {
    perf::Scope z(perf::Zone::HookAward);
    const std::int32_t lot = static_cast<std::int32_t>(static_cast<u32>(lot_arg));
    const bool host_only = static_cast<u8>(host_only_arg) != 0;
    const PartyRole role = Role();
    const int own = OwnWorld();
    const std::int32_t flag = ItemLotFlag(lot);
    Log("award lot %d (hostOnly %d, flag %d) in %s world, role %s", lot, host_only ? 1 : 0, flag,
        own == 1 ? "the own" : own == 0 ? "another's" : "an unknown",
        role == PartyRole::Host ? "host" : role == PartyRole::Guest ? "guest" : "none");
    if (own == 1 && host_only && flag < 0 && !ItemLotDenied(lot, flag)) {
        // A ledger lot this player earns in its own world (any role, solo too): its ledger bit, so
        // a host's later replay of the same lot gives nothing twice.
        const std::int32_t idx = ItemLedgerIndex(lot);
        if (idx >= 0) {
            SetFlag(Ptr(kFlagMan), std::int64_t(kItemLedgerBase) + idx);
            Log("own award of ledger lot %d: ledger flag %d set", lot, int(kItemLedgerBase) + idx);
        }
    }
    if (role == PartyRole::Host && own == 1) {
        const std::optional<ItemGrant> g = ClassifyAward(lot, host_only);
        {
            std::lock_guard<std::mutex> lk(g_host_mu);
            if (flag > 0) {
                g_host.Capture(flag, lot);
            }
        }
        if (!g && host_only && flag < 0 && !ItemLotDenied(lot, flag)) {
            Log("host award lot %d: flagless and not in the ledger table; not replayed", lot);
        }
        return g;
    } else if (role == PartyRole::Guest && own == 0 && !host_only && flag > 0 && !ItemLotDenied(lot, flag)) {
        // We got it in the host's world; its flag went to the overlay only. Set it at home so the
        // host's replay of the same lot gives nothing twice.
        ItemGrant m;
        m.lot = lot;
        m.flag = flag;
        m.source = ItemSource::Mark;
        {
            std::lock_guard<std::mutex> lk(g_guest_mu);
            g_guest.Offer({m});
        }
        Log("guest received lot %d while summoned: flag %d goes into the own save (pool)", lot, flag);
        if (GuestGiftShareable(lot, flag)) {
            // D5: an NPC's gift in the host's world (shared quest choices): the host takes it too.
            std::lock_guard<std::mutex> lk(g_gift_mu);
            if (g_gift_up.size() < 64) {
                g_gift_up.push_back(GiftUpToJsonText(lot, flag));
                Log("gift: lot %d (flag %d) reported to the host (the NPC moved on in its world too)", lot, flag);
            }
        }
    }
    return std::nullopt;
}

BB_COOP_SYSV void AwardReplace(u64 mim, u64 lot_arg, u64 host_only_arg) {
    if (!g_on.load() || g_in_apply.load()) {
        g_award_original(mim, static_cast<u32>(lot_arg), static_cast<u32>(host_only_arg));
        return;
    }
    std::optional<ItemGrant> g = AwardEntry(lot_arg, host_only_arg);
    g_captured.clear();
    g_captured_bad = false;
    g_capturing = g.has_value();
    g_award_original(mim, static_cast<u32>(lot_arg), static_cast<u32>(host_only_arg));
    g_capturing = false;
    if (!g) {
        return;
    }
    // What the host's roll really gave: guests replay exactly that while summoned.
    if (!g_captured_bad && g_captured.size() <= kMaxGrantItems) {
        g->items = g_captured;
    }
    bool queued;
    {
        std::lock_guard<std::mutex> lk(g_host_mu);
        queued = g_host.Offer(*g);
    }
    std::string list;
    for (const GrantItem& it : g->items) {
        list += (list.empty() ? "" : ", ") + std::to_string(it.category) + ":" + std::to_string(it.id) + "x" +
                std::to_string(it.count);
    }
    for (const GrantItem& it : g->items) {
        if (it.has_gem) {
            list += " [" + GemText(it) + "]";
        }
    }
    Log("host award %s %s; items [%s]%s", DescribeItem(*g).c_str(), queued ? "queued for the party" : "already sent",
        list.c_str(), g_captured_bad ? " (an item could not be read: guests resolve the lot themselves)" : "");
}

// Our own award's inventory adds (evidence for the apply log): ItemList {u32 n, then n x
// {u32 gaitem, u32 itemId | category << 28, u32 count, u32 -1}} from +4 (0x17D8A42..0x17D8A8A).
BB_COOP_SYSV void GiveListEntry(u64, u64 list, u64, u64, u64, u64) {
    perf::Scope z(perf::Zone::HookGiveList);
    // Host side: the award's list (g_capturing), or a pickup's list (it may hold a blood gem).
    const bool host_pickup = !g_in_apply.load() && !g_capturing && g_on.load() && Role() == PartyRole::Host &&
                             OwnWorld() == 1;
    if (!list || (!g_in_apply.load() && !g_capturing && !host_pickup)) {
        return;
    }
    u32 n = 0;
    if (!SafeGet(list, &n)) {
        return;
    }
    if (g_capturing || host_pickup) {
        std::vector<GrantItem> items;
        bool bad = false, gem = false;
        for (u32 i = 0; i < n && i < 8; ++i) {
            u32 e[4] = {};
            if (!SafeRead(list + 4 + 16ull * i, e, sizeof e)) {
                bad = true;
                continue;
            }
            GrantItem it;
            it.category = e[1] >> 28;
            it.id = static_cast<std::int32_t>(e[1] & 0x0fffffffu);
            it.count = static_cast<std::int32_t>(e[2]);
            if (it.category == 8) {
                if (it.count != 1 || !ReadGem(e[0], &it)) {
                    bad = true;
                    continue;
                }
                gem = true;
            }
            if (!GrantItemSupported(it) || it.id <= 0 || it.count < 1 || it.count > 255) {
                bad = true;
                continue;
            }
            items.push_back(it);
        }
        if (g_capturing) {
            g_captured.insert(g_captured.end(), items.begin(), items.end());
            g_captured_bad = g_captured_bad || bad;
        } else if (gem && !bad) {
            g_recent_gem_gives.push_back({Now(), items});
            while (g_recent_gem_gives.size() > 8) {
                g_recent_gem_gives.pop_front();
            }
            for (const GrantItem& it : items) {
                if (it.has_gem) {
                    Log("host picked up %s; kept for its treasure flag's report", GemText(it).c_str());
                }
            }
        }
        return;
    }
    g_added.fetch_add(n);
    for (u32 i = 0; i < n && i < 8; ++i) {
        u32 e[4] = {};
        if (SafeRead(list + 4 + 16ull * i, e, sizeof e)) {
            Log("  inventory add %u/%u: item %u category %u count %u (gaitem 0x%x)", i + 1, n, e[1] & 0x0fffffffu,
                e[1] >> 28, e[2], e[0]);
        }
    }
}

// ---- Parity patches ----

bool WriteImage(u64 off, const u8* bytes, std::size_t n) {
    unsigned char* at = Image() + off;
#ifdef _WIN32
    DWORD old = 0;
    if (!VirtualProtect(at, n, PAGE_EXECUTE_READWRITE, &old)) {
        return false;
    }
    std::memcpy(at, bytes, n);
    DWORD unused = 0;
    VirtualProtect(at, n, old, &unused);
    FlushInstructionCache(GetCurrentProcess(), at, n);
#else
    std::memcpy(at, bytes, n);
#endif
    return true;
}

void Patch(const char* name, u64 off, std::initializer_list<u8> original, std::initializer_list<u8> patched) {
    if (Matches(off, patched.begin(), patched.size())) {
        Log("%s (+0x%llx): already applied", name, ull(off));
    } else if (!Matches(off, original.begin(), original.size())) {
        Log("%s (+0x%llx): MISMATCH, not applied", name, ull(off));
    } else if (!WriteImage(off, patched.begin(), patched.size())) {
        Log("%s (+0x%llx): could not be written", name, ull(off));
    } else {
        Log("%s (+0x%llx): applied", name, ull(off));
    }
}

void ParityPatches() {
    // docs/party/items.md 5, "optional parity patches"; each verified against the 1.09 bytes.
    // 0x18FC93D test cl, cl (isClient); 0x18FC93F jne +6 -> the 0.5 kill-echo multiplier.
    Patch("full kill echoes for clients", 0x18fc93f, {0x75, 0x06}, {0x90, 0x90});
    // 0x133557F cmp eax, 8 (chr type | 8 == 8: host or own-world grey); je skips the halving.
    Patch("full boss clear bonus for phantoms", 0x1335582, {0x74, 0x12}, {0xeb, 0x12});
    // 0x17DD18E setne cl; 0x17DD191 or cl, al -> xor cl, cl: the isGuestDrop filter's only input
    // ([rbp-0x208], read once at 0x17DD75D) is 0, so a client keeps the whole enemy drop.
    Patch("full enemy drops for clients", 0x17dd191, {0x08, 0xc1}, {0x30, 0xc9});
}

std::vector<long> EnvList(const char* name) {
    std::vector<long> out;
    const char* v = std::getenv(name);
    if (!v) {
        return out;
    }
    std::string s(v);
    std::size_t at = 0;
    while (at < s.size()) {
        std::size_t end = s.find(',', at);
        if (end == std::string::npos) {
            end = s.size();
        }
        const long x = std::strtol(s.substr(at, end - at).c_str(), nullptr, 10);
        if (x > 0) {
            out.push_back(x);
        }
        at = end + 1;
    }
    return out;
}

void ParseHostTest() {
    for (const long lot : EnvList("BB_PARTY_GIFT_TEST")) {
        g_gift_test = static_cast<std::int32_t>(lot);
        Log("BB_PARTY_GIFT_TEST: a summoned guest awards lot %d itself (shareable %d)", g_gift_test,
            GuestGiftShareable(g_gift_test, ItemLotFlag(g_gift_test)) ? 1 : 0);
    }
    for (const long lot : EnvList("BB_PARTY_ITEMS_HOST_TEST")) {
        g_host_test.push_back(static_cast<std::int32_t>(lot));
    }
    for (const long f : EnvList("BB_PARTY_ITEMS_HOST_TEST_FLAGS")) {
        g_host_test_flags.push_back(static_cast<std::uint32_t>(f));
    }
    if (!g_host_test.empty()) {
        Log("BB_PARTY_ITEMS_HOST_TEST: %zu lot(s), %zu flag(s): the host awards them once a cooperator is in",
            g_host_test.size(), g_host_test_flags.size());
    }
}

/// The host fixture (main thread): the game's award with hostOnly 1, through our hook.
void HostTestTick(double now) {
    if (g_host_test_next >= g_host_test.size() || Role() != PartyRole::Host || OwnWorld() != 1) {
        return;
    }
    const GameSnapshot quick = ReadGameState(false);
    if (!quick.world_up || quick.loading) {
        return;
    }
    if (!g_host_test_coop) {
        if (now - g_host_test_poll < 1.0) {
            return;
        }
        g_host_test_poll = now;
        if (ReadGameState(true).cooperators > 0) {
            g_host_test_coop = now;
            Log("host test: a cooperator is in the world; awards in 20 s");
        }
        return;
    }
    if (now - g_host_test_coop < 20.0 || now - g_host_test_last < 10.0) {
        return;
    }
    g_host_test_last = now;
    const std::int32_t lot = g_host_test[g_host_test_next++];
    const u64 mim = Ptr(kMapItemMan);
    if (!mim) {
        return;
    }
    Log("host test: awarding lot %d through 0x17DDC50 (hostOnly 1)", lot);
    reinterpret_cast<AwardFn>(Guest(kAwardLot))(mim, static_cast<u32>(lot), 1);
    if (g_host_test_next == 1) {
        const u64 man = Ptr(kFlagMan);
        for (const std::uint32_t f : g_host_test_flags) {
            const bool was = IsFlag(man, f);
            SetFlag(man, f);
            Log("host test: flag %u %d -> %d", f, was ? 1 : 0, IsFlag(man, f) ? 1 : 0);
        }
    }
}

/// Held counts of a lot's deterministic items (evidence in the logs).
/// Defined below (the ItemLotParam readers).
std::vector<LotRowData> LotChain(std::int32_t lot);

std::string HeldSummary(std::int32_t lot) {
    std::string out;
    for (const LotRowData& r : LotChain(lot)) {
        for (int i = 0; i < 8; ++i) {
            if ((r.base[i] > 0 || r.cumulate[i] > 0) && r.id[i] > 0 && GrantCategorySupported(r.category[i])) {
                char b[96];
                std::snprintf(b, sizeof b, "%s%u:%d held %d", out.empty() ? "" : ", ", r.category[i], r.id[i],
                              ItemCount(r.category[i] << 28, static_cast<u32>(r.id[i])));
                out += b;
            }
        }
    }
    return out.empty() ? "-" : out;
}

void ParseTestLots() {
    const char* v = std::getenv("BB_PARTY_ITEMS_TEST");
    if (!v || !*v) {
        return;
    }
    std::string s(v);
    std::size_t at = 0;
    while (at < s.size()) {
        std::size_t end = s.find(',', at);
        if (end == std::string::npos) {
            end = s.size();
        }
        const long lot = std::strtol(s.substr(at, end - at).c_str(), nullptr, 10);
        at = end + 1;
        if (lot <= 0) {
            continue;
        }
        ItemGrant g;
        g.lot = static_cast<std::int32_t>(lot);
        g.flag = ItemLotFlag(g.lot);
        g.ledger = g.flag < 0 ? ItemLedgerIndex(g.lot) : kItemNone;
        g.source = ItemSource::Test;
        g.seq = g_test.size() + 1;
        if (g.DoneFlag() < 0) {
            Log("BB_PARTY_ITEMS_TEST: lot %d has neither a flag nor a ledger index; skipped", g.lot);
            continue;
        }
        g_test.push_back(g);
        Log("BB_PARTY_ITEMS_TEST: will apply %s in the own world", DescribeItem(g).c_str());
    }
}

void FillGoodsLimits(LotSlotState* s) {
    if (s->category != 4) {
        return;
    }
    s->owned = ItemCount(0x40000000u, static_cast<u32>(s->id));
    if (const u64 goods = GameParamRow("EquipParamGoods", "EQUIP_PARAM_GOODS_ST", static_cast<u32>(s->id))) {
        std::int16_t mx = -1, rep = -1;
        if (SafeGet(goods + 0x36, &mx) && SafeGet(goods + 0x49, &rep)) {
            s->max_num = mx;
            s->max_storage = rep;
        }
    }
}

// ItemLotParam (ITEMLOT_PARAM_ST, 1.09 paramdef): lotItemId01..08 s32 +0x00, lotItemCategory01..08
// u32 +0x20, lotItemBasePoint01..08 u16 +0x40, lotItemNum01..08 u8 +0x8A. EquipParamGoods
// (EQUIP_PARAM_GOODS_ST): maxNum s16 +0x36, maxRepositoryNum s16 +0x49.
std::vector<LotSlotState> LotSlots(std::int32_t lot) {
    std::vector<LotSlotState> out;
    const u64 row = GameParamRow("ItemLotParam", "ITEMLOT_PARAM_ST", static_cast<u32>(lot));
    if (!row) {
        return out;
    }
    for (int i = 0; i < 8; ++i) {
        LotSlotState s;
        std::uint16_t base = 0;
        u8 num = 0;
        if (!SafeGet(row + 4u * i, &s.id) || !SafeGet(row + 0x20 + 4u * i, &s.category) ||
            !SafeGet(row + 0x40 + 2u * i, &base) || !SafeGet(row + 0x8a + i, &num)) {
            continue;
        }
        if (s.id <= 0 || s.category == 0xffffffffu || base == 0) {
            continue;
        }
        s.num = num;
        FillGoodsLimits(&s);
        out.push_back(s);
    }
    return out;
}

/// ItemLotParam rows lot, lot + 1, ... while they exist (the roll's chain, 0x17CEAF0).
std::vector<LotRowData> LotChain(std::int32_t lot) {
    std::vector<LotRowData> out;
    for (std::size_t k = 0; k < kMaxLotChain; ++k) {
        const u64 row = GameParamRow("ItemLotParam", "ITEMLOT_PARAM_ST", static_cast<u32>(lot) + static_cast<u32>(k));
        if (!row) {
            break;
        }
        LotRowData r;
        r.lot = lot + static_cast<std::int32_t>(k);
        bool ok = SafeGet(row + 0x80, &r.flag);
        for (int i = 0; i < 8 && ok; ++i) {
            ok = SafeGet(row + 4u * i, &r.id[i]) && SafeGet(row + 0x20 + 4u * i, &r.category[i]) &&
                 SafeGet(row + 0x40 + 2u * i, &r.base[i]) && SafeGet(row + 0x50 + 2u * i, &r.cumulate[i]) &&
                 SafeGet(row + 0x8a + i, &r.num[i]);
        }
        if (!ok) {
            break;
        }
        out.push_back(r);
    }
    return out;
}

/// Host: a random lot gets one roll here, so every guest gets the same items (deterministic lots
/// are resolved by each guest from its own ItemLotParam).
void AttachHostRoll(ItemGrant* g) {
    if (!g || !g->items.empty()) {
        return;
    }
    const std::vector<LotRowData> chain = LotChain(g->lot);
    if (!LotChainRandom(chain) || LotChainHasGem(chain)) {
        return; // a gem cannot be rolled here (no instance data): the guest waits for its own world
    }
    static std::uint64_t salt = static_cast<std::uint64_t>(Clock::now().time_since_epoch().count());
    salt = salt * 6364136223846793005ull + 1442695040888963407ull;
    g->items = RollLotChain(chain, salt ^ static_cast<std::uint64_t>(g->lot));
    Log("host rolled random lot %d once for the party: %zu item(s)", g->lot, g->items.size());
}

/// True when the award ran (a popup may have opened).
bool Apply(const ItemGrant& g) {
    const u64 man = Ptr(kFlagMan);
    const u64 mim = Ptr(kMapItemMan);
    const std::int64_t done = g.DoneFlag();
    if (g.source == ItemSource::Mark) {
        const bool was = IsFlag(man, done);
        SetFlag(man, done);
        Log("mark lot %d: flag %lld %s", g.lot, static_cast<long long>(done), was ? "was already set" : "set");
        return false;
    }
    if (g.source == ItemSource::Test) {
        // BB_PARTY_ITEMS_TEST: what the inventory check sees, before any other rule.
        std::string why;
        const std::vector<LotSlotState> slots = LotSlots(g.lot);
        const LotFit fit = ClassifyLotFit(slots, &why);
        for (const LotSlotState& s : slots) {
            Log("test lot %d slot: category %u id %d num %d held %d max %d storage max %d", g.lot, s.category, s.id,
                s.num, s.owned, s.max_num, s.max_storage);
        }
        Log("test lot %d: %zu slot(s), %s%s%s", g.lot, slots.size(), LotFitName(fit), why.empty() ? "" : ": ",
            why.c_str());
    }
    if (IsFlag(man, done)) {
        Log("skip %s: already given (flag %lld set)", DescribeItem(g).c_str(), static_cast<long long>(done));
        return false;
    }
    if (!mim) {
        Log("skip %s: no MapItemMan", DescribeItem(g).c_str());
        return false;
    }
    // A flagless (ledger) lot the guest earned itself is not checked through the awarding event's
    // completion flag here: C2 writes the host's boss / event flags into this save (join snapshot
    // at the first steady world, live while summoned) before any grant is applied, so the flag
    // would also skip every boss reward the guest never got (a boss killed together: 12401800
    // synced, lot 50000001 skipped). SeedLedgerFromOwnSave records the save's own history as
    // ledger bits before C2 touches it, and own-world awards set their bit in the award hook.
    // An item the game would refuse (a unique key / badge already held, a count at its max with
    // no storage): it would open a blocking "inventory or storage max" dialog. Count it as given.
    std::string why;
    const LotFit fit = ClassifyLotFit(LotSlots(g.lot), &why);
    if (fit != LotFit::Give) {
        SetFlag(man, done);
        Log("skip %s: %s (%s); flag %lld set instead", DescribeItem(g).c_str(), LotFitName(fit), why.c_str(),
            static_cast<long long>(done));
        return false;
    }
    // The ledger bit goes in first: the give can start a save (run A of the C3 check lost a
    // ledger bit written after the award), so the save that holds the item holds the bit too.
    // A lot that gives nothing clears it again.
    if (g.flag < 0) {
        SetFlag(man, done);
    }
    g_added = 0;
    g_in_apply = true;
    reinterpret_cast<AwardFn>(Guest(kAwardLot))(mim, static_cast<u32>(g.lot), 0);
    g_in_apply = false;
    const u32 added = g_added.load();
    if (g.flag < 0 && added == 0) {
        SetFlag(man, done, false);
    }
    const bool now_set = IsFlag(man, done);
    Log("gave %s: 0x17DDC50(lot %d, 0) added %u item entr%s; flag %lld is %s", DescribeItem(g).c_str(), g.lot, added,
        added == 1 ? "y" : "ies", static_cast<long long>(done), now_set ? "set" : "CLEAR (nothing given)");
    return true;
}

const char* CategoryWord(std::uint32_t c) {
    switch (c) {
    case 0: return "weapon";
    case 1: return "armor";
    case 2: return "rune";
    case 4: return "goods";
    }
    return "item";
}

bool OwnSaveFlag(std::int64_t id) {
    bool v = false;
    return id >= 0 && progress::ReadFlagOwnSave(static_cast<u32>(id), &v) && v;
}

enum class SummonedResult { Given, Skipped, Defer };

/// While summoned (load mode 1: the live flag store is the host's overlay, where the host's flag
/// is already set, so 0x17DDC50 would roll nothing): the lot's items go straight into the own
/// inventory (GiveItemDirect 0x131CB70, no popup) and its flags / ledger bit into the own save's
/// pool (C2's mode-1 pool write). Nothing is written to the overlay.
SummonedResult ApplySummoned(const ItemGrant& g) {
    const std::int64_t done = g.DoneFlag();
    if (g.source == ItemSource::Mark) {
        const bool was = OwnSaveFlag(done);
        const bool ok = progress::WriteFlagOwnSave(static_cast<u32>(done), true);
        Log("mark lot %d while summoned: own-save flag %lld %s", g.lot, static_cast<long long>(done),
            was ? "was already set" : ok ? "set (pool)" : "NOT written");
        if (!was && ok) {
            RequestGameSave("C3 mark");
        }
        return SummonedResult::Skipped;
    }
    if (OwnSaveFlag(done)) {
        Log("skip %s: already given (own-save flag %lld set; %s)", DescribeItem(g).c_str(),
            static_cast<long long>(done), HeldSummary(g.lot).c_str());
        return SummonedResult::Skipped;
    }
    const std::vector<LotRowData> chain = LotChain(g.lot);
    const LotPlan plan = PlanSummonedLot(chain, g.items, [](std::int32_t f) { return OwnSaveFlag(f); });
    if (plan.result != LotPlanResult::Give) {
        Log("%s: not while summoned (%s: %s); waits for the own world", DescribeItem(g).c_str(),
            LotPlanResultName(plan.result), plan.why.c_str());
        return SummonedResult::Defer;
    }
    // The same refusal rule as at home: a unique item already held / no room counts as given.
    std::vector<LotSlotState> slots;
    for (const GrantItem& it : plan.items) {
        LotSlotState s;
        s.category = it.category;
        s.id = it.id;
        s.num = it.count;
        FillGoodsLimits(&s);
        slots.push_back(s);
    }
    std::string why;
    const LotFit fit = ClassifyLotFit(slots, &why);
    // Flags first (the save that holds the items holds the flags; a save between the two loses an
    // item rather than giving it twice).
    std::vector<std::int64_t> flags = {done};
    for (const std::int32_t f : plan.row_flags) {
        if (f != done) {
            flags.push_back(f);
        }
    }
    std::string flag_list;
    for (const std::int64_t f : flags) {
        const bool ok = progress::WriteFlagOwnSave(static_cast<u32>(f), true);
        flag_list += (flag_list.empty() ? "" : ",") + std::to_string(f) + (ok ? "" : "(NOT written)");
    }
    if (fit != LotFit::Give) {
        Log("skip %s while summoned: %s (%s); own-save flag(s) %s set instead", DescribeItem(g).c_str(),
            LotFitName(fit), why.c_str(), flag_list.c_str());
        RequestGameSave("C3 item flags");
        return SummonedResult::Skipped;
    }
    std::string given, notice;
    int gave = 0, native = 0;
    for (const GrantItem& it : plan.items) {
        char b[256];
        if (it.category == 8) {
            // A blood gem: the host's own gem recreated, given through the award's give list
            // (which also queues the native item-get dialog).
            std::string why;
            const u32 added_before = g_added.load();
            const bool ok = GiveGem(it, &why);
            gave += ok ? 1 : 0;
            native += ok ? 1 : 0;
            std::snprintf(b, sizeof b, "blood %s (%s)", GemText(it).c_str(),
                          !ok ? why.c_str()
                              : g_added.load() != added_before ? "inventory add, item-get dialog"
                                                                 : "given, item-get dialog");
            given += (given.empty() ? "" : "; ") + std::string(b);
            std::snprintf(b, sizeof b, "blood gem %d", it.id);
            notice += (notice.empty() ? "" : ", ") + std::string(b);
            continue;
        }
        const u32 bits = it.category << 28;
        const int before = ItemCount(bits, static_cast<u32>(it.id));
        const bool ok = GiveItem(bits, static_cast<u32>(it.id), it.count);
        const int after = ItemCount(bits, static_cast<u32>(it.id));
        // The game's own "item acquired" dialog entry, as the host's lot award shows it.
        const bool shown = ok && ShowItemGet(bits, static_cast<u32>(it.id), it.count);
        gave += ok ? 1 : 0;
        native += shown ? 1 : 0;
        std::snprintf(b, sizeof b, "%s %d x%d (held %d -> %d%s%s)", CategoryWord(it.category), it.id, it.count,
                      before, after, ok ? "" : ", GiveItemDirect unavailable",
                      !ok ? "" : shown ? ", item-get dialog" : ", NO item-get dialog");
        given += (given.empty() ? "" : "; ") + std::string(b);
        std::snprintf(b, sizeof b, "%s %d x%d", CategoryWord(it.category), it.id, it.count);
        notice += (notice.empty() ? "" : ", ") + std::string(b);
    }
    if (!plan.items.empty() && gave == 0) {
        for (const std::int64_t f : flags) {
            progress::WriteFlagOwnSave(static_cast<u32>(f), false);
        }
        Log("%s: the direct give is not available; flags cleared again, waits for the own world",
            DescribeItem(g).c_str());
        return SummonedResult::Defer;
    }
    Log("gave %s while summoned (%s): %s; own-save flag(s) %s set (pool, load mode %d), overlay untouched",
        DescribeItem(g).c_str(), plan.why.c_str(), given.empty() ? "nothing left to give" : given.c_str(),
        flag_list.c_str(), progress::FlagLoadMode());
    RequestGameSave("C3 items given while summoned"); // items and flags land in the same save
    if (gave == 0) {
        return SummonedResult::Skipped;
    }
    if (native < gave) {
        // Fallback only: the native dialog could not be queued for some item.
        party::status::SetLastEvent("Party item received: " + notice);
    }
    return SummonedResult::Given;
}

} // namespace

void InstallItemsPatches() {
    static std::atomic<bool> done{false};
    if (done.exchange(true)) {
        return;
    }
    if (!Image()) {
        Log("no image; items off");
        return;
    }
    if (bb_party_enabled() && !EnvOff("BB_PARTY_FULL_REWARDS")) {
        ParityPatches();
    } else {
        Log("parity patches off (%s)", bb_party_enabled() ? "BB_PARTY_FULL_REWARDS=0" : "not in party mode");
    }
    if (EnvOff("BB_PARTY_ITEMS")) {
        Log("BB_PARTY_ITEMS=0: no item replay");
        return;
    }
    // push rbp; mov rbp, rsp; push r15, r14, r13, r12, rbx (13 bytes; then sub rsp, 0x1a8).
    // Replaced (not an entry hook): the host's call runs inside ours, so the items its roll gave
    // (0x17D89F0, GiveListEntry) travel with the grant.
    void* original = nullptr;
    if (ReplacePrologue(kAwardLot, {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54, 0x53},
                        reinterpret_cast<const void*>(&AwardReplace), &original, "item award (0x17DDC50)")) {
        g_award_original = reinterpret_cast<AwardFn>(original);
    } else {
        Log("no award hook: host-only lots are not reported (flag reports still work)");
    }
    HookPrologue(kGiveList, {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54, 0x53},
                 &GiveListEntry, "item give log (0x17D89F0)");
    SeedHostSeq();
    ParseTestLots();
    ParseHostTest();
    // C2 hands every host item_lot_picked flag 0 -> 1 to OnHostFlagSet (main thread).
    progress::SetItemFlagObserver(&OnHostFlagSet);
    progress::SetBeforeApplyHook(&SeedLedgerFromOwnSave);
    Log("C2 item-flag observer registered");
    Log("%zu flagged lots, %zu ledger lots (flags %u..%u)", ItemLotFlagCount(), ItemLedgerCount(), kItemLedgerBase,
        kItemLedgerBase + kItemLedgerSize - 1);
    g_on = true;
}

void SeedLedgerFromOwnSave() {
    if (!g_on.load()) {
        return;
    }
    const u64 man = Ptr(kFlagMan);
    const int mode = LoadMode(man);
    if (!man || (mode != 0 && mode != 1)) {
        return;
    }
    // Mode 0: the live store is the own save. Mode 1 (summoned from the first load on, seamless
    // play): the own pool, never the host's overlay.
    auto is_set = [man, mode](std::uint32_t id) { return mode == 0 ? IsFlag(man, id) : OwnSaveFlag(id); };
    if (is_set(kItemLedgerSeeded)) {
        return;
    }
    // Once per save, before C2 ever wrote a host flag into it: every ledger lot whose awarding
    // event already ran here was earned by this player itself.
    const std::vector<std::uint32_t> bits = LedgerBitsToSeed(is_set);
    for (const std::uint32_t bit : bits) {
        if (mode == 0) {
            SetFlag(man, bit);
        } else {
            progress::WriteFlagOwnSave(bit, true);
        }
    }
    if (mode == 0) {
        SetFlag(man, kItemLedgerSeeded);
    } else {
        progress::WriteFlagOwnSave(kItemLedgerSeeded, true);
    }
    Log("ledger seeded from the own save (load mode %d): %zu lot%s this player already earned (marker flag %u)", mode,
        bits.size(), bits.size() == 1 ? "" : "s", kItemLedgerSeeded);
}

void OnHostFlagSet(std::uint32_t flag) {
    if (!g_on.load() || Role() != PartyRole::Host || flag > 0x7fffffffu) {
        return;
    }
    std::optional<ItemGrant> g;
    bool queued = false;
    {
        std::lock_guard<std::mutex> lk(g_host_mu);
        const auto& cap = g_host.Captured();
        if (InstancedTreasureFlag(static_cast<std::int32_t>(flag), progress::InstancedItems(),
                                  cap.count(static_cast<std::int32_t>(flag)) != 0)) {
            Log("host flag %u: map treasure, per player (guests pick up their own)", flag);
            return;
        }
        g = ClassifyFlag(static_cast<std::int32_t>(flag), cap);
    }
    if (g && g->items.empty()) {
        // A treasure with a blood gem: the gem the host picked up a moment ago (its give list).
        const std::vector<LotRowData> chain = LotChain(g->lot);
        if (LotChainHasGem(chain)) {
            const double now = Now();
            for (auto it = g_recent_gem_gives.rbegin(); it != g_recent_gem_gives.rend(); ++it) {
                if (now - it->at > 120.0) {
                    break;
                }
                const LotPlan plan = PlanSummonedLot(chain, it->items, nullptr);
                if (plan.result == LotPlanResult::Give && plan.why == "host's item list") {
                    g->items = it->items;
                    g_recent_gem_gives.erase(std::next(it).base());
                    Log("host flag %u: lot %d carries the blood gem the host picked up", flag, g->lot);
                    break;
                }
            }
        }
    }
    if (g) {
        AttachHostRoll(&*g); // main thread (C2's observer)
        std::lock_guard<std::mutex> lk(g_host_mu);
        queued = g_host.Offer(*g);
    }
    if (queued) {
        Log("host flag %u -> %s queued for the party", flag, DescribeItem(*g).c_str());
    }
}

bool PopHostItems(ItemGrant* out) {
    std::lock_guard<std::mutex> lk(g_host_mu);
    return g_host.Pop(out);
}

void RequestHostFullItems(int slot) {
    if (!g_on.load()) {
        return;
    }
    std::lock_guard<std::mutex> lk(g_host_mu);
    if (std::find(g_full_due.begin(), g_full_due.end(), slot) == g_full_due.end()) {
        g_full_due.push_back(slot);
    }
}

bool TakeHostFullItems(int* slot, std::vector<ItemGrant>* out) {
    if (!g_on.load()) {
        return false;
    }
    {
        std::lock_guard<std::mutex> lk(g_host_mu);
        if (g_full_due.empty()) {
            return false;
        }
    }
    // The host's own save must be live: world up, flag store in mode 0, own world.
    const GameSnapshot gs = ReadGameState(false);
    const u64 man = Ptr(kFlagMan);
    if (!gs.world_up || gs.loading || LoadMode(man) != 0 || OwnWorld() != 1) {
        return false;
    }
    std::vector<ItemGrant> list;
    std::map<std::int32_t, std::int32_t> captured;
    {
        std::lock_guard<std::mutex> lk(g_host_mu);
        *slot = g_full_due.front();
        g_full_due.pop_front();
        captured = g_host.Captured();
    }
    std::set<std::int32_t> seen;
    for (const LotFlag& e : kLotFlags) {
        if (!seen.insert(e.flag).second || !IsFlag(man, e.flag) ||
            InstancedTreasureFlag(e.flag, progress::InstancedItems(), captured.count(e.flag) != 0)) {
            continue;
        }
        if (std::optional<ItemGrant> g = ClassifyFlag(e.flag, captured)) {
            g->source = ItemSource::Full;
            list.push_back(*g);
        }
    }
    for (const LedgerRow& r : kLedger) {
        if (IsFlag(man, r.done_flag) && !ItemLotDenied(r.lot, kItemNone)) {
            ItemGrant g;
            g.lot = r.lot;
            g.ledger = r.idx;
            g.source = ItemSource::Full;
            list.push_back(g);
        }
    }
    for (ItemGrant& g : list) {
        AttachHostRoll(&g);
    }
    {
        std::lock_guard<std::mutex> lk(g_host_mu);
        for (ItemGrant& g : list) {
            g.seq = g_host.NextSeq();
        }
    }
    Log("full item list for slot %d: %zu lots", *slot, list.size());
    *out = std::move(list);
    return true;
}

void RequestGuestItems(const std::vector<ItemGrant>& items) {
    if (!g_on.load()) {
        return;
    }
    std::size_t taken, pending;
    {
        std::lock_guard<std::mutex> lk(g_guest_mu);
        taken = g_guest.Offer(items);
        pending = g_guest.Pending();
    }
    Log("guest got %zu grants from the host, %zu new; %zu pending", items.size(), taken, pending);
}

namespace {

/// No HP lost for kCalmAfter s (ChrIns +0x3B0 -> +0x20: +0xF8 HP): not in a fight, so an award
/// popup does not land on a player under attack. A new player (load) starts calm.
bool Calm(u64 player, double now) {
    constexpr double kCalmAfter = 15.0;
    static u64 last_player = 0;
    static std::int32_t last_hp = -1;
    static double last_hit = -1e9;
    u64 a = 0, b = 0;
    std::int32_t hp = -1;
    if (!player || !SafeGet(player + 0x3b0, &a) || !a || !SafeGet(a + 0x20, &b) || !b || !SafeGet(b + 0xf8, &hp)) {
        return true;
    }
    if (player == last_player && last_hp >= 0 && hp < last_hp) {
        last_hit = now;
    }
    last_player = player;
    last_hp = hp;
    return now - last_hit >= kCalmAfter;
}

std::atomic<u64> g_hud_obj{0}; // BB_PARTY_ITEMGET_PROBE: the HUD object 0x1BFB2A0 last ran with

BB_COOP_SYSV void HudTickEntry(u64 hud, u64, u64, u64, u64, u64) {
    g_hud_obj = hud;
}

// 0x1C02290 (functor, Scaleform list item, const u32* index): one GetItemList row from the HUD model.
std::atomic<u32> g_row_calls{0}, g_row_max_index{0};
std::atomic<u64> g_hud_update_calls{0};
BB_COOP_SYSV void ItemRowEntry(u64, u64, u64 index_ptr, u64, u64, u64) {
    u32 idx = 0;
    SafeGet(index_ptr, &idx);
    g_row_calls.fetch_add(1);
    if (idx > g_row_max_index.load()) {
        g_row_max_index = idx;
    }
}
BB_COOP_SYSV void HudUpdateEntry(u64, u64, u64, u64, u64, u64) {
    g_hud_update_calls.fetch_add(1);
}

// 0x1F5E200 (out, menu res, flags, const wchar16* name): loads menu:/<name>.gfx. Probe: who asks
// for an empty name.
using MovieLoadFn = u64(BB_COOP_SYSV*)(u64, u64, u64, u64);
MovieLoadFn g_movie_load_orig = nullptr;
BB_COOP_SYSV u64 MovieLoadReplace(u64 out, u64 res, u64 flags, u64 name) {
    const u64 ret = reinterpret_cast<u64>(__builtin_return_address(0));
    std::uint16_t first = 0;
    if (!name || !SafeGet(name, &first) || first == 0) {
        Log("item-get probe: menu movie with an EMPTY name (flags 0x%llx, name ptr 0x%llx) from guest +0x%llx",
            static_cast<unsigned long long>(flags), static_cast<unsigned long long>(name),
            static_cast<unsigned long long>(ret - Guest(0)));
    }
    return g_movie_load_orig(out, res, flags, name);
}

/// BB_PARTY_ITEMGET_PROBE=1: logs every change of the item-get dialog's state - entries in the
/// list at *0x553B1C0 (+8), the "dialog up" word *0x5562878 +0x130 that 0x16D86E0 sets while the
/// list is not empty, and the gate of its confirm check (player flag WorldChrMan+0x60 -> +0x58 ->
/// +0x38 -> +0x41 bit 7, *0x5540050).
void ItemGetProbe() {
    static const bool on = [] {
        const char* v = std::getenv("BB_PARTY_ITEMGET_PROBE");
        return v && *v && *v != '0';
    }();
    if (!on) {
        return;
    }
    static int last_n = -1, last_up = -1, last_gate = -1;
    static double since = 0;
    const u64 list = Ptr(kItemGetList);
    int n = 0;
    u64 node = 0;
    if (list && SafeGet(list + 8, &node)) {
        while (node && n < 16) {
            ++n;
            if (!SafeGet(node, &node)) {
                break;
            }
        }
    }
    u32 up = 0;
    const u64 menu = Ptr(kMenuState);
    if (menu) {
        SafeGet(menu + 0x130, &up);
    }
    u64 a = Ptr(0x553e878), b = 0, c = 0;
    u8 flag = 0;
    const bool chr = a && SafeGet(a + 0x60, &b) && b && SafeGet(b + 0x58, &c) && c && SafeGet(c + 0x38, &c) && c &&
                     SafeGet(c + 0x41, &flag);
    const int gate = (chr && (flag & 0x80)) ? 0 : (Ptr(0x5540050) ? 1 : 0);
    // The HUD model's item-get rows (0x1BFB2A0 copies the list into HUD +0xA88 -> +0x1238, count
    // +0x13A8, up to 5 a frame).
    static int last_rows = -2;
    static bool hooked = false;
    if (!hooked) {
        hooked = true;
        HookPrologue(0x1bfb2a0, {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54, 0x53},
                     &HudTickEntry, "HUD tick (item-get probe)");
        HookPrologue(0x1c02290, {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54, 0x53},
                     &ItemRowEntry, "GetItemList row (item-get probe)");
        HookPrologue(0x1bf7c20, {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54, 0x53},
                     &HudUpdateEntry, "ingameTop update (item-get probe)");
        void* orig = nullptr;
        if (ReplacePrologue(0x1f5e200, {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54, 0x53},
                            reinterpret_cast<const void*>(&MovieLoadReplace), &orig, "menu movie load (item-get probe)")) {
            g_movie_load_orig = reinterpret_cast<MovieLoadFn>(orig);
        }
    }
    // Once: the menu movie tables 0x1F5D0E0 loads from (name pointers; empty names fail to load).
    static bool tables_dumped = false;
    if (!tables_dumped && Ptr(kMenuState) && g_hud_obj.load()) {
        tables_dumped = true;
        struct T {
            u64 base;
            int n;
            int stride;
            int name_off;
        };
        const T tabs[] = {{0x5595e30, 0x4f, 16, 8}, {0x5595cc0, 0x16, 16, 8}, {0x5356ad0, 9, 8, 0}, {0x5356aa0, 6, 8, 0}};
        for (const T& t : tabs) {
            std::string line;
            for (int i = 0; i < t.n; ++i) {
                u64 first = 0, name = 0;
                SafeGet(Guest(t.base + u64(i) * t.stride), &first);
                SafeGet(Guest(t.base + u64(i) * t.stride + t.name_off), &name);
                char s[48] = {};
                if (name) {
                    SafeRead(name, s, sizeof s - 1);
                }
                char b[96];
                std::snprintf(b, sizeof b, " [%d 0x%llx '%s']", i, static_cast<unsigned long long>(first), s);
                line += b;
            }
            Log("item-get probe: movie table 0x%llx:%s", static_cast<unsigned long long>(t.base), line.c_str());
        }
        // The GetItemList row functor's vtable (0x1BF7C20: local functor &0x5344970 over HUD rows).
        std::string vt;
        for (int i = 0; i < 8; ++i) {
            u64 f = 0;
            SafeGet(Guest(0x5344970 + 8ull * i), &f);
            char b[32];
            std::snprintf(b, sizeof b, " +0x%llx", static_cast<unsigned long long>(f ? f - Guest(0) : 0));
            vt += b;
        }
        Log("item-get probe: GetItemList functor vtable 0x5344970:%s", vt.c_str());
    }
    int rows = -1;
    u64 model = 0, cnt = 0;
    if (const u64 hud = g_hud_obj.load(); hud && SafeGet(hud + 0xa88, &model) && model && SafeGet(model + 0x13a8, &cnt)) {
        rows = static_cast<int>(cnt);
    }
    // 0x1BFB2A0's open edge (rows 0 -> n): *0x5578A38 < 1, menu +0x84 == 0, GSM +0x1544 == 0
    // -> menu +0x25C = 1 (and a save request).
    std::int32_t blk = -1, m84 = -1, m25c = -1;
    u8 g1544 = 0xff;
    SafeGet(Guest(0x5578a38), &blk);
    if (menu) {
        SafeGet(menu + 0x84, &m84);
        SafeGet(menu + 0x25c, &m25c);
    }
    if (const u64 gsm = Ptr(0x5556678)) {
        SafeGet(gsm + 0x1544, &g1544);
    }
    static std::int32_t last_blk = -2, last_m84 = -2, last_m25c = -2;
    static int last_g1544 = -2;
    static double last_rowlog = 0;
    if (Now() - last_rowlog >= 5.0) {
        last_rowlog = Now();
        Log("item-get probe: ingameTop updates %llu, GetItemList row calls %u (max index %u)",
            static_cast<unsigned long long>(g_hud_update_calls.load()), g_row_calls.load(), g_row_max_index.load());
    }
    if (rows != last_rows || blk != last_blk || m84 != last_m84 || m25c != last_m25c || g1544 != last_g1544) {
        Log("item-get probe: HUD model rows %d (HUD 0x%llx); open gate *0x5578A38 %d, menu+0x84 %d, GSM+0x1544 %u, "
            "menu+0x25C %d",
            rows, static_cast<unsigned long long>(g_hud_obj.load()), blk, m84, g1544, m25c);
        last_rows = rows;
        last_blk = blk;
        last_m84 = m84;
        last_m25c = m25c;
        last_g1544 = g1544;
    }
    if (n != last_n || static_cast<int>(up) != last_up || gate != last_gate) {
        const double now = Now();
        Log("item-get probe: %d entr%s in the dialog list, dialog %s, confirm check %s (%.2f s since the last change)", n,
            n == 1 ? "y" : "ies", up ? "UP" : "down", gate ? "armed" : "held (player busy / no action-button man)",
            now - since);
        since = now;
        last_n = n;
        last_up = static_cast<int>(up);
        last_gate = gate;
    }
}

} // namespace

namespace {

/// Main thread: the guest's gift test and the host's gift awards.
void GiftTick(double now) {
    const PartyRole role = Role();
    const int own = OwnWorld();
    if (g_gift_test > 0 && !g_gift_test_done && role == PartyRole::Guest) {
        const GameSnapshot q = ReadGameState(false);
        if (own != 0 || !q.world_up || q.loading || LoadMode(Ptr(kFlagMan)) != 1) {
            g_gift_test_since = 0;
        } else if (!g_gift_test_since) {
            g_gift_test_since = now;
        } else if (now - g_gift_test_since >= 20.0 && Ptr(kMapItemMan)) {
            g_gift_test_done = true;
            Log("gift test: awarding lot %d through 0x17DDC50 (hostOnly 0) in the host's world", g_gift_test);
            reinterpret_cast<AwardFn>(Guest(kAwardLot))(Ptr(kMapItemMan), static_cast<u32>(g_gift_test), 0);
        }
    }
    if (role != PartyRole::Host || own != 1 || now - g_gift_last < 2.0) {
        return;
    }
    GiftDue d;
    {
        std::lock_guard<std::mutex> lk(g_gift_mu);
        if (g_gift_due.empty()) {
            return;
        }
        d = g_gift_due.front();
    }
    const GameSnapshot q = ReadGameState(false);
    const u64 mim = Ptr(kMapItemMan);
    if (!q.world_up || q.loading || !mim || LoadMode(Ptr(kFlagMan)) != 0) {
        return;  // keep it until the host's own world is steady
    }
    {
        std::lock_guard<std::mutex> lk(g_gift_mu);
        g_gift_due.pop_front();
    }
    g_gift_last = now;
    if (IsFlag(Ptr(kFlagMan), d.flag)) {
        Log("gift from slot %d: lot %d already in the host's world (flag %d set); nothing to give", d.slot, d.lot, d.flag);
        return;
    }
    Log("gift from slot %d: lot %d (flag %d) awarded in the host's world; C3 hands it to the party", d.slot, d.lot, d.flag);
    // The game's own award (hostOnly 1, as EMEVD 2003[4]): the award hook captures it and C3
    // broadcasts it; the guest that talked holds the flag already (its mark) and skips it.
    reinterpret_cast<AwardFn>(Guest(kAwardLot))(mim, static_cast<u32>(d.lot), 1);
    Log("gift from slot %d: flag %d is now %d", d.slot, d.flag, IsFlag(Ptr(kFlagMan), d.flag) ? 1 : 0);
}

} // namespace

bool PopGuestGift(std::string* body) {
    std::lock_guard<std::mutex> lk(g_gift_mu);
    if (g_gift_up.empty()) {
        return false;
    }
    *body = std::move(g_gift_up.front());
    g_gift_up.pop_front();
    return true;
}

bool OnHostGiftUp(int slot, const std::string& body, std::string* why) {
    std::int32_t lot = 0, flag = 0;
    if (!GiftUpFromJsonText(body, &lot, &flag, why)) {
        return false;
    }
    std::lock_guard<std::mutex> lk(g_gift_mu);
    if (!g_gift_rate.Take(slot, Now())) {
        if (why) {
            *why = "gift_up: rate limit";
        }
        return false;
    }
    if (g_gift_due.size() >= 32) {
        if (why) {
            *why = "gift_up: queue full";
        }
        return false;
    }
    g_gift_due.push_back({slot, lot, flag});
    Log("gift from slot %d: lot %d (flag %d) queued for the host's world", slot, lot, flag);
    return true;
}

void ItemsTick() {
    if (!g_on.load()) {
        return;
    }
    ItemGetProbe();
    if (!g_test_offered && !g_test.empty()) {
        g_test_offered = true;
        std::lock_guard<std::mutex> lk(g_guest_mu);
        g_guest.Offer(g_test);
    }
    HostTestTick(Now());
    GiftTick(Now());
    const GameSnapshot gs = ReadGameState(false);
    ItemApplyState s;
    s.world_up = gs.world_up && gs.map_id != 0xffffffffu; // the player stands in a map
    s.loading = gs.loading;
    s.session_role = gs.session_role;
    s.load_mode = LoadMode(Ptr(kFlagMan));
    s.own_world = OwnWorld();
    s.game_data = gs.player_rec != 0 && Ptr(kMapItemMan) != 0;
    s.calm = Calm(gs.player, Now());
    static ItemApplyMode gate_logged = ItemApplyMode::None;
    const ItemApplyMode mode_now = ItemApplyModeNow(s);
    if (mode_now != gate_logged) {
        gate_logged = mode_now;
        Log("apply gate %s (%s, load mode %d, own world %d)",
            mode_now == ItemApplyMode::Home       ? "open: own world"
            : mode_now == ItemApplyMode::Summoned ? "open: summoned (direct give, own pool)"
                                                  : "closed",
            Describe(gs).c_str(), s.load_mode, s.own_world);
    }
    std::optional<ItemGrant> g;
    ItemApplyMode mode;
    {
        std::lock_guard<std::mutex> lk(g_guest_mu);
        g = g_guest.Step(s, Now());
        mode = g_guest.LastMode();
    }
    if (!g) {
        return;
    }
    if (mode == ItemApplyMode::Summoned) {
        const SummonedResult r = ApplySummoned(*g);
        std::lock_guard<std::mutex> lk(g_guest_mu);
        if (r == SummonedResult::Defer) {
            g_guest.Defer(*g);
            return;
        }
        g_guest.Done(g->Key());
        if (r == SummonedResult::Given) {
            g_guest.Awarded(Now());
        }
        return;
    }
    const bool awarded = Apply(*g);
    std::lock_guard<std::mutex> lk(g_guest_mu);
    g_guest.Done(g->Key());
    if (awarded) {
        g_guest.Awarded(Now());
    }
}

#endif // BB_PARTY_ITEMS_NO_GAME

} // namespace coop
