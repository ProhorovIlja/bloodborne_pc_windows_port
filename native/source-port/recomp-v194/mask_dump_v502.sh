#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Linux negative boot test: hide the original dump at its canonical path.
# Not a security sandbox: other copies, hard links and inherited fds are out of scope.
set -euo pipefail
if (( $# < 3 )) || [[ $2 != -- || $3 != /* ]]; then
    echo 'usage: mask_dump_v502.sh DUMP_DIRECTORY -- /absolute/host-executable [args...]' >&2
    exit 2
fi
dump=$(realpath -e -- "$1")
shift 2
exe=$(realpath -e -- "$1")
cwd=$(pwd -P)
if [[ $dump == / || ! -d $dump || ! -f $exe || ! -x $exe ||
      $exe == "$dump" || $exe == "$dump/"* ||
      $cwd == "$dump" || $cwd == "$dump/"* ]]; then
    echo 'refused: dump must be separate from the executable and working directory' >&2
    exit 2
fi
# Prepare an empty mount source outside the dump; refuse overlap even with a custom TMPDIR.
empty=$(mktemp -d)
trap 'rmdir -- "$empty"' EXIT
empty=$(realpath -e -- "$empty")
if [[ $empty == "$dump/"* ]]; then
    echo 'refused: temporary mount source is inside the dump' >&2
    exit 2
fi
unshare --user --map-root-user --mount --propagation private -- bash -euc '
    dump=$1; empty=$2; exe=$3; shift 4
    mount --bind -- "$empty" "$dump"
    mount -o remount,bind,ro -- "$dump"
    if [[ ! "$empty" -ef "$dump" ]]; then
        echo "refused: dump mount was not masked" >&2
        exit 2
    fi
    printf "V502 dump masked at canonical path\n" >&2
    exec "$exe" "$@"
' mask "$dump" "$empty" "$exe" "$@"
