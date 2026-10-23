#!/usr/bin/env python3
"""Pinned Yharnam Together launcher updater source generator: our GitHub only."""
import argparse, ast, pathlib, subprocess
PIN="77e350743a7cb4524cfcc1782fb6e3af64e25b15"
REPO_ID=1429375055
CHANNEL="shyt-v"
def once(s,old,new,label):
    n=s.count(old)
    if n!=1:raise ValueError(f"{label}: upstream source anchor count {n} (expected 1)")
    return s.replace(old,new,1)
COMPAT="""
def sh_compatibility_release(release,timeout=15):
    if release is None or not release.get('manifest') or not release.get('setup') or not release.get('sha256'):
        return None
    req=urllib.request.Request(release['manifest'],headers={'Accept':'application/json',
                                                             'User-Agent':'Seamless-Hunt-launcher'})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        meta=json.loads(response.read(32768).decode('utf-8'))
    if not isinstance(meta,dict):return None
    if meta.get('schema')!=1 or meta.get('release_tag')!=SH_RELEASE_PREFIX+release['version']:return None
    if meta.get('client_protocol')!=SH_SERVER_PROTO or meta.get('server_protocol')!=SH_SERVER_PROTO:return None
    if meta.get('link_protocol')!=SH_LINK_PROTO or meta.get('server_host')!=SH_SERVER_HOST:return None
    if meta.get('release_ready') is not True or meta.get('server_deployed') is not True:return None
    if meta.get('installer')!=release['name'] or not re.fullmatch(r'[0-9a-f]{64}',str(meta.get('installer_sha256',''))):return None
    if not re.fullmatch(r'[0-9a-f]{64}',str(meta.get('server_sha256',''))):return None
    return dict(release,channel_manifest=meta)
"""
def patch_coop(s):
    s=once(s,"RELEASES_API = 'https://api.github.com/repositories/1405692683/releases?per_page=100'",
       "SH_RELEASE_PREFIX = 'shyt-v'\nSH_MANIFEST_NAME = 'seamless-hunt-release.json'\nSH_SERVER_PROTO = 8\nSH_LINK_PROTO = 2\nSH_SERVER_HOST = '199.195.193.131'\nRELEASES_API = 'https://api.github.com/repositories/1429375055/releases?per_page=100'","repo ID")
    s=once(s,"        if not setup or not assets.get(setup + '.sha256'):\n            continue",
      "        if not setup or not assets.get(setup + '.sha256') or not assets.get(SH_MANIFEST_NAME):\n            continue","installer assets")
    s=once(s,"                    'name': setup}","                    'name': setup, 'manifest': assets[SH_MANIFEST_NAME]}","manifest URL")
    old="        version = release['tag_name'].lstrip('v')\n        if not version_key(version)[0]:\n            continue"
    new="        if not release['tag_name'].startswith(SH_RELEASE_PREFIX):\n            continue\n        version = release['tag_name'][len(SH_RELEASE_PREFIX):]\n        if not version_key(version)[0]:\n            continue"
    if s.count(old)!=2:raise ValueError("release lookup and changelog anchor mismatch")
    s=s.replace(old,new)
    s=once(s,"\ndef fetch_newest_release(timeout=15):",COMPAT+"\ndef fetch_newest_release(timeout=15):","compatibility validator")
    s=once(s,"    return newest_release(fetch_releases(timeout))",
           "    return sh_compatibility_release(newest_release(fetch_releases(timeout)),timeout)","guard update")
    ast.parse(s);return s
def patch_launcher(s):
    s=once(s,"('bbport-launcher-coop' if COOP_TEST else 'bbport-launcher')",
      "('bbport-launcher-coop-seamlesshunt' if COOP_TEST else 'bbport-launcher-seamlesshunt')","profile")
    # Keep Yharnam's co-op updater/patch notes, disable the other native updater.
    s=once(s,"def fetch_update_release(beta=False):",
           "def fetch_update_release(beta=False):\n    return None  # upstream native engine updates disabled; coop channel stays enabled","upstream native updates")
    ast.parse(s);return s
def apply(checkout,out):
    checkout,out=checkout.resolve(),out.resolve()
    if checkout==out or checkout in out.parents or out in checkout.parents:
        raise ValueError("refusing in-place source update")
    sha=subprocess.check_output(["git","-C",str(checkout),"rev-parse","HEAD"],text=True).strip()
    if sha!=PIN:raise ValueError(f"source revision mismatch: {sha}")
    if out.exists() and any(out.iterdir()):raise ValueError("output already exists")
    root=checkout/"bbport/launcher"
    changes={"bbport_coop.py":patch_coop((root/"bbport_coop.py").read_text('utf-8')),
             "bbport_launcher_win.py":patch_launcher((root/"bbport_launcher_win.py").read_text('utf-8'))}
    out.mkdir(parents=True,exist_ok=True)
    for name,src in changes.items():(out/name).write_text(src,encoding='utf-8')
    print("SH_V8_PATCH_OK: Seamless Hunt release channel and changelog, source untouched")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--checkout",type=pathlib.Path,required=True)
    p.add_argument("--out",type=pathlib.Path,required=True)
    a=p.parse_args();apply(a.checkout,a.out)
