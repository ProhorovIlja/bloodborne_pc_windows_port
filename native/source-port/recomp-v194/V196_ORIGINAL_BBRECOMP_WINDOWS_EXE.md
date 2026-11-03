# Native V196: actual broad Bloodborne recompiler -> native Win64 EXE

**Verified source-only / synthetic generated code, NOT Bloodborne gameplay.**
This is the first end-to-end CI gate in our source-port line that runs the
**original public full** `bloodborne-native/bloodborne-recomp`
`tools/recomp/bbrecomp.c` generator, not merely ten locally hand-written
instruction grammars or a manually authored fake RcFunction table.

## Public, exact and inspectable evidence (2026-11-01)

- Source: [bloodborne-native/bloodborne-recomp](https://github.com/bloodborne-native/bloodborne-recomp)
  pinned at `8f31ec7c41f252730c6325d52647046baef7549f` (GPL-2.0+).
- Original compiler's `bbrecomp.c` Git blob:
  `f5032c9ead4988579e005af8a0a0ce4ba4ab66d8`.
- Its real x86 decoder: Zydis **v4.1.1** plus actual Zycore library,
  built and linked into the original generator. No fake Zydis interpreter.
- Native build-host fixes are source-locked in
  `recomp-v194/patch_upstream_linux_generator_v196.py`, applied only to a
  disposable clone: Linux compile must declare full `bbcpu.h`, GNU Linux
  thread and `Dl_info` APIs, use x86-64 CMPXCHG16B atomic support,
  and link the genuine `libm`, `dl` and `pthread` dependencies. Not
  part of the final Windows executable and not a proprietary code import.
- Entirely **invented** input (no Bloodborne bytes): five source x86-64
  instruction encodings, `mov rax,rdi`, `add rax,rsi`,
  `xor eax,eax`, `inc rax`, `mov rax,1`.
- Calls original upstream `bbrecomp --snippets`: output contains exactly
  five **real** generator-emitted C functions and an upstream `RcFunction`
  table. A guarded source checker rejects missing functions, invalid table
  contents, executable-path interpreter fallbacks and unknown guest imports.
  Upstream emits a cold generic `L_dispatch` that names `rc->tail/bail`;
  this is unreachable for these straight-line synthetic inputs, and the
  callback hooks are fail-fast in the executable.
- The generated C, real Zydis header set and pinned upstream source are
  passed to an isolated Windows Server 2022 job; its complete original
  `src/recomp/rc.h` has our source-locked Windows QPC clock patch (V195),
  while other existing Win64 ABI fields remain source-checked (V194).
- **Actual Clang-generated AMD64 PE EXE** statically compiles and links
  `bbrecomp`'s generated synthetic C with the independent
  `bbrecomp_generated_host_v196.c`; invokes five different C functions,
  compares register outputs, guest RIP and stack effects, and confirms that
  the program **refuses** an `--eboot` runtime argument. The Linux native
  executable executes the same generated C.
- **Both GitHub Actions jobs completed successfully:**
  [V196 full original generator -> Linux + Windows CI](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41252201178).
  No private game images, game-derived output, generated proprietary code
  or original assets were in GitHub Actions/artifacts.

## Strict limits and WHY this matters

This proves, for five invented instruction forms, the pipeline:

`synthetic x86-64 bytes -> ORIGINAL pinned bbrecomp + REAL Zydis -> generated portable C -> original RcApi v4/complete BbCpu -> Windows-native PE EXE -> executed native C instructions`.

There is **no PS4 EBOOT or ELF loaded at process runtime**. This is the
desired final *code-build shape*, but not yet an executable Bloodborne.
The input is tiny; it avoids imports, branches, original-world pointers,
threads, SSE/AVX interaction, OS exceptions, game state and engine graphics.

The upstream broader program can emit many functions, but it **still**
contains 0.9% of translated instructions that fall back to `rc->step`,
`rc->bail`, `rc->call` and the upstream PS4-shaped runtime. The target
cannot retain those dependencies. The next work must:

1. Run exact **PRIVATE original 1.09** `bbrecomp` on a full function table,
   compile real generated **Windows** game C in shards, and verify actual
   original-code function hashes/entry, call dispatch and replay against
   real original x86. Keep every derived file private/out of git.
2. Convert direct/tail/indirect calls, memory, TLS, imports, AVX/FPU, x87,
   windows SEH, data relocations and async threads to native Win64
   dispatch. Source-verified bail/step availability is not a final game
   runtime: eliminate/fail closed on fallback before shipping.
3. Replace PS4 kernel/graphics/audio/save/media interfaces with native
   Windows engine implementations; no generic PS4 compatibility layer
   or mandatory decrypted executable at runtime.
4. Reach **real offline** splash, title, character creator, Iosefka,
   Hunter's Dream, all areas, main game, DLC, chalices, NG+, endings,
   full save compatibility and real hardware/stability testing.
5. Only afterward adapt optional seamless co-op, hybrid secure P2P,
   friends/invites/invasions, native dedicated server, native polished
   launcher/installer and gameplay QoL.

Read [NO_EBOOT_WINDOWS_NATIVE_TARGET.md](../NO_EBOOT_WINDOWS_NATIVE_TARGET.md)
for final acceptance. All future upstream findings must first answer
**which verified step toward a full independent Windows game they unblock**.

No merge, Fornex, production deploy, public retail game file or misleading
assertion of finished native gameplay. Draft PR #84 remains research.
