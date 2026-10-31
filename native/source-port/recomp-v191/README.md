# V191: bounded forward CFG native AOT from private Bloodborne 1.09

**Research stage, not the game.** This module reads the user's *own* clean 1.09
`eboot.bin-decrypted`, validates the exact public original image SHA-256 via
V189, and selects six real EH-frame function entries containing conditional
branches. It reconstructs a strict instruction-level, forward-only control-flow
graph (CFG), checks all path targets and return-value definition, and produces
plain C for a real native compiled module. No PS4 executable is used at runtime
in this **small module test**. A complete native Windows Bloodborne does **not**
exist in this PR, and no original PS4 kernel/renderer system is removed.

The deliberately narrow x86 instruction whitelist is: `cmp edi, imm8`,
`test edi, edi`, `xor eax, eax`, `mov eax, imm32`, `mov eax, edi`,
`je`/`jne` forward rel8, `jmp` forward rel8, and `ret`. Every accepted
16/32/48-byte EH interval must have >=2 conditional branches, no backedges,
fully covered reachable bytecode, no jump into an instruction, complete
canonical NOP padding only, and assigned EAX on **every** returning path.

No stack instructions, calls, callbacks, dynamic libraries, FS/TLS, SSE/AVX,
unknown memory effects, loops or arbitrary opcodes are accepted in V191.
The earlier V190 handles *separate* whitelisted memory/SSE leaves. These
are complementary bounded prototypes, not a full disassembler or recompiler.

## Real private offline evidence (2026-11-01)

- The user's Bloodborne CUSA03173 1.09 original SCE ELF, 91,042,036-byte
  canonical reconstructed image, matched public clean-image SHA-256
  `071df19c8880086d97182dbc057bc8cb37badaca57d9112683836b24a0444c0a`.
- Existing V189 FDE scanner identified 162,959 entries. A strictly validated
  source-code CFG finder found eight functions of the supported class and
  selected **six distinct real functions**: four 48-byte and two 32-byte
  frames, 10–14 reachable instructions per frame, several return paths.
- Direct execution of the original *private* machine code from W^X pages on
  Linux AMD64 matched **702 / 702** results, including the five defined flags
  CF, PF, ZF, SF, OF (not AF). The original code is never printed or saved
  in public source.
- Privately generated C compiled to a native Linux shared object, executed
  through the public RcApi-v4-shaped ABI, matched **702 / 702** results.
- The *same private game-derived C* compiled into two true AMD64 COFF `.obj`
  units and an AMD64 PE32+ DLL, with `bb_recomp_init` export verified. The
  private Windows DLL was **not executed on Windows**. Public Windows CI
  runs **synthetic instructions only**, not these game-derived functions.
- All eight synthetic-only local tests passed (including Linux W^X original
  byte oracle and compiled-C differential checks). This is a real game-code
  branch recompilation *micro-proof*, **not evidence of an actual game boot**.

## Reproduce privately, without distributing game files

Place the V187, V188, V189 and V190 source-port research modules in sibling
folders as done in the stacked PRs. Use a **new, empty private output folder**:

```sh
python native/source-port/recomp-v191/branch_cfg_v191.py \
  --eboot /private/Bloodborne/eboot.bin-decrypted \
  --private-output-dir /private/build/v191-generated
```

The tool prints only bounded summary counts and refuses invalid inputs or source
code. It writes two **private** generated translation units. Use V188 locally
for a Windows COFF/PE DLL if desired. Do not commit generated C, binaries,
per-function addresses, private traces or the original game. The public CI
uses only synthetic hand-assembled fixture bytes, and links an actual Windows
DLL from those synthetic bytes without retail assets.

**Scope/nonclaims:** V191's `BbCpu` is an explicitly tested **prefix subset**
of the full upstream state, not a verified complete ABI. It does not verify
game physics, event logic, boss behavior, saves, rendering, native GX, Win32
runtime services, online, Direct P2P or five-player co-op. Next: real stack
prologues and safe inter-function calls with address relocation and return
address semantics; then expand to source-locked high-coverage upstream
recompilers and native engine services. Stacked under Draft #81; no Fornex
change, no merge and no game distribution.
