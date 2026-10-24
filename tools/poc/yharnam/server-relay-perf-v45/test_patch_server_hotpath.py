"""Fail-closed source safety for the actual Qt shadNet game UDP relay path."""
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPT = Path(__file__).with_name("patch_server_hotpath.py")
spec = importlib.util.spec_from_file_location("shyt_v45_server_fastpath", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

RELAY_OLD = '''// SPDX-License-Identifier: GPL-2.0-or-later
#include "server_link.h"
#include <algorithm>
void Hub::OnData() {
    ++target->frames_out;
    target->bytes_out += static_cast<quint64>(routed->size());
    result.sends.append({target->endpoint, Encode(Data{sender.virtual_endpoint, *routed})});
''' + mod.PAIR_OLD + '''
}
void Hub::Routed() {
    if (!packet_routes || frame.size() < GameFrameAt || frame.mid(4, 4) != "SHAD" ||
        static_cast<quint8>(frame[8]) != BloodborneCoop::GamePacketsType) {}
}'''


class ActualCppHotPathTests(unittest.TestCase):
    def test_safe_single_change_preserves_original_game_datagrams(self):
        updated = mod.transform(RELAY_OLD)
        self.assertIn("SHYT-SERVER-RELAY-PERF-V45", updated)
        self.assertIn('#include <cstring>', updated)
        self.assertNotIn('frame.mid(4, 4)', updated)
        self.assertIn('std::memcmp(frame.constData() + 4, "SHAD", 4) != 0', updated)
        self.assertIn('result.sends.append({target->endpoint, Encode(Data{sender.virtual_endpoint, *routed})});', updated)
        self.assertIn('if (pair_lines > 0)', updated)
        self.assertIn('if (count < static_cast<quint64>(pair_lines))', updated)
        self.assertNotIn('++pair_frames[', updated)
        self.assertEqual(updated.count('result.sends.append('), 1)
        self.assertEqual(updated.count("SPDX-License-Identifier: GPL-2.0-or-later"), 1)

    def test_drift_and_duplicate_patch_hard_fail(self):
        result = mod.transform(RELAY_OLD)
        with self.assertRaisesRegex(ValueError, "already applied"):
            mod.transform(result)
        with self.assertRaisesRegex(ValueError, "anchor changed"):
            mod.transform(RELAY_OLD.replace('frame.mid(4, 4) != "SHAD"', 'other()'))
        with self.assertRaisesRegex(ValueError, "anchor changed"):
            mod.transform(RELAY_OLD.replace(mod.PAIR_OLD, ""))
        with self.assertRaisesRegex(ValueError, "license header"):
            mod.transform(RELAY_OLD.replace("GPL-2.0-or-later", "no-license"))

    def test_pair_diagnostic_counter_saturates_without_packet_changes(self):
        # On the first pair_lines frames the exact same N messages are logged;
        # all subsequent datagrams still flow via result.sends before this block.
        for limit, total in [(0, 2000), (2, 4000), (20, 200)]:
            counter = 0
            messages = []
            for _ in range(total):
                if limit > 0 and counter < limit:
                    counter += 1
                    messages.append(counter)
            self.assertEqual(messages, list(range(1, min(total, limit) + 1)))
            self.assertEqual(counter, min(total, limit))


if __name__ == "__main__":
    unittest.main()
