// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// Bounded multipart stream assembler. Reject oversized messages *and their
// remaining fragments* so an attacker cannot use endless non-final chunks to
// grow server RAM or splice a truncated malicious prefix into a new message.
#include <cstddef>
#include <cstdint>
#include <span>
#include <utility>
#include <vector>

namespace SeamlessHunt::StreamBounds {
class Assembler {
public:
    // High enough for co-op snapshots and map state; bounded per peer.
    static constexpr std::size_t MaxMessageBytes = 8ull * 1024 * 1024;
    // Max input frame is guarded separately by the existing UDP/TCP framing.
    bool Push(std::span<const std::uint8_t> fragment, bool last,
              std::vector<std::uint8_t>& completed) {
        completed.clear();
        if (dropping_) {
            if (last) dropping_ = false;
            return false;
        }
        if (fragment.size() > MaxMessageBytes - partial_.size()) {
            partial_.clear();
            dropping_ = !last;
            return false;
        }
        partial_.insert(partial_.end(),fragment.begin(),fragment.end());
        if (!last) return false;
        completed = std::move(partial_);
        partial_.clear();
        return true;
    }
    void Reset() {
        partial_.clear();
        dropping_ = false;
    }
    std::size_t Buffered() const { return partial_.size(); }
    bool Discarding() const { return dropping_; }
private:
    std::vector<std::uint8_t> partial_;
    bool dropping_ = false;
};
} // namespace SeamlessHunt::StreamBounds
