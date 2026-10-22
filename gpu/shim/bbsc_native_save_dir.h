// SPDX-License-Identifier: GPL-2.0-or-later
// Native Windows BBSC save lookup. The native game's active SaveData user is 1:
//   <BB_GPU_USER_DIR>/savedata/1/<actual retail title ID>/SPRJ0005
//
// The BBSC patch-site compatibility ID is independently CUSA03173 (byte-checked
// by its upstream hooks). NEVER reuse that canonical patch ID for save lookup.
// This module chooses ONLY the native game's own save, not arbitrary shadPS4/
// Awaken profiles or a file with the newest timestamp in another user folder.
//
// Pure read-only filesystem operations. No moves, writes, copy, mkdir or
// directory traversal, and refuse symbolic links/junctions for candidates.
// This header can be tested without game files, Vulkan or BBSC runtime.
#ifndef BBSC_NATIVE_SAVE_DIR_H
#define BBSC_NATIVE_SAVE_DIR_H

#include <filesystem>
#include <string_view>
#include <system_error>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#endif

namespace SeamlessBbsc {
namespace fs = std::filesystem;

inline bool ValidRetailSerial(std::string_view id) {
    if (id.size() != 9 || id.substr(0, 4) != "CUSA") return false;
    for (unsigned i = 4; i < 9; ++i)
        if (id[i] < '0' || id[i] > '9') return false;
    return true;
}

inline bool OrdinaryDirectory(const fs::path& path) {
    std::error_code error;
    const auto state = fs::symlink_status(path, error);
    if (error || !fs::is_directory(state) || fs::is_symlink(state)) return false;
#ifdef _WIN32
    // Filesystem directory junctions can be reparse points even when
    // symlink_status does not classify them as ordinary symlinks.
    const DWORD attributes = GetFileAttributesW(path.c_str());
    if (attributes == INVALID_FILE_ATTRIBUTES ||
        (attributes & FILE_ATTRIBUTE_REPARSE_POINT)) return false;
#endif
    return true;
}

inline bool OrdinaryDirectoryOrMissing(const fs::path& path) {
    std::error_code error;
    const auto state = fs::symlink_status(path, error);
    if (error == std::errc::no_such_file_or_directory) return true;
    if (error) return false;
    if (state.type() == fs::file_type::not_found) return true;
    return OrdinaryDirectory(path);
}

inline fs::path ActiveSaveFolder(const fs::path& native_user_root,
                                 std::string_view retail_serial) {
    if (!ValidRetailSerial(retail_serial) || native_user_root.empty())
        return {};
    const fs::path root = native_user_root;
    const fs::path savedata = root / "savedata";
    const fs::path active_user = savedata / "1";
    const fs::path title = active_user / std::string(retail_serial);
    const fs::path game = title / "SPRJ0005";

    // The runtime can start a NEW character before any of these directories
    // exist. Return only the native runtime's exact deterministic destination;
    // never scan other users/regions or import from an arbitrary save tree.
    // Existing components must be directories, not files, links or junctions.
    // Missing components are fine: the GAME's SaveData implementation owns
    // directory creation later. Do not mkdir or write from this resolver.
    if (!OrdinaryDirectory(root) ||
        !OrdinaryDirectoryOrMissing(savedata) ||
        !OrdinaryDirectoryOrMissing(active_user) ||
        !OrdinaryDirectoryOrMissing(title) ||
        !OrdinaryDirectoryOrMissing(game))
        return {};
    return game;
}
// An optional, explicit BBSC_SAVE_DIR must resolve to the same folder as
// the native game's own SaveData root. Accept an identical as-yet-uncreated
// path on a brand-new character, but NEVER an override into another port.
inline bool MatchesActiveSaveFolder(const fs::path& active,
                                    const fs::path& configured) {
    if (active.empty() || configured.empty()) return false;
    std::error_code error;
    if (fs::equivalent(active, configured, error)) return true;
    if (error && error != std::errc::no_such_file_or_directory)
        return false;
    std::error_code active_error, configured_error;
    const auto left = fs::absolute(active, active_error).lexically_normal();
    const auto right = fs::absolute(configured, configured_error).lexically_normal();
    return !active_error && !configured_error && !left.empty() && left == right;
}
} // namespace SeamlessBbsc
#endif
