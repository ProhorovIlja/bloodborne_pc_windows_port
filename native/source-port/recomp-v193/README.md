# V193: bulk native AOT of verified short Bloodborne 1.09 game functions

**A genuine but very limited game-code recompilation experiment, NOT a playable Windows-native Bloodborne port.** This step scales the previous exact-whitelist V189/V190 leaf probes instead of claiming that three more functions are an engine. The original user's 1.09 game executable, derived C, generated function addresses and private DLL remain PRIVATE. No retail bytes, source generated from them, artifacts or private manifests are published to GitHub.

## Real verified evidence, 2026-11-01, private source

- Input is the actual user's private `CUSA03173 / APP_VER=01.09` decrypted Bloodborne SCE ELF64; V189 rejects a nonmatching canonical **91,042,036-byte** loaded image SHA256 unless exactly `071df19c8880086d97182dbc057bc8cb37badaca57d9112683836b24a0444c0a`.
- Original `.eh_frame_hdr` reports **162,959 function starts**, yielding **162,958 complete start-to-next-start intervals**. These are FDE-oriented *candidate intervals*, not an exhaustive semantically correct function inventory (the last interval lacks a next boundary; other functions may exist without FDEs). 80,883 intervals were <=64 bytes.
- **9,955** exact 16-byte intervals matched one of **10 fail-closed x86 instruction grammars**, with complete canonical NOP tail validation: 1,554 `zero32`, 2,873 `imm32`, 169 `identity64`, 1 `identity32`, 3,355 `mem64`, 573 `mem32`, 108 `store64`, 1,256 `lea64`, 65 `sse32`, 1 `flags_eq32`. This is **6.1% of counted FDE starts**, not 6.1% of all game instructions or game completion.
- The private batch generator emitted **32 C function units** (320 functions max each) plus a real v4 `RcFunction` table, **9,955 function entries** and a private SHA256 source manifest, totaling ~2.3 MB of C; each entry is freshly revalidated against the full verified original image before any file is written.
- The C built into a **native Linux ELF shared library** (~3.0 MB) with clang. Every one of the 9,955 functions was invoked from that native C library **once** with a deterministic pseudo-random or controlled test input and its modeled output/memory side effects checked: **9,955 / 9,955 PASS**. This is not full formal equivalence or all flags/inputs checked.
- **Original game's x86-64 machine code** independently executed in isolated Linux W^X pages **once for every one of the 9,955 exact-whitelist functions**, and return values + memory side effects checked: **9,955 / 9,955 PASS**. The blanket batch test does **not** independently check all defined RFLAGS for each function, nor AVX high lanes; previous bounded V190 samples independently checked defined flags and vector semantics. No arbitrary original PS4 imports/calls/branches were executed: only precisely decoded no-call/leaf instruction forms.
- The SAME game-derived C compiled using **clang-cl** to **33 genuine AMD64 COFF objects**, then **lld-link** to a private PE32+ Windows DLL (~547 KB) exporting `bb_recomp_init`. Export checked. **Private game-derived Windows DLL not executed on Windows** yet, no claim of game boot.

The generic source file contains only *instruction grammar encoders*; actual addresses/constant values are emitted and kept locally. No game's original executable, private generated C, original instruction bytes, private Windows DLL or individual function addresses enter public source/CI.

## Reproduce PRIVATE original-game verification

Use a local checkout of Draft PR #84 containing the stacked V187-V192 source code; **use a brand-new empty private output directory**.

```sh
mkdir -p /PRIVATE/new-empty-bulk-v193
python native/source-port/recomp-v193/bulk_aot_v193.py \
  --eboot /PRIVATE/Bloodborne/eboot.bin-decrypted \
  --private-output-dir /PRIVATE/new-empty-bulk-v193 \
  --shard-size 320

python native/source-port/recomp-v188/win64_coff_link_v188.py \
  --source-dir /PRIVATE/new-empty-bulk-v193 \
  --include-dir native/source-port/recomp-v187 \
  --out /PRIVATE/new-parent/private-bb-leaf-v193.dll
```

**Never upload** `PRIVATE_DO_NOT_UPLOAD_manifest.json`, `recomp.c`, `recomp_*.c`, COFF, DLL, ELF, function offsets, or original game. Their mere names in this document do not authorize publication. The CLI prints **only category counts and boolean gates**. It does NOT itself execute original game bytes, which must be separately audited with the private differential-test oracle; only the read-only SHA/FDE/grammar validation and private source generation are in the public tool. This division avoids accidentally executing untrusted data in GitHub Actions.

