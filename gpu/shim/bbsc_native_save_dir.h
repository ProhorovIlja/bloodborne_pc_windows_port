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
    return !error && fs::is_directory(state) && !fs::is_symlink(state);
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

    // Never follow a symlinked user root, 1/ user, title or SPRJ0005 to a
    // different save tree. The active game save folder is expected to have
    // been created/adopted by runtime_savedata_configure first.
    if (!OrdinaryDirectory(root) || !OrdinaryDirectory(savedata) ||
        !OrdinaryDirectory(active_user) || !OrdinaryDirectory(title) ||
        !OrdinaryDirectory(game))
        return {};
    return game;
}
} // namespace SeamlessBbsc
#endif
