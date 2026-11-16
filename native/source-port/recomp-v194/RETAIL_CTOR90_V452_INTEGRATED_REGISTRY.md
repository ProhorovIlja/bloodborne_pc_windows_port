# V452 integrated native registry and constructor 90 tail

Using hash-matched private 1.09 input, link the complete supported registry success path, vector growth, original sort and primary key lookup into one Linux x86-64 executable. The host supplies the registry singleton storage, guard word, allocator and libc calls. Unsupported cold/diagnostic paths are not validated.

The integrated harness checked 2,048 registrations, both vector growth paths and balanced allocation/free. It checked sorted order and value/object pair integrity after each registration, 8,192 final pairs, explicit-length and computed-length lookups, missing keys and five independent sort inputs. Sort fixtures cover sorted, reversed, equal, mixed, and signed extremes with a zero depth budget.

A second test enters constructor 90 at its object publication block with a synthetic frame. The original instructions publish the object, invoke the connected registry function with six relocation-verified virtual methods, link the object to the existing list, check the guard and return through the original epilogue. Both empty and two-node fixture lists passed. Fixture strings and static storage replace retail data; the list-head getter is a host binding.

GCC and Clang optimized and Clang ASan/UBSan harness runs all passed. The assembly itself is not sanitizer instrumented. The original executable is read offline during the build only. Runtime uses a host executable in an isolated directory with no PS4 ELF, loader, interpreter or JIT. No original executable bytes or addresses are committed.

This verifies the late constructor segment, not a full constructor 90 return from its entry. It has not been connected to the earlier cold allocator/flags/singleton path or replayed after constructors 1–89. No whole-game boot or Windows/macOS retail execution is claimed.
