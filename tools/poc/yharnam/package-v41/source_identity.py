#!/usr/bin/env python3
"""Internal source provenance for coupled native Windows game + Qt server builds.

It establishes same-project exact-commit identity, NOT a cryptographic
signature, runtime ABI proof, or a public updater trust root.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import zipfile

GAME_NAME = "SHYT-CLIENT-SOURCE-IDENTITY.json"
SERVER_NAME = "SHYT-SERVER-SOURCE-IDENTITY.json"
UPSTREAM = "77e350743a7cb4524cfcc1782fb6e3af64e25b15"
FIELDS = {"schema", "component", "source_commit", "upstream_pin", "release_ready"}


class SourceIdentityError(ValueError):
    pass


def identity(component: str, source_commit: str) -> dict:
    if component not in ("game", "server"):
        raise SourceIdentityError("unknown build component")
    if not isinstance(source_commit, str) or re.fullmatch(r"[0-9a-f]{40}", source_commit) is None:
        raise SourceIdentityError("source commit must be a lowercase 40-digit SHA-1")
    return {"schema": 1, "component": component, "source_commit": source_commit,
            "upstream_pin": UPSTREAM, "release_ready": False}


def validate(raw: bytes, component: str) -> dict:
    if len(raw) > 4096:
        raise SourceIdentityError("oversized source identity")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise SourceIdentityError("invalid source identity JSON") from exc
    if (not isinstance(data, dict) or set(data) != FIELDS
            or type(data.get("schema")) is not int or data["schema"] != 1
            or data.get("component") != component
            or data.get("upstream_pin") != UPSTREAM
            or data.get("release_ready") is not False
            or not isinstance(data.get("source_commit"), str)
            or re.fullmatch(r"[0-9a-f]{40}", data["source_commit"]) is None):
        raise SourceIdentityError("source identity schema, component, commit, or upstream mismatch")
    return data


def stamp_file(path: Path, component: str, source_commit: str) -> None:
    content = (json.dumps(identity(component, source_commit), sort_keys=True) + "\n").encode("utf-8")
    if path.exists():
        raise SourceIdentityError("refusing to overwrite a source identity")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def stamp_game_zip(path: Path, source_commit: str) -> None:
    member = "bbport-windows/" + GAME_NAME
    if not path.is_file():
        raise SourceIdentityError("native game ZIP missing")
    content = (json.dumps(identity("game", source_commit), sort_keys=True) + "\n").encode("utf-8")
    with zipfile.ZipFile(path, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        if any(m.filename.casefold() == member.casefold() for m in archive.infolist()):
            raise SourceIdentityError("game ZIP source identity already exists")
        archive.writestr(member, content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--game-zip", type=Path)
    target.add_argument("--server-dir", type=Path)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    if args.game_zip:
        stamp_game_zip(args.game_zip, args.commit)
    else:
        if not args.server_dir.is_dir():
            parser.error("native server staging directory missing")
        stamp_file(args.server_dir / SERVER_NAME, "server", args.commit)
    print("MATCHED_NATIVE_SOURCE_IDENTITY_STAMPED_INTERNAL_ONLY")


if __name__ == "__main__":
    main()
