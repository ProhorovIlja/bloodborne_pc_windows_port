// SPDX-License-Identifier: GPL-2.0-or-later
// Native save selection regression: no Bloodborne files, no network or writes by
// the resolver under test. Only this test creates/destroys dummy directories.
#include "../gpu/shim/bbsc_native_save_dir.h"

#include <cassert>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <string>
#include <system_error>

namespace fs = std::filesystem;

int main() {
    using SeamlessBbsc::ActiveSaveFolder;
    using SeamlessBbsc::ValidRetailSerial;
    assert(ValidRetailSerial("CUSA03173"));
    assert(ValidRetailSerial("CUSA00207"));
    assert(ValidRetailSerial("CUSA00900"));
    assert(ValidRetailSerial("CUSA03023"));
    for (const auto bad : {"", "UNKNOWN", "CUSA0317", "CUSA031730",
                           "ABCD03173", "CUSA0317X", "cusa03173", "../CUSA03"}) {
        assert(!ValidRetailSerial(bad));
    }
    std::error_code err;
    const auto key = std::chrono::steady_clock::now().time_since_epoch().count();
    const fs::path base = fs::temp_directory_path() /
                          ("seamless-hunt-save-test-" + std::to_string(key));
    const fs::path native = base / "native user";
    const auto us = native / "savedata" / "1";
    const auto eu = us / "CUSA03173" / "SPRJ0005";
    const auto us_region = us / "CUSA00207" / "SPRJ0005";
    const auto other_user = native / "savedata" / "1004" / "CUSA03173" / "SPRJ0005";
    const auto party = native / "savedata_party" / "1" / "CUSA00900" / "SPRJ0005";
    fs::create_directories(eu);
    fs::create_directories(us_region);
    fs::create_directories(other_user);
    fs::create_directories(party);
    {
        std::ofstream(eu / "userdata0000") << "HUNTER-A";
        std::ofstream(us_region / "userdata0000") << "HUNTER-B";
        std::ofstream(other_user / "userdata0000") << "WRONG-USER";
        std::ofstream(party / "userdata0000") << "SEPARATE-PARTY";
    }

    assert(ActiveSaveFolder(native, "CUSA03173") == eu);
    assert(ActiveSaveFolder(native, "CUSA00207") == us_region);
    assert(ActiveSaveFolder(native, "CUSA00900").empty()); // no accidental party save
    assert(ActiveSaveFolder(native, "CUSA03023").empty()); // no fallback to another region
    assert(ActiveSaveFolder(native, "CUSA0317X").empty());
    assert(ActiveSaveFolder(native / "missing", "CUSA03173").empty());
    assert(fs::exists(eu / "userdata0000"));
    assert(fs::exists(us_region / "userdata0000"));
    assert(fs::exists(party / "userdata0000"));

    // Refuse a symlinked title pointing to another user's save (if OS allows).
    auto linked = us / "CUSA03023";
    fs::create_directory_symlink(other_user.parent_path(), linked, err);
    if (!err) assert(ActiveSaveFolder(native, "CUSA03023").empty());
    err.clear();

    // Do not delete other people's folders on a cleanup failure: only remove
    // the unique test directory this test created.
    fs::remove_all(base, err);
    assert(!err);
    std::puts("Native BBSC actual-region/save-user isolation PASS");
}
