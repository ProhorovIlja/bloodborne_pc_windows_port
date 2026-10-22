"""Prepare hash-verified deadinside bbnet20 sources for a separate Win64 DLL build.

This never builds a DLL, touches game files or modifies the production server.
Pinned sources are validated before applying allowlisted Win64 ABI, save, and network adaptations.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

try:
    from .bbsc_win32_memscan import SOURCE as MEMSCAN, adapt_win32_memscan
except ImportError:  # direct script invocation from tools/interop/
    from bbsc_win32_memscan import SOURCE as MEMSCAN, adapt_win32_memscan

REVISION = "8185b88d80573fa300595d5c54450183b4109935"
FORMAT = "seamless-hunt-bbnet20-source-v1"
ROOTS = ("gpu/bbnet20/", "gpu/bbnet/bbnet.h", "gpu/third_party/httplib/")
GLUE = "gpu/bbnet20/bbnet_glue.cpp"
BBSC_GLUE = "gpu/bbnet20/bbsc/bbsc_glue.cpp"
RELAY = "gpu/bbnet20/vendor/shadps4/core/net/p2p_relay.cpp"
CMAKE = "gpu/bbnet20/CMakeLists.txt"
EXPORT = '#define BBNET_EXPORT extern "C" __attribute__((visibility("default")))'
LINK_OPTS = "target_link_options(bbnet20 PRIVATE -Wl,-Bsymbolic -Wl,--exclude-libs,ALL)"


def prepare(staged: Path, workspace: Path) -> dict:
    staged, workspace = staged.resolve(strict=True), workspace.resolve(strict=True)
    if not (workspace / "gpu/CMakeLists.txt").is_file():
        raise ValueError("workspace must be the native Windows port repository")
    inventory = staged / "PORT-SOURCE-MANIFEST.json"
    if not inventory.is_file() or inventory.is_symlink():
        raise ValueError("missing pinned source inventory")
    manifest = json.loads(inventory.read_text(encoding="utf-8"))
    if manifest.get("format") != FORMAT or manifest.get("revision") != REVISION:
        raise ValueError("unsupported or unreviewed upstream revision")
    if not isinstance(manifest.get("files"), list):
        raise ValueError("invalid source inventory")
    sources: dict[str, bytes] = {}
    for entry in manifest["files"]:
        if not isinstance(entry, dict):
            raise ValueError("bad inventory record")
        name = entry.get("path")
        if not isinstance(name, str):
            raise ValueError("bad source path")
        if not name.startswith(ROOTS):
            continue
        if ".." in name.split("/") or "\\" in name or name.startswith("/"):
            raise ValueError("unsafe upstream source path")
        source = staged.joinpath(*name.split("/"))
        if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(staged):
            raise ValueError(f"invalid upstream file: {name}")
        data = source.read_bytes()
        if (len(data) != entry.get("size") or
                hashlib.sha256(data).hexdigest() != entry.get("sha256")):
            raise ValueError(f"source SHA256 mismatch: {name}")
        if name in sources:
            raise ValueError("duplicate inventory entry")
        sources[name] = data
    expected = (GLUE, BBSC_GLUE, RELAY, CMAKE, MEMSCAN, "gpu/bbnet/bbnet.h",
                "gpu/third_party/httplib/httplib.h", "gpu/third_party/httplib/LICENSE")
    if any(x not in sources for x in expected):
        raise ValueError("pinned source or third-party MIT license missing")
    # Git for Windows can check out upstream C++/CMake files as CRLF even
    # though GitHub shows LF. Verify the ORIGINAL bytes against the pinned
    # manifest first, then normalize only the five files we will transform.
    # Never alter unmodified vendor files: their upstream hashes stay auditable.
    for name in (GLUE, BBSC_GLUE, RELAY, CMAKE, MEMSCAN):
        sources[name] = sources[name].replace(b"\r\n", b"\n")
    if EXPORT.encode() not in sources[GLUE] or LINK_OPTS.encode() not in sources[CMAKE]:
        raise ValueError("upstream changed: explicitly review Windows adaptations")
    sources[GLUE] = sources[GLUE].replace(
        EXPORT.encode(),
        b'#ifdef _WIN32\n#define BBNET_EXPORT extern "C" __declspec(dllexport)\n'
        b'#else\n' + EXPORT.encode() + b'\n#endif')
    # The Linux host glue uses POSIX mprotect and /proc/self/maps to keep
    # Bloodborne's known executable image writable for runtime BBSC hooks.
    # Win64 must inspect actual mapped executable regions before changing
    # protection; never broaden access to unrelated host pages.
    glue = sources[GLUE]
    if b"#include <sys/mman.h>" in glue:
        before = b"#include <sys/mman.h>"
        glue = glue.replace(before,
            b"#ifdef _WIN32\n#include <windows.h>\n#else\n" +
            before + b"\n#endif", 1)
        # The upstream Linux BBSC port guesses CUSA00207, regardless of the
        # current Bloodborne region or actual native save user. That can back
        # up or attribute another character's state to this session.
        # Replace ONLY the Windows branch; keep Linux's original byte-for-byte.
        save_start = b'    // BBSC finds the save it backs up and journals in shadPS4\'s folders; the port\'s are\n'
        save_end = b'    // BBSC writes its byte patches straight into the game\'s code'
        if glue.count(save_start) != 1 or glue.count(save_end) != 1:
            raise ValueError("upstream BBSC save discovery changed")
        start = glue.index(save_start)
        end = glue.index(save_end, start)
        original_discovery = glue[start:end]
        if (original_discovery.count(b'"CUSA00207"') != 1
                or original_discovery.count(b'setenv("BBSC_SAVE_DIR"') != 1):
            raise ValueError("unreviewed upstream save lookup")
        win_discovery = (
            b'#ifdef _WIN32\n'
            b'    // The BBSC patch code internally checks the canonical CUSA03173\n'
            b'    // site set. Its save path must instead use the ACTUAL game SFO ID.\n'
            b'    const char* user_root = std::getenv("BB_GPU_USER_DIR");\n'
            b'    const auto active_save = SeamlessBbsc::ActiveSaveFolder(\n'
            b'        std::filesystem::path(user_root && *user_root ? user_root : "user"),\n'
            b'        g_host.serial ? g_host.serial : "");\n'
            b'    if (active_save.empty()) {\n'
            b'        std::puts("BBSC: native active save for retail title not found; "\n'
            b'                  "seamless patches disabled to protect other-port saves");\n'
            b'        return;\n'
            b'    }\n'
            b'    if (const char* specified = std::getenv("BBSC_SAVE_DIR");\n'
            b'        specified && *specified) {\n'
            b'        if (!SeamlessBbsc::MatchesActiveSaveFolder(active_save,\n'
            b'                std::filesystem::path(specified))) {\n'
            b'            std::puts("BBSC: explicit save override is NOT the native active "\n'
            b'                      "save; seamless patches disabled");\n'
            b'            return;\n'
            b'        }\n'
            b'    } else {\n'
            b'        const auto utf8 = active_save.u8string();\n'
            b'        if (_putenv_s("BBSC_SAVE_DIR",\n'
            b'              reinterpret_cast<const char*>(utf8.c_str())) != 0) {\n'
            b'            std::puts("BBSC: cannot bind native save folder; patches disabled");\n'
            b'            return;\n'
            b'        }\n'
            b'    }\n'
            b'    std::printf("BBSC: native active save bound to retail title %s; "\n'
            b'                "canonical hook map CUSA03173 (byte-verified)\\n",\n'
            b'                g_host.serial ? g_host.serial : "?");\n'
            b'#else\n' + original_discovery + b'#endif\n'
        )
        glue = glue[:start] + win_discovery + glue[end:]
        windows_inc = b'#ifdef _WIN32\n#include <windows.h>\n'
        if glue.count(windows_inc) != 1:
            raise ValueError("native Win64 include point moved")
        glue = glue.replace(windows_inc,
            windows_inc + b'#include "../shim/bbsc_native_save_dir.h"\n', 1)
        version_line = b'        psf->app_ver = host->app_ver ? host->app_ver : "";'
        if glue.count(version_line) != 1:
            raise ValueError("upstream app_version assignment changed")
        glue = glue.replace(version_line,
            b'        // Retail SFO often writes 01.09; the native runtime may expose 1.09.\n'
            b'        // The upstream BBSC hook checks exact 01.09; normalize ONLY here.\n'
            b'        const std::string_view game_ver = host->app_ver ? host->app_ver : "";\n'
            b'        psf->app_ver = game_ver == "1.09" ? "01.09" : std::string(game_ver);', 1)
        linux_start = b'    unsigned writable = 0;\n    if (FILE* maps = std::fopen("/proc/self/maps", "r")) {'
        linux_end = b'    std::printf("BBSC: seamless co-op hooks for the image'
        if linux_start not in glue or linux_end not in glue:
            raise ValueError("upstream BBSC writable image mapping code changed")
        start = glue.index(linux_start)
        end = glue.index(linux_end, start)
        linux_block = glue[start:end]
        windows_block = (
            b"#ifdef _WIN32\n    unsigned writable = 0;\n"
            b"    // Restrict this developer-only bridge to the mapped guest image.\n"
            b"    const uintptr_t lo = static_cast<uintptr_t>(base);\n"
            b"    const uintptr_t hi = lo + static_cast<uintptr_t>(size);\n"
            b"    if (hi >= lo) {\n"
            b"        for (uintptr_t cursor = lo; cursor < hi;) {\n"
            b"            MEMORY_BASIC_INFORMATION info{};\n"
            b"            if (!VirtualQuery(reinterpret_cast<const void*>(cursor), &info, sizeof(info))) break;\n"
            b"            const auto region = reinterpret_cast<uintptr_t>(info.BaseAddress);\n"
            b"            const uintptr_t region_end = region + info.RegionSize;\n"
            b"            if (region_end <= cursor) break;\n"
            b"            const uintptr_t from = std::max(cursor, region);\n"
            b"            const uintptr_t to = std::min(hi, region_end);\n"
            b"            const DWORD p = info.Protect & 0xff;\n"
            b"            if (info.State == MEM_COMMIT && !(info.Protect & PAGE_GUARD) &&\n"
            b"                (p == PAGE_EXECUTE || p == PAGE_EXECUTE_READ ||\n"
            b"                 p == PAGE_EXECUTE_READWRITE || p == PAGE_EXECUTE_WRITECOPY)) {\n"
            b"                DWORD previous = 0;\n"
            b"                if (VirtualProtect(reinterpret_cast<void*>(from), to - from,\n"
            b"                                   PAGE_EXECUTE_READWRITE, &previous)) ++writable;\n"
            b"            }\n"
            b"            cursor = region_end;\n"
            b"        }\n"
            b"    }\n#else\n"
        )
        glue = glue[:start] + windows_block + linux_block + b"#endif\n" + glue[end:]
        probe_start = b'    if (const char* probe = std::getenv("BB_BBSC_PROBE")) {'
        probe_end = b'    // The cinematic camera '
        if probe_start not in glue or probe_end not in glue:
            raise ValueError("upstream Linux-only BBSC memory probe changed")
        start = glue.index(probe_start)
        end = glue.index(probe_end, start)
        glue = glue[:start] + b"#ifndef _WIN32\n" + glue[start:end] + b"#endif\n" + glue[end:]
        sources[GLUE] = glue
    # Critical Windows static-vs-shared distinction: the Linux bbnet20 module
    # shares a libbbgpu with its host. The Windows engine instead links bbgpu
    # STATIC into bbport.exe. Directly linking the plugin to another copy of
    # bbgpu would make the cinematic camera register into the WRONG SDL
    # window, and its loading status would be invisible in the real renderer.
    # Rewire exactly two genuine upstream call sites to host-EXE forwarders.
    # These forwarders use explicit GetProcAddress on the primary process,
    # with no changes to the gameplay packets, memory or the P2P protocol.
    video_include = b'#include "bbgpu.h"'
    video_func = b"bbgpu_add_event_filter("
    dialog_func = b"bbgpu_overlay_banner("
    if (glue.count(video_include) != 1 or glue.count(video_func) != 1 or
        sources[BBSC_GLUE].count(video_include) != 1 or
        sources[BBSC_GLUE].count(dialog_func) != 2):
        raise ValueError("Upstream BBSC-to-GPU integration changed; review required")
    glue = glue.replace(video_include,
        video_include + b'\nextern "C" void bbnet20_host_add_event_filter(BbGpuEventFilter);', 1)
    sources[GLUE] = glue.replace(video_func, b"bbnet20_host_add_event_filter(", 1)
    dialog = sources[BBSC_GLUE].replace(video_include,
        video_include + b'\nextern "C" void bbnet20_host_overlay_banner(const char*);', 1)
    sources[BBSC_GLUE] = dialog.replace(dialog_func, b"bbnet20_host_overlay_banner(")
    # The real CLS memory scanner uses MSVC __try SEH, which cannot compile
    # with Win64 clang++ (GNU ABI). Keep upstream FindInMemory and use the
    # Win32 kernel safe-copy API like Linux's process_vm_readv snapshot.
    sources[MEMSCAN] = adapt_win32_memscan(sources[MEMSCAN])
    # The shadPS4 P2P relay reuses POSIX address-conversion headers on Linux.
    # WinSock2 already provides identical byte-order and IPv4 layout APIs
    # (inet_pton, htons, ntohs, sockaddr_in). Never touch its packet framing
    # or relay protocol; only replace these two compile-time includes.
    posix_includes = b"#include <arpa/inet.h>\n#include <netinet/in.h>"
    if sources[RELAY].count(posix_includes) != 1:
        raise ValueError("Upstream P2P relay platform includes changed; review required")
    sources[RELAY] = sources[RELAY].replace(posix_includes,
        b"#ifdef _WIN32\n"
        b"#ifndef WIN32_LEAN_AND_MEAN\n#define WIN32_LEAN_AND_MEAN\n#endif\n"
        b"#include <winsock2.h>\n#include <ws2tcpip.h>\n"
        b"#else\n" + posix_includes + b"\n#endif", 1)
    sources[CMAKE] = sources[CMAKE].replace(
        LINK_OPTS.encode(),
        b'if(NOT WIN32)\n    ' + LINK_OPTS.encode() + b'\nelse()\n'
        b'    target_compile_definitions(bbnet20 PRIVATE _CRT_SECURE_NO_WARNINGS)\n'
        b'    target_link_libraries(bbnet20 PRIVATE ws2_32 iphlpapi crypt32 bcrypt user32)\n'
        b'    set_target_properties(bbnet20 PROPERTIES PREFIX "" RUNTIME_OUTPUT_DIRECTORY "' +
        b'$' + b'{CMAKE_SOURCE_DIR}' + b'/../out/gpu")\n'
        b'endif()')
    destinations = (
        ("gpu/bbnet20", "gpu/bbnet20"),
        ("gpu/bbnet/bbnet.h", "gpu/bbnet/bbnet.h"),
        ("gpu/third_party/httplib", "gpu/third_party/httplib"),
    )
    for _, target in destinations:
        obj = workspace / target
        if obj.exists() or obj.is_symlink():
            raise ValueError(f"refusing to overwrite: {target}")
    for name in sources:
        target = workspace.joinpath(*name.split("/"))
        if not target.parent.resolve().is_relative_to(workspace):
            raise ValueError("destination escapes workspace")
    with tempfile.TemporaryDirectory(prefix=".bbnet20-source-", dir=workspace) as tmp:
        root = Path(tmp)
        for name, data in sorted(sources.items()):
            dest = root.joinpath(*name.split("/"))
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        moved = []
        try:
            for origin, dest in destinations:
                target = workspace / dest
                target.parent.mkdir(parents=True, exist_ok=True)
                os.rename(root / origin, target)
                moved.append(target)
        except OSError:
            for dest in reversed(moved):
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            raise
    return {"source_revision": REVISION, "files_staged": len(sources),
            "adapted": [GLUE, BBSC_GLUE, RELAY, CMAKE, MEMSCAN], "windows_online_dll_built": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.staged, args.workspace), sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
