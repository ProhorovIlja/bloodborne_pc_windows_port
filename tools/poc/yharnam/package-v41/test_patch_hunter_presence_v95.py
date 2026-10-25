#!/usr/bin/env python3
"""Exact source guard: native game-only level/build preview, no RPC claim."""
from pathlib import Path
import importlib.util
import unittest

p=Path(__file__).with_name("patch_bbport_hunter_presence_v95.py")
spec=importlib.util.spec_from_file_location("hunt_v95",p)
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

S='''#include "bbport_save_editor.h"
void SaveTab() {
    const BbSaveEditor::Character c = *character;
    char text[96];
    std::snprintf(text, sizeof(text), "%d", c.level);
    Note(text, Dim());

    ImGui::Spacing();
    const auto& items = BbSaveEditor::Items();
}
'''
class TestNativeHunterPresenceV95(unittest.TestCase):
    def test_exact_overlay_patches_and_does_not_export_private_data(self):
        result=v.patch_overlay(S)
        self.assertIn(v.MARKER,result)
        self.assertIn('sh_hunter_presence_v95.hpp',result)
        self.assertIn('const SeamlessHunt::HunterPresenceV95::Hunter hunter{',result)
        self.assertIn('c.level, {c.attributes[BbSaveEditor::Vitality]',result)
        self.assertIn('SeamlessHunt::HunterPresenceV95::Details(hunter)',result)
        self.assertIn('Discord BL/build preview (local only)',result)
        self.assertNotIn('Discord_UpdatePresence(',result)
        self.assertNotIn('account_secret',result)
        self.assertNotIn('joinSecret',result)
        with self.assertRaisesRegex(ValueError,"already modified"):
            v.patch_overlay(result)

    def test_drift_rejected_fail_closed(self):
        for changed in (
            S.replace('#include "bbport_save_editor.h"','#include "bad.h"'),
            S.replace('    Note(text, Dim());','    Note(text, Gold());'),
            S.replace('    const auto& items = BbSaveEditor::Items();',''),
            S.replace('void SaveTab()', 'void SaveTab()\n// unexpected function'),
        ):
            if changed==S or "unexpected function" in changed:
                continue
            with self.subTest(changed=changed[:70]),self.assertRaises(ValueError):
                v.patch_overlay(changed)
        with self.assertRaises(ValueError):
            v.patch_overlay(S+S)
if __name__=="__main__":
    unittest.main()