## Public CI acceptance (synthetic only)

`test_bulk_aot_v193.py` uses ten entirely invented function bodies and tests malformed NOPs, unsafe pointer offsets, missing FDE boundaries, source revalidation, determinism, no overwrite of private output, safe manifest handling and **real C native module compilation/execution**. On Windows the fixture invokes `clang-cl` + `lld-link`, checks actual AMD64 COFF/PE32+ export using the proven V188 stage, loads/executes the 10-function DLL with the v4 ABI and unloads it. The fixture is **not** derived from the retail game. Upstream `RcApi v4` and partial `BbCpu` offset checks are inherited from V187/V190; full CPU ABI still missing.

## Experimental x86 guest return path (opt-in only)

The V193 leaf proof has a critical distinction from an upstream-runtime-usable module: the original `RcFunction` table currently records `hash=0`, while the actual `bloodborne-recomp` runtime recomputes `bbcpu_recomp_hash` and rejects mismatching game functions. The old test-only leaves also returned to their **host C caller** without performing the guest x86-64 `RET`: popping the guest return address from `RSP`, advancing `RSP` by eight, and setting guest `RIP`. These facts mean the old DLL must **not** be described as loadable game code, even if it compiles.

The optional `--guest-return-prototype` switch now emits that specific guest return operation after the verified leaf body. It assumes an already validated/mapped guest stack, and Windows and Linux synthetic-only native tests exercise the stack/RIP effects for all ten patterns. It does **not** compute the upstream original-code hashes or implement guest memory, calls, imports, exceptions, a full `BbCpu` ABI, or runtime integration. Output explicitly reports `upstream_code_hashes_ready=false` and remains private. The default remains the old test-only return behavior to preserve the existing private batch results and tests. Do not promote the opt-in prototype to a production module.

### Strict-leaf FNV hash prototype (also opt-in)

The newly reviewed upstream code `bloodborne-native/bloodborne-recomp` `src/cpu/recomp.c` (blob `2e005442`) defines `bbcpu_recomp_hash` as a 64-bit FNV-1a fold over the bytes of each decoded instruction. Its special `FS/GS` TCB-load substitution **does not occur** in the ten exact accepted V193 grammars. `src/cpu/decode.c` (blob `e3a84f80`) ends a basic block at `RET`, then the hash continues at the following fully validated NOP instructions. Consequently a completely decoded, exact 16-byte V193 frame can be provisionally hashed by FNV-1a of all 16 original bytes.

Use **both** `--guest-return-prototype --upstream-hash-prototype` for this research-only mode. The generator rejects hash mode without guest RET, revalidates each original function's full bytes/FDE *before writing*, and places per-function hashes **only in private generated C**. The output prints just `upstream_hash_prototype=true`, while `upstream_code_hashes_ready=false` remains mandatory. Public synthetic Windows/Linux CI checks two pinned independent FNV reference vectors, altered inputs, rejected unknown instruction tails, each function's compiled `RcFunction.hash`, and actual guest stack/RIP effects.

**Not proven:** a direct independent comparison with upstream `bbcpu_recomp_hash` over the user's original full game image; non-16-byte/general game functions, runtime insertion or dispatch, whole `BbCpu`/unwind state, original Windows gameplay and any final native PC runtime. Do not use this optional table in a live game or claim it is upstream-runtime compatible. The default V193 output remains the historical zero-hash test DLL to preserve previous evidence.

The next acceptance gate is a true source-locked **live upstream Zydis/hash comparison on original unmodified game functions** (privately), then guest dispatch tests and a complete `BbCpu` layout check. Never use fabricated hashes to bypass that check.

## Not yet solved

These 9,955 functions use **10 very narrow leaf grammars**, almost all 16-byte FDE intervals; no general direct/indirect calls, loops, guest stack management, exception/TLS, full original CPU/AVX state, native gameplay subsystem, Windows game process, engine GX-native graphics, five-user Yharnam Together, secure NAT Direct P2P or QoS >=99% at 200 players. The path forward is to integrate and differential-test the **much broader real upstream game recompilers** `bloodborne-native/bloodborne-recomp` and `Astrr00/BloodbornePC`, rather than scaling 10 whitelisted templates indefinitely; then replace PS4 kernel/HLE and GNM hardware processing with native Win32/engine-level implementations.

No merge, production deployment or Fornex action. DRAFT.
