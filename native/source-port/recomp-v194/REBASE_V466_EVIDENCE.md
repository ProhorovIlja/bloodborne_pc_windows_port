# V466: what still depends on the original executable

Audited Astrr00/BloodbornePC at 802e3f2bf2e38e71da0a46362ae4510a429f7213.
The AOT generator and the runtime dependency are separate: src/app/main.cpp
requires an eboot argument, reads and parses it, and feeds the resulting image
to load_image and setup_main_thread. --app0 overrides the asset root only.
The upstream roadmap reports reaching the clinic with a save template on
1.09, not a verified run without the original executable. Its 1.00 coverage
and differential counts must not be extrapolated to this project's 1.09 image.
Useful references: bbelf relocation/CFG inventory and bbdiff full-state parity.
No upstream code was imported.

Private Linux check on CUSA03173 1.09: normalized 235,000 SCE RELA records
and checked each eight-byte destination span against the PT_LOAD layout.
All destinations are file-backed writable data, with no overlaps.
231,478 relative relocations round-tripped at two guest base addresses:
202,757 into the RX segment (not necessarily code), 21,349 into file-backed
data and 7,372 into zero-fill. The other 3,522 records are symbol-based
(types 1/6/7: 2,838/23/661); this audit does not resolve them.
Mutations for a duplicate destination, negative addend, RX write and
unknown relocation kind all rejected. The synthetic fixture also covers
unmapped gaps, truncated spans, nonzero symbol index on RELATIVE, bad slides
and overlap between distinct destinations.

Runtime data packaging still needs a source of read-only constants, writable
initial data, zero-fill, TLS and symbol bindings. Never copy the whole RX
segment and call it a data pack; it contains code as well as constants. Any
function address kept as guest data must dispatch to an attested host function
or fail; never cast it to a native pointer. This is an offline audit, not a
loader, and does not extend the previously attested 1–1073 ordered prefix.
