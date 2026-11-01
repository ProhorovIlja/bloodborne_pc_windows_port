# V209: actual Bloodborne original constant-return functions -> native Win64 COFF/DLL

**Actual private test on 2026-11-01.** Original input is the owner's
decrypted CUSA03173 PS4 executable from private Drive. This is a
REAL input, not a synthetic function array.

## Exact supported isolated instruction forms

Only complete FDE-described function bodies matching these exact x86-64
byte patterns are translated. All other functions are ignored:

- xor eax,eax; ret: **4,721**
- mov eax,imm32; ret: **2,978**
- mov rax,imm64; ret: **3**

**7,702 functions** accepted of 162,959 verified FDE entries. Mere
ret-only functions are excluded: they do not specify an RAX return
value. The original C source and Win64 code were generated locally and
NOT checked into GitHub.

## Private real compilation and independent PE checks

- clang-cl produced a **1,033,814-byte Win64 COFF object**.
- lld-link /dll /noentry /nodefaultlib produced a PE32+ x64 DLL.
- First link accidentally folded same-code functions: 7,702 exported
  names but only **309 distinct function code RVAs**. Distinct original
  function addresses may be semantically observable, so this is not
  acceptable for source-function identity.
- Fixed link with **/opt:noicf**. New DLL **309,760 bytes** and
  **7,702 unique function RVAs** for 7,702 exported names.
- PE import directory is empty. The DLL does NOT need the original
  EBOOT at runtime to return these isolated constants.
- Read each native export's actual PE machine code, decoded its return
  constant, re-read the corresponding original ELF function instructions
  and compared them **7,702/7,702 match**, 0 mismatches.

Public reusable local-only generator:
`build_private_constant_aot_v209.py` uses
`audit_private_original_fde_v208.py` as a strict original ELF/FDE
preflight. Refuses to write generated files inside Git and captures
compiler diagnostics to PRIVATE files without flooding chat.

```
python native/source-port/recomp-v194/build_private_constant_aot_v209.py \
  --input /private/CUSA03173/eboot.bin-decrypted \
  --output-dir /private/bb-win64-constant-aot
```

**CI validation is SYNTHETIC ONLY:** Ubuntu/Windows test against invented
C functions; original binary, generated address list, objects and private
DLL do not enter public CI.

## Scope limitations: DO NOT call this a native playable Bloodborne

- An isolated C constant-return leaf can reproduce return values while
  other register/flag/stack effects and caller ABI translation remain
  unverified. Exact whole-CPU equivalence is not proven.
- 7,702 is neither 7,702 working gameplay functions wired into a
  native engine nor an accurate estimate of full-game completion.
- No renderer/asset/game state/OS I/O/PS4 import compatibility closure,
  launcher integration, game boot or 5-player networking is implied.
- The target remains a complete native Windows EXE with a native
  runtime and game assets, with no need for the original EBOOT at
  launch. Additional methods must handle all remaining functions,
  global data relocations, imports, threading, scheduler, rendering
  and audio, before the game will run.

No Fornex changes and no public uploads of proprietary data.
