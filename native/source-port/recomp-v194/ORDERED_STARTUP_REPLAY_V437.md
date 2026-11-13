# V433–V437: focused native startup replay

V433 (#163) identifies evidenced indirect gaps; V434 (#164) checks the private rebuild; V435 (#165) prebinds scoped native routes; V436 (#166) supplies the strict RcApi callback. V437 adds a sequencer for trusted per-constructor drivers. It validates the requested ordinal range before any invocation, retains one CPU and VM, and stops at the first callback failure or outer RIP/RSP mismatch. The report counts only successful steps, never an attempted or recovered step.

Retail drivers must still check the saved return word, import/lock postconditions and original constructor identity. Preserve existing audited import handlers; use V436 only on the native CALL branch. Recovered state must be discarded. The sequencer neither materializes proprietary inputs nor runs the retail image.

The last independently documented retail prefix is 1–1088. The next private run must regenerate the focused build for the missing indirect target, pass the V434 gate, then replay and validate the return from 1089. Public CI exercises invented fixtures only.
