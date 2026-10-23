import unittest
from patch_chart_cache import transform

SOURCE='''#include <deque>
#include "bbport_settings.h"
std::condition_variable wake;
bool worker_started = false;
void Work() {
#ifdef _WIN32
    x;
#endif
            wake.wait(lock, [] { return !queue.empty(); });
            next = queue.front();
            auto mesh = MakeMesh(next & ~7u);
            std::scoped_lock lock{mutex};
            if (mesh) {
                ready_meshes[next & ~7u] = std::move(mesh);
        auto chart = Make(next);
        std::scoped_lock lock{mutex};
        if (chart) {
            ready[next] = std::move(chart);
        return found->second;
    }
    if (packed_map != 0
        return found->second;
    }
    const std::uint32_t key = packed_map | MeshKey;
        if (!worker_started) {
            worker_started = true;
            std::thread(Work).detach();
        }
        if (!worker_started) {
            worker_started = true;
            std::thread(Work).detach();
        }
'''
class Tests(unittest.TestCase):
    def test_worker_and_cache(self):
        s=transform(SOURCE)
        for needle in ['std::jthread worker','std::condition_variable_any wake','wake.wait(lock, stop','CachePublish(next, bytes)','cache_budget.Touch(packed_map)', 'asked.erase(evicted)']:
            self.assertIn(needle,s)
        self.assertEqual(s.count('std::jthread(Work)'),2)
        self.assertNotIn('.detach()',s)
    def test_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'stop-aware condition'):
            transform(SOURCE.replace('std::condition_variable wake;','std::condition_variable wakeX;'))
        with self.assertRaisesRegex(ValueError,'already applied'):
            transform(transform(SOURCE))
    def test_does_not_mutate_input(self):
        s=SOURCE
        transform(s)
        self.assertEqual(s,SOURCE)
if __name__=='__main__':unittest.main()
