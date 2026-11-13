# V441: first corrected retail constructor dependencies

Read-only inspection of the private Bloodborne ELF's first callback in corrected order finds two direct calls through relocation-backed import stubs, two other direct calls, one virtual indirect call, and one out-of-body tail jump. The second callback starts with a separate direct tail transfer. These are dependencies, not measured execution or a complete reachable graph. The import stubs are not ordinary compiled native callees. Resolve the two import identities and lifecycle semantics, then translate the reachable local routines and verify the virtual call's actual object/target in a private replay. Do not use the old constructor count as a substitute.

The owner-local V441 tool takes a privately established first-load slot and reviewed function extent, invokes GNU objdump only as a decoder, and reports aggregate counts. Do not publish the ELF, addresses, extent selection notes, disassembly, or generated game code.
