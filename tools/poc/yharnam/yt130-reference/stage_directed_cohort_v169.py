#!/usr/bin/env python3
"""Optional source-exact V169 directed synthetic bbload QoS evidence (YT1.3).

Stage ONLY after V161 on a disposable pinned original YT1.3 checkout.
Per-team/seat route numbers are synthetic load-generator indices, never game
account IDs, real online identifiers, IPs, or player packet bytes.
No gameplay or production server changes. This is an extra diagnostic, not a
release QoS claim. Its overhead is part of the load-generator, not server CPU.
"""
from pathlib import Path
import subprocess
import sys

PIN='0645740a33ae21c56df3b4a0d9777086dbca6053'
BB='server/loadtest/bbload.cpp'
SHARDS='server/loadtest/run_shards.py'
MARK='SHYT_V169_SYNTHETIC_DIRECTED_GAME_COHORT'
CLASS_OLD='  std::map<s64, std::pair<quint64, quint64>> cohort_epoch_entries;\n'
CLASS_NEW=CLASS_OLD+('  // '+MARK+': synthetic local seat-pair indices only.\n'
  '  std::map<std::pair<s64, u32>, std::pair<quint64, quint64>> cohort_pair_entries;\n'
  '  quint64 cohort_unknown_senders = 0;\n'
  '  // One 64-sequence receipt bitmap per synthetic directed route.\n'
  '  std::map<u32, std::pair<u32, u64>> cohort_seen_sequences;\n'
  '  quint64 cohort_nonunique_receipts = 0;\n'
  '  // Source-send-time seconds for all-run errors, to isolate stable QoS.\n'
  '  std::map<s64, std::pair<quint64, quint64>> cohort_bad_epochs;\n')
GAME_SEAT_FIELD_OLD = '  int seat;\n'
GAME_SEAT_FIELD_NEW = GAME_SEAT_FIELD_OLD+('  // Synthetic team names remain in this process, never exported.\n'
  '  std::vector<std::string> cohort_sender_names;\n')
