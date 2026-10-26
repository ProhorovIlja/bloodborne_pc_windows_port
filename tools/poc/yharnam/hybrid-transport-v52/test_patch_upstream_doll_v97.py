#!/usr/bin/env python3
"""V97 exact-original pin drift + all-or-nothing gameplay source tests."""
import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).with_name("patch_upstream_doll_flag_v97.py")
spec=importlib.util.spec_from_file_location("shyt_v97",p)
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

FIXTURES={
v.HEADER:'''    Range(6680, 6697, FlagOwner::PerPlayer, FlagCarriesHome,
          "had a weapon the Bath shop then sells (OwnedWeaponFlags, common events 6680-6697: "
          "Ludwig's Holy Blade, the DLC weapons): this player's own"),
    Range(9180, 9199, FlagOwner::Session, 0,''',
v.PARTY_H:'''std::vector<s32> LightRequestsToClear(u32 packed_map, const std::function<bool(s32)>& on);
// The other player's "set this event flag"''',
v.PARTY_CPP:'''bool RefusesLampLight(s32 flag, std::optional<bool> lamp_character_off) {
    return LampOfLightRequest(flag).has_value() && lamp_character_off.value_or(false);
}

std::vector<s32> LightRequestsToClear''',
v.STORE:'''void SetGuestPickupsBeforeMapItems() {
    ApplyTeamWorldOnLoad();
    ClearLightRequestsThatLitNothing();'''
}
class DollMenuV97Tests(unittest.TestCase):
    def test_strict_all_four_files_and_singleplayer_preserved(self):
        originals={k:val.encode() for k,val in FIXTURES.items()}
        result=v.patch(originals)
        self.assertEqual(len(result),4)
        self.assertEqual(originals[v.HEADER],FIXTURES[v.HEADER].encode())
        self.assertIn(b'Range(6700, 6700, FlagOwner::PerPlayer, 0',result[v.HEADER])
        self.assertIn(b'constexpr s32 DollLevelUpFlag = 6700;',result[v.PARTY_H])
        self.assertIn(b'party_configured && flag_on',result[v.PARTY_CPP])
        self.assertIn(b'if (!ClearsDollLevelUpFlag(party_controller.has_value()',result[v.STORE])
        self.assertIn(b'ClearStuckDollLevelUpFlag();',result[v.STORE])
        # Map-load only, no background game-tick clearing during live talk.
        self.assertIn(b'void SetGuestPickupsBeforeMapItems()',result[v.STORE])
        self.assertLess(result[v.STORE].index(b'ApplyTeamWorldOnLoad();'),
                        result[v.STORE].index(b'ClearStuckDollLevelUpFlag();'))
        self.assertNotIn(b'if (!party_controller.has_value()) return',result[v.STORE])
        with self.assertRaisesRegex(ValueError,"already applied"):
            v.patch(result)
    def test_mismatching_original_is_never_modified(self):
        originals={k:s.encode() for k,s in FIXTURES.items()}
        for name in v.FILES:
            altered=dict(originals)
            altered[name]=b'incompatible new upstream source'
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,"drift"):
                v.patch(altered)
            self.assertEqual(originals[name],FIXTURES[name].encode())
        missing=dict(originals);del missing[v.STORE]
        with self.assertRaisesRegex(ValueError,"absent"):
            v.patch(missing)

if __name__=="__main__":
    unittest.main()
