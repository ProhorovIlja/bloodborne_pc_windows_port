#!/usr/bin/env python3
"""V182: retain only anonymous effective Qt UDP socket buffer readbacks in load JSON.

Source-exact modification of the disposable pinned YT1.3 server/loadtest
run_shards.py AFTER V174. Server emits the V181 one-line post-bind readback.
This is host diagnostics only; it cannot prove particular per-socket loss or
turn a failing 200-hunter delivery sample into a successful QoS grade.
"""
from pathlib import Path
import subprocess
import sys

PIN="0645740a33ae21c56df3b4a0d9777086dbca6053"
FILE="server/loadtest/run_shards.py"
MARK="SHYT_V182_ORIGINAL_QT_UDP_SOCKET_BUFFER_REPORT"
BEFORE="""        per_shard = []
        for i in range(args.shards):
            wire_in, wire_out, wire_bytes_in, wire_bytes_out, wire_windows = data_wire(i)
            (policy_allowed, policy_filtered, policy_enemy_hp_05,
             policy_event_sync_31, policy_windows) = route_policy(i)
"""
AFTER="""        # SHYT_V182_ORIGINAL_QT_UDP_SOCKET_BUFFER_REPORT:
        # Only the one-time readback numeric line, not the server's raw logs.
        # Count each bind; multiple or missing binds are NOT confirmed capacity.
        udp_buffers = re.compile(
            r'Link UDP socket buffers requested_bytes=(\d+) '
            r'effective_receive_bytes=(\d+) effective_send_bytes=(\d+)(?!\d)')
        def socket_buffers(shard_index):
            values = []
            path = os.path.join(root, f"shard{shard_index}", "shadnet.log")
            with open(path, encoding="utf-8", errors="replace") as log:
                for line in log:
                    match = udp_buffers.search(line)
                    if match:
                        numbers = tuple(map(int, match.groups()))
                        if any(v <= 0 or v > 2**31-1 for v in numbers):
                            raise RuntimeError("original Qt socket buffer readback invalid")
                        values.append(numbers)
                        if len(values) > 8:
                            raise RuntimeError("too many original Qt UDP bind reports")
            if not values:
                return (0, 0, 0, 0, False)
            request = min(v[0] for v in values)
            receive = min(v[1] for v in values)
            send = min(v[2] for v in values)
            return (request, receive, send, len(values),
                    len(values) == 1 and request == (16 << 20))

        per_shard = []
        for i in range(args.shards):
            (udp_requested, udp_receive, udp_send, udp_binds,
             udp_readback_valid) = socket_buffers(i)
            wire_in, wire_out, wire_bytes_in, wire_bytes_out, wire_windows = data_wire(i)
            (policy_allowed, policy_filtered, policy_enemy_hp_05,
             policy_event_sync_31, policy_windows) = route_policy(i)
"""
ROW_OLD='''                "game_policy_sample_windows": policy_windows,
'''
ROW_NEW=ROW_OLD+'''                "udp_socket_requested_bytes": udp_requested,
                "udp_socket_effective_receive_bytes": udp_receive,
                "udp_socket_effective_send_bytes": udp_send,
                "udp_socket_bind_reports": udp_binds,
                "udp_socket_readback_valid": udp_readback_valid,
'''
TOTAL_OLD='''            "game_policy_scope": "original Qt Hub::Routed count-only 5s all-run pre-socket decisions, NOT same as V161 source-clock cohort",
'''
TOTAL_NEW=TOTAL_OLD+'''            "udp_socket_readback_complete": all(
                r["udp_socket_readback_valid"] for r in per_shard),
            "udp_socket_min_effective_receive_bytes": min(
                (r["udp_socket_effective_receive_bytes"] for r in per_shard), default=0),
            "udp_socket_min_effective_send_bytes": min(
                (r["udp_socket_effective_send_bytes"] for r in per_shard), default=0),
            "udp_socket_readback_scope": "one numeric bind report per original Qt shard; kernel effective values, NOT per-socket packet losses or production QoS",
'''

def replace(source: str, old: str, new: str, label: str) -> str:
    if source.count(old)!=1 or new in source:
        raise ValueError("V182 original Qt load source drift: "+label)
    return source.replace(old,new,1)

def patch(source: str) -> str:
    if (MARK in source or
        "SHYT_V174_ORIGINAL_QT_POLICY_FILTER_JSON" not in source or
        "SHYT_V161_GLOBAL_COHORT_SEND_TIMESTAMP_BUCKETS" not in source):
        raise ValueError("V182 expects source-locked V161 + V174 stages once")
    for old,new,label in ((BEFORE,AFTER,"read original server bind logs"),
                          (ROW_OLD,ROW_NEW,"per-shard numbers"),
                          (TOTAL_OLD,TOTAL_NEW,"all-shards numeric summary")):
        source=replace(source,old,new,label)
    return source

def stage(root: Path) -> None:
    root=root.resolve(strict=True)
    if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                               text=True,stderr=subprocess.DEVNULL).strip()!=PIN:
        raise ValueError("V182 requires exact original YT1.3 checkout")
    file=root/FILE
    if not file.is_file() or file.is_symlink():
        raise ValueError("V182 missing regular load generator")
    candidate=patch(file.read_text(encoding="utf-8"))
    file.write_text(candidate,encoding="utf-8")
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True,stdout=subprocess.DEVNULL)
    print("SHYT_V182_QT_UDP_BUFFER_READBACK_NUMERIC_JSON_STAGED_NOT_QOS_PASS")

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("usage: stage_udp_buffer_readback_report_v182.py PINNED_YT")
    stage(Path(sys.argv[1]))
