# V16 Native 3D Map Safety

Pinned source: lKaniel/bloodborne-server @ 77e350743a7cb4524cfcc1782fb6e3af64e25b15, `bbport/gpu/shim/bbport_map_3d.cpp`.

Prevents resource leakage if a VMA buffer allocation succeeds without a mapped pointer; frees map render targets if ImGui Vulkan descriptor allocation fails; refuses reuse without a descriptor; validates chart sizes and finite viewport dimensions before GPU work. The 4096-pixel bound applies only to the optional 3D map viewport, not gameplay rendering resolution. The patch never applies itself to a binary and refuses changed upstream anchors.

Verification: `python -m unittest discover -s tools/poc/yharnam/map-safety-v16 -v`. Integration: `unified-v9/compose_sources.py` after V14. Complete Windows game runtime not yet tested. No changes to Fornex or production co-op.

Licensed GPL-2.0-or-later, aligned with the original implementation.
