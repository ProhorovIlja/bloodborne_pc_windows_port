"""V96 original native Windows launcher per-game Vulkan layer safety tests."""
import ast
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).with_name("patch_vk_layer_compat_v96.py")
spec=importlib.util.spec_from_file_location("shyt_vk_v96",path)
patch=importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)
FIXTURE='''RESHADE_LAYER = 'VK_LAYER_bbport_reshade'

def game_environment(s, frame_generation=None):
    env = dict(os.environ)
    if not s.get('experimental'):
        env['BB_FSR4VK'] = '0'
    else:
        env.pop('BB_FSR4VK', None)  # the switch decides: an inherited 0 would leave the dropdown on and the game off
    for item in str(s['extra_env']).split():
        if '=' in item:
            key, value = item.split('=', 1)
            env[key] = value
    return env
'''
def get_helper(patched):
    tree=ast.parse(patched)
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and
                  n.name=="add_crashing_vk_layer_guard")
    globals_={"CRASHING_VK_LAYERS":("*HudSight*",)}
    exec(compile(ast.Module(body=[function],type_ignores=[]),"<v96>", "exec"),globals_)
    return globals_["add_crashing_vk_layer_guard"]

class NativeLauncherVkLayerV96Tests(unittest.TestCase):
    def test_original_game_only_no_global_ambient_mutation(self):
        patched=patch.patch_launcher(FIXTURE)
        self.assertIn(patch.MARKER,patched)
        self.assertIn("add_crashing_vk_layer_guard(env)",patched)
        self.assertLess(patched.index("add_crashing_vk_layer_guard(env)",patched.index("for item in str(s['extra_env']).split()"))
        with self.assertRaisesRegex(ValueError,"already applied"):
            patch.patch_launcher(patched)
        helper=get_helper(patched)
        inherited={"VK_LOADER_LAYERS_DISABLE":"~implicit~,VK_LAYER_KHRONOS_validation"}
        child=dict(inherited)
        helper(child)
        self.assertEqual(child["VK_LOADER_LAYERS_DISABLE"],
                         "~implicit~,VK_LAYER_KHRONOS_validation,*HudSight*")
        self.assertEqual(inherited["VK_LOADER_LAYERS_DISABLE"],
                         "~implicit~,VK_LAYER_KHRONOS_validation")
        helper(child)
        self.assertEqual(child["VK_LOADER_LAYERS_DISABLE"].count("*HudSight*"),1)
        disabled={}
        helper(disabled)
        self.assertEqual(disabled["VK_LOADER_LAYERS_DISABLE"],"*HudSight*")
        # The game's Advanced extra_env has last word, including empty.
        disabled["VK_LOADER_LAYERS_DISABLE"]=""
        self.assertEqual(disabled["VK_LOADER_LAYERS_DISABLE"],"")

    def test_bad_vendor_source_must_not_be_silently_patched(self):
        for broken in [
            FIXTURE.replace("RESHADE_LAYER = 'VK_LAYER_bbport_reshade'","RESHADE_LAYER = 'different'"),
            FIXTURE.replace("    for item in str(s['extra_env']).split():","    for item in s['extra_env']:"),
            FIXTURE + FIXTURE,
        ]:
            with self.subTest(broken=broken[:45]), self.assertRaises(ValueError):
                patch.patch_launcher(broken)

if __name__=="__main__":
    unittest.main()
