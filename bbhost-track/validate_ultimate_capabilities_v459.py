#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V459: fail closed when cross-project best-of plans silently duplicate state owners.

This validates an architectural ownership REGISTER, not actual code or game
execution. Shipping still requires original sources, builds, game clients,
network/load tests, authorization audits and signed runtime evidence.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().with_name("ultimate_capability_ownership_v459.json")
REQUIRED={
 "net.transport.udp_socket":"bbhost",
 "net.gameframe.routing":"yt-server",
 "net.session.auth_identity":"yt-shadnet",
 "world.team.progress":"yt-server",
 "world.session.membership":"yt-server",
 "graphics.vulkan.renderer":"bbhost",
 "graphics.fps.pacing":"bbhost",
 "runtime.guest_memory.permissions":"bbhost",
 "save.personal_character":"bbhost",
 "save.team_world_log":"yt-server",
 "gameplay.trade.transactions":"yt-server",
 "gameplay.mod_event_patches":"yt-launcher",
 "launcher.settings_authority":"yt-launcher",
 "gameplay.hud_party":"yt-game",
}
PINS={
 "bbhost":"bdc5cdf8be5f37188da9c2368e92be444fdc04cb",
 "yt":"efa0ad265d840d9195e55db2e3216f46f7daedd0",
 "cls":"7c00d46f01b67ff1cf12cef346c245960b627141a9c1047d00e2ceadd167ca04",
 "pr85":"de28395180484960b095d00535e008b6025bd13f",
 "visy":"11cc47537fd4",
 "libjuice":"b89c792e3612faf2f12cf35bcc56857313a06be3",
}
DECISIONS={
 "disabled_candidate_replace_only","disabled_extension","opt_in_bugfix",
 "disabled_bugfix","candidate_bugfix_if_reproducible",
 "adapter_not_parallel_route","adapter_not_parallel_authority",
 "concepts_only_no_parallel_writer","concepts_only_no_parallel_renderer",
 "concepts_only_no_parallel_frameclock",
 "concepts_only_no_parallel_world_persistence",
 "disabled_launcher_extension","concepts_only_no_parallel_ui",
 "concepts_only_no_parallel_overlay",
}
LAYERS={"host-network-adapter","routing-policy","authenticated-control",
        "authoritative-world","game-session-authority","runtime-graphics",
        "engine-runtime","host-memory-adapter","game-io-adapter",
        "authoritative-persistence","gameplay-authority","launcher-setup",
        "launcher-ui","gameplay-display"}
ID=re.compile(r"^[a-z][a-z0-9_-]{2,80}$")
DOMAIN=re.compile(r"^[a-z]+\.[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")

def fail(msg:str)->None:
    raise ValueError("SHYT_V459_DUPLICATION_POLICY_REFUSED "+msg)

def string(value:object,field:str,minlen:int=1,maxlen:int=1000)->str:
    if not isinstance(value,str) or not(minlen<=len(value)<=maxlen):
        fail(field+" missing/too large")
    return value

def url(value:object,field:str)->str:
    v=string(value,field,12,400)
    if not v.startswith("https://github.com/") and not v.startswith("https://www.rfc-editor.org/"):
        fail(field+" not an approved auditable source")
    return v

