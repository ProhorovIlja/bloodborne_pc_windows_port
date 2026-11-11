/* SPDX-License-Identifier: GPL-2.0-or-later
 * V364 renderer-neutral source ranges and draw contracts.
 * FLVER2 validation and bounds are delegated to the independently tested
 * V362 validator; these ranges intentionally do not decode vertex elements
 * or pretend to perform Vulkan/Direct3D uploads.
 */
#include "native_flver2_gpu_plan_v364.h"
#include <stdint.h>
#include <string.h>

#define SHYT_GPU_PLAN_MAX_DRAWS_V364 1000000ull
static uint32_t le32_v364(const unsigned char *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8) |
           ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}
static int bounded_v364(uint64_t offset,uint64_t count,uint64_t size) {
    return offset<=size && count<=size-offset;
}
/* Distinct caller-owned output ranges must never mutate FLVER source,
 * descriptor arrays, or the published stats during plan construction.
 * Checked unsigned addresses avoid undefined cross-allocation comparisons.
 */
static int ranges_overlap_v364(
    const void *a,size_t a_len,const void *b,size_t b_len) {
    if (!a_len || !b_len) return 0;
    if (!a || !b) return 1;
    const uintptr_t start_a=(uintptr_t)a,start_b=(uintptr_t)b;
    if (a_len>UINTPTR_MAX-start_a || b_len>UINTPTR_MAX-start_b)
        return 1;
    return start_a<start_b+b_len && start_b<start_a+a_len;
}
static int align4_v364(uint64_t *value) {
    if (*value>UINT64_MAX-3u) return 0;
    *value=(*value+3u)&~(uint64_t)3u;
    return 1;
}
static int validate_asset_v364(
    const ShytNativeFlver2AssetV363 *asset,
    ShytNativeFlver2GeometryV362 *geometry) {
    if (!asset || !asset->flver || !geometry || !asset->flver_bytes)
        return 0;
    return shyt_native_flver2_geometry_probe_v362(
        asset->flver,asset->flver_bytes,geometry);
}
static int requirements_inner_v364(
    const ShytNativeFlver2AssetV363 *asset,
    const ShytNativeFlver2GeometryV362 *geometry,
    ShytNativeGpuUploadCountsV364 *out) {
    const unsigned char *p=asset->flver;
    const uint64_t limit=asset->flver_bytes;
    uint64_t draws=0;
    uint64_t staging=0;
    out->vertex_buffers=geometry->vertex_buffer_count;
    out->index_buffers=geometry->face_set_count;
    for (uint32_t i=0;i<geometry->vertex_buffer_count;++i) {
        const uint64_t rec=(uint64_t)geometry->first_vertex_record_offset+32ull*i;
        if (!bounded_v364(rec,32,limit)) return 0;
        const uint64_t bytes=le32_v364(p+(size_t)rec+24);
        if (!align4_v364(&staging) || staging>UINT64_MAX-bytes ||
            out->vertex_source_bytes>UINT64_MAX-bytes) return 0;
        staging+=bytes;
        out->vertex_source_bytes+=bytes;
    }
    for (uint32_t i=0;i<geometry->face_set_count;++i) {
        const uint64_t rec=(uint64_t)geometry->first_face_record_offset+32ull*i;
        if (!bounded_v364(rec,32,limit)) return 0;
        const uint64_t bytes=le32_v364(p+(size_t)rec+16);
        if (!align4_v364(&staging) || staging>UINT64_MAX-bytes ||
            out->index_source_bytes>UINT64_MAX-bytes) return 0;
        staging+=bytes;
        out->index_source_bytes+=bytes;
    }
    for (uint32_t i=0;i<geometry->mesh_count;++i) {
        const uint64_t rec=(uint64_t)geometry->first_mesh_record_offset+48ull*i;
        if (!bounded_v364(rec,48,limit)) return 0;
        draws+=le32_v364(p+(size_t)rec+32);
        if (draws>SHYT_GPU_PLAN_MAX_DRAWS_V364) return 0;
    }
    out->draws=(uint32_t)draws;
    out->staging_bytes_total=staging;
    return 1;
}
int shyt_native_flver2_gpu_requirements_v364(
    const ShytNativeFlver2AssetV363 *asset,
    ShytNativeGpuUploadCountsV364 *out) {
    if (!out) return 0;
    if (asset && asset->flver && ranges_overlap_v364(
            out,sizeof(*out),asset->flver,asset->flver_bytes))
        return 0; /* aliased output is a caller contract violation */
    memset(out,0,sizeof(*out));
    ShytNativeFlver2GeometryV362 g;
    ShytNativeGpuUploadCountsV364 counts={0};
    if (!validate_asset_v364(asset,&g) ||
        !requirements_inner_v364(asset,&g,&counts)) return 0;
    *out=counts;
    return 1;
}
int shyt_native_flver2_gpu_plan_v364(
    const ShytNativeFlver2AssetV363 *asset,
    ShytNativeGpuVertexSpanV364 *vertices, size_t vertices_capacity,
    ShytNativeGpuIndexSpanV364 *indices, size_t indices_capacity,
    ShytNativeGpuDrawV364 *draws, size_t draws_capacity,
    uint64_t staging_budget_bytes,
    ShytNativeGpuUploadCountsV364 *out) {
    if (!out) return 0;
    if (asset && asset->flver && ranges_overlap_v364(
            out,sizeof(*out),asset->flver,asset->flver_bytes))
        return 0; /* aliased output is a caller contract violation */
    memset(out,0,sizeof(*out));
    ShytNativeFlver2GeometryV362 g;
    ShytNativeGpuUploadCountsV364 counts={0};
    if (!validate_asset_v364(asset,&g) ||
        !requirements_inner_v364(asset,&g,&counts) ||
        (counts.vertex_buffers && !vertices) ||
        (counts.index_buffers && !indices) ||
        (counts.draws && !draws) ||
        vertices_capacity<counts.vertex_buffers ||
        indices_capacity<counts.index_buffers ||
        draws_capacity<counts.draws ||
        counts.staging_bytes_total>staging_budget_bytes) return 0;
    const size_t vb_bytes=(size_t)counts.vertex_buffers*sizeof(*vertices);
    const size_t ib_bytes=(size_t)counts.index_buffers*sizeof(*indices);
    const size_t draw_bytes=(size_t)counts.draws*sizeof(*draws);
    if (ranges_overlap_v364(vertices,vb_bytes,asset->flver,asset->flver_bytes) ||
        ranges_overlap_v364(indices,ib_bytes,asset->flver,asset->flver_bytes) ||
        ranges_overlap_v364(draws,draw_bytes,asset->flver,asset->flver_bytes) ||
        ranges_overlap_v364(vertices,vb_bytes,indices,ib_bytes) ||
        ranges_overlap_v364(vertices,vb_bytes,draws,draw_bytes) ||
        ranges_overlap_v364(indices,ib_bytes,draws,draw_bytes) ||
        ranges_overlap_v364(vertices,vb_bytes,out,sizeof(*out)) ||
        ranges_overlap_v364(indices,ib_bytes,out,sizeof(*out)) ||
        ranges_overlap_v364(draws,draw_bytes,out,sizeof(*out)))
        return 0;
    const unsigned char *p=asset->flver;
    const uint64_t limit=asset->flver_bytes;
    const uint64_t data_start=g.data_offset;
    uint64_t staging=0;
    for (uint32_t i=0;i<counts.vertex_buffers;++i) {
        const uint64_t rec=(uint64_t)g.first_vertex_record_offset+32ull*i;
        const uint32_t relative=le32_v364(p+(size_t)rec+28);
        const uint32_t bytes=le32_v364(p+(size_t)rec+24);
        const uint64_t absolute=data_start+relative;
        if (absolute>UINT32_MAX || !bounded_v364(absolute,bytes,limit))
            return 0;
        if (!align4_v364(&staging) || staging>UINT64_MAX-bytes)
            return 0;
        vertices[i]=(ShytNativeGpuVertexSpanV364){
            (uint32_t)absolute,bytes,staging,le32_v364(p+(size_t)rec+12),
            le32_v364(p+(size_t)rec+8),le32_v364(p+(size_t)rec+4),i};
        staging+=bytes;
    }
    for (uint32_t i=0;i<counts.index_buffers;++i) {
        const uint64_t rec=(uint64_t)g.first_face_record_offset+32ull*i;
        const uint32_t relative=le32_v364(p+(size_t)rec+12);
        const uint32_t bytes=le32_v364(p+(size_t)rec+16);
        const uint64_t absolute=data_start+relative;
        if (absolute>UINT32_MAX || !bounded_v364(absolute,bytes,limit))
            return 0;
        if (!align4_v364(&staging) || staging>UINT64_MAX-bytes)
            return 0;
        indices[i]=(ShytNativeGpuIndexSpanV364){
            (uint32_t)absolute,bytes,staging,le32_v364(p+(size_t)rec+8),
            le32_v364(p+(size_t)rec+24)/8u,le32_v364(p+(size_t)rec),
            p[(size_t)rec+4],p[(size_t)rec+5]};
        staging+=bytes;
    }
    uint32_t draw_idx=0;
    for (uint32_t i=0;i<g.mesh_count;++i) {
        const uint64_t rec=(uint64_t)g.first_mesh_record_offset+48ull*i;
        const uint32_t fcount=le32_v364(p+(size_t)rec+32);
        const uint32_t first_face_ref=le32_v364(p+(size_t)rec+36);
        const uint32_t vcount=le32_v364(p+(size_t)rec+40);
        const uint32_t first_vb_ref=le32_v364(p+(size_t)rec+44);
        if (vcount==0 || vcount>3u ||
            !bounded_v364(first_face_ref,(uint64_t)fcount*4u,g.data_offset) ||
            !bounded_v364(first_vb_ref,(uint64_t)vcount*4u,g.data_offset))
            return 0;
        uint32_t vb_indices[3]={0,0,0};
        uint32_t vertex_count=UINT32_MAX;
        for (uint32_t k=0;k<vcount;++k) {
            const uint32_t n=le32_v364(p+(size_t)first_vb_ref+(size_t)k*4);
            if (n>=counts.vertex_buffers) return 0;
            vb_indices[k]=n;
            if (vertex_count!=UINT32_MAX && vertex_count!=vertices[n].vertex_count)
                return 0;
            vertex_count=vertices[n].vertex_count;
        }
        for (uint32_t j=0;j<fcount;++j) {
            const uint32_t face=le32_v364(p+(size_t)first_face_ref+(size_t)j*4);
            if (face>=counts.index_buffers || draw_idx>=counts.draws) return 0;
            draws[draw_idx]=(ShytNativeGpuDrawV364){
                i,le32_v364(p+(size_t)rec+4),face,vcount,
                {vb_indices[0],vb_indices[1],vb_indices[2]},vertex_count};
            ++draw_idx;
        }
    }
    if (draw_idx!=counts.draws || staging!=counts.staging_bytes_total)
        return 0;
    *out=counts;
    return 1;
}
int shyt_native_flver2_stage_bytes_v364(
    const ShytNativeFlver2AssetV363 *asset,
    uint32_t source_offset,uint32_t bytes,
    void *destination,size_t destination_capacity,size_t *written) {
    if (!written) return 0;
    /* An aliased size output would corrupt model input or staged bytes.
     * Such pointers violate the API contract and are not written at all. */
    if (asset && asset->flver &&
        ranges_overlap_v364(written,sizeof(*written),
                            asset->flver,asset->flver_bytes)) return 0;
    if (destination &&
        ranges_overlap_v364(written,sizeof(*written),destination,bytes))
        return 0;
    *written=0;
    if (!asset || !asset->flver || !destination ||
        bytes==0 || destination_capacity<(size_t)bytes ||
        !bounded_v364(source_offset,bytes,asset->flver_bytes)) return 0;
    /* Refuse ALL destination/source-asset overlap. Requiring only the
     * selected source span to be disjoint would let one stream overwrite
     * another during preparation. uintptr_t avoids undefined relational
     * pointer comparisons between unrelated allocations. */
    const uintptr_t src=(uintptr_t)asset->flver;
    const uintptr_t dst=(uintptr_t)destination;
    if (asset->flver_bytes>UINTPTR_MAX-src || bytes>UINTPTR_MAX-dst)
        return 0;
    if (dst<src+asset->flver_bytes && src<dst+bytes)
        return 0;
    memcpy(destination,asset->flver+source_offset,bytes);
    *written=bytes;
    return 1;
}
