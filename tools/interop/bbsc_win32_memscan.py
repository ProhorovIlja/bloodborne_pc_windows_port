"""Pinned-source-only Win64 clang adaptation of CLS BBSC's memory scanner.

deadinside28's bbsc_memscan.cpp contains MSVC __try/__except. The CLANG64
GNU C++ ABI does not support SEH syntax there. We keep the *actual* BBSC
FindInMemory API and pattern search logic, replacing only the platform's
potentially faulting memory reads with Windows ReadProcessMemory snapshots,
the equivalent of its Linux process_vm_readv approach.

The outer source manifest already hashes and pins the upstream file.
Refuse unreviewed upstream changes rather than patching arbitrary code.
"""
from __future__ import annotations

SOURCE = "gpu/bbnet20/bbsc/core/bbsc_memscan.cpp"

START = b"#ifdef _WIN32\n// One region."
END = b"#endif\n\n} // namespace"

WINDOWS_SCANNER = r'''#ifdef _WIN32
// The Windows clang64 build has no MSVC SEH (__try/__except).
// Snapshot committed pages through the OS instead of dereferencing guest
// memory. ReadProcessMemory fails cleanly when protection changes concurrently.
// Chunk overlap preserves signatures straddling a 1 MiB scan boundary.
void SearchRegion(const std::uint8_t* start, std::size_t size, const std::uint8_t* needle,
                  std::size_t length, std::vector<std::uint64_t>& hits, std::size_t max_hits) {
    constexpr std::size_t Piece = 1u << 20;
    if (length == 0 || length > Piece || length > size || hits.size() >= max_hits) return;
    std::vector<std::uint8_t> buffer(Piece + length - 1);
    for (std::size_t at = 0; at < size && hits.size() < max_hits; at += Piece) {
        const std::size_t own = std::min(Piece, size - at);
        const std::size_t want = std::min(size - at, buffer.size());
        SIZE_T got = 0;
        if (!ReadProcessMemory(GetCurrentProcess(), start + at,
                               buffer.data(), want, &got) || got < length) {
            continue;
        }
        const std::size_t limit = std::min(own, std::size_t(got) - length + 1);
        for (std::size_t i = 0; i < limit && hits.size() < max_hits;) {
            const auto* found = static_cast<const std::uint8_t*>(
                std::memchr(buffer.data() + i, needle[0], limit - i));
            if (!found) break;
            i = std::size_t(found - buffer.data());
            if (std::memcmp(found, needle, length) == 0)
                hits.push_back(reinterpret_cast<std::uint64_t>(start + at + i));
            ++i;
        }
    }
}
#endif
'''.encode("utf-8")

CALL_START = (b'            SearchRegion(reinterpret_cast<const std::uint8_t*>(start), info.RegionSize,\n'
              b'                         needle.data(), needle.size(), hits, max_hits);')
CALL_REPLACE = (b'            // Never search outside the explicitly requested [lo, hi) interval.\n'
                b'            const auto from = std::max(start, lo);\n'
                b'            const auto to = std::min(end, hi);\n'
                b'            if (to > from && to - from >= needle.size())\n'
                b'                SearchRegion(reinterpret_cast<const std::uint8_t*>(from),\n'
                b'                             static_cast<std::size_t>(to - from),\n'
                b'                             needle.data(), needle.size(), hits, max_hits);')


def adapt_win32_memscan(data: bytes) -> bytes:
    """Replace only known upstream Windows SEH scanning with safe snapshots."""
    if (data.count(START) != 1 or data.count(END) != 1
            or data.count(CALL_START) != 1):
        raise ValueError("upstream BBSC memory scanner layout changed")
    a = data.index(START)
    b = data.index(END, a) + len(b"#endif")
    original = data[a:b]
    if (original.count(b"__try") != 1 or original.count(b"__except") != 1
            or original.count(b"std::memchr") != 1
            or original.count(b"std::memcmp") != 1):
        raise ValueError("unreviewed upstream Windows memory scanner")
    converted = data[:a] + WINDOWS_SCANNER + data[b:]
    return converted.replace(CALL_START, CALL_REPLACE, 1)
