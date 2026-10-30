#!/usr/bin/env python3
"""V139: source-exact fix for original YT1.3 pipeline-cache worker counter race.

Port of reviewed shadPS4 PR #5577. The producer increments under submit_mutex,
but the worker previously decremented/observed num_requests outside that lock.
On a stale/lost counter update, ProcessIO can spin on an empty task queue,
wasting a core for a whole session. Never change queue, shutdown or game state.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys

PATH = Path("bbport/gpu/shadps4/video_core/cache_storage.cpp")
UPSTREAM_PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
BLOB_PIN = "65a7df5eb8aff2bdb128467c4680182ca2ef8080"
CHANGES = (
    ("#include <condition_variable>\n",
     "#include <atomic>\n#include <condition_variable>\n"),
    ("u32 num_requests{};\n",
     "std::atomic<u32> num_requests{};\n"),
    ("[&] { return num_requests; });",
     "[&] { return num_requests.load(std::memory_order_acquire) != 0; });"),
    ("while (num_requests) {",
     "while (num_requests.load(std::memory_order_acquire) != 0) {"),
)

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + bytes([0]) + data).hexdigest()

def rewrite(source: str) -> str:
    for before, after in CHANGES:
        if source.count(before) != 1:
            raise ValueError("V139 original GPU cache-storage source drift: " + before[:50])
        source = source.replace(before, after, 1)
    if "++num_requests;" not in source or "--num_requests;" not in source:
        raise ValueError("V139 original cache request lifecycle missing")
    if source.count("std::atomic<u32> num_requests{};") != 1:
        raise ValueError("V139 unexpected atomic counter")
    return source

def transform(raw: bytes) -> bytes:
    if git_blob_sha(raw) != BLOB_PIN:
        raise ValueError("V139 not exact pinned YT1.3 original GPU source")
    return rewrite(raw.decode("utf-8")).encode("utf-8")

def stage(root: Path) -> None:
    target = root.resolve() / PATH
    if not target.is_file() or target.is_symlink():
        raise ValueError("V139 only stages a regular original GPU source")
    target.write_bytes(transform(target.read_bytes()))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_cache_io_atomic_v139.py PINNED_DISPOSABLE_YT_ROOT")
    stage(Path(sys.argv[1]))
    print("V139_ORIGINAL_GPU_PIPELINE_CACHE_IO_ATOMIC_SOURCE_ONLY_NOT_GAMEPLAY")
