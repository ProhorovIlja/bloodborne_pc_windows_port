#!/usr/bin/env python3
"""V174: persist original Qt V173 intentional routing policy counters in JSONL.

MUST run AFTER original V155 shard-wire parser and V161/V169 shared-clock
staging. Parses only anonymized fixed counters printed by the original
LinkServer; NEVER parses player IDs or logs packet content. No production
game, server route, native launcher or Fornex modification.
"""
from pathlib import Path
import subprocess
import sys

PIN="0645740a33ae21c56df3b4a0d9777086dbca6053"
SHARDS="server/loadtest/run_shards.py"
MARK="SHYT_V174_ORIGINAL_QT_POLICY_FILTER_JSON"
OLD_BEGIN='''        per_shard = []
        for i in range(args.shards):
            wire_in, wire_out, wire_bytes_in, wire_bytes_out, wire_windows = data_wire(i)
'''
NEW_BEGIN='''        # SHYT_V174_ORIGINAL_QT_POLICY_FILTER_JSON:
        # Same original server temp logs as V155, now retain exactly the
        # authoritative pre-socket route FILTER decisions for each 5s window.
        # This is aggregate/all-phases diagnostic; do NOT subtract these
        # from only the V161 post-Playing steady source-clock interval.
        policy_pattern = re.compile(
            r'YT130_ROUTE_POLICY allowed_entries=(\d+) '
            r'filtered_entries=(\d+) filtered_enemy_hp_05=(\d+) '
            r'filtered_event_sync_31=(\d+)(?!\d)')
        def route_policy(shard_index):
            counts = [0, 0, 0, 0]
            windows = 0
            name = os.path.join(root, f"shard{shard_index}", "shadnet.log")
            with open(name, encoding="utf-8", errors="replace") as log:
                for line in log:
                    match = policy_pattern.search(line)
                    if match:
                        values = list(map(int, match.groups()))
                        if (values[2] + values[3] > values[1] or
                                any(x > 2**53 for x in values)):
                            raise RuntimeError("original Qt policy counters inconsistent")
                        counts = [a+b for a,b in zip(counts,values)]
                        windows += 1
            return (*counts, windows)

        per_shard = []
        for i in range(args.shards):
            wire_in, wire_out, wire_bytes_in, wire_bytes_out, wire_windows = data_wire(i)
            (policy_allowed, policy_filtered, policy_enemy_hp_05,
             policy_event_sync_31, policy_windows) = route_policy(i)
'''
OLD_ROW='''                "game_wire_sample_windows": wire_windows,
'''
NEW_ROW=OLD_ROW+'''                "game_policy_allowed_entries": policy_allowed,
                "game_policy_filtered_entries": policy_filtered,
                "game_policy_filtered_enemy_hp_05": policy_enemy_hp_05,
                "game_policy_filtered_event_sync_31": policy_event_sync_31,
                "game_policy_sample_windows": policy_windows,
'''
OLD_TOTAL='''            "game_wire_sample_windows": sum(r["game_wire_sample_windows"] for r in per_shard),
'''
NEW_TOTAL=OLD_TOTAL+'''            "game_policy_allowed_entries": sum(r["game_policy_allowed_entries"] for r in per_shard),
            "game_policy_filtered_entries": sum(r["game_policy_filtered_entries"] for r in per_shard),
            "game_policy_filtered_enemy_hp_05": sum(r["game_policy_filtered_enemy_hp_05"] for r in per_shard),
            "game_policy_filtered_event_sync_31": sum(r["game_policy_filtered_event_sync_31"] for r in per_shard),
            "game_policy_sample_windows": sum(r["game_policy_sample_windows"] for r in per_shard),
            "game_policy_scope": "original Qt Hub::Routed count-only 5s all-run pre-socket decisions, NOT same as V161 source-clock cohort",
'''

def one(s,old,new,label):
    if s.count(old)!=1 or new in s:
        raise ValueError("V174 original staged shard parser drift: "+label)
    return s.replace(old,new,1)

def patch(source):
    if ("SHYT-V155-ORIGINAL-QT-ANONYMOUS-DATA-WIRE" not in source or
            "SHYT_V161_GLOBAL_COHORT_SEND_TIMESTAMP_BUCKETS" not in source or
            "SHYT_V169_SYNTHETIC_DIRECTED_GAME_COHORT" not in source):
        raise ValueError("V174 requires staged V155/V161/V169 original source")
    for old,new,label in ((OLD_BEGIN,NEW_BEGIN,"per-shard original log reader"),
                          (OLD_ROW,NEW_ROW,"per-shard policy decision summary"),
                          (OLD_TOTAL,NEW_TOTAL,"full-run JSON policy census")):
        source=one(source,old,new,label)
    return source

def stage(root):
    root=Path(root).resolve(strict=True)
    if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()!=PIN:
        raise ValueError("V174 requires original YT1.3 pinned Qt load generator")
    path=root/SHARDS
    if not path.is_file() or path.is_symlink():
        raise ValueError("V174 source path unavailable")
    source=patch(path.read_text(encoding="utf-8"))
    path.write_text(source,encoding="utf-8")
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
    print("SHYT_V174_ORIGINAL_QT_AUTHENTICATED_POLICY_FILTER_JSON_STAGED_DIAGNOSTIC_ONLY")

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("usage: stage_policy_route_report_v174.py DISPOSABLE_PINNED_YT")
    stage(sys.argv[1])
