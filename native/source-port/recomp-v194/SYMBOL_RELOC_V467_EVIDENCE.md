# V467: scoped symbol relocation planning

In the private CUSA03173 1.09 image, 3,522 symbol relocations reference 686
scoped import keys (666 functions and 20 objects). Scope is NID, library
selector, module selector and ELF symbol type within this image, not a global
NID-only lookup. 214 R_X86_64_64 object entries have a nonzero addend of 16.
OpenOrbis documents the SCE table locations; shadPS4's linker independently
corroborates S+A for type 1 and S for types 6/7.

On Linux, the normalized owner-local records were checked first against V466's
destination rules, then against V467's scoped planning rules. 7,044 encoded
writes matched separate expected-value checks at two synthetic binding bases.
An empty binding set or removing one key emitted no writes. Duplicate
destinations and invalid symbol indices were rejected. These bindings are
synthetic, not implementations of retail imports. The V467 Python module has
no ELF or PS4 library dependency. It is a planner, not the runtime loader;
native services, object storage and dispatch identity must be attested before
a real write plan is accepted. The constructor frontier is unchanged.

External cross-check: AnyPS5 #3093/#3094 reports the same relocation count on
CUSA00900 1.09 after its SCE-table and scan-boundary fixes, then stops at an
overlapping-instruction error. Equal counts do not imply matching addresses
or interchangeable builds. PS4Recomp provides an Apple Silicon packaging
reference; its README reports a Bloodborne crash at game start. Astrr00
still documents opening the same eboot at runtime. No upstream source or
owner-local game data was added.
