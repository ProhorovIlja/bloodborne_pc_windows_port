#!/usr/bin/env python3
"""V161 cohort-synchronized game-entry evidence from original Qt bbload.

V120 steady counters were armed independently per bbload process. A sender
could count its steady entries while the destination worker had not yet armed
steady receives. V161 does NOT relax existing V120 QoS. It adds a second,
independent comparison: original packet send-time timestamp places BOTH sender
and receiver counts into the same global one-second steady_clock bucket. Only
FULL buckets AFTER every worker reports all its 5-seat teams Playing, and
BEFORE the earliest worker stops (2s drain margin), can be scored.

This is diagnostic, same original LinkVersion/protocol, no private IDs/packet
bytes, no game or production modification. Apply AFTER V159 on the disposable
YT1.3 source checkout.
"""
from pathlib import Path
import subprocess
import sys

PIN="0645740a33ae21c56df3b4a0d9777086dbca6053"
BB="server/loadtest/bbload.cpp"
SHARDS="server/loadtest/run_shards.py"
MARK="SHYT_V161_GLOBAL_COHORT_SEND_TIMESTAMP_BUCKETS"
INCLUDE_OLD="#include <QHostAddress>\n"
INCLUDE_NEW="#include <QHostAddress>\n#include <QJsonArray>\n"
CLASS_OLD="""  s64 steady_since_us = 0; // set once, after real full-team Playing
"""
CLASS_NEW="""  s64 steady_since_us = 0; // set once, after real full-team Playing
  // SHYT_V161_GLOBAL_COHORT_SEND_TIMESTAMP_BUCKETS: steady_clock shared by
  // every hosted Qt process; keyed on original game packet creation time.
  std::map<s64, std::pair<quint64, quint64>> cohort_epoch_entries;
"""
SENT_OLD="""    load.totals.packets_sent += frame.entries.size();
    if (load.steady_since_us > 0 && now_us >= load.steady_since_us) {
"""
SENT_NEW="""    load.totals.packets_sent += frame.entries.size();
    // Same packet send timestamp epoch is used by the remote receiver.
    load.cohort_epoch_entries[(now_us / 1'000'000) * 1'000'000].first +=
        static_cast<quint64>(frame.entries.size());
    if (load.steady_since_us > 0 && now_us >= load.steady_since_us) {
"""
RECEIVED_OLD="""    ++received_game_packets;
    if (load.steady_since_us > 0 &&
"""
RECEIVED_NEW="""    ++received_game_packets;
    // Group by the embedded sender's steady_clock timestamp, NOT the
    // receive callback's wall/ready time. The parent intersects windows.
    load.cohort_epoch_entries[(static_cast<s64>(sent) / 1'000'000) * 1'000'000].second++;
    if (load.steady_since_us > 0 &&
"""
FINISH_OLD="""    const double seconds = (NowUs() - started_us) / 1e6;
    QJsonObject out{
"""
FINISH_NEW="""    const s64 cohort_finish_us = NowUs();
    QJsonArray cohort_json;
    for (const auto& [stamp, counts] : cohort_epoch_entries) {
      cohort_json.append(QJsonObject{
          {"start_us", static_cast<double>(stamp)},
          {"sent_entries", static_cast<double>(counts.first)},
          {"received_entries", static_cast<double>(counts.second)}});
    }
    const double seconds = (NowUs() - started_us) / 1e6;
    QJsonObject out{
        {"cohort_ready_us", static_cast<double>(steady_since_us)},
        {"cohort_finish_us", static_cast<double>(cohort_finish_us)},
        {"cohort_epoch_entries", cohort_json},
"""
ANCHOR_AGG="""        per_shard = []
        for i in range(args.shards):
            wire_in, wire_out, wire_bytes_in, wire_bytes_out, wire_windows = data_wire(i)
"""
PATCH_AGG="""        # SHYT_V161_GLOBAL_COHORT_SEND_TIMESTAMP_BUCKETS: original C++
        # steady_clock send-time stamps are the same monotonic clock across
        # all hosted bbload worker processes (and the source packet contains
        # the same send time when decoded by the receiver).
        # Never compare V120 per-process readiness windows as if synchronized.
        cohort_quality = "NO_GLOBAL_200_PLAYER_FIVE_SEAT_COHORT"
        cohort_start_us = cohort_end_us = cohort_sent = cohort_received = 0
        cohort_seconds = 0
        if results and all(
                r.get("playing") == r.get("games") and
                r.get("complete_teams") == r.get("games") // args.team_size and
                isinstance(r.get("cohort_ready_us"), (int, float)) and
                0 < r["cohort_ready_us"] < 2**53 and
                isinstance(r.get("cohort_finish_us"), (int, float)) and
                r["cohort_ready_us"] < r["cohort_finish_us"] < 2**53 and
                isinstance(r.get("cohort_epoch_entries"), list)
                for r in results):
            tick = 1_000_000
            # The intersection begins after the LAST worker is fully ready.
            # 2s tail margin: late UDP deliveries, game callbacks and process
            # stop cannot make the final bucket look spuriously lossy.
            latest_ready = max(int(r["cohort_ready_us"]) for r in results)
            earliest_done = min(int(r["cohort_finish_us"]) for r in results) - 2*tick
            cohort_start_us = ((latest_ready + tick - 1)//tick)*tick
            cohort_end_us = (earliest_done//tick)*tick
            cohort_seconds = max(0,(cohort_end_us-cohort_start_us)//tick)
            if cohort_seconds >= 5:
                counts = {}
                valid = True
                expected_buckets = set(range(cohort_start_us, cohort_end_us, tick))
                for r in results:
                    # Fail closed: a silent/stalled worker must not borrow
                    # another process's healthy UDP traffic to score green.
                    seen = set()
                    worker_scored_buckets = set()
                    worker_sent = worker_received = 0
                    for window in r["cohort_epoch_entries"]:
                        if (not isinstance(window, dict) or
                                set(window) != {"start_us","sent_entries","received_entries"} or
                                any(type(window.get(k)) not in (int,float)
                                    or not (0 <= window[k] < 2**53)
                                    or int(window[k]) != window[k]
                                    for k in ("start_us","sent_entries","received_entries"))):
                            valid = False
                            break
                        bucket = int(window["start_us"])
                        if bucket % tick or bucket in seen:
                            valid = False
                            break
                        seen.add(bucket)
                        if cohort_start_us <= bucket < cohort_end_us:
                            # Every Playing 5-seat worker must continuously
                            # participate in EVERY fully scored second; one
                            # healthy worker must not mask another stalled one.
                            if (int(window["sent_entries"]) == 0 or
                                    int(window["received_entries"]) == 0):
                                valid = False
                                break
                            worker_scored_buckets.add(bucket)
                            out, inc = counts.get(bucket, (0, 0))
                            counts[bucket] = (out + int(window["sent_entries"]),
                                              inc + int(window["received_entries"]))
                            worker_sent += int(window["sent_entries"])
                            worker_received += int(window["received_entries"])
                    if (worker_sent == 0 or worker_received == 0 or
                            worker_scored_buckets != expected_buckets):
                        valid = False
                if valid:
                    cohort_sent = sum(x[0] for x in counts.values())
                    cohort_received = sum(x[1] for x in counts.values())
                    if cohort_sent < 10_000 or cohort_received > cohort_sent:
                        cohort_quality = "INSUFFICIENT_OR_INVALID_GLOBAL_GAME_COHORT"
                    elif 100 * cohort_received < 99 * cohort_sent:
                        cohort_quality = "GLOBAL_GAME_COHORT_DELIVERY_DEGRADED"
                    else:
                        cohort_quality = "GLOBAL_GAME_COHORT_PASS_DIAGNOSTIC_ONLY"
                else:
                    cohort_quality = "INVALID_GLOBAL_COHORT_BUCKETS"

        per_shard = []
        for i in range(args.shards):
            wire_in, wire_out, wire_bytes_in, wire_bytes_out, wire_windows = data_wire(i)
"""
SUMMARY_OLD="""            "per_shard": per_shard,
"""
SUMMARY_NEW="""            "per_shard": per_shard,
            "cohort_quality": cohort_quality,
            "cohort_start_us": cohort_start_us,
            "cohort_end_us": cohort_end_us,
            "cohort_seconds": cohort_seconds,
            "cohort_packets_sent": cohort_sent,
            "cohort_packets_received": cohort_received,
            "cohort_scope": "shared monotonic send-timestamp whole buckets, after all bbload teams Playing; NOT a production QoS pass",
"""

