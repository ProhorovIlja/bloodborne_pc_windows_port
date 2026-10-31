# V190: real Bloodborne 1.09 memory, flags and scalar SSE leaf AOT

This is a strict, narrowly supported proof of independently compiling **six real functions** from the user's private original Bloodborne 1.09 game executable. The output is *not* a Windows Bloodborne game. The final PC title must eventually execute all game logic with independent Windows/PC services and a native GX renderer, without a PS4 ELF-derived image or PS4 system-call compatibility at runtime.

V190 builds on V189's clean Bloodborne 1.09 ELF64 loaded-image SHA-256 check, PT_GNU_EH_FRAME parsing and guarded CPU oracle, and V188's genuine Windows LLVM `clang-cl` → AMD64 COFF `.obj` → `lld-link` PE32+ DLL backend. **The original game executable is needed at private analysis/build time only**, and no proprietary bytes or derived code are distributed in this PR.

## First actual private-game results, 2026-11-01

- 6 actual 16-byte, FDE-bounded and exact-whitelisted original functions selected from the verified private CUSA03173 1.09 executable: 64-bit load from `[rdi + disp8]`, zero-extending 32-bit load, 64-bit store of `rsi`, `lea rax,[rdi+disp8]`, `vmovss xmm0,[rdi+disp8]`, and `test edi,edi; sete al` (with `ret`). **Only** these six specific instruction grammars are accepted. Subsequent bytes within the FDE interval must be canonical x86 alignment NOPs. Any negative or unsafe displacement, unknown instruction, branch, call, indirect jump, TLS, out-of-bounds access or non-NOP after ret is rejected.
- 204 actual direct CPU comparisons on Linux x86-64 against private game instructions executed from W^X pages. Tests compare register returns, full buffer contents after memory stores, IEEE-754 float32 bits, and **defined** CF/PF/ZF/SF/OF flags via a separate safe test wrapper. Unspecified AF intentionally not compared.
- 444 comparisons against independently **native Linux-compiled** C functions generated from those original inputs. The C uses bounded `__builtin_memcpy` for 4- and 8-byte unaligned memory, explicit AVX scalar load+upper-lane clearing, register masking and arithmetic flag semantics. Generated C is not a copied original game source file. Small experimental mock CPU layout is **not** equal to full upstream BbCpu.
- The same private generated C compiled to **two genuine Win64 AMD64 COFF objects** and linked as a valid **PE32+ DLL** with the expected `bb_recomp_init` export via the existing V188 compiler. **This private game-derived Windows DLL was not executed on Windows**; only its exported PE format was checked. Windows CI uses *synthetic instructions only*, never original game inputs or derived binaries.
- Both public Python generator and six synthetic tests passed locally on Linux. Windows CI must independently prove the same synthetic 6-form DLL execution, not private game execution.

## Reproduce with one's own legally obtained decrypted Bloodborne 1.09

```sh
# Linux x86-64 with Python 3.12 and clang. Directory must exist and be EMPTY.
mkdir -p /private/v190-generated
python native/source-port/recomp-v190/nontrivial_leaves_v190.py \
  --eboot /private/Bloodborne/eboot.bin-decrypted \
  --private-output-dir /private/v190-generated

# Windows x64 with clang-cl, lld-link, V187 header (user-local private build).
python native/source-port/recomp-v188/win64_coff_link_v188.py \
  --source-dir /private/v190-generated \
  --include-dir native/source-port/recomp-v187 \
  --out /private/v190-game-derived.dll
```

The CLI emits one bounded JSON summary containing *only* stage, six kinds, comparison counts and explicit **false** game-boot / Windows-private-module execution claims. Does not emit code, bytes, function addresses, private user paths or game memory contents. Never upload original ELF, generated C, DLL, source traces, offsets, private manifests or game assets to GitHub/CI. Keep generated outputs private.

## Boundaries and next decisions

- ✅ Original PS4 game image SHA, six exact original function entrypoints, CPU memory/SSE/defined flags compared on an actual x86-64 CPU, native compiled C results verified.
- ✅ The private derived C builds into real x64 Windows COFF + PE DLL, exported entrypoint verified.
- ⏳ Run CI synthetic Win64 DLL native execution; not a private game-derived Windows executable proof.
- ❌ No full BbCpu state, full 16 vector register semantics in live gameplay, cross-function control flow, stack unwinding, whole-game import binding, Windows engine runtime, GPU or boss fight.
- ❌ No standalone PS4-ELF-free Windows Bloodborne game, five-player live Yharnam Together session or measured secure WAN P2P.

Next pick **nontrivial original functions with branches, stack memory or multi-register SSE** with strictly bounded differential oracles. Compare approaches from bloodborne-recomp, Astrr00, Remill, bbhost, LanternEngine and Paleblood. Don't substitute simple proof counts for game progress.

## Public CPU register layout pin, added V190.1

The new `audit_upstream_cpu_layout_v190.py` checks the **first four fields** of upstream `BbCpu` in `bloodborne-native/bloodborne-recomp` commit `8f31ec7c41f252730c6325d52647046baef7549f`: sixteen `r[16]` general registers (0–127 bytes), `rip` (128), `flags` (136), and 16 `BbVec` registers at offset 144 (32-byte byte/f32 lanes). The emitted C has static prefix layout assertions. Four additional synthetic unit tests require exact field order and byte shape, fail on inserted fields/reordered registers/differently sized vectors. **This only proves the CPU-state prefix used by V190.** It does not replace a full ABI verification of the upstream `BbCpu`, interpreter/JIT state, stack, TLS or `RcApi` callbacks.
