#!/usr/bin/env python3
"""V98 source-transaction and original gameplay call-site regression."""
import importlib.util
from pathlib import Path
import unittest

f=Path(__file__).with_name("patch_upstream_lethal_catches_v98.py")
spec=importlib.util.spec_from_file_location("shyt_v98",f)
patch=importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)

DATA={
patch.GAME_H:'''// Holding a button for '''+chr(96)+'''hold_ms'''+chr(96)+''' (giving up): fires once per hold.
class HoldToConfirm {''',
patch.GAME_CPP:'''bool HoldToConfirm::Tick(bool held, s64 now_ms) {''',
patch.INTERNAL_H:'''    ReviveHits revive_hits;
    u32 seen_catches = 0;
    u32 seen_attacks = 0;''',
patch.DEATH_CPP:'''    bool armed = false;
    bool alive = false;
};

// Without party death the vitals board
void TickStanding(PartyDeathRun& run, const DeathTick& tick) {
    const u32 catches = party_death_catches.load();
    const bool caught = catches != run.seen_catches;
    run.seen_catches = catches;
    if (caught && tick.alive) {
    ReadLocalAliveState(tick.player, tick.alive);
    if (const u32 uses = lamp_uses.load(); uses != run.seen_lamp_uses) {'''
}

class LethalCatchesV98(unittest.TestCase):
    def test_replaces_old_queued_dead_catches_without_guest_wire_change(self):
        previous={k:val.encode() for k,val in DATA.items()}
        out=patch.patch(previous)
        self.assertEqual(len(out),4)
        self.assertEqual(previous[patch.GAME_CPP],DATA[patch.GAME_CPP].encode())
        self.assertIn(b'bool LethalCatches::Take(u32 count, Vital vital)',out[patch.GAME_CPP])
        self.assertIn(b'const bool caught = count != seen;',out[patch.GAME_CPP])
        self.assertIn(b'seen = count;',out[patch.GAME_CPP])
        self.assertIn(b'vital == Vital::Up || vital == Vital::Off',out[patch.GAME_CPP])
        self.assertIn(b'LethalCatches lethal_catches;',out[patch.INTERNAL_H])
        self.assertNotIn(b'seen_catches',out[patch.INTERNAL_H])
        self.assertNotIn(b'run.seen_catches',out[patch.DEATH_CPP])
        self.assertIn(b'if (tick.caught && tick.alive)',out[patch.DEATH_CPP])
        self.assertIn(b'run.lethal_catches.Take(',out[patch.DEATH_CPP])
        src=out[patch.DEATH_CPP]
        self.assertLess(src.index(b'run.lethal_catches.Take('),
                        src.index(b'if (const u32 uses = lamp_uses.load();'))
        self.assertIn(b'// SHYT-V98-UPSTREAM-LETHAL-CATCHES',out[patch.DEATH_CPP])
        with self.assertRaisesRegex(ValueError,"already present"):
            patch.patch(out)

    def test_mixed_old_and_new_file_rejected_transactionally(self):
        original={k:val.encode() for k,val in DATA.items()}
        for path in patch.FILES:
            bad=dict(original)
            bad[path]=b"fork drift, not this source pin"
            with self.subTest(path=path), self.assertRaisesRegex(ValueError,"drift"):
                patch.patch(bad)
            self.assertEqual(original[path],DATA[path].encode())
        missing=dict(original);del missing[patch.INTERNAL_H]
        with self.assertRaisesRegex(ValueError,"absent"):
            patch.patch(missing)

if __name__=="__main__":
    unittest.main()