GAME_CTOR_OLD = '''  QObject::connect(&socket, &QUdpSocket::readyRead, [this] { OnReadyRead(); });
'''
GAME_CTOR_NEW = '''  // Cache stable synthetic team names once, not four string allocations per
  // decoded game packet at 200-player worst-case owner traffic.
  cohort_sender_names.reserve(load.settings.team_size);
  for (int sender_seat = 0; sender_seat < load.settings.team_size; ++sender_seat)
    cohort_sender_names.push_back(load.NameOf(team, sender_seat));
'''+GAME_CTOR_OLD
SEQ_HELPER = '''// Source-locked V170: O(1) bounded exact-duplicate receipt tracking.
// The original bbload sequence is independent per sender->destination.
bool FreshDirectedSequence(u32 seq, std::pair<u32, u64>& window) {
  if (seq == 0) return false;
  if (window.first == 0) {
    window = {seq, 1};
    return true;
  }
  if (seq > window.first) {
    const u32 shift = seq - window.first;
    window.second = shift >= 64 ? 1 : (window.second << shift) | 1;
    window.first = seq;
    return true;
  }
  const u32 lag = window.first - seq;
  if (lag >= 64) return false;
  const u64 bit = u64{1} << lag;
  if (window.second & bit) return false;
  window.second |= bit;
  return true;
}

'''
SEQ_ANCHOR = 'void Game::SendGamePackets(s64 now_us) {\n'
SEND_OLD='''    load.cohort_epoch_entries[(now_us / 1'000'000) * 1'000'000].first +=
        static_cast<quint64>(frame.entries.size());
'''
SEND_NEW=SEND_OLD+'''    const u32 route = static_cast<u32>(
        (team * load.settings.team_size + seat) * load.settings.team_size + other);
    load.cohort_pair_entries[{(now_us / 1'000'000) * 1'000'000, route}].first +=
        static_cast<quint64>(frame.entries.size());
'''
RECEIVED_OLD='''    load.cohort_epoch_entries[(static_cast<s64>(sent) / 1'000'000) * 1'000'000].second++;
'''
RECEIVED_NEW=RECEIVED_OLD+'''    // The original frame's synthetic sender name stays in process memory.
    // Export ONLY its bounded integer seat-pair index, never the name.
    int sender_seat = -1;
    for (int candidate = 0; candidate < load.settings.team_size; ++candidate) {
      if (candidate != seat && game_frame->sender == cohort_sender_names[candidate]) {
        sender_seat = candidate;
        break;
      }
    }
    const s64 sent_bucket = (static_cast<s64>(sent) / 1'000'000) * 1'000'000;
    if (sender_seat < 0) {
      ++load.cohort_unknown_senders;
      ++load.cohort_bad_epochs[sent_bucket].first;
    } else {
      const u32 route = static_cast<u32>(
          (team * load.settings.team_size + sender_seat) * load.settings.team_size + seat);
      if (FreshDirectedSequence(seq, load.cohort_seen_sequences[route])) {
        load.cohort_pair_entries[{(static_cast<s64>(sent) / 1'000'000) * 1'000'000,
                                  route}].second++;
      } else {
        // Duplicate or >64-packet reordering is not a second delivery.
        ++load.cohort_nonunique_receipts;
        ++load.cohort_bad_epochs[sent_bucket].second;
      }
    }
'''
FINISH_OLD='''    const double seconds = (NowUs() - started_us) / 1e6;
    QJsonObject out{
'''
FINISH_NEW='''    QJsonArray directed_json;
    for (const auto& [key, counts] : cohort_pair_entries) {
      directed_json.append(QJsonObject{
          {"start_us", static_cast<double>(key.first)},
          {"route", static_cast<double>(key.second)},
          {"sent_entries", static_cast<double>(counts.first)},
          {"received_entries", static_cast<double>(counts.second)}});
    }
    // These errors are counted across ALL phases for diagnostics, but only
    // their send-time overlap with the global steady cohort can fail QoS.
    QJsonArray bad_epoch_json;
    for (const auto& [stamp, counts] : cohort_bad_epochs) {
      bad_epoch_json.append(QJsonObject{
          {"start_us", static_cast<double>(stamp)},
          {"unknown_senders", static_cast<double>(counts.first)},
          {"nonunique_receipts", static_cast<double>(counts.second)}});
    }
'''+FINISH_OLD
JSON_OLD='''        {"cohort_epoch_entries", cohort_json},
'''
JSON_NEW=JSON_OLD+'''        {"cohort_directed_entries", directed_json},
        {"cohort_unknown_senders", static_cast<double>(cohort_unknown_senders)},
        {"cohort_nonunique_receipts", static_cast<double>(cohort_nonunique_receipts)},
        {"cohort_bad_epoch_entries", bad_epoch_json},
'''
RUN_ANCHOR='''        per_shard = []
        for i in range(args.shards):
            wire_in, wire_out, wire_bytes_in, wire_bytes_out, wire_windows = data_wire(i)
'''
DIRECTED_AGG='''        # SHYT_V169_SYNTHETIC_DIRECTED_GAME_COHORT (synthetic integers only)
        # Every directed sender->receiver pair across EVERY full cohort second
        # must be present. This detects one lossy low-volume pair that the
        # aggregate >=99% delivery might otherwise obscure. Unknown frame
        # senders, unowned routes and duplicate epochs fail closed.
        directed_quality = "NO_VERIFIED_DIRECTED_GAME_COHORT"
        directed_sent = directed_received = directed_routes = 0
        if cohort_quality in ("GLOBAL_GAME_COHORT_PASS_DIAGNOSTIC_ONLY",
                              "GLOBAL_GAME_COHORT_DELIVERY_DEGRADED"):
            directed_valid = True
            directed_loss = False
            directed_expected = {}
            for worker_index, r in enumerate(results):
                n = args.team_size
                # Original run_shards assigns complete synthetic teams to
                # children in order, keeping their local indices in each.
                worker_teams = per[worker_index]
                rows = r.get("cohort_directed_entries")
                unknown = r.get("cohort_unknown_senders")
                nonunique = r.get("cohort_nonunique_receipts")
                bad_rows = r.get("cohort_bad_epoch_entries")
                if (type(rows) is not list or type(bad_rows) is not list or
                        any(type(v) not in (int, float) or
                            not (0 <= v < 2**53) or int(v) != v
                            for v in (unknown, nonunique)) or worker_teams <= 0):
                    directed_valid = False
                    break
                bad_unknown = bad_nonunique = 0
                bad_seen = set()
                for bad in bad_rows:
                    if (type(bad) is not dict or
                            set(bad) != {"start_us", "unknown_senders", "nonunique_receipts"} or
                            any(type(bad.get(k)) not in (int, float) or
                                not (0 <= bad[k] < 2**53) or int(bad[k]) != bad[k]
                                for k in ("start_us", "unknown_senders", "nonunique_receipts"))):
                        directed_valid = False
                        break
                    bad_sec = int(bad["start_us"])
                    if (bad_sec % 1_000_000 or bad_sec in bad_seen or
                            int(bad["unknown_senders"]) + int(bad["nonunique_receipts"]) == 0):
                        directed_valid = False
                        break
                    bad_seen.add(bad_sec)
                    bad_unknown += int(bad["unknown_senders"])
                    bad_nonunique += int(bad["nonunique_receipts"])
                    if cohort_start_us <= bad_sec < cohort_end_us:
                        directed_valid = False
                        break
                if (not directed_valid or bad_unknown != unknown or
                        bad_nonunique != nonunique):
                    directed_valid = False
                    break
                seen = set()
                sent_by_second = {}
                received_by_second = {}
                for item in rows:
                    if (type(item) is not dict or
                            set(item) != {"start_us", "route", "sent_entries", "received_entries"} or
                            any(type(item.get(k)) not in (int, float) or
                                not (0 <= item[k] < 2**53) or int(item[k]) != item[k]
                                for k in ("start_us", "route", "sent_entries", "received_entries"))):
                        directed_valid = False
                        break
                    sec = int(item["start_us"])
                    route = int(item["route"])
                    team, within = divmod(route, n*n)
                    src, dst = divmod(within, n)
                    if (sec % 1_000_000 or team >= worker_teams or
                            src == dst or route < 0):
                        directed_valid = False
                        break
                    if not cohort_start_us <= sec < cohort_end_us:
                        continue
                    key = (sec, route)
                    if key in seen or item["sent_entries"] <= 0:
                        directed_valid = False
                        break
                    seen.add(key)
                    sent = int(item["sent_entries"])
                    received = int(item["received_entries"])
                    if received > sent:
                        directed_valid = False
                        break
                    directed_sent += sent
                    directed_received += received
                    if received * 100 < sent * 99:
                        directed_loss = True
                    sent_by_second[sec] = sent_by_second.get(sec, 0) + sent
                    received_by_second[sec] = received_by_second.get(sec, 0) + received
                if not directed_valid:
                    break
                # Every synthetic directed pair sends in every full second.
                expected_routes = {((team*n + src)*n + dst)
                                   for team in range(worker_teams)
                                   for src in range(n) for dst in range(n)
                                   if src != dst}
                directed_routes += len(expected_routes)
                expected_seen = {(sec, route)
                                 for sec in range(cohort_start_us, cohort_end_us, 1_000_000)
                                 for route in expected_routes}
                if seen != expected_seen:
                    directed_valid = False
                    break
                # Cross-check all routed entries against the original V161
                # per-worker buckets. Otherwise a fabricated pair census
                # could score green without representing all source packets.
                for item in r["cohort_epoch_entries"]:
                    sec = int(item["start_us"])
                    if cohort_start_us <= sec < cohort_end_us and (
                            sent_by_second.get(sec, 0) != int(item["sent_entries"]) or
                            received_by_second.get(sec, 0) != int(item["received_entries"])):
                        directed_valid = False
                        break
                if not directed_valid:
                    break
            if (not directed_valid or directed_sent != cohort_sent or
                    directed_received != cohort_received):
                directed_quality = "INVALID_DIRECTED_GAME_COHORT"
                directed_sent = directed_received = directed_routes = 0
            elif directed_loss:
                directed_quality = "DIRECTED_GAME_COHORT_DELIVERY_DEGRADED"
            else:
                directed_quality = "DIRECTED_GAME_COHORT_PASS_DIAGNOSTIC_ONLY"

'''
SUMMARY_OLD='''            "cohort_scope": "shared monotonic send-timestamp whole buckets, after all bbload teams Playing; NOT a production QoS pass",
'''
SUMMARY_NEW=SUMMARY_OLD+'''            "directed_quality": directed_quality,
            "directed_packets_sent": directed_sent,
            "directed_packets_received": directed_received,
            "directed_routes": directed_routes,
            "directed_scope": "anonymous synthetic team/seat flow counters, source-clock aligned; NOT a production QoS pass",
'''

