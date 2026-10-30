#!/usr/bin/env python3
"""V158: original YT1.3 real bbload UDP receive and payload decode census.

Stage AFTER V141 five-hunter bbload and V156 lobby diagnostics. Preserve
existing networking/gameplay, 5-player rules, original server and privacy:
only aggregate counters, no IPs, auth tickets, names, packets, or bytes logged.
No QoS threshold relaxation. Source-exact original C++ anchors only.
"""
from pathlib import Path
import subprocess
import sys

PIN="0645740a33ae21c56df3b4a0d9777086dbca6053"
PATH="server/loadtest/bbload.cpp"
MARKER="SHYT_V158_NATIVE_QT_RECEIVE_DIAGNOSTICS"
TOTAL_OLD="""  quint64 datagrams_received = 0;
  quint64 refused = 0;"""
TOTAL_NEW="""  quint64 datagrams_received = 0;
  // SHYT_V158_NATIVE_QT_RECEIVE_DIAGNOSTICS: counters, never packet content.
  quint64 udp_read_failed = 0;
  quint64 udp_read_short = 0;
  quint64 game_data_datagrams_received = 0;
  quint64 game_data_decode_failed = 0;
  quint64 game_frame_decode_failed = 0;
  quint64 game_frame_bad_header = 0;
  quint64 game_frame_short_entries = 0;
  quint64 game_frame_decoded = 0;
  quint64 refused = 0;"""
READ_OLD="""    socket.readDatagram(datagram.data(), datagram.size(), &from, &from_port);
    if (from_port != port || from != server) {"""
READ_NEW="""    const qint64 bytes_read =
        socket.readDatagram(datagram.data(), datagram.size(), &from, &from_port);
    if (bytes_read < 0) {
      ++load.totals.udp_read_failed;
      continue;
    }
    if (bytes_read != datagram.size()) {
      ++load.totals.udp_read_short;
      continue;
    }
    if (from_port != port || from != server) {"""
DATA_OLD="""    case ServerLink::Kind::Data:
      if (const auto data = ServerLink::DecodeData(datagram)) {
        TakeData(data->frame, now_us);
      }
      break;"""
DATA_NEW="""    case ServerLink::Kind::Data:
      ++load.totals.game_data_datagrams_received;
      if (const auto data = ServerLink::DecodeData(datagram)) {
        TakeData(data->frame, now_us);
      } else {
        ++load.totals.game_data_decode_failed;
      }
      break;"""
FRAME_OLD="""  if (frame.size() < GameFrameAt || frame.mid(4, 4) != "SHAD") {
    return;
  }
  const auto game_frame = DecodeGameFrame(
      {reinterpret_cast<const u8 *>(frame.constData()) + GameFrameAt,
       static_cast<size_t>(frame.size() - GameFrameAt)});
  if (!game_frame) {
    return;
  }
  for (const GameFrameEntry &entry : game_frame->entries) {
    if (entry.packet.size() < 8 + 12) {
      continue;
    }"""
FRAME_NEW="""  if (frame.size() < GameFrameAt || frame.mid(4, 4) != "SHAD") {
    ++load.totals.game_frame_bad_header;
    return;
  }
  const auto game_frame = DecodeGameFrame(
      {reinterpret_cast<const u8 *>(frame.constData()) + GameFrameAt,
       static_cast<size_t>(frame.size() - GameFrameAt)});
  if (!game_frame) {
    ++load.totals.game_frame_decode_failed;
    return;
  }
  ++load.totals.game_frame_decoded;
  for (const GameFrameEntry &entry : game_frame->entries) {
    if (entry.packet.size() < 8 + 12) {
      ++load.totals.game_frame_short_entries;
      continue;
    }"""
OUTPUT_OLD="""        {"datagrams_received", static_cast<double>(totals.datagrams_received)},
        {"bytes_sent", static_cast<double>(totals.bytes_sent)},"""