def one(s:str, old:str,new:str,label:str)->str:
    if s.count(old)!=1 or new in s:
        raise ValueError("V161 pinned original Qt cohort source drift: "+label)
    return s.replace(old,new,1)

def patch_bbload(s:str)->str:
    if ("SHYT_V158_NATIVE_QT_RECEIVE_DIAGNOSTICS" not in s or
            "SHYT_V159_ORIGINAL_TEAM_LOBBY_REFUSAL_DETAIL" not in s or
            "steady_since_us" not in s):
        raise ValueError("V161 requires staged V120+V158+V159 original Qt")
    for a,b,label in (
        (INCLUDE_OLD,INCLUDE_NEW,"Qt array JSON include"),
        (CLASS_OLD,CLASS_NEW,"all five seat Playing marker"),
        (SENT_OLD,SENT_NEW,"real sender entry timestamp bucket"),
        (RECEIVED_OLD,RECEIVED_NEW,"original sender timestamp on receiver"),
        (FINISH_OLD,FINISH_NEW,"original child JSON readiness and bucket totals")):
        s=one(s,a,b,label)
    return s

def patch_shards(s:str)->str:
    if ("SHYT-V155-ORIGINAL-QT-ANONYMOUS-DATA-WIRE" not in s or
            '"game_frame_decoded": sum(' not in s or
            '"team_unknown_other": sum(' not in s):
        raise ValueError("V161 requires staged V155+V158+V159 original shard")
    s=one(s,ANCHOR_AGG,PATCH_AGG,"global cohort readiness and original child counters")
    s=one(s,SUMMARY_OLD,SUMMARY_NEW,"durable separate cohort scores")
    return s

def git(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],
                                   text=True,stderr=subprocess.DEVNULL).strip()

def stage(root:Path)->None:
    root=root.resolve(strict=True)
    bb,shards=root/BB,root/SHARDS
    if (git(root,"rev-parse","HEAD")!=PIN or
            git(root,"rev-parse","HEAD:"+BB)!="edfb6ea39b898cca2638d65826981cf9fc81c334" or
            not bb.is_file() or bb.is_symlink() or
            not shards.is_file() or shards.is_symlink()):
        raise ValueError("V161 pinned original disposable YT1.3 Qt source required")
    cpp=patch_bbload(bb.read_text(encoding="utf-8"))
    py=patch_shards(shards.read_text(encoding="utf-8"))
    bb.write_text(cpp,encoding="utf-8")
    shards.write_text(py,encoding="utf-8")
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
    print("SHYT_V161_COHORT_WHOLE_SECONDS_SHARED_PACKET_CREATION_CLOCK_STAGED")

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: stage_global_cohort_v161.py DISPOSABLE_ORIGINAL_YT130")
    stage(Path(sys.argv[1]))
