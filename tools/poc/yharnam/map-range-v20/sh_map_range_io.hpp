// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <limits>
#include <vector>
namespace SeamlessHunt::MapIO {
constexpr std::uint64_t MaxRangeBytes = 512ull * 1024 * 1024;
inline std::vector<std::uint8_t> ReadExact(const std::filesystem::path& path,
                                           std::uint64_t offset, std::uint64_t bytes) {
    if (bytes == 0 || bytes > MaxRangeBytes ||
        offset > static_cast<std::uint64_t>(std::numeric_limits<std::streamoff>::max()) ||
        bytes > static_cast<std::uint64_t>(std::numeric_limits<std::streamsize>::max())) {
        return {};
    }
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) return {};
    const auto end = file.tellg();
    if (end < 0) return {};
    const std::uint64_t file_size = static_cast<std::uint64_t>(static_cast<std::streamoff>(end));
    if (offset > file_size || bytes > file_size - offset) return {};
    file.seekg(static_cast<std::streamoff>(offset), std::ios::beg);
    if (!file) return {};
    std::vector<std::uint8_t> data(static_cast<std::size_t>(bytes));
    file.read(reinterpret_cast<char*>(data.data()), static_cast<std::streamsize>(bytes));
    if (file.gcount() != static_cast<std::streamsize>(bytes)) return {};
    return data;
}
} // namespace SeamlessHunt::MapIO
