# V490 — separate progress denominators

The owner-local V488 generator now emits a JSON inventory with exact
metadata-start and constructor-slot ratios, and thresholds 10/25/50/75/90/100.
Repeated constructor addresses count as separate slots. Generated IDs are
deduplicated across families and must belong to the scanned start set.
Ordered execution, linked coverage and gameplay are not inferred from
the emitted table. The CLI leaves those fields null. The current
previously verified prefix is 1–1073; the CLI does not replay it.

The ALU emitter now shares identical straight-line native bodies across
IDs, including exact tail aliases. It preserves separate dispatch IDs.
The synthetic fixture checks sharing plus cycle/depth rejection; the
native fixture tests the same results through the dispatcher. No
proprietary generated output or address lists are committed.

V488 CI is explicitly triggered for relevant feature-branch pushes
as well as pull requests. A shared concurrency key cancels duplicate
or superseded runs on the same branch. The three host targets remain.
