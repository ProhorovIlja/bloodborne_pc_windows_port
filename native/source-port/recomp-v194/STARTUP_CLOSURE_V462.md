# V462 — strict startup dependency planning

Baseline: current V461 (#186) reports ordered native fixture returns 1–1073. The older V432 (#162) separately reports 1–1088 and stops at a transitive indirect callee present in the whole-image output but absent from the focused build. Do not sum, substitute, or promote these results across branches; replay the overlap on V461. Neither reached retail main.

## Offline check of owner input

On the decrypted CUSA03173 ELF, independently recovered the descending initializer list from executable-relative SCE relocations and the sentinel; checked the first slot against the load in DT_INIT. It contains 18,444 ordered targets. A conservative root-only GNU objdump walk of 1074–1500 identified 1,019 direct call sites, 173 indirect call sites, 14 indirect branch sites and 10 branches out of the root windows. There are 17 distinct external direct candidates, 11 with unwind anchors. No root in the range has an unwind start. These are candidates: the walk stops at known neighboring seeds or its local bound, and it neither resolves dynamic targets nor traverses callees. In particular, the 1089 root appeared to return directly in this walk; that does not reproduce or disprove the earlier same-process failure at ordinal 1089. Compare exact ordinal-to-target mapping and trace before attributing the old stop to a specific function.

## New gate

`python startup_closure_v462.py --self-test` exercises the normalized manifest planner. Run the checker on a private manifest with `--start 1074 --end 1500`. Exit 0 = covered by focused inventory; 1 = native generated functions must be added; 2 = unresolved dependencies; 3 = invalid input or I/O. On a non-blocking plan, `--private-add-list` can write a new local JSON list, never to be committed. Summary output contains aggregate counters only. An omitted or incomplete manifest cannot establish actual binary coverage; the scanner adapter, linked-image check and ordered replay are separate work.

Donor roles: Astrr00 for x86-64 code emission; ducvd89 for extra AOT entries and independent discovery; PS4Recomp for disputed CFG and multi-module TLS contracts; Paleblood for overlapping verified families. NielsL92 provides a separate callback/TLS differential reference, not execution evidence for this branch. Dark Souls III is a format comparison input (e.g. EMEVD variants), not a replacement for Bloodborne startup or runtime binaries. No donor runtime, proprietary code, addresses, images or generated game output committed.

Release gate: native Windows x86-64, Linux x86-64 and Apple Silicon macOS builds independently boot offline, load a real location, accept movement, quit, save and load again without any PS4 executable/modules, original executable image in any packaging, interpreter or JIT. A fixture pass and constructor returns do not meet that gate.
