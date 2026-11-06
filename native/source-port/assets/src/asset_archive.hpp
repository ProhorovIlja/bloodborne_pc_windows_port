// SPDX-License-Identifier: GPL-2.0-or-later
// V186: Source-port asset reader. Never executes the original PS4 ELF.
#pragma once
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <span>
#include <string>
#include <vector>

namespace bb::native {
struct BinderEntry {
    std::u16string name;
    std::int32_t id = -1;
    std::uint8_t flags = 0;
    std::uint32_t data_offset = 0;
    std::uint64_t stored_size = 0;
    std::uint64_t decoded_size = 0;
};

class AssetArchive {
public:
    static constexpr std::size_t max_file_bytes = 256u * 1024u * 1024u;
    static constexpr std::size_t max_decoded_bytes = 512u * 1024u * 1024u;
    static AssetArchive from_bytes(std::span<const std::uint8_t> file);
    static AssetArchive from_file(const std::filesystem::path& path);
    [[nodiscard]] const std::vector<BinderEntry>& entries() const noexcept {return entries_;}
    [[nodiscard]] std::size_t decoded_archive_size() const noexcept {return data_.size();}
    [[nodiscard]] std::vector<std::uint8_t> payload(std::size_t index) const;
private:
    std::vector<std::uint8_t> data_;
    std::vector<BinderEntry> entries_;
};
} // namespace bb::native
