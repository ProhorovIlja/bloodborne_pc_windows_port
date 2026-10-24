# SH Patch Safety Audit V15

Read-only standard-library utility for shadPS4 XML files. It never patches the executable or enables cheats. Usage: `python audit_patches.py Bloodborne.xml DollRebirth.xml --json findings.json --strict`. Exit 2 = a conflicting active patch or invalid metadata; do not auto-apply. Identical overlapping writes are informational. The input files and generated report remain local.

This compares only active 1.09 eboot XML patches. Cheat JSON uses a potentially different address space and is deliberately excluded. Native BBPort integration must also verify the game executable hash, built-in hooks and pre-existing patches. Online play should default to safe/unchanged gameplay patches.
