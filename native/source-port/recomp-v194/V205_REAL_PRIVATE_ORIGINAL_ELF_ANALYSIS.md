# V205: REAL private Bloodborne 1.09 ELF metadata, not synthetic code

**Status: actual user's private, decrypted Bloodborne executable FOUND,
downloaded to a private analysis container, and parsed.** Earlier
repeated statements that the user did not upload EBOOT were wrong.
Google Drive metadata search hid the root files, but directly fetching
the parent CUSA03173 folder confirmed BOTH
`eboot.bin-decrypted` and `eboot.bin`.

## Real original binary, exact observations

- Private decrypted `eboot.bin-decrypted`: **93,667,640 bytes**.
- Original adjacent `eboot.bin`: **93,825,704 bytes**.
- Decrypted input begins with genuine ELF64 little-endian x86-64 magic
  and uses PS4 executable type **0xfe10**; e_machine **62**.
- PS4 ELF program headers: **10**.
- Executable original code segment: **84,776,668 bytes**.
- Original `PT_GNU_EH_FRAME` header version 1:
  DW_EH_PE pcrel/sdata4, udata4 count, datarel/sdata4 table.
- **162,959** actual unwind FDE function records, all ordered and unique.
- Independently read every FDE's physical record and **confirmed all
  162,959 start and range lengths agree with the unwind-header lookup**;
  no zero-length/malformed ranges or overlapping unwind functions.
- Sum of these 162,959 unwind function body range lengths:
  **41,719,719 bytes**. This is **NOT** total executable code coverage:
  additional leaf functions, jumptables, shared fragments, and dynamic
  branch targets may lie outside unwind-listed ranges.
- Original PS4 dynamic linker entries: **199**.
- Original PS4 dynamic symbols: **703**; these are all undefined
  against game-local symbol definitions, as is normal for an executable
  importing its platform libraries.
- Original ELF relocation counts (actual original tables):
  - `R_X86_64_64` (1): **2,838**
  - `R_X86_64_GLOB_DAT` (6): **23**
  - `R_X86_64_JUMP_SLOT` (7): **661**
  - `R_X86_64_RELATIVE` (8): **231,478**
  - **235,000 relocations TOTAL**.
- Relative relocation addends pointing into executable code:
  **202,757**, with **129,135** distinct code-address targets.
  This supplies a large extra set for original function scanning,
  especially vtables/function pointers. Not all targets can be assumed
  to be distinct valid function entrypoints.
- Original jump/data import relocation slots: **684**.
- The adjacent private `sce_sys/param.sfo` in the same CUSA03173
  install was downloaded and parsed in the same private session:
  **APP_VER 01.09**, **TITLE_ID CUSA03173**, title **Bloodborne**.
  This validates the game-package version metadata but does **not**
  cryptographically bind the executable's internal version on its own.

These figures came from **the real user-owned decrypted executable**
and original PS4 package metadata. They do not come from a 5-function
toy ELF, public guessed addresses, or emulator execution.

## Reproducible local source code

`profile_private_original_elf_v205.py` is a standalone Python stdlib
read-only analyzer for this exact PS4 ELF layout. Its public code
contains NO original game bytes and reports *aggregate counts only*.
Usage in a PRIVATE directory:

    python3 native/source-port/recomp-v194/profile_private_original_elf_v205.py --decrypted-elf /private/eboot.bin-decrypted

This can be rerun against the original binary to cross-check its
function unwind, relocation, import-slot and dynamic-linker metadata.
The underlying original binary, actual function addresses, and any
copyrighted output remain strictly private and OUTSIDE GitHub.

## What this immediately changes

- **The original executable IS present and accessible.** Do NOT ask
  the user to upload it again or repeat a name-search-only Drive query.
- V204's real-original offline pipeline can take this input. Its
  original Zydis source scanner and full `bbrecomp` AOT C generator
  need to run next, with the executable strictly as build-time input.
- The existing analysis container could not resolve github.com to
  clone the **full exact pinned original upstream source/Zydis build
  toolchain**. Hence the real original whole-function generator and
  Windows COFF output have **not** yet been run. Only the genuine
  original ELF/unwind/linker metadata analysis is complete.
- The strict-native Windows executable cannot claim game boot:
  original imports need native Windows replacements, unsupported
  instructions and dynamic target coverage must be resolved,
  and original engine graphics, audio, game assets, input, save
  support and DLC/chalice flows still need real tests.

PR #84 is Draft. Do not publish original copyrighted bytes or code,
merge, deploy to Fornex, or present these counts as a native game boot.