def exactly(s,old,new,label):
    if old==new or s.count(old)!=1 or new in s:
        raise ValueError('V169 original source drift: '+label)
    return s.replace(old,new,1)

def patch_cpp(s):
    if ('SHYT_V161_GLOBAL_COHORT_SEND_TIMESTAMP_BUCKETS' not in s or
            'SHYT_V158_NATIVE_QT_RECEIVE_DIAGNOSTICS' not in s):
        raise ValueError('V169 requires already staged original Qt V161')
    s=exactly(s,SEQ_ANCHOR,SEQ_HELPER+SEQ_ANCHOR,
              'original Qt 64-sequence fixed-bitmap de-duplication')
    for before,after,label in (
            (GAME_SEAT_FIELD_OLD,GAME_SEAT_FIELD_NEW,'source-exact Game synthetic name cache'),
            (GAME_CTOR_OLD,GAME_CTOR_NEW,'only once at Game construction'),
            (CLASS_OLD,CLASS_NEW,'synthetic seat-pair ledger'),
            (SEND_OLD,SEND_NEW,'original Game::SendGamePackets exact frame entries'),
            (RECEIVED_OLD,RECEIVED_NEW,'original decoded Game::TakeData sender'),
            (FINISH_OLD,FINISH_NEW,'original Qt per-flow JSON output'),
            (JSON_OLD,JSON_NEW,'bounded original synthetic flow JSON fields')):
        s=exactly(s,before,after,label)
    return s

