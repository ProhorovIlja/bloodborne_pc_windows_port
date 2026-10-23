#!/usr/bin/env python3
"""V16: defensive 3D map resource ownership and descriptor failure recovery.

Apply only to pinned Yharnam BBPort bbport_map_3d.cpp, fail closed on source drift.
"""
from __future__ import annotations
from pathlib import Path

PATH = 'bbport/gpu/shim/bbport_map_3d.cpp'

def replace_exact(source: str, old: str, new: str, count: int, label: str) -> str:
    actual = source.count(old)
    if actual != count:
        raise ValueError(f'V16 {label}: expected {count} anchors, found {actual}')
    return source.replace(old, new)

def transform(source: str) -> str:
    if 'SH-MAP-V16' in source:
        raise ValueError('V16 already applied')
    old_create = '''    if (vmaCreateBuffer(allocator, &buffer_ci, &alloc_ci, &out.buffer, &out.allocation, &info) != VK_SUCCESS ||
        info.pMappedData == nullptr) {
        out = {};
        return false;
    }'''
    new_create = '''    // SH-MAP-V16: a successful allocation without mapping still belongs to us.
    const VkResult result = vmaCreateBuffer(allocator, &buffer_ci, &alloc_ci,
                                            &out.buffer, &out.allocation, &info);
    if (result != VK_SUCCESS) {
        out = {};
        return false;
    }
    if (info.pMappedData == nullptr) {
        vmaDestroyBuffer(allocator, out.buffer, out.allocation);
        out = {};
        return false;
    }'''
    source = replace_exact(source, old_create, new_create, 2, 'VMA buffers')
    source = replace_exact(source,
        '''bool MakeBuffer(Buffer& out, const void* data, std::size_t size, VkBufferUsageFlags usage) {
    const VkBufferCreateInfo buffer_ci{''',
        '''bool MakeBuffer(Buffer& out, const void* data, std::size_t size, VkBufferUsageFlags usage) {
    if (!data || size == 0) return false;
    const VkBufferCreateInfo buffer_ci{''', 1, 'MakeBuffer input')
    source = replace_exact(source,
        '''bool MakeStaging(Buffer& out, const void* data, std::size_t size) {
    const VkBufferCreateInfo buffer_ci{''',
        '''bool MakeStaging(Buffer& out, const void* data, std::size_t size) {
    if (!data || size == 0) return false;
    const VkBufferCreateInfo buffer_ci{''', 1, 'MakeStaging input')
    source = replace_exact(source,
        'if (w <= target_width && h <= target_height && color.image != VK_NULL_HANDLE) {',
        'if (w <= target_width && h <= target_height && color.image != VK_NULL_HANDLE &&\n'
        '        texture != VK_NULL_HANDLE) {', 1, 'reusable targets require descriptor')
    source = replace_exact(source,
        '''    texture = ImGui_ImplVulkan_AddTexture(*color.view, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
    return texture != VK_NULL_HANDLE;''',
        '''    texture = ImGui_ImplVulkan_AddTexture(*color.view, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
    if (texture == VK_NULL_HANDLE) {
        // Never return a usable render target without a valid ImGui texture descriptor.
        FreeTarget(color);
        FreeTarget(depth);
        target_width = target_height = 0;
        return false;
    }
    return true;''', 1, 'descriptor allocation failure')
    source = replace_exact(source,
        '''    Mesh made;
    made.dx = dx;''',
        '''    // Validate texture upload extents before creating any GPU resources.
    // Division rather than multiplication avoids overflow on malformed chart sizes.
    if (chart->width <= 0 || chart->height <= 0 || chart->storeys.width <= 0 ||
        chart->storeys.height <= 0 || !std::isfinite(chart->ppm) || chart->ppm <= 0 ||
        std::size_t(chart->width) > chart->rgba.size() / 4 / std::size_t(chart->height) ||
        std::size_t(chart->storeys.width) >
            chart->storeys.roof.size() / std::size_t(chart->storeys.height)) {
        std::printf("Map 3D: invalid chart dimensions for %s\\n", BbMapArt::MapNameOf(map).c_str());
        return;
    }
    Mesh made;
    made.dx = dx;''', 1, 'chart transfer input validation')
    source = replace_exact(source,
        '''    width = static_cast<std::uint32_t>(std::max(1.0f, std::round(wanted.x1 - wanted.x0)));
    height = static_cast<std::uint32_t>(std::max(1.0f, std::round(wanted.y1 - wanted.y0)));''',
        '''    const float extent_w = wanted.x1 - wanted.x0, extent_h = wanted.y1 - wanted.y0;
    if (!std::isfinite(extent_w) || !std::isfinite(extent_h) ||
        extent_w <= 0 || extent_h <= 0) {
        asked = false;
        return ImTextureRef();
    }
    // Defensive render target bound in case of stale window or corrupt camera dimensions.
    width = static_cast<std::uint32_t>(std::clamp(std::round(extent_w), 1.0f, 4096.0f));
    height = static_cast<std::uint32_t>(std::clamp(std::round(extent_h), 1.0f, 4096.0f));''', 1, 'invalid map viewport guard')
    return source

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    if args.source.resolve() == args.output.resolve():
        p.error('source and output must be separate files')
    args.output.write_text(transform(args.source.read_text(encoding='utf-8')), encoding='utf-8')
    print('V16 map resource safety patch passed, source preserved')
