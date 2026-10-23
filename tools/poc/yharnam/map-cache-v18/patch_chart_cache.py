#!/usr/bin/env python3
"""V18: bounded CPU map cache and stoppable worker for pinned Yharnam source.

Only modifies bbport/gpu/shim/bbport_map_charts.cpp, fails closed on source drift.
"""
from pathlib import Path

PATH = 'bbport/gpu/shim/bbport_map_charts.cpp'
HEADER_PATH = 'bbport/gpu/shim/sh_map_cache.hpp'
HERE = Path(__file__).resolve().parent

def one(s: str, old: str, new: str, label: str, count: int=1) -> str:
    n=s.count(old)
    if n != count:
        raise ValueError(f'V18 {label}: expected {count} anchors, got {n}')
    return s.replace(old, new)

def transform(s: str) -> str:
    if 'SH-MAP-CACHE-V18' in s:
        raise ValueError('V18 already applied')
    s=one(s, '#include <deque>\n', '#include <deque>\n#include <exception>\n#include <stop_token>\n', 'headers')
    s=one(s, '#include "bbport_settings.h"', '#include "bbport_settings.h"\n#include "sh_map_cache.hpp"', 'local header')
    s=one(s,'std::condition_variable wake;', 'std::condition_variable_any wake;', 'stop-aware condition')
    s=one(s, 'bool worker_started = false;', '''// SH-MAP-CACHE-V18: the worker is declared last so its destructor stops
// and joins before the mutex, queue or cache storage is destroyed.
SeamlessHunt::MapCache::Budget cache_budget;
std::jthread worker;

std::size_t CacheSize(const BbMapArt::Chart& c) {
    return c.rgba.size() + c.labels.size()*sizeof(BbMapArt::Chart::Label) +
           c.storeys.roof.size()*sizeof(std::int16_t) +
           c.storeys.level.size()*sizeof(std::int16_t) +
           c.storeys.rgb.size()*sizeof(std::uint32_t);
}
std::size_t CacheSize(const BbMapArt::AreaMesh& m) {
    return m.positions.size()*sizeof(float) + m.colors.size()*sizeof(std::uint32_t) +
           m.indices.size()*sizeof(std::uint32_t);
}
// Called with mutex locked. Eviction only releases a cache-owned shared_ptr;
// an active map still holds its own shared_ptr and remains safe to render.
void CachePublish(std::uint32_t key, std::size_t bytes) {
    for (const std::uint32_t evicted : cache_budget.Record(key, bytes)) {
        if ((evicted & 7u) == MeshKey) {
            ready_meshes.erase(evicted & ~7u);
        } else {
            ready.erase(evicted);
        }
        asked.erase(evicted); // let Get() requeue a previously visited area
    }
}''', 'background ownership')
    s=one(s,
'''void Work() {
#ifdef _WIN32''',
'''void Work(std::stop_token stop) {
#ifdef _WIN32''', 'worker token')
    s=one(s,
'''            wake.wait(lock, [] { return !queue.empty(); });
            next = queue.front();''',
'''            if (!wake.wait(lock, stop, [] { return !queue.empty(); }) || stop.stop_requested())
                return;
            next = queue.front();''', 'wake shutdown')
    s=one(s,
'''            auto mesh = MakeMesh(next & ~7u);
            std::scoped_lock lock{mutex};
            if (mesh) {
                ready_meshes[next & ~7u] = std::move(mesh);''',
'''            std::shared_ptr<const BbMapArt::AreaMesh> mesh;
            try { mesh = MakeMesh(next & ~7u); }
            catch (const std::exception& e) { std::printf("Map: mesh worker error: %s\\n", e.what()); }
            if (stop.stop_requested()) return;
            std::scoped_lock lock{mutex};
            if (mesh) {
                const std::size_t bytes = CacheSize(*mesh);
                ready_meshes[next & ~7u] = std::move(mesh);
                CachePublish(next, bytes);''', 'mesh publish')
    s=one(s,
'''        auto chart = Make(next);
        std::scoped_lock lock{mutex};
        if (chart) {
            ready[next] = std::move(chart);''',
'''        std::shared_ptr<const BbMapArt::Chart> chart;
        try { chart = Make(next); }
        catch (const std::exception& e) { std::printf("Map: chart worker error: %s\\n", e.what()); }
        if (stop.stop_requested()) return;
        std::scoped_lock lock{mutex};
        if (chart) {
            const std::size_t bytes = CacheSize(*chart);
            ready[next] = std::move(chart);
            CachePublish(next, bytes);''', 'chart publish')
    s=one(s,
'''        return found->second;
    }
    if (packed_map != 0''',
'''        cache_budget.Touch(packed_map);
        return found->second;
    }
    if (packed_map != 0''', 'chart touch')
    s=one(s,
'''        return found->second;
    }
    const std::uint32_t key = packed_map | MeshKey;''',
'''        cache_budget.Touch(packed_map | MeshKey);
        return found->second;
    }
    const std::uint32_t key = packed_map | MeshKey;''', 'mesh touch')
    s=one(s,
'''        if (!worker_started) {
            worker_started = true;
            std::thread(Work).detach();
        }''',
'''        if (!worker.joinable()) worker = std::jthread(Work);''', 'start worker', 2)
    return s

if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args()
    if args.source.resolve()==args.output.resolve():p.error('refuses source overwrite')
    args.output.write_text(transform(args.source.read_text('utf-8')),encoding='utf-8')
