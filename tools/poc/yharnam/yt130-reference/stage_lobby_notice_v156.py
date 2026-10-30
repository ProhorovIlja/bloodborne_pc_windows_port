#!/usr/bin/env python3
"""V156: count original YT1.3 lobby refusals by anonymous category in real bbload.

The original TeamLobby populates LobbyState.notice with a reason. Original
bbload ignores it, so 15 players still in Lobby cannot be attributed to a
missing remote directory entry, rate limit, or a different server refusal.
Stage AFTER pinned V141 five-player bbload instrumentation in a DISPOSABLE
checkout. Never print the notice text, usernames, IDs or raw network data.
"""
from pathlib import Path
import subprocess
import sys

PIN="0645740a33ae21c56df3b4a0d9777086dbca6053"
BLOB="edfb6ea39b898cca2638d65826981cf9fc81c334"
PATH=Path("server/loadtest/bbload.cpp")
MARKER="SHYT_V156_ANONYMOUS_LOBBY_NOTICE_CATEGORIES"
COUNTERS_OLD="""  quint64 refused = 0;
  quint64 untagged = 0; // datagrams from the server that did not open"""
COUNTERS_NEW="""  quint64 refused = 0;
  // SHYT_V156_ANONYMOUS_LOBBY_NOTICE_CATEGORIES. No raw notice text retained.
  quint64 team_name_absent = 0;
  quint64 team_name_ambiguous = 0;
  quint64 team_lookup_throttled = 0;
  quint64 team_other_notice = 0;
  quint64 team_total_notices = 0;
  quint64 untagged = 0; // datagrams from the server that did not open"""
TAKE_OLD="""  if (envelope.has_lobby_state()) {
    const bbcoop::LobbyState &lobby = envelope.lobby_state();
    if (lobby.has_team()) {"""
TAKE_NEW="""  if (envelope.has_lobby_state()) {
    const bbcoop::LobbyState &lobby = envelope.lobby_state();
    // Count the real original server's reason, never the names/IDs or text.
    // These events may be repeated if a client retransmits its request:
    // counts are reply observations, not unique affected players.
    if (!lobby.notice().empty()) {
      ++load.totals.team_total_notices;
      if (lobby.notice() == "no hunter of that name is online") {
        ++load.totals.team_name_absent;
      } else if (lobby.notice() == "several hunters have that name: give yours the team's code") {
        ++load.totals.team_name_ambiguous;
      } else if (lobby.notice() == "too many wrong codes or names: try again in a minute") {
        ++load.totals.team_lookup_throttled;
      } else {
        ++load.totals.team_other_notice;
      }
    }
    if (lobby.has_team()) {"""
OUT_OLD="""        {"refused", static_cast<double>(totals.refused)},
        {"untagged", static_cast<double>(totals.untagged)},"""
OUT_NEW="""        {"refused", static_cast<double>(totals.refused)},
        {"team_name_absent", static_cast<double>(totals.team_name_absent)},
        {"team_name_ambiguous", static_cast<double>(totals.team_name_ambiguous)},
        {"team_lookup_throttled", static_cast<double>(totals.team_lookup_throttled)},
        {"team_other_notice", static_cast<double>(totals.team_other_notice)},
        {"team_total_notices", static_cast<double>(totals.team_total_notices)},
        {"untagged", static_cast<double>(totals.untagged)},"""
SHARD_OLD="""            "playing": sum(r["playing"] for r in results),"""
SHARD_NEW="""            "playing": sum(r["playing"] for r in results),
            # V156 observed original TeamLobby::Request refusals, by category.
            "team_name_absent": sum(r["team_name_absent"] for r in results),
            "team_name_ambiguous": sum(r["team_name_ambiguous"] for r in results),
            "team_lookup_throttled": sum(r["team_lookup_throttled"] for r in results),
            "team_other_notice": sum(r["team_other_notice"] for r in results),
            "team_total_notices": sum(r["team_total_notices"] for r in results),"""

def once(s:str,old:str,new:str,name:str)->str:
    if s.count(old)!=1 or new in s:
        raise ValueError("V156 original source drift or duplicate: "+name)
    return s.replace(old,new,1)

def patch_bbload(s:str)->str:
    if MARKER in s or "udp_write_failed" not in s or "steady_packets_sent" not in s:
        raise ValueError("V156 must follow exact V141 original five-seat bbload")
    for a,b,label in ((COUNTERS_OLD,COUNTERS_NEW,"real loadgen Totals"),
                      (TAKE_OLD,TAKE_NEW,"real server LobbyState notice"),
                      (OUT_OLD,OUT_NEW,"original JSON report")):
        s=once(s,a,b,label)
    return s

def patch_shards(s:str)->str:
    if "SHYT-V155-ORIGINAL-QT-ANONYMOUS-DATA-WIRE" not in s:
        raise ValueError("V156 must follow V155 real Qt generator")
    if '"team_total_notices": sum(' in s:
        raise ValueError("V156 original shard generator already staged")
    return once(s,SHARD_OLD,SHARD_NEW,"hosted children notice aggregation")

def git(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True,
                                   stderr=subprocess.DEVNULL).strip()

def stage(root:Path)->None:
    root=root.resolve(strict=True)
    code=root/PATH
    gen=root/"server/loadtest/run_shards.py"
    if (git(root,"rev-parse","HEAD")!=PIN or
        git(root,"rev-parse","HEAD:"+PATH)!=BLOB or
        not code.is_file() or code.is_symlink() or
        not gen.is_file() or gen.is_symlink()):
        raise ValueError("V156 requires exact pristine commit, prior staging and regular files")
    a=patch_bbload(code.read_text(encoding="utf-8"))
    b=patch_shards(gen.read_text(encoding="utf-8"))
    # Both prospective files verified before committing either of them.
    code.write_text(a,encoding="utf-8")
    gen.write_text(b,encoding="utf-8")
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
    print("SHYT_V156_YT130_ANONYMOUS_REAL_LOBBY_REFUSAL_COUNTERS_STAGED_DIAG_ONLY")

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: stage_lobby_notice_v156.py DISPOSABLE_YT130_SOURCE")
    stage(Path(sys.argv[1]))
