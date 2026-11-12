/* SPDX-License-Identifier: GPL-2.0-or-later
 * Win64 D3D12 WARP offscreen FLVER2 indexed draw/readback proof.
 * No original BB game bytes, EBOOT, PS4 code, guest interpreter or Wine.
 */
#include "native_d3d12_flver_draw_v373.h"
#include "native_flver2_gpu_plan_v364.h"
#include <windows.h>
#include <d3dcompiler.h>
#include <dxgi1_4.h>
#include <wrl/client.h>
#include <cstdint>
#include <cstring>
#include <new>
#include <limits>
#include <climits>
#include <utility>
using Microsoft::WRL::ComPtr;
namespace shyt_native_v373 {
namespace {
constexpr DXGI_FORMAT kColor=DXGI_FORMAT_R8G8B8A8_UNORM;
constexpr unsigned kW=kFrameWidthV373,kH=kFrameHeightV373;
/* Invented HLSL diagnostic. This is NOT a Bloodborne shader. */
static constexpr char kHLSL[]=
    "struct VIn{float3 position:POSITION;};\n"
    "struct VOut{float4 position:SV_POSITION;};\n"
    "VOut VSMain(VIn v){VOut o;o.position=float4(v.position,1.0);return o;}\n"
    "float4 PSMain(VOut v):SV_TARGET{return float4(0.0,1.0,0.0,1.0);}\n";

D3D12_HEAP_PROPERTIES heap(D3D12_HEAP_TYPE type) noexcept {
    D3D12_HEAP_PROPERTIES h{};
    h.Type=type;
    h.CPUPageProperty=D3D12_CPU_PAGE_PROPERTY_UNKNOWN;
    h.MemoryPoolPreference=D3D12_MEMORY_POOL_UNKNOWN;
    h.CreationNodeMask=1;
    h.VisibleNodeMask=1;
    return h;
}
D3D12_RESOURCE_DESC readback_desc(UINT64 bytes) noexcept {
    D3D12_RESOURCE_DESC d{};
    d.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;
    d.Width=bytes;d.Height=1;d.DepthOrArraySize=1;d.MipLevels=1;
    d.Format=DXGI_FORMAT_UNKNOWN;d.SampleDesc.Count=1;
    d.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
    return d;
}
bool same_device(ID3D12Device* device,ID3D12CommandQueue* queue) noexcept {
    if(!device||!queue||queue->GetDesc().Type!=D3D12_COMMAND_LIST_TYPE_DIRECT)
        return false;
    ComPtr<ID3D12Device> from_queue;
    ComPtr<IUnknown> a,b;
    return SUCCEEDED(queue->GetDevice(IID_PPV_ARGS(&from_queue))) &&
        SUCCEEDED(device->QueryInterface(IID_PPV_ARGS(&a))) &&
        SUCCEEDED(from_queue->QueryInterface(IID_PPV_ARGS(&b))) &&
        a.Get()==b.Get();
}
/* Graphics allocations are scoped and retained through the fence. */
struct Frame {
    ComPtr<ID3D12Resource> texture,readback;
    ComPtr<ID3D12DescriptorHeap> rtv;
    ComPtr<ID3D12RootSignature> root;
    ComPtr<ID3D12PipelineState> pipeline;
    ComPtr<ID3D12CommandAllocator> allocator;
    ComPtr<ID3D12GraphicsCommandList> list;
    ComPtr<ID3D12Fence> fence;
    ComPtr<ID3D12CommandQueue> queue;
    HANDLE event=nullptr;
    bool submitted=false,signaled=false,completed=false;
    ~Frame() {
        /* Never destroy command allocators or render targets while GPU is
         * using them. This blocking cleanup is ONLY for a diagnostic test. */
        if(submitted && signaled && !completed && fence && event) {
            if (fence->GetCompletedValue()!=UINT64_MAX &&
                SUCCEEDED(fence->SetEventOnCompletion(1,event))) {
                (void)WaitForSingleObject(event,INFINITE);
            }
        }
        if(event) CloseHandle(event);
    }
};

bool validate_source(const ShytNativeFlver2AssetV363& source,
                     const shyt_native_v367::UploadedModelV367& model,
                     uint32_t* stride) noexcept {
    if(!stride||!source.flver||!source.flver_bytes||!model.gpu_buffer ||
       !model.fence||model.vertices.size()!=1||model.indices.size()!=1||
       model.draws.size()!=1) return false;
    ShytNativeGpuUploadCountsV364 counts{};
    if(!shyt_native_flver2_gpu_requirements_v364(&source,&counts)||
       counts.vertex_buffers!=1||counts.index_buffers!=1||counts.draws!=1||
       counts.staging_bytes_total!=model.bytes) return false;
    ShytNativeGpuVertexSpanV364 vb{};
    ShytNativeGpuIndexSpanV364 ib{};
    ShytNativeGpuDrawV364 draw{};
    ShytNativeGpuUploadCountsV364 plan{};
    if(!shyt_native_flver2_gpu_plan_v364(&source,&vb,1,&ib,1,&draw,1,
                                        model.bytes,&plan) ||
       plan.staging_bytes_total!=model.bytes) return false;
    if(vb.buffer_index!=0||vb.vertex_count!=3||
       (vb.vertex_stride!=12&&vb.vertex_stride!=36&&vb.vertex_stride!=44)||
       ib.index_count!=3||ib.index_element_bytes!=2||ib.triangle_strip!=0||
       draw.mesh_index!=0||draw.face_set_index!=0||draw.vertex_buffer_count!=1||
       draw.vertex_buffer_indices[0]!=0||draw.vertex_count!=3) return false;
    ShytNativeFlver2VertexLayoutV371 layout{};
    if(!shyt_native_flver2_vertex_layout_v371(source.flver,source.flver_bytes,
          0,&layout)||layout.vertex_count!=vb.vertex_count||
       layout.stride!=vb.vertex_stride||layout.data_offset!=vb.source_offset||
       !layout.member_count||layout.members[0].semantic!=0||
       layout.members[0].type!=2||layout.members[0].semantic_index!=0||
       layout.members[0].offset!=0||!(layout.present&SHYT_V371_POSITION))
       return false;
    /* Preflight NaN/Inf before issuing any GPU commands, but do not build
     * a new float3 VB; WARP fetches the packed source VB directly. */
    ShytNativeFlver2VertexV371 decoded[3]{};
    if(!shyt_native_flver2_decode_vertices_v371(source.flver,
        source.flver_bytes,0,0,3,decoded,3)) return false;
    const auto base=model.gpu_buffer->GetGPUVirtualAddress();
    if(!base||vb.staging_offset>UINT64_MAX-base||
       ib.staging_offset>UINT64_MAX-base||
       model.vertices[0].BufferLocation!=base+vb.staging_offset||
       model.vertices[0].StrideInBytes!=vb.vertex_stride||
       model.vertices[0].SizeInBytes!=vb.bytes||
       model.indices[0].BufferLocation!=base+ib.staging_offset||
       model.indices[0].SizeInBytes!=ib.bytes||
       model.indices[0].Format!=DXGI_FORMAT_R16_UINT||
       model.draws[0].mesh_index!=draw.mesh_index||
       model.draws[0].material_index!=draw.material_index||
       model.draws[0].face_set_index!=draw.face_set_index||
       model.draws[0].vertex_buffer_count!=draw.vertex_buffer_count||
       model.draws[0].vertex_buffer_indices[0]!=0||
       model.draws[0].vertex_count!=draw.vertex_count)
       return false;
    *stride=layout.stride;
    return true;
}

bool compile_shader(const char* entry,const char* target,ID3DBlob** out) {
    ComPtr<ID3DBlob> errors;
    const HRESULT hr=D3DCompile(kHLSL,sizeof(kHLSL)-1,nullptr,nullptr,nullptr,
      entry,target,D3DCOMPILE_OPTIMIZATION_LEVEL3,0,out,&errors);
    return SUCCEEDED(hr)&&*out;
}

bool make_pipeline(ID3D12Device* device,Frame& f,uint32_t stride) {
    ComPtr<ID3DBlob> vs,ps,root_blob,error_blob;
    if(!compile_shader("VSMain","vs_5_1",&vs)||
       !compile_shader("PSMain","ps_5_1",&ps)) return false;
    D3D12_ROOT_SIGNATURE_DESC root_desc{};
    root_desc.Flags=D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT;
    if(FAILED(D3D12SerializeRootSignature(&root_desc,
        D3D_ROOT_SIGNATURE_VERSION_1,&root_blob,&error_blob))||
       FAILED(device->CreateRootSignature(0,root_blob->GetBufferPointer(),
        root_blob->GetBufferSize(),IID_PPV_ARGS(&f.root))))return false;
    D3D12_INPUT_ELEMENT_DESC element{};
    element.SemanticName="POSITION";
    element.SemanticIndex=0;
    element.Format=DXGI_FORMAT_R32G32B32_FLOAT;
    element.InputSlot=0;
    element.AlignedByteOffset=0;
    element.InputSlotClass=D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA;
    element.InstanceDataStepRate=0;
    D3D12_GRAPHICS_PIPELINE_STATE_DESC pso{};
    pso.pRootSignature=f.root.Get();
    pso.VS={vs->GetBufferPointer(),vs->GetBufferSize()};
    pso.PS={ps->GetBufferPointer(),ps->GetBufferSize()};
    pso.InputLayout={&element,1};
    pso.RasterizerState.FillMode=D3D12_FILL_MODE_SOLID;
    pso.RasterizerState.CullMode=D3D12_CULL_MODE_NONE;
    pso.RasterizerState.FrontCounterClockwise=TRUE;
    pso.RasterizerState.DepthClipEnable=TRUE;
    pso.BlendState.RenderTarget[0].RenderTargetWriteMask=D3D12_COLOR_WRITE_ENABLE_ALL;
    pso.DepthStencilState.DepthEnable=FALSE;
    pso.DepthStencilState.StencilEnable=FALSE;
    pso.SampleMask=UINT_MAX;
    pso.PrimitiveTopologyType=D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
    pso.NumRenderTargets=1;
    pso.RTVFormats[0]=kColor;
    pso.SampleDesc.Count=1;
    /* The D3D12 input descriptor's effective stride is the VB view
     * bound at draw time, not PSO creation. Validate our accepted values. */
    if(stride!=12&&stride!=36&&stride!=44)return false;
    return SUCCEEDED(device->CreateGraphicsPipelineState(&pso,
                                                          IID_PPV_ARGS(&f.pipeline)));
}

bool allocate_frame(ID3D12Device* device,Frame& f,UINT64* bytes,
                    D3D12_PLACED_SUBRESOURCE_FOOTPRINT* footprint) {
    if(!bytes||!footprint)return false;
    D3D12_RESOURCE_DESC tex{};
    tex.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;
    tex.Width=kW;tex.Height=kH;tex.DepthOrArraySize=1;tex.MipLevels=1;
    tex.Format=kColor;tex.SampleDesc.Count=1;
    tex.Layout=D3D12_TEXTURE_LAYOUT_UNKNOWN;
    tex.Flags=D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET;
    D3D12_CLEAR_VALUE clear{};
    clear.Format=kColor;clear.Color[3]=1.0f;
    const auto props=heap(D3D12_HEAP_TYPE_DEFAULT);
    if(FAILED(device->CreateCommittedResource(&props,D3D12_HEAP_FLAG_NONE,
       &tex,D3D12_RESOURCE_STATE_RENDER_TARGET,&clear,
       IID_PPV_ARGS(&f.texture))))return false;
    D3D12_DESCRIPTOR_HEAP_DESC rtv{};
    rtv.Type=D3D12_DESCRIPTOR_HEAP_TYPE_RTV;
    rtv.NumDescriptors=1;
    if(FAILED(device->CreateDescriptorHeap(&rtv,IID_PPV_ARGS(&f.rtv))))return false;
    device->CreateRenderTargetView(f.texture.Get(),nullptr,
                                   f.rtv->GetCPUDescriptorHandleForHeapStart());
    device->GetCopyableFootprints(&tex,0,1,0,footprint,nullptr,nullptr,bytes);
    if(!*bytes||footprint->Footprint.RowPitch<kW*4||
       footprint->Footprint.RowPitch% D3D12_TEXTURE_DATA_PITCH_ALIGNMENT||
       *bytes>16ull*1024*1024)return false;
    const auto rbprops=heap(D3D12_HEAP_TYPE_READBACK);
    const auto rb=readback_desc(*bytes);
    return SUCCEEDED(device->CreateCommittedResource(&rbprops,
       D3D12_HEAP_FLAG_NONE,&rb,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,
       IID_PPV_ARGS(&f.readback)));
}

bool record(ID3D12Device* device,Frame& f,
            const shyt_native_v367::UploadedModelV367& model,
            const D3D12_PLACED_SUBRESOURCE_FOOTPRINT& footprint) {
    if(FAILED(device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,
       IID_PPV_ARGS(&f.allocator)))||
       FAILED(device->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,
       f.allocator.Get(),f.pipeline.Get(),IID_PPV_ARGS(&f.list))))return false;
    ID3D12GraphicsCommandList* list=f.list.Get();
    list->SetGraphicsRootSignature(f.root.Get());
    const D3D12_CPU_DESCRIPTOR_HANDLE rtv=f.rtv->GetCPUDescriptorHandleForHeapStart();
    static constexpr float clear[4]={0.f,0.f,0.f,1.f};
    list->OMSetRenderTargets(1,&rtv,FALSE,nullptr);
    list->ClearRenderTargetView(rtv,clear,0,nullptr);
    D3D12_VIEWPORT vp{};
    vp.Width=static_cast<float>(kW);vp.Height=static_cast<float>(kH);
    vp.MaxDepth=1.f;
    D3D12_RECT scissor{};
    scissor.right=kW;scissor.bottom=kH;
    list->RSSetViewports(1,&vp);
    list->RSSetScissorRects(1,&scissor);
    list->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    list->IASetVertexBuffers(0,1,model.vertices.data());
    list->IASetIndexBuffer(model.indices.data());
    list->DrawIndexedInstanced(3,1,0,0,0);
    D3D12_RESOURCE_BARRIER barrier{};
    barrier.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
    barrier.Transition.pResource=f.texture.Get();
    barrier.Transition.Subresource=D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;
    barrier.Transition.StateBefore=D3D12_RESOURCE_STATE_RENDER_TARGET;
    barrier.Transition.StateAfter=D3D12_RESOURCE_STATE_COPY_SOURCE;
    list->ResourceBarrier(1,&barrier);
    D3D12_TEXTURE_COPY_LOCATION destination{};
    destination.pResource=f.readback.Get();
    destination.Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;
    destination.PlacedFootprint=footprint;
    D3D12_TEXTURE_COPY_LOCATION source{};
    source.pResource=f.texture.Get();
    source.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;
    source.SubresourceIndex=0;
    list->CopyTextureRegion(&destination,0,0,0,&source,nullptr);
    return SUCCEEDED(list->Close());
}
} // namespace

