import unittest
from patch_map import transform

VMA='''    if (vmaCreateBuffer(allocator, &buffer_ci, &alloc_ci, &out.buffer, &out.allocation, &info) != VK_SUCCESS ||
        info.pMappedData == nullptr) {
        out = {};
        return false;
    }'''
SOURCE='''bool MakeBuffer(Buffer& out, const void* data, std::size_t size, VkBufferUsageFlags usage) {
    const VkBufferCreateInfo buffer_ci{\n''' + VMA + '''\nbool MakeStaging(Buffer& out, const void* data, std::size_t size) {
    const VkBufferCreateInfo buffer_ci{\n''' + VMA + '''
if (w <= target_width && h <= target_height && color.image != VK_NULL_HANDLE) {
    texture = ImGui_ImplVulkan_AddTexture(*color.view, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
    return texture != VK_NULL_HANDLE;
    Mesh made;
    made.dx = dx;
    width = static_cast<std::uint32_t>(std::max(1.0f, std::round(wanted.x1 - wanted.x0)));
    height = static_cast<std::uint32_t>(std::max(1.0f, std::round(wanted.y1 - wanted.y0)));
'''

class MapPatchTests(unittest.TestCase):
    def test_both_vma_failure_paths_free_allocated_buffer(self):
        result=transform(SOURCE)
        self.assertEqual(result.count('vmaDestroyBuffer(allocator, out.buffer, out.allocation);'),2)
        self.assertEqual(result.count('if (result != VK_SUCCESS)'),2)
        self.assertEqual(result.count('if (!data || size == 0)'),2)
        self.assertEqual(result.count('SH-MAP-V16'),2)
    def test_map_descriptor_failure_resets_render_targets(self):
        result=transform(SOURCE)
        self.assertIn('texture != VK_NULL_HANDLE)',result)
        self.assertIn('if (texture == VK_NULL_HANDLE)',result)
        self.assertIn('FreeTarget(color);\n        FreeTarget(depth);\n        target_width = target_height = 0;',result)
    def test_malformed_chart_and_viewport_rejected(self):
        result=transform(SOURCE)
        self.assertIn('chart->rgba.size() / 4 / std::size_t(chart->height)',result)
        self.assertIn('!std::isfinite(chart->ppm)',result)
        self.assertIn('!std::isfinite(extent_w)',result)
        self.assertIn('4096.0f',result)
        self.assertIn(r'std::printf("Map 3D: invalid chart dimensions for %s\n",',result)
        self.assertNotIn('std::printf("Map 3D: invalid chart dimensions for %s\n",',result)
    def test_fail_closed_changed_upstream(self):
        with self.assertRaisesRegex(ValueError,'VMA buffers'):
            transform(SOURCE.replace('info.pMappedData == nullptr','info.pMappedData == NULL',1))
    def test_fail_closed_double_apply(self):
        with self.assertRaisesRegex(ValueError,'already applied'):
            transform(transform(SOURCE))
    def test_original_unchanged(self):
        original=SOURCE
        transform(original)
        self.assertEqual(original,SOURCE)

if __name__=='__main__':unittest.main()
