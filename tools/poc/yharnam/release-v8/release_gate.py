#!/usr/bin/env python3
"""Create an UNPUBLISHED matched client+server release manifest. Never deploy."""
import argparse,hashlib,json,re
from pathlib import Path
PIN="77e350743a7cb4524cfcc1782fb6e3af64e25b15"
CHECKS=("client_native_build","server_native_build","gameplay_two_pc_join",
        "dbno_on_off_live","direct_udp_real_peers","relay_fallback_live",
        "quickplay_ping_actual_peers","staging_server_deployed",
        "staging_healthcheck","rollback_tested")
def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as src:
        for chunk in iter(lambda:src.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()
def contract(version,client,server,proof):
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-z0-9.-]+)?",version):raise ValueError("invalid version")
    if not client.is_file() or not server.is_file() or not client.name.lower().endswith("-setup.exe"):
        raise ValueError("matched client setup.exe and Linux server binary required")
    if proof.get("source_sha")!=PIN or proof.get("client_protocol")!=8 or proof.get("server_protocol")!=8 or proof.get("link_protocol")!=2:
        raise ValueError("wrong source or protocol: refused")
    for check in CHECKS:
        if proof.get("checks",{}).get(check) is not True:
            raise ValueError(f"missing passed integration check: {check}")
    if proof.get("installer_sha256")!=sha(client) or proof.get("server_sha256")!=sha(server):
        raise ValueError("client/server binary digest mismatch")
    return {"schema":1,"release_tag":"shyt-v"+version,
            "source_sha":PIN,"release_ready":True,"server_deployed":True,
            "client_protocol":8,"server_protocol":8,"link_protocol":2,
            "server_host":"199.195.193.131","installer":client.name,
            "installer_sha256":sha(client),"server_sha256":sha(server)}
def prepare(version,client,server,evidence,out):
    proof=json.loads(evidence.read_text("utf-8"))
    result=contract(version,client,server,proof)
    out.mkdir(parents=True,exist_ok=True)
    manifest=out/"seamless-hunt-release.json"
    checksum=out/(client.name+".sha256")
    if manifest.exists() or checksum.exists():raise ValueError("refusing to overwrite existing release files")
    manifest.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    checksum.write_text(result["installer_sha256"]+" *"+client.name+"\n",encoding="utf-8")
    print("REVIEW_ONLY (not published):",manifest)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for param in ("version","client","server","evidence","out"):
        p.add_argument("--"+param,required=True,type=str if param=="version" else Path)
    a=p.parse_args()
    prepare(a.version,a.client,a.server,a.evidence,a.out)