bool draw_offscreen_verified_flver_v373(
    ID3D12Device* device,ID3D12CommandQueue* direct_queue,
    const ShytNativeFlver2AssetV363& source,
    const shyt_native_v367::UploadedModelV367& model,
    std::vector<uint8_t>* out) {
    if(!out)return false;
    out->clear();
    uint32_t stride=0;
    if(!same_device(device,direct_queue)||
       !validate_source(source,model,&stride))return false;
    try {
        Frame f;
        f.queue=direct_queue;
        UINT64 allocated=0;
        D3D12_PLACED_SUBRESOURCE_FOOTPRINT footprint{};
        if(!allocate_frame(device,f,&allocated,&footprint)||
           !make_pipeline(device,f,stride)||
           !record(device,f,model,footprint)||
           FAILED(device->CreateFence(0,D3D12_FENCE_FLAG_NONE,
                 IID_PPV_ARGS(&f.fence)))) return false;
        f.event=CreateEventW(nullptr,FALSE,FALSE,nullptr);
        if(!f.event)return false;
        ID3D12CommandList* lists[]={f.list.Get()};
        direct_queue->ExecuteCommandLists(1,lists);
        f.submitted=true;
        if(FAILED(direct_queue->Signal(f.fence.Get(),1)))return false;
        f.signaled=true;
        if(f.fence->GetCompletedValue()==UINT64_MAX)return false;
        if(FAILED(f.fence->SetEventOnCompletion(1,f.event)))return false;
        if(WaitForSingleObject(f.event,30000)!=WAIT_OBJECT_0)return false;
        if(f.fence->GetCompletedValue()==UINT64_MAX||
           f.fence->GetCompletedValue()<1)return false;
        f.completed=true;
        const UINT64 row_bytes=static_cast<UINT64>(kW)*4u;
        const UINT64 pitch=footprint.Footprint.RowPitch;
        const UINT64 src_end=footprint.Offset+pitch*(kH-1u)+row_bytes;
        if(src_end>allocated)return false;
        std::vector<uint8_t> rgba(static_cast<size_t>(kW*kH*4u));
        void* pixels=nullptr;
        D3D12_RANGE range{};
        range.Begin=static_cast<SIZE_T>(footprint.Offset);
        range.End=static_cast<SIZE_T>(src_end);
        if(FAILED(f.readback->Map(0,&range,&pixels))||!pixels)return false;
        const auto* base=static_cast<const uint8_t*>(pixels);
        const auto* src=base+footprint.Offset;
        for(unsigned y=0;y<kH;++y)
            std::memcpy(rgba.data()+static_cast<size_t>(y)*row_bytes,
                        src+static_cast<size_t>(y)*pitch,
                        static_cast<size_t>(row_bytes));
        const D3D12_RANGE no_write={0,0};
        f.readback->Unmap(0,&no_write);
        *out=std::move(rgba);
        return true;
    } catch(const std::bad_alloc&) {return false;}
}
} // namespace shyt_native_v373
