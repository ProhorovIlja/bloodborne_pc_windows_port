#!/usr/bin/env bash
# Pin two Windows-only CMake dependencies which MSYS2 does not package.
# These repositories are build-time inputs, not additional clients for users.
# Pinned to revisions used by Supermedo/bloodborne_pc on 2026-10-22.
set -euo pipefail
cd "$(dirname "$0")/.."

clone_exact() {
  local name="$1" url="$2" revision="$3" folder="gpu/third_party/$1"
  if [[ -e "$folder" && ! -d "$folder/.git" ]]; then
    echo "ERROR: $folder already exists but is not a Git checkout; refusing to overwrite it" >&2
    exit 1
  fi
  if [[ ! -d "$folder/.git" ]]; then
    git clone --quiet "$url" "$folder"
  fi
  git -C "$folder" fetch --quiet --depth 1 origin "$revision"
  git -C "$folder" checkout --quiet --detach "$revision"
  test "$(git -C "$folder" rev-parse HEAD)" = "$revision"
  echo "$name pinned: $revision"
}

clone_exact magic_enum https://github.com/Neargye/magic_enum.git e046b69a3736d314fad813e159b1c192eaef92cd
clone_exact miniz https://github.com/richgel999/miniz.git 2948eebafc5b9f1c69bebed80333e403a09bd62d
# The shader SRT generator needs xbyak, a header-only assembly emitter.
# Pin the same submodule revision as shadPS4 main (2026-10-22).
clone_exact xbyak https://github.com/herumi/xbyak.git 44a72f369268f7d552650891b296693e91db86bb

test -f gpu/third_party/magic_enum/include/magic_enum/magic_enum.hpp
test -f gpu/third_party/miniz/CMakeLists.txt
test -f gpu/third_party/xbyak/xbyak/xbyak.h
echo "Windows-only upstream build dependencies ready."
