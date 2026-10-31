# V192: direct interprocedural CALL verification from real private Bloodborne 1.09

**Status:** limited genuine game-code proof, not a game/engine or full static recompiler. Designed for the true Windows PC-port track, not the bbport PS4-executable compatibility host. Derived game code and original assets MUST remain outside public GitHub, including Actions artifacts.

## What is verified privately (2026-11-01)

Read the original user's **private** Bloodborne `CUSA03173`, game update `APP_VER=01.09`, decrypted SCE ELF64. Existing V189 loaded-image verification requires the exact upstream-clean SHA256 `071df19c8880086d97182dbc057bc8cb37badaca57d9112683836b24a0444c0a`, with strict ELF bounds and 162,959 original EH-frame starts. Found **three pairs of original game functions**: one direct `CALL rel32` + 64-bit addition of the callee's immediate result; two direct `CALL rel32` + 32-bit sign-mask of the callee's zero result. Two original callee function bodies are verified independent leafs, reachable by **precisely correct** relative CALL from the original callers.

The original caller instructions have `push rbp; mov rbp,rsp`, `call`, real post-call instructions, `pop rbp; ret`, plus recognized NOP padding. To execute safely in isolation on Linux x86-64, the tool checks both original complete FDE ranges and changes **only the CALL rel32 relocation** when placing caller/callee in one newly created anonymous page. The page transitions RW to RX **before** execution, with no writable+executable mapping, no other game code, no external imports. This is a relocated original **instruction** execution test, not byte-for-byte execution at original image addresses; all original source bytes remain private. It repeats **216 original-caller CPU result+defined-flags differential comparisons** (72 inputs × 3), and **216 separately generated and native-compiled C comparisons**, with the callee marked `noinline` to preserve the native call boundary. PF/ZF/SF/CF/OF are compared, not undefined AF.

Same locally generated game C is compiled **privately** via V188 `clang-cl` AMD64 COFF and `lld-link /DLL` to a real PE32+ Windows DLL exporting `bb_recomp_init`, and disassembly verifies machine-code CALL instructions. **That private game-derived DLL has not executed on Windows**; Windows CI uses synthetic fixtures only. `RcApi`/`BbCpu` is still a tested prefix, not production-compatible complete upstream guest CPU state.

## Reproduce privately (Linux x86-64)

Use a local checkout of PR #83, without pushing any generated output:

```sh
mkdir -p /PRIVATE/new-empty-v192
python native/source-port/recomp-v192/call_graph_v192.py \
  --eboot /PRIVATE/Bloodborne/eboot.bin-decrypted \
  --private-output-dir /PRIVATE/new-empty-v192
```

Prints **only counts and boolean gates**, no game offsets, machine bytes, game-derived C or file paths. Never upload the original ELF, generated C, local `.so`, Windows PE DLL, original function addresses, stack traces, or assets to public GitHub. The private source output must be a new empty non-symlinked folder. Generated game code stays in that private directory. On a partial error, inspect/destroy the incomplete private folder yourself; no automatic deletion.

## CI and actual scope

Nine **synthetic-only** regression tests exercise strict caller/callee pattern validation, FDE-to-FDE link integrity, NOP vs hidden instruction refusal, unsafe target rejection, no source-folder overwrite, W^X execution on Linux x86-64 and native compiled C. On Windows Server 2022, two synthetic generated C source units go through `clang-cl` COFF + `lld-link` PE DLL, load under the actual Win64 process, run and unload safely.

**Not proved:** full x86 semantics, arbitrary calls/recursion/exception unwinding/stack data, real game event logic, Windows execution of the *private* game DLL, actual whole-game PE boot, native GX graphics, five real Yharnam Together hunters, secure NAT Direct P2P or 200-player QoS. Upstream compiler-scale progress must be measured separately and fairly: `bloodborne-recomp` and `Astrr00/BloodbornePC` can produce much more generated source, but their current full-game runtime still contains PS4-oriented compatibility components. Focus next on branch-and-call composition with independent verifiable stack/memory state and upstream generated-code ABI, rather than hand-encoding thousands of instruction forms.
