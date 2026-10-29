// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstdint>
#include <string_view>

// V72: non-cryptographic IN-MEMORY world-version fingerprint.
// Purpose: invalidate an internal server P2P candidate snapshot if the
// authoritative game world/map/enemy owner changes. NEVER use as an auth
// signature, client-supplied grant, or replacement for secure control-plane
// MAC/AEAD. The issuer must recheck session/consent on each grant renewal.
namespace SeamlessHunt::Hybrid {
struct WorldRevisionInput {
    std::uint64_t world_epoch=0;
    std::uint64_t map_reset_version=0;
    std::uint64_t session_run=0;
    std::uint32_t from_map=0;
    std::uint32_t to_map=0;
    std::string_view current_enemy_owner{};
    bool from_on_team=false;
    bool to_on_team=false;
    bool from_cut_from_team=false;
    bool to_cut_from_team=false;
};

constexpr std::uint64_t RevisionStep(std::uint64_t state,
                                      std::uint8_t byte) noexcept {
    return (state ^ byte) * UINT64_C(1099511628211);
}
constexpr std::uint64_t RevisionNumber(std::uint64_t state,
                                        std::uint64_t number) noexcept {
    for (unsigned i=0;i<8;++i) {
        state=RevisionStep(state,static_cast<std::uint8_t>(number & 0xff));
        number >>= 8;
    }
    return state;
}
inline std::uint64_t BoundWorldRevision(const WorldRevisionInput& in) noexcept {
    if (!in.world_epoch || !in.from_map || !in.to_map ||
        in.from_map!=in.to_map || !in.from_on_team || !in.to_on_team ||
        in.from_cut_from_team || in.to_cut_from_team ||
        in.current_enemy_owner.size()>255)
        return 0;
    // Stable across processes, but deliberately NOT a secret or a signature.
    std::uint64_t h=UINT64_C(14695981039346656037);
    h=RevisionNumber(h,UINT64_C(0x534859543732)); // SHYT72 domain
    h=RevisionNumber(h,in.world_epoch);
    h=RevisionNumber(h,in.map_reset_version);
    h=RevisionNumber(h,in.session_run);
    h=RevisionNumber(h,in.from_map);
    h=RevisionNumber(h,in.to_map);
    h=RevisionNumber(h,in.current_enemy_owner.size());
    for (const unsigned char c:in.current_enemy_owner) h=RevisionStep(h,c);
    return h ? h : 1; // zero remains reserved for deny/no world
}
} // namespace SeamlessHunt::Hybrid
