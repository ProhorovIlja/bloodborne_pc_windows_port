#!/usr/bin/env python3
"""V159: classify previously opaque original YT1.3 TeamLobby notices.

After V156, repeated 'other' notices during high-concurrency invites cannot
distinguish expected retries from real missing/expired invites or full teams.
Use ONLY exact public original TeamLobby refusal constants; emit aggregate
categories, never raw notice values, account names, team codes or IPs.
"""
from pathlib import Path
import subprocess
import sys

PIN="0645740a33ae21c56df3b4a0d9777086dbca6053"
PATH="server/loadtest/bbload.cpp"
MARK="SHYT_V159_ORIGINAL_TEAM_LOBBY_REFUSAL_DETAIL"
C_OLD="""  quint64 team_other_notice = 0;
  quint64 team_total_notices = 0;"""
C_NEW="""  quint64 team_other_notice = 0;
  // SHYT_V159_ORIGINAL_TEAM_LOBBY_REFUSAL_DETAIL: no raw player data.
  quint64 team_no_invite = 0;
  quint64 team_no_code = 0;
  quint64 team_full = 0;
  quint64 team_already_joined = 0;
  quint64 team_create_first = 0;
  quint64 team_world_unavailable = 0;
  quint64 team_unknown_other = 0;
  quint64 team_total_notices = 0;"""
D_OLD="""      } else {
        ++load.totals.team_other_notice;
      }
    }
    if (lobby.has_team()) {"""
D_NEW="""      } else {
        ++load.totals.team_other_notice;
        if (lobby.notice() == "no such invite") {
          ++load.totals.team_no_invite;
        } else if (lobby.notice() == "no team has that code") {
          ++load.totals.team_no_code;
        } else if (lobby.notice() == "the team is full") {
          ++load.totals.team_full;
        } else if (lobby.notice() == "you are in a team already: leave it first" ||
                   lobby.notice() == "already in your team") {
          ++load.totals.team_already_joined;
        } else if (lobby.notice() == "create a team first") {
          ++load.totals.team_create_first;
        } else if (lobby.notice() == "that team is gone" ||
                   lobby.notice() == "another team plays that world now") {
          ++load.totals.team_world_unavailable;
        } else {
          ++load.totals.team_unknown_other;
        }
      }
    }
    if (lobby.has_team()) {"""
OUT_OLD="""        {"team_other_notice", static_cast<double>(totals.team_other_notice)},
        {"team_total_notices", static_cast<double>(totals.team_total_notices)},"""
OUT_NEW="""        {"team_other_notice", static_cast<double>(totals.team_other_notice)},
        {"team_no_invite", static_cast<double>(totals.team_no_invite)},
        {"team_no_code", static_cast<double>(totals.team_no_code)},
        {"team_full", static_cast<double>(totals.team_full)},
        {"team_already_joined", static_cast<double>(totals.team_already_joined)},
        {"team_create_first", static_cast<double>(totals.team_create_first)},
        {"team_world_unavailable", static_cast<double>(totals.team_world_unavailable)},
        {"team_unknown_other", static_cast<double>(totals.team_unknown_other)},
        {"team_total_notices", static_cast<double>(totals.team_total_notices)},"""
SHARDS_OLD="""            "team_other_notice": sum(r["team_other_notice"] for r in results),
            "team_total_notices": sum(r["team_total_notices"] for r in results),"""
SHARDS_NEW="""            "team_other_notice": sum(r["team_other_notice"] for r in results),
            "team_no_invite": sum(r["team_no_invite"] for r in results),
            "team_no_code": sum(r["team_no_code"] for r in results),
            "team_full": sum(r["team_full"] for r in results),
            "team_already_joined": sum(r["team_already_joined"] for r in results),
            "team_create_first": sum(r["team_create_first"] for r in results),
            "team_world_unavailable": sum(r["team_world_unavailable"] for r in results),
            "team_unknown_other": sum(r["team_unknown_other"] for r in results),
            "team_total_notices": sum(r["team_total_notices"] for r in results),"""

def one(text:str,old:str,new:str,label:str)->str:
    if text.count(old)!=1 or new in text:
        raise ValueError("V159 pinned YT original source drift: "+label)
    return text.replace(old,new,1)

def patch_load(s:str)->str:
    if "SHYT_V156_ANONYMOUS_LOBBY_NOTICE_CATEGORIES" not in s:
        raise ValueError("V159 requires previous real original V156 notices")
    for a,b,why in ((C_OLD,C_NEW,"original Qt totals"),
                    (D_OLD,D_NEW,"original Qt lobby notice categorization"),
                    (OUT_OLD,OUT_NEW,"Qt numeric JSON")):
        s=one(s,a,b,why)
    return s

def patch_shards(s:str)->str:
    if "SHYT-V155-ORIGINAL-QT-ANONYMOUS-DATA-WIRE" not in s or (
            '"team_total_notices": sum(' not in s):
        raise ValueError("V159 requires exact original V155+V156 shard generator")
    return one(s,SHARDS_OLD,SHARDS_NEW,"real shard generator numeric summary")

def git(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],
                                   text=True,stderr=subprocess.DEVNULL).strip()

def stage(root:Path)->None:
    root=root.resolve(strict=True)
    f=root/PATH
    shard=root/"server/loadtest/run_shards.py"
    if (git(root,"rev-parse","HEAD")!=PIN or
            not f.is_file() or f.is_symlink() or
            not shard.is_file() or shard.is_symlink()):
        raise ValueError("V159 requires disposable pinned original YT1.3 checkout")
    rewritten=patch_load(f.read_text(encoding="utf-8"))
    rewritten_shard=patch_shards(shard.read_text(encoding="utf-8"))
    f.write_text(rewritten,encoding="utf-8")
    shard.write_text(rewritten_shard,encoding="utf-8")
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
    print("SHYT_V159_ANONYMOUS_TEAM_LOBBY_OTHER_REASON_CATEGORIES_STAGED")

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: stage_lobby_notice_detail_v159.py PINNED_DISPOSABLE_SOURCE")
    stage(Path(sys.argv[1]))
