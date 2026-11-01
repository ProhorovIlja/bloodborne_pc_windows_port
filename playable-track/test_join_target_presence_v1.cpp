#include <cassert>
#include <cstdint>
#include <ranges>
#include <string>
#include <vector>
#include <algorithm>
enum class Vital { Down, Up };
struct MemberVitals {
    std::string member;
    uint32_t map;
    Vital vital;
};
// This predicate matches the exact target_here condition in the pinned
// experimental upstream patch, but uses deliberately fabricated hunters.
bool target_here(const std::vector<MemberVitals>& board,
                 const std::string& self,
                 const std::string& target, uint32_t here_map) {
    return !target.empty() && !self.empty() && target != self &&
           here_map != 0 &&
           std::ranges::any_of(board, [&](const MemberVitals& member) {
               return member.member == target && member.map == here_map &&
                      member.vital == Vital::Up;
           });
}
// Matches the source-only candidate's conservative identity ambiguity guard.
bool unique_member_ids(std::vector<std::string> ids) {
    std::ranges::sort(ids);
    return std::adjacent_find(ids.begin(), ids.end()) == ids.end();
}
int main() {
    assert(unique_member_ids({"a","b","c","d","e"}));
    assert(!unique_member_ids({"a","b","c","c","e"}));
    assert(!unique_member_ids({"same","same"}));
    const std::vector<MemberVitals> players{
        {"A", 1, Vital::Up}, {"B", 1, Vital::Up},
        {"C", 2, Vital::Up}, {"D", 1, Vital::Down}};
    assert(target_here(players, "A", "B", 1));
    assert(!target_here(players, "A", "C", 1));
    assert(!target_here(players, "A", "D", 1));
    assert(!target_here(players, "A", "A", 1));
    assert(!target_here(players, "A", "missing", 1));
    assert(!target_here(players, "A", "B", 0));
    assert(!target_here(players, "A", "B", 2));
    assert(!target_here(players, "A", "", 1));
    return 0;
}
