/* SPDX-License-Identifier: GPL-2.0-or-later
 * V372 diagnostic direct GPU vertex input for actual BB/DS3 layout subset.
 * Independently authored; no original game code/assets or SDK fragments.
 */
#include "native_vulkan_flver_semantic_draw_v372.h"
#include "native_flver2_gpu_plan_v364.h"
#include <cstdint>
namespace shyt_native_v372 {
bool draw_offscreen_verified_flver_v372(
    VkPhysicalDevice physical,VkDevice device,VkQueue queue,
    uint32_t family,const ShytNativeFlver2AssetV363& source,
    const shyt_native_v369::UploadedModelV369& model,
    const uint32_t* vs,size_t vlen,const uint32_t* fs,size_t flen,
    std::vector<uint8_t>* rgba) {
    if (!rgba) return false;
    rgba->clear();
    if (!source.flver || !source.flver_bytes || !model.gpu_buffer() ||
        model.ticket==0 || model.vertices.size()!=1 ||
        model.indices.size()!=1 || model.draws.size()!=1)
        return false;
    ShytNativeGpuUploadCountsV364 counts{};
    if (!shyt_native_flver2_gpu_requirements_v364(&source,&counts) ||
        counts.vertex_buffers!=1 || counts.index_buffers!=1 ||
        counts.draws!=1 || counts.staging_bytes_total!=model.bytes)
        return false;
    ShytNativeGpuVertexSpanV364 vb{};
    ShytNativeGpuIndexSpanV364 ib{};
    ShytNativeGpuDrawV364 draw{};
    ShytNativeGpuUploadCountsV364 plan{};
    if (!shyt_native_flver2_gpu_plan_v364(
            &source,&vb,1,&ib,1,&draw,1,model.bytes,&plan))
        return false;
    if (vb.buffer_index!=0 || vb.vertex_count!=3 ||
        (vb.vertex_stride!=12 && vb.vertex_stride!=36 &&
         vb.vertex_stride!=44) ||
        ib.index_count!=3 || ib.index_element_bytes!=2 ||
        ib.triangle_strip!=0 ||
        draw.mesh_index!=0 || draw.face_set_index!=0 ||
        draw.vertex_buffer_count!=1 ||
        draw.vertex_buffer_indices[0]!=0 || draw.vertex_count!=3)
        return false;
    ShytNativeFlver2VertexLayoutV371 layout{};
    if (!shyt_native_flver2_vertex_layout_v371(
            source.flver,source.flver_bytes,0,&layout) ||
        layout.vertex_count!=vb.vertex_count ||
        layout.stride!=vb.vertex_stride ||
        layout.data_offset!=vb.source_offset ||
        layout.member_count==0 ||
        layout.members[0].semantic!=0 ||
        layout.members[0].type!=2 ||
        layout.members[0].semantic_index!=0 ||
        layout.members[0].offset!=0 ||
        !(layout.present&SHYT_V371_POSITION))
        return false;
    /* Decode once as a semantic assertion, not to create a second vertex
     * buffer. V371 checks position finite and all supported member formats.
     * Rendering still reads the ORIGINAL packed GPU-resident VB directly. */
    ShytNativeFlver2VertexV371 vertices[3]{};
    if (!shyt_native_flver2_decode_vertices_v371(
            source.flver,source.flver_bytes,0,0,3,vertices,3))
        return false;
    if (model.vertices[0].offset!=vb.staging_offset ||
        model.vertices[0].stride!=vb.vertex_stride ||
        model.vertices[0].count!=vb.vertex_count ||
        model.indices[0].offset!=ib.staging_offset ||
        model.indices[0].count!=ib.index_count ||
        model.indices[0].type!=VK_INDEX_TYPE_UINT16 ||
        model.draws[0].mesh_index!=draw.mesh_index ||
        model.draws[0].material_index!=draw.material_index ||
        model.draws[0].face_set_index!=draw.face_set_index ||
        model.draws[0].vertex_buffer_count!=draw.vertex_buffer_count ||
        model.draws[0].vertex_buffer_indices[0]!=0 ||
        model.draws[0].vertex_count!=draw.vertex_count)
        return false;
    return shyt_native_v370::draw_offscreen_flver_strided_v372(
        physical,device,queue,family,model,layout.stride,
        vs,vlen,fs,flen,rgba);
}
} // namespace shyt_native_v372
