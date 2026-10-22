"""Offline Win64 bbnet20 source-port regression tests; synthetic sources only."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from tools.interop.prepare_bbnet20_windows import BBSC_GLUE, CMAKE, EXPORT, FORMAT, GLUE, RELAY, LINK_OPTS, REVISION, prepare


class NativeBbscPrepareTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.staged = root / "staged"
        self.staged.mkdir()
        self.workspace = root / "windows"
        (self.workspace / "gpu").mkdir(parents=True)
        (self.workspace / "gpu/CMakeLists.txt").write_text("project(test)")
        files = {
            GLUE: b'#include "bbgpu.h"\n#include <sys/mman.h>\n' +
                  EXPORT.encode() + b'\n' +
                  b'void test() { bbgpu_add_event_filter(nullptr); }\n'
                  b'        psf->app_ver = host->app_ver ? host->app_ver : "";\n'
                  b'    // BBSC finds the save it backs up and journals in shadPS4\'s folders; the port\'s are\n'
                  b'    // <user>/savedata/<user id>/CUSA00207/SPRJ0005 (BBSC_SAVE_DIR: the folder of userdata0000..).\n'
                  b'    if (!std::getenv("BBSC_SAVE_DIR")) {\n'
                  b'        auto folder = id.path() / "CUSA00207" / "SPRJ0005";\n'
                  b'        setenv("BBSC_SAVE_DIR", folder.c_str(), 0);\n'
                  b'    }\n'
                  b'    // BBSC writes its byte patches straight into the game\'s code\n'
                  b'    unsigned writable = 0;\n'
                  b'    if (FILE* maps = std::fopen("/proc/self/maps", "r")) {\n'
                  b'        mprotect(nullptr, 0, 0);\n'
                  b'    }\n'
                  b'    std::printf("BBSC: seamless co-op hooks for the image");\n'
                  b'    if (const char* probe = std::getenv("BB_BBSC_PROBE")) {\n'
                  b'        /* linux test probe */\n'
                  b'    }\n'
                  b'    // The cinematic camera goes here\n',
            BBSC_GLUE: b'#include "bbgpu.h"\n'
                       b'void show() { bbgpu_overlay_banner("host"); }\n'
                       b'void hide() { bbgpu_overlay_banner(nullptr); }\n',
            CMAKE: LINK_OPTS.encode(),
            RELAY: b'#include <arpa/inet.h>\n#include <netinet/in.h>\n'
                   b'void relay() { /* protocol unchanged */ }\n',
                 "gpu/bbnet20/vendor/shadps4/network.cpp": b"vendor",
                 "gpu/bbnet/bbnet.h": b"ABI2",
                 "gpu/third_party/httplib/httplib.h": b"HTTP",
                 "gpu/third_party/httplib/LICENSE": b"MIT"}
        self.manifest = {"format": FORMAT, "revision": REVISION, "files": []}
        for name, data in files.items():
            f = self.staged / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
            self.manifest["files"].append({
                "path": name, "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest()})
        self.save()

    def save(self):
        (self.staged / "PORT-SOURCE-MANIFEST.json").write_text(json.dumps(self.manifest))

    def test_stages_and_rejects_overwrite(self):
        result = prepare(self.staged, self.workspace)
        self.assertEqual(result["files_staged"], 8)
        self.assertEqual(result["adapted"], [GLUE, BBSC_GLUE, RELAY, CMAKE])
        self.assertFalse(result["windows_online_dll_built"])
        self.assertIn("__declspec(dllexport)", (self.workspace / GLUE).read_text())
        glue = (self.workspace / GLUE).read_text()
        self.assertIn('SeamlessBbsc::ActiveSaveFolder(', glue)
        self.assertIn('#include "../shim/bbsc_native_save_dir.h"', glue)
        self.assertIn('SeamlessBbsc::MatchesActiveSaveFolder(active_save,', glue)
        self.assertIn('g_host.serial ? g_host.serial : ""', glue)
        self.assertIn('game_ver == "1.09" ? "01.09"', glue)
        self.assertIn('native active save for retail title not found', glue)
        self.assertIn('#else\n    // BBSC finds the save it backs up', glue)
        self.assertIn('"CUSA00207"', glue)  # Unmodified Linux source still present.
        self.assertIn("bbnet20_host_add_event_filter(",
                      (self.workspace / GLUE).read_text())
        self.assertNotIn("bbgpu_add_event_filter(",
                         (self.workspace / GLUE).read_text())
        self.assertEqual((self.workspace / BBSC_GLUE).read_text().count(
            "bbnet20_host_overlay_banner("), 3)
        self.assertNotIn("bbgpu_overlay_banner(",
                         (self.workspace / BBSC_GLUE).read_text())
        self.assertIn("if(NOT WIN32)", (self.workspace / CMAKE).read_text())
        relay = (self.workspace / RELAY).read_text()
        self.assertIn("#include <winsock2.h>", relay)
        self.assertIn("#include <ws2tcpip.h>", relay)
        self.assertIn("#include <arpa/inet.h>", relay)
        self.assertIn("protocol unchanged", relay)
        self.assertIn("$"+"{CMAKE_SOURCE_DIR}", (self.workspace / CMAKE).read_text())
        self.assertEqual((self.workspace / "gpu/bbnet20/vendor/shadps4/network.cpp").read_bytes(), b"vendor")
        with self.assertRaisesRegex(ValueError, "overwrite"):
            prepare(self.staged, self.workspace)

    def test_fail_closed_revision_hash_and_signatures(self):
        self.manifest["revision"] = "f" * 40
        self.save()
        with self.assertRaisesRegex(ValueError, "unreviewed"):
            prepare(self.staged, self.workspace)
        self.manifest["revision"] = REVISION
        self.save()
        (self.staged / GLUE).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "SHA256"):
            prepare(self.staged, self.workspace)
        blob = b"changed upstream ABI"
        (self.staged / GLUE).write_bytes(blob)
        record = next(x for x in self.manifest["files"] if x["path"] == GLUE)
        record.update(size=len(blob), sha256=hashlib.sha256(blob).hexdigest())
        self.save()
        with self.assertRaisesRegex(ValueError, "review Windows adaptations"):
            prepare(self.staged, self.workspace)

    def test_crlf_real_bbsc_memory_windows_platform_patch(self):
        # Git for Windows checkouts can convert native C++ files to CRLF.
        # Verify the original pinned bytes, then normalize only the adapted
        # glue and CMake, preserving everything else from upstream.
        upstream = (
            '#include "bbgpu.h"\n'
            + '#include <sys/mman.h>\n'
            + EXPORT + '\n'
            + 'void patch(unsigned long long base, unsigned long long size) {\n'
            + '        psf->app_ver = host->app_ver ? host->app_ver : "";\n'
            + '    // BBSC finds the save it backs up and journals in shadPS4\'s folders; the port\'s are\n'
            + '    // <user>/savedata/<user id>/CUSA00207/SPRJ0005 (BBSC_SAVE_DIR).\n'
            + '    if (!std::getenv("BBSC_SAVE_DIR")) {\n'
            + '        auto folder = id.path() / "CUSA00207" / "SPRJ0005";\n'
            + '        setenv("BBSC_SAVE_DIR", folder.c_str(), 0);\n'
            + '    }\n'
            + '    // BBSC writes its byte patches straight into the game\'s code\n'
            + '    unsigned writable = 0;\n'
            + '    if (FILE* maps = std::fopen("/proc/self/maps", "r")) {\n'
            + '      /* POSIX-only range loop */\n'
            + '    }\n'
            + '    std::printf("BBSC: seamless co-op hooks for the image");\n'
            + '    if (const char* probe = std::getenv("BB_BBSC_PROBE")) {\n'
            + '      /* POSIX-only address probe */\n'
            + '    }\n'
            + '    // The cinematic camera (other game hooks follow)\n'
            + '    bbgpu_add_event_filter(nullptr);\n'
            + '}\n'
        ).replace("\n", "\r\n").encode("utf-8")
        self._replace_fixture(GLUE, upstream)
        self._replace_fixture(CMAKE, (LINK_OPTS + "\r\n").encode())
        self._replace_fixture(RELAY,
            b"#include <arpa/inet.h>\r\n#include <netinet/in.h>\r\n"
            b"// unchanged UDP protocol\r\n")
        prepare(self.staged, self.workspace)
        glue = (self.workspace / GLUE).read_text()
        self.assertIn("#include <windows.h>", glue)
        self.assertIn("VirtualQuery(", glue)
        self.assertIn("VirtualProtect(", glue)
        self.assertIn("_putenv_s(", glue)
        self.assertIn("SeamlessBbsc::ActiveSaveFolder", glue)
        self.assertIn('game_ver == "1.09" ? "01.09"', glue)
        self.assertIn('CUSA03173 (byte-verified)', glue)
        self.assertIn("#ifndef _WIN32", glue)
        self.assertIn("BBSC_SAVE_DIR", glue)
        self.assertEqual(glue.count("    unsigned writable = 0;"), 2)
        self.assertIn("#ifdef _WIN32", glue)
        self.assertIn("#else", glue)
        self.assertIn("    unsigned writable = 0;\n    if (FILE* maps", glue)

    def _replace_fixture(self, name, blob):
        path = self.staged / name
        path.write_bytes(blob)
        record = next(x for x in self.manifest["files"] if x["path"] == name)
        record["size"] = len(blob)
        record["sha256"] = hashlib.sha256(blob).hexdigest()
        self.save()

    def test_reject_source_traversal(self):
        self.manifest["files"].append({
            "path": "gpu/bbnet20/../other.cpp", "size": 0, "sha256": "0"*64})
        self.save()
        with self.assertRaisesRegex(ValueError, "unsafe"):
            prepare(self.staged, self.workspace)


if __name__ == "__main__":
    unittest.main()
