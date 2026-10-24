# Seamless Hunt native source audit V20

This audit found a defect in live map and launcher map preparation: archive range reads allocated a buffer from untrusted metadata prior to file-size validation. V20 adds bounded exact reads in both code paths.

The same audit caught a potential long-session VRAM regression in the earlier V17 patch: treating the sticky `scene_proxy` flag as proof of current GPU use. The V17 guard has been corrected to rely on actual bindings/targets instead.

V18–V20 compose in order on the same native `bbport_map_charts.cpp` source. The latest branch and tests are at tools/poc/yharnam.

Status: individual source tests and C++20 helper compilation passed, but **no full Windows game build or proof of a fixed VRAM leak**. No production co-op server touched.

See tools/poc/yharnam/map-range-v20/README.md for exact tests and compatibility considerations.
