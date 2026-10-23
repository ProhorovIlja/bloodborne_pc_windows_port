// V14: opt-in, bounded, passive long-session diagnostics. Not an automatic cache purge.
namespace ShPerformance {
bool enabled=false;
SeamlessHunt::Perf::Watch history;
std::uint64_t WorkingSetBytes(){
#ifdef _WIN32
    // Dynamic lookup avoids requiring an additional Psapi.lib dependency.
    using Query=BOOL (WINAPI*)(HANDLE, PPROCESS_MEMORY_COUNTERS, DWORD);
    static const auto query=reinterpret_cast<Query>(
        GetProcAddress(GetModuleHandleA("kernel32.dll"),"K32GetProcessMemoryInfo"));
    PROCESS_MEMORY_COUNTERS value{};
    value.cb=sizeof(value);
    return query&&query(GetCurrentProcess(),&value,sizeof(value))
        ?static_cast<std::uint64_t>(value.WorkingSetSize):0;
#else
    std::ifstream statm("/proc/self/statm");
    std::uint64_t total=0,resident=0;
    if(!(statm>>total>>resident))return 0;
    return resident*static_cast<std::uint64_t>(sysconf(_SC_PAGESIZE));
#endif
}
void Draw(unsigned map,float present_frame_ms,int textures){
    if(!enabled)return;
    const auto now=std::chrono::steady_clock::now();
    const auto ms=std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()).count();
    if(ms>0&&(history.Size()==0||ms-history.Latest().timestamp_ms>=10000)){
        SeamlessHunt::Perf::Sample s;
        s.timestamp_ms=ms;s.map_id=map;s.frame_ms=present_frame_ms;
        s.process_bytes=WorkingSetBytes();
        s.image_bytes=BbStats::live_image_bytes.load(std::memory_order_relaxed);
        s.live_images=BbStats::live_images.load(std::memory_order_relaxed);
        s.gpu_bytes=BbStats::vk_image_bytes.load(std::memory_order_relaxed);
        s.gc_freed=BbStats::gc_freed_images.load(std::memory_order_relaxed);
        s.gc_used_bytes=BbStats::gc_used_bytes.load(std::memory_order_relaxed);
        s.gc_trigger_bytes=BbStats::gc_trigger_bytes.load(std::memory_order_relaxed);
        s.gc_critical_bytes=BbStats::gc_critical_bytes.load(std::memory_order_relaxed);
        s.gc_kept=BbStats::gc_kept_images.load(std::memory_order_relaxed);
        if(history.Add(s)&&history.Size()%6==0){
            const auto trend=history.Compare();
            std::printf("SH-PERF: map=%08x frame=%.2fms rss=%lluMiB gpuimg=%lluMiB images=%llu gc_freed=%llu samples=%u drift_ms=%.1f%% rss_drift=%lldMiB gpu_drift=%lldMiB gc_used=%lluMiB gc_trigger=%lluMiB gc_critical=%lluMiB gc_kept=%llu gc_used_drift=%lldMiB\n",
                s.map_id,s.frame_ms,static_cast<unsigned long long>(s.process_bytes/1048576),
                static_cast<unsigned long long>(s.gpu_bytes/1048576),
                static_cast<unsigned long long>(s.live_images),
                static_cast<unsigned long long>(s.gc_freed),history.Size(),
                trend.comparable?trend.frame_percent:0.f,
                static_cast<long long>(trend.rss_mib_delta),
                static_cast<long long>(trend.gpu_mib_delta),
                static_cast<unsigned long long>(s.gc_used_bytes/1048576),
                static_cast<unsigned long long>(s.gc_trigger_bytes/1048576),
                static_cast<unsigned long long>(s.gc_critical_bytes/1048576),
                static_cast<unsigned long long>(s.gc_kept),
                static_cast<long long>(trend.gc_used_mib_delta));
        }
    }
    if(history.Size()==0)return;
    const auto& sample=history.Latest();
    const auto trend=history.Compare();
    ImGui::SetNextWindowPos(ImVec2(12.0f*base_scale,50.0f*base_scale),ImGuiCond_Always);
    ImGui::SetNextWindowBgAlpha(0.68f);
    ImGui::Begin("##sh-session-perf",nullptr,
        ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_AlwaysAutoResize|
        ImGuiWindowFlags_NoInputs|ImGuiWindowFlags_NoNav|
        ImGuiWindowFlags_NoFocusOnAppearing|ImGuiWindowFlags_NoSavedSettings);
    ImGui::TextUnformatted("Seamless Hunt: Session Monitor [F9]");
    ImGui::Text("Frame %.1f ms (present) | Map %08X",sample.frame_ms,sample.map_id);
    ImGui::Text("Working set %llu MiB | Vk images %llu MiB",
        static_cast<unsigned long long>(sample.process_bytes/1048576),
        static_cast<unsigned long long>(sample.gpu_bytes/1048576));
    ImGui::Text("Live images %llu | GC freed %llu | ImGui textures %d",
        static_cast<unsigned long long>(sample.live_images),
        static_cast<unsigned long long>(sample.gc_freed),textures);
    ImGui::Text("GC effective usage %llu MiB | trigger %llu | critical %llu",
        static_cast<unsigned long long>(sample.gc_used_bytes/1048576),
        static_cast<unsigned long long>(sample.gc_trigger_bytes/1048576),
        static_cast<unsigned long long>(sample.gc_critical_bytes/1048576));
    ImGui::Text("GC kept %llu | Registered image bytes %llu MiB",
        static_cast<unsigned long long>(sample.gc_kept),
        static_cast<unsigned long long>(sample.image_bytes/1048576));
    if(trend.comparable){
        ImGui::Text("Same-map trend: frame %+.0f%% | RAM %+lld MiB | GPU %+lld MiB",
            trend.frame_percent,static_cast<long long>(trend.rss_mib_delta),
            static_cast<long long>(trend.gpu_mib_delta));
        ImGui::Text("GC usage change %+lld MiB (not total dedicated VRAM)",
            static_cast<long long>(trend.gc_used_mib_delta));
        if(trend.slowdown||trend.process_growth||trend.gpu_growth)
            ImGui::TextUnformatted("Long-session drift suspected. Capture the SH-PERF log.");
    }else{
        ImGui::TextUnformatted("Collecting ~2 min of same-map observations...");
    }
    ImGui::End();
}
} // namespace ShPerformance