def patch_shards(s):
    if ('SHYT_V161_GLOBAL_COHORT_SEND_TIMESTAMP_BUCKETS' not in s or
            'if load.returncode != 0 or len(child_rows) != 1:' not in s):
        raise ValueError('V169 needs validated successful child JSON and V161 original source')
    s=exactly(s,RUN_ANCHOR,DIRECTED_AGG+RUN_ANCHOR,'per-flow source-clock aggregate')
    return exactly(s,SUMMARY_OLD,SUMMARY_NEW,'durable directed comparison')

def stage(root):
    root=Path(root).resolve(strict=True)
    if subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()!=PIN:
        raise ValueError('V169 only the pinned YT1.3 source checkout')
    old_cpp=(root/BB).read_text(encoding='utf-8')
    old_shards=(root/SHARDS).read_text(encoding='utf-8')
    cpp=patch_cpp(old_cpp)
    shards=patch_shards(old_shards)
    # Validate BOTH full source candidates before any writes.
    (root/BB).write_text(cpp,encoding='utf-8')
    (root/SHARDS).write_text(shards,encoding='utf-8')
    subprocess.run(['git','-C',str(root),'diff','--check'],check=True)
    print('SHYT_V169_SOURCE_PINNED_ANON_DIRECTED_GAME_QOS_STAGED_NOT_PLAYTEST')

if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('usage: stage_directed_cohort_v169.py DISPOSABLE_ORIGINAL_YT130')
    stage(sys.argv[1])