OUTPUT_NEW="""        {"datagrams_received", static_cast<double>(totals.datagrams_received)},
        {"udp_read_failed", static_cast<double>(totals.udp_read_failed)},
        {"udp_read_short", static_cast<double>(totals.udp_read_short)},
        {"game_data_datagrams_received",
         static_cast<double>(totals.game_data_datagrams_received)},
        {"game_data_decode_failed", static_cast<double>(totals.game_data_decode_failed)},
        {"game_frame_decode_failed", static_cast<double>(totals.game_frame_decode_failed)},
        {"game_frame_bad_header", static_cast<double>(totals.game_frame_bad_header)},
        {"game_frame_short_entries", static_cast<double>(totals.game_frame_short_entries)},
        {"game_frame_decoded", static_cast<double>(totals.game_frame_decoded)},
        {"bytes_sent", static_cast<double>(totals.bytes_sent)},"""
AGG_OLD="""            "packets_received": sum(r["packets_received"] for r in results),"""
AGG_NEW="""            "packets_received": sum(r["packets_received"] for r in results),
            # V158 original Qt Game::OnReadyRead and TakeData decode observations.
            "udp_read_failed": sum(r["udp_read_failed"] for r in results),
            "udp_read_short": sum(r["udp_read_short"] for r in results),
            "game_data_datagrams_received": sum(r["game_data_datagrams_received"] for r in results),
            "game_data_decode_failed": sum(r["game_data_decode_failed"] for r in results),
            "game_frame_decode_failed": sum(r["game_frame_decode_failed"] for r in results),
            "game_frame_bad_header": sum(r["game_frame_bad_header"] for r in results),
            "game_frame_short_entries": sum(r["game_frame_short_entries"] for r in results),
            "game_frame_decoded": sum(r["game_frame_decoded"] for r in results),"""

def only_one(text:str,old:str,new:str,label:str)->str:
    if text.count(old)!=1 or new in text:
        raise ValueError("V158 original native Qt source drift: "+label)
    return text.replace(old,new,1)

def patch_load(source:str)->str:
    if "SHYT_V156_ANONYMOUS_LOBBY_NOTICE_CATEGORIES" not in source:
        raise ValueError("V158 requires real V141+V156 original Qt load generator")
    for a,b,label in (
        (TOTAL_OLD,TOTAL_NEW,"real Qt loadgen counters"),
        (READ_OLD,READ_NEW,"Qt readDatagram actual result"),
        (DATA_OLD,DATA_NEW,"real ServerLink Data decoder"),
        (FRAME_OLD,FRAME_NEW,"game-frame and entry decoders"),
        (OUTPUT_OLD,OUTPUT_NEW,"real original JSON output")):
        source=only_one(source,a,b,label)
    return source

def patch_shards(source:str)->str:
    if "SHYT-V155-ORIGINAL-QT-ANONYMOUS-DATA-WIRE" not in source or (
            '"team_total_notices": sum(' not in source):
        raise ValueError("V158 requires real V155+V156 shard generator")
    return only_one(source,AGG_OLD,AGG_NEW,"original hosted Qt load generator summary")

def git(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],
                                   text=True,stderr=subprocess.DEVNULL).strip()

def stage(root:Path)->None:
    root=root.resolve(strict=True)
    load=root/PATH
    shards=root/"server/loadtest/run_shards.py"
    if (git(root,"rev-parse","HEAD")!=PIN or
            not load.is_file() or load.is_symlink() or
            not shards.is_file() or shards.is_symlink()):
        raise ValueError("V158 requires disposable exact original YT1.3 checkout")
    new_load=patch_load(load.read_text(encoding="utf-8"))
    new_shards=patch_shards(shards.read_text(encoding="utf-8"))
    # All source checks happen before either file is modified.
    load.write_text(new_load,encoding="utf-8")
    shards.write_text(new_shards,encoding="utf-8")
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
    print("SHYT_V158_ORIGINAL_QT_UDP_READ_AND_GAME_FRAME_DECODE_COUNTERS_STAGED")

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: stage_qt_receive_v158.py DISPOSABLE_YT130_CHECKOUT")
    stage(Path(sys.argv[1]))
