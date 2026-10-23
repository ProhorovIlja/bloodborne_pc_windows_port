// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <unordered_map>
#include <vector>
namespace SeamlessHunt::MapCache {
// UI and GPU consumers keep shared_ptrs to data in their own active area.
// This cache owns only idle CPU-side area/chart copies.
class Budget {
public:
    static constexpr std::size_t DefaultLimit = 384ull * 1024 * 1024;
    explicit Budget(std::size_t limit = DefaultLimit) : limit_(limit) {}
    bool Touch(std::uint32_t key) {
        if (!weights_.contains(key)) return false;
        auto found = std::find(recent_.begin(), recent_.end(), key);
        if (found != recent_.end()) recent_.erase(found);
        recent_.push_back(key);
        return true;
    }
    std::vector<std::uint32_t> Record(std::uint32_t key, std::size_t bytes) {
        if (const auto found = weights_.find(key); found != weights_.end()) {
            used_ -= found->second;
            weights_.erase(found);
        }
        weights_[key] = bytes;
        used_ += bytes;
        Touch(key);
        std::vector<std::uint32_t> evicted;
        while (used_ > limit_ && recent_.size() > 1) {
            const auto oldest = recent_.front();
            recent_.pop_front();
            if (const auto it = weights_.find(oldest); it != weights_.end()) {
                used_ -= it->second;
                weights_.erase(it);
                evicted.push_back(oldest);
            }
        }
        return evicted;
    }
    std::size_t Used() const {return used_;}
    std::size_t Size() const {return weights_.size();}
private:
    const std::size_t limit_;
    std::size_t used_ = 0;
    std::deque<std::uint32_t> recent_;
    std::unordered_map<std::uint32_t, std::size_t> weights_;
};
}
