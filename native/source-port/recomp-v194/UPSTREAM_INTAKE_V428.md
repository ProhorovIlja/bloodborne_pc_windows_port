# Native port: upstream intake and asset-layout preflight

The strict build target is Windows/Linux x64 and macOS arm64, with owner-local AOT preparation. Neither the PS4 executable nor PS4 library code may execute at runtime. Existing compatible runtimes can supply tests or adapted components; their ability to launch does not satisfy this gate.

## Reviewed candidates (2026-11-13)

| Source | Candidate | Decision and acceptance test |
|---|---|---|
| [bloodborne-runtime #7](https://github.com/bloodborne-native/bloodborne-runtime/pull/7), merged at `14736cb3261ec1e137240a41fc02693484991ffc` | Host-side math and wide-string paths that avoid retail libc execution. | Prioritize as missing imports are exercised. PS4 code units are 16-bit: don't bind to platform `wchar_t`. Test unsigned comparisons, bounded guest memory and invalid ranges on all three hosts. |
| [bloodborne-recomp #12](https://github.com/bloodborne-native/bloodborne-recomp/pull/12), merged at `a5aab0590c0eddaa4f4356150d9a687333755368` | Less register copying at generated call boundaries. | Candidate for an isolated emitter backport. Includes dependencies on #10 and #11; do not import fast paths that bypass VM pin, ownership or memory filters. Differential replay first; benchmark only after correctness. |
| [Supermedo #169](https://github.com/Supermedo/bloodborne_pc/pull/169), open, head `c2b6b8032b98ef9909fb9a01d7b6286834c1167f` | Read-only owner inputs, transactional cache and headless preparation. | Reuse preparation and rollback ideas, not executable-link or launch assumptions. Test interrupted preparation and a launch with the source executable and console modules unavailable. |
| [Mrsuss60 #190](https://github.com/Mrsuss60/bloodborne_pc_windows_port/pull/190), merged at `34e567b9e4f8ffdfd29f2a5c1510c8a2d58f7df0` | Stencil-only UI mask routing. | Regression case: quick-item and loading icons at non-default resolution with upscaling off. Adapt only to the actual renderer. |
| [droogie/bbhost #244](https://github.com/droogie/bbhost/pull/244), open, head `17e8ecf3c65f0f26fb9273856c7e9b3343a252c8` | Populate Linux direct-memory pages before host-pointer import. | Compare time to first frame and peak memory on affected iGPU path. Do not force eager population globally. |
| [bmy/bbport-mac #8](https://github.com/bmy/bbport-mac/pull/8), closed/unmerged, head `827e27c540eece5b0fe2d478b9435d1cb042c72f` | Command-buffer retention stress test and driver revision. | Use a long-running allocation regression test; only apply driver change if that backend and failure are reproduced. |
| [bloodborne-runtime #12](https://github.com/bloodborne-native/bloodborne-runtime/pull/12), closed/unmerged, head `872ee9bd337656c78aae928830e3c93c1d108777` | Metal render-pass split and encoder-wait reductions. | Review independently from Vulkan changes. Require capture parity and resource hazards tests before reducing synchronization. |
| [shadPS4 #5709](https://github.com/shadps4-emu/shadPS4/pull/5709), open, head `dfccb74b3eaf04b1f4738286b81bbdd1e6d291f1` | macOS semaphore timeout overflow. | Use timeout-boundary cases for eventual host wait adapter. This is not a fix for the current mutex-attribute callsite. |
| [visy #34](https://github.com/visy/bloodborne_pc_windows_port/pull/34), merged at `c12fd51ea4fc842631e71317708087e2336bdff9` | LAN compatibility labels and join mismatch behavior. | Keep separate from strict startup. Use mismatch cases later; labels are not authentication. |
| [WitchyBND](https://github.com/ividyon/WitchyBND) | Independent reference for DCX, BND/BXF, TPF and related data. | Compare format metadata against owner-local reads; inspect licenses before reuse. Do not require users to unpack assets or ship retail samples for CI. |

No upstream code imported in this change. Upstream test figures are not this project's performance results. Review each actual diff and license, preserve notices and record source revision before any backport. A fork's default branch, an open PR and an unmerged experiment are not interchangeable.

## Asset gate

Run `python3 native/source-port/recomp-v194/check_asset_layout_v428.py --title-root <owner-local-title-folder>`. This read-only check looks for selected directory anchors and reports console executable/module paths separately. It doesn't read, copy, validate, or convert assets. Empty fixture directories can pass, and passing without console paths does not prove the game can run. The next real asset gate is to read one representative archive and enumerate its metadata, then load the first map without mutating the source tree.

Startup baseline remains V427. First reproduce the ordinal 953 mutex-attribute refusal and verify its import, exact callsite, temporary slot and native object binding before admitting it. The next boot gate remains process entry through main with a real content read and no PS4 executable or PS4 modules loaded.