def validate(data:object)->dict[str,int]:
    if not isinstance(data,dict) or data.get("schema")!="SHYT_V459_ONE_CAPABILITY_ONE_AUTHORITY":
        fail("unknown schema")
    pins=data.get("source_pins")
    if not isinstance(pins,dict) or pins!=PINS:
        fail("floating or missing original source pins")
    if set(data.get("allowed_decisions",[]))!=DECISIONS:
        fail("approved candidate-action vocabulary drift")
    notice=string(data.get("status_notice"),"scope limitations",80,500)
    if "not proof" not in notice:
        fail("must disclaim claims about game integration")
    caps=data.get("capabilities")
    if not isinstance(caps,list) or len(caps)>70 or len(caps)<len(REQUIRED):
        fail("empty, truncated or oversized owner matrix")
    domains=set()
    ids=set()
    alt_ids=set()
    known={}
    alternatives=0
    for row in caps:
        if not isinstance(row,dict):
            fail("non-object capability")
        cap=string(row.get("id"),"capability id")
        domain=string(row.get("domain"),"ownership domain")
        if not ID.fullmatch(cap) or not DOMAIN.fullmatch(domain):
            fail("unbounded capability/domain identifier")
        if cap in ids or domain in domains:
            fail("duplicate active capability or resource domain: "+domain)
        ids.add(cap)
        domains.add(domain)
        selected=row.get("selected")
        if not isinstance(selected,dict):
            fail("capability has no single selected owner: "+domain)
        owner=string(selected.get("owner"),"selected owner")
        impl=string(selected.get("implementation"),"selected implementation",8)
        if selected.get("layer") not in LAYERS:
            fail("unknown owner layer: "+domain)
        state=string(selected.get("status"),"integration proof state")
        if state in ("production","integrated","fully_playable","verified_live"):
            fail("unproven production/in-game success claim")
        known[domain]=owner
        if len(row.get("evidence",[]))<1 or len(row.get("acceptance_tests",[]))<1:
            fail("missing original-source evidence or proposed validation: "+domain)
        if not isinstance(row["evidence"],list) or not isinstance(row["acceptance_tests"],list):
            fail("invalid proof list: "+domain)
        for item in row["evidence"]:
            url(item,"source evidence")
        for item in row["acceptance_tests"]:
            string(item,"acceptance regression",14,420)
        alts=row.get("alternatives")
        if not isinstance(alts,list) or not alts or len(alts)>10:
            fail("no explicit preserve/replace/extend comparison: "+domain)
        for candidate in alts:
            if not isinstance(candidate,dict):
                fail("non-object alternative")
            altid=string(candidate.get("id"),"source alternative")
            if not ID.fullmatch(altid) or altid in alt_ids or altid==cap:
                fail("duplicate or invalid source alternative: "+altid)
            alt_ids.add(altid)
            origin=string(candidate.get("source"),"upstream provenance",10,160)
            decision=string(candidate.get("decision"),"migration decision")
            if decision not in DECISIONS:
                fail("active duplicate or unreviewed migration: "+altid)
            reason=string(candidate.get("reason"),"comparison and precedence",50,600)
            gate=string(candidate.get("acceptance_gate"),"tested upgrade gate",25,600)
            rollback=string(candidate.get("rollback"),"safe previous owner",12,200)
            if not any(x in origin for x in ("/","#","@")):
                fail("candidate lacks auditable source identity: "+altid)
            if rollback==origin:
                fail("unsafe migration without rollback")
            alternatives+=1
    if known!=REQUIRED:
        missing=sorted(set(REQUIRED)-set(known))
        added=sorted(set(known)-set(REQUIRED))
        replaced=[d for d in REQUIRED.keys()&known.keys() if REQUIRED[d]!=known[d]]
        fail("authority change needs separate code+test review: "+repr((missing,added,replaced)))
    if alternatives<20:
        fail("candidate comparison prematurely truncated")
    return {"capabilities":len(caps),"alternatives":alternatives,"authority_domains":len(domains)}

def test_negative(data:dict)->None:
    tests=[
        ("duplicate ownership domain",lambda c:c["capabilities"].append(copy.deepcopy(c["capabilities"][0]))),
        ("duplicate alternate id",lambda c:c["capabilities"][1]["alternatives"].append(copy.deepcopy(c["capabilities"][0]["alternatives"][0]))),
        ("active unreviewed parallel route",lambda c:c["capabilities"][1]["alternatives"][0].update({"decision":"enable_parallel_transport"})),
        ("unverified world replacement",lambda c:c["capabilities"][3]["selected"].update({"owner":"visy"})),
        ("unreviewed floating source",lambda c:c["source_pins"].update({"bbhost":"main"})),
        ("no acceptance tests",lambda c:c["capabilities"][8].update({"acceptance_tests":[]})),
        ("no rollback",lambda c:c["capabilities"][2]["alternatives"][0].update({"rollback":""})),
        ("silent false production claim",lambda c:c["capabilities"][6]["selected"].update({"status":"fully_playable"})),
        ("missing capability",lambda c:c["capabilities"].pop()),
        ("missing provenance",lambda c:c["capabilities"][0]["alternatives"][0].update({"source":"guess"})),
    ]
    for label,change in tests:
        subject=copy.deepcopy(data)
        change(subject)
        try:
            validate(subject)
        except ValueError:
            continue
        raise AssertionError("V459 mistakenly accepted "+label)
    print("SHYT_V459_TEN_NEGATIVE_DUPLICATE_AUTHORITY_REGRESSIONS_PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--matrix",type=Path,default=ROOT)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    data=json.loads(a.matrix.read_text(encoding="utf-8"))
    counts=validate(data)
    if a.self_test:test_negative(data)
    print("SHYT_V459_SINGLE_AUTHORITY_CAPABILITY_GATE_PASS")
    print("SHYT_V459_COUNTS",json.dumps(counts,sort_keys=True))
    print("SHYT_V459_CANDIDATES_ONLY_NO_CLIENT_OR_SERVER_DEPLOYMENT")

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,json.JSONDecodeError) as error:
        sys.exit(str(error))
