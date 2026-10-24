import unittest
from patch_texture_gc import transform

SOURCE='''    const auto clean_up = [&](Image& image) {
        if (num_deletions == 0 || ++visited > 256) {
            return true;
        }
        const auto image_id = slot_images.GetSlotId(image);
        constexpr auto CpuWritten = ImageFlagBits::MaybeCpuDirty | ImageFlagBits::CpuDirty;
        // unchanged policy
'''

class TestGcPatch(unittest.TestCase):
    def test_guard_protects_inflight_targets_before_gc_decision(self):
        result=transform(SOURCE)
        guard=result.index('if (image.binding.is_bound')
        action=result.index('constexpr auto CpuWritten')
        self.assertLess(guard,action)
        for tag in ['image.binding.is_target','image.usage.vo_surface']:
            self.assertIn(tag,result)
        # scene_proxy is sticky across SceneTargets::SetSize: do NOT use it
        # as an unconditional evict guard or long-session VRAM can grow.
        conditional=result[result.index('if (image.binding.is_bound'):result.index(') {',result.index('if (image.binding.is_bound'))]
        self.assertNotIn('image.scene_proxy',conditional)
        self.assertIn('image_lru_cache.Touch(image, gc_tick);',result)
    def test_depth_eviction_explicitly_opt_in_and_age_guard_preserved(self):
        result=transform(SOURCE)
        self.assertIn('SH_GC_RECLAIM_DEPTH',result)
        self.assertIn('reclaim_stale_depth && image.info.props.is_depth',result)
        self.assertIn('FreeImage(image_id)',result)
        self.assertIn('if (num_deletions == 0 || ++visited > 256)',result)
        self.assertNotIn('BB_GC_IDLE_SECONDS',result)
    def test_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'anchor drift'):
            transform(SOURCE.replace('const auto image_id','auto image_id'))
        with self.assertRaisesRegex(ValueError,'already applied'):
            transform(transform(SOURCE))
    def test_original_not_mutated(self):
        s=SOURCE
        transform(s)
        self.assertEqual(s,SOURCE)

if __name__=='__main__':unittest.main()
