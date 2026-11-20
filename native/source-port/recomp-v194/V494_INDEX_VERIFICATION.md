# V494 — indexed dispatch verification

The production generator now builds the index directly from typed emitter
rows, not by parsing the generated C. Each family must be sorted, unique,
and nonempty; load aliases must resolve to a real load body, every load
body must own an exact route, and families cannot overlap. The ID column
uses 32 bits when the entire set fits and retains 64 bits otherwise.
This halves that column for fitting inputs; it does not imply a speedup.

The CI fixture compares V492 and V493 on 65,792 synthetic calls, checking
result, arithmetic flags, status, and the entire write buffer with both
memory permissions independently absent or present. Test cases include
all fixture routes and ID misses. The fixture generator retains the
text parser only as an independent check of the emitted test tables.
No retail AOT or ordered startup is claimed by this change.

Previous V493/V492, relocation, and V475 startup-replay fixtures were
confirmed on Linux and Windows; their macOS jobs were still queued.
Progress baseline: 23,048/179,030 (12.87% truncated) verified partial
AOT IDs, 1,073/18,444 (~5.82%) ordered constructor slots. These are not
gameplay metrics. Full generation and game boot remain unverified.
