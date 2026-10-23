import unittest
from patch_quit_perf import transform,PATH
class Tests(unittest.TestCase):
 def fixture(self):
  return '''#include "bbport_settings.h"
 // Hold L3 + R3, or the menu's Quit row:
         const bool down = event.type == SDL_EVENT_KEY_DOWN;
         // bbport: numpad 0
     // Title and the team's state.
     ImGui::PushFont(MenuArt::Font(), 40.0f);
 if (Team::open && !menu_open) {
         Team::Screen();
 return initialized && (menu_open || quit_open || prompt_active || BbSettings::Get().show_fps || party || compass ||
     if (BbSettings::Get().show_fps && !menu_open) {
         FpsCounter();
     }
 '''.replace("\n ","\n")
 def test_quit_and_perf(self):
  out=transform(self.fixture());s=out[PATH]
  assert 'SDLK_F9' in s and 'SDLK_F10' in s
  assert 'sh-quit-desktop' in s and 'ShPerformance::Draw' in s
 def test_changed_anchor_fails(self):
  with self.assertRaises(ValueError):transform(self.fixture().replace("FpsCounter();","Fake();"))
 def test_double_patch_fails(self):
  with self.assertRaises(ValueError):transform(transform(self.fixture())[PATH])
 def test_original_not_mutated(self):
  original=self.fixture();transform(original)
  assert original==self.fixture()
if __name__=="__main__":unittest.main()
