#!/usr/bin/env python3
"""Pin-and-port ONLY session identity cache from actual YT upstream PR #442.

The user reported long-session guest stutters. Original YT1.3 could do
~1000 memory permission checks for each session member every second; the
upstream PR records max ~500ms guest stalls. Our existing V109/V110 stage
already backports that PR's param span/slot optimizations, so this transports
ONLY SessionNameCache plus the *original upstream C++ tests* and the callsite.
The extra source is extracted byte-for-byte from immutable upstream PR head.

Strict: source-verified official 1.3.0 checkout, source-verified reviewed
PR head, no network/source fetching by this script; caller supplies separate
disposable checkouts. No proprietary game assets/saves, no server/P2P changes.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
UPSTREAM_442 = "0a2434dcbf70d681943996c226f1c1bfdc163608"
FILES = {
    "emulator/src/core/bloodborne_party.h": (
        "dc42d0509461fda6f557fa88f98a29fa28d877af",
        "69ff7fea89b221f14c83026ead12fcdeadfe16ea",
    ),
    "emulator/src/core/bloodborne_party.cpp": (
        "5186b4ed9fa9387752f4dc21362950d70d062505",
        "9fd804e9ee2caef838e309540081b25cff58c2c3",
    ),
    "emulator/src/core/bloodborne_join.cpp": (
        "9f70cec7eefb9a76b71a492b8ff772233173ca04",
        "b067cf1c7f7382b983d0d2e7c37b0109653dd37c",
    ),
    "emulator/tests/bloodborne/test_bloodborne_party_death.cpp": (
        "ad3c3f3f3b8fdbefeaa7a4ec876144a9a93f4bc6",
        "247a1fef0bba1b9c6328ddfef79d6a77a98a8a0a",
    ),
}
HEADER_START = "class SessionNameCache {"
HEADER_END = "std::string OnlineIdOfBoardMember("
METHOD_START = "SessionNameCache::Look SessionNameCache::Lookup("
METHOD_END = "u64 ParamTableSize("
JOIN_START = "std::optional<std::string> SessionMemberBoardName("
JOIN_END = "// The bell's search effect is lost with the old stage;"


def region(src: str, begin: str, end: str, where: str) -> str:
    if src.count(begin) != 1 or src.count(end) != 1:
        raise ValueError("V129 source span anchor missing: " + where)
    i, j = src.index(begin), src.index(end)
    if j <= i:
        raise ValueError("V129 source span in wrong order: " + where)
    return src[i:j]


def change(current: dict[str, str], original: dict[str, str],
           reference: dict[str, str]) -> dict[str, str]:
    h, cpp, join, tests = FILES
    for name in FILES:
        if not original[name] or not reference[name]:
            raise ValueError("Missing verified official/upstream source: " + name)
    if "SHYT-YT130-PR442-PARAM-SPAN-V109" not in current[cpp] or (
            "SHYT-YT130-PR442-PARAM-SLOTS-V110" not in current[cpp]):
        raise ValueError("Apply the already-proven 1.3 V109/V110 first")
    if HEADER_START in current[h] or METHOD_START in current[cpp]:
        raise ValueError("V129 already applied; prevent conflicting double stage")
    class_text = region(reference[h], HEADER_START, HEADER_END, "source-reviewed class")
    methods = region(reference[cpp], METHOD_START, METHOD_END, "source-reviewed methods")
    original_function = region(original[join], JOIN_START, JOIN_END, "old member scanner")
    new_function = region(reference[join], JOIN_START, JOIN_END, "new member scanner")
    if "SessionNameCache::Block" not in new_function or "cache.Missed(" not in new_function:
        raise ValueError("Missing full upstream cached scan logic")
    if current[join].count(original_function) != 1:
        raise ValueError("Pinned original member scan changed by another patch")
    if not reference[tests].startswith(original[tests]):
        raise ValueError("Upstream 442 party-death C++ tests do not merely append")
    additional = reference[tests][len(original[tests]):]
    if additional.count("TEST(SessionNameCache,") < 6 or "SessionNameCache::MissRetryMaxMs" not in additional:
        raise ValueError("Missing upstream cache hit/miss/invalidation GTests")
    if "TEST(SessionNameCache," in current[tests]:
        raise ValueError("Unexpected existing cache tests")
    out = dict(current)
    if current[h].count(HEADER_END) != 1:
        raise ValueError("V129 insertion header drift")
    out[h] = current[h].replace(HEADER_END, class_text + HEADER_END, 1)
    if current[cpp].count("RecreatePlan PlanRecreate(") != 1:
        raise ValueError("V129 insertion methods drift")
    out[cpp] = current[cpp].replace("RecreatePlan PlanRecreate(",
                                 methods + "RecreatePlan PlanRecreate(", 1)
    out[join] = current[join].replace(original_function, new_function, 1)
    out[tests] = current[tests].rstrip() + "\n" + additional.lstrip("\n")
    if out[join].count("static SessionNameCache cache;") != 1:
        raise ValueError("Session cache was not enabled in real native game")
    if out[h].count(HEADER_START) != 1 or out[cpp].count(METHOD_START) != 1:
        raise ValueError("Cache implementation duplicated")
    return out


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def run(pinned_root: Path, reviewed_root: Path) -> None:
    pinned_root, reviewed_root = pinned_root.resolve(), reviewed_root.resolve()
    if pinned_root == reviewed_root or git(pinned_root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Wrong official YT1.3 or shared checkout")
    if git(reviewed_root, "rev-parse", "HEAD") != UPSTREAM_442:
        raise ValueError("Wrong upstream official #442 PR head")
    current = {}
    original = {}
    upstream = {}
    for path, (baseblob, headblob) in FILES.items():
        if git(pinned_root, "rev-parse", "HEAD:" + path) != baseblob:
            raise ValueError("Official 1.3 source blob drift: " + path)
        if git(reviewed_root, "rev-parse", "HEAD:" + path) != headblob:
            raise ValueError("Reviewed upstream #442 blob drift: " + path)
        f, u = pinned_root / path, reviewed_root / path
        if not f.is_file() or f.is_symlink() or not u.is_file() or u.is_symlink():
            raise ValueError("Unexpected game source file/symlink: " + path)
        current[path] = f.read_text(encoding="utf-8")
        upstream[path] = u.read_text(encoding="utf-8")
        original[path] = subprocess.check_output(
            ["git", "-C", str(pinned_root), "show", "HEAD:" + path],
        ).decode("utf-8")
    edited = change(current, original, upstream)
    for path, text in edited.items():
        (pinned_root / path).write_bytes(text.encode("utf-8"))
    subprocess.run(["git", "-C", str(pinned_root), "diff", "--check"], check=True)
    print("YT130_V129_ORIGINAL_NATIVE_GUEST_SESSION_NAME_CACHE_PR442_STAGED_ONLY")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pinned", type=Path, required=True)
    parser.add_argument("--reviewed-pr442", type=Path, required=True)
    args = parser.parse_args()
    run(args.pinned, args.reviewed_pr442)
