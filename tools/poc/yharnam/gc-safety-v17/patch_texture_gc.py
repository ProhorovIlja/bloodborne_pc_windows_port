#!/usr/bin/env python3
"""V17: conservative GC guard for active Vulkan resources and opt-in stale depth reclaim.

Pinned Yharnam Together texture_cache.cpp only; never alters VRAM pressure timings.
"""
from pathlib import Path

PATH = 'bbport/gpu/shadps4/video_core/texture_cache/texture_cache.cpp'

def transform(source: str) -> str:
    if 'SH-GC-V17' in source:
        raise ValueError('V17 already applied')
    anchor = '''        const auto image_id = slot_images.GetSlotId(image);
        constexpr auto CpuWritten = ImageFlagBits::MaybeCpuDirty | ImageFlagBits::CpuDirty;'''
    replacement = '''        const auto image_id = slot_images.GetSlotId(image);
        // SH-GC-V17: protect only currently bound attachments and presentation.
        // IMPORTANT: scene_proxy remains true even after SceneTargets::SetSize()
        // clears its entries; protecting it here would pin old area textures in
        // VRAM indefinitely. The original GC age and writeback policy applies.
        if (image.binding.is_bound || image.binding.is_target ||
            image.usage.vo_surface) {
            image_lru_cache.Touch(image, gc_tick);
            return false;
        }
        // Depth/shadow images can be large and stay GPU-modified. Deleting them
        // after the existing age/pressure gate helps reclaim stale area resources.
        // Off by default until multi-area GPU regression testing is complete.
        static const bool reclaim_stale_depth = [] {
            const char* env = std::getenv("SH_GC_RECLAIM_DEPTH");
            return env && env[0] == '1' && env[1] == 0;
        }();
        if (reclaim_stale_depth && image.info.props.is_depth) {
            --num_deletions;
            ++gc_evictions;
            BbStats::gc_freed_images.fetch_add(1, std::memory_order_relaxed);
            FreeImage(image_id);
            return false;
        }
        constexpr auto CpuWritten = ImageFlagBits::MaybeCpuDirty | ImageFlagBits::CpuDirty;'''
    if source.count(anchor) != 1:
        raise ValueError(f'V17 pinned GC anchor drift: expected 1 found {source.count(anchor)}')
    return source.replace(anchor, replacement, 1)

if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('output',type=Path)
    args=p.parse_args()
    if args.source.resolve()==args.output.resolve():
        p.error('will not overwrite source')
    args.output.write_text(transform(args.source.read_text(encoding='utf-8')),encoding='utf-8')
