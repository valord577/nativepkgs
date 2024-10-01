#!/usr/bin/env bash
set -e

case "$(uname -m)" in
  "aarch64")
    export TARGET_ARCH="arm64"
    ;;
  "x86_64")
    export TARGET_ARCH="amd64"
    ;;
  *)
    printf "\e[1m\e[31m%s\e[0m\n" "Unsupported TARGET ARCH: '${TARGET_ARCH}'."
    exit 1
    ;;
esac

export PARALLEL_JOBS="$(nproc)"
if command -v ccache >/dev/null 2>&1 ; then
  export CCACHE_SRC="$(command -v ccache)"

  export CMAKE_EXTRA_ARGS="${CMAKE_EXTRA_ARGS} -D CMAKE_C_COMPILER_LAUNCHER=ccache"
  export CMAKE_EXTRA_ARGS="${CMAKE_EXTRA_ARGS} -D CMAKE_CXX_COMPILER_LAUNCHER=ccache"
fi

function chk_compiler() {
  local c_key="${1}"
  local c_value=$(eval echo "\${${c_key}}")
  if [ -z "${c_value}" ]; then { c_value="${2}"; } fi
  if ! command -v ${c_value} >/dev/null 2>&1 ; then
    printf "\e[4m\e[33m%s\e[0m\n" "Not found ${c_key} compiler: ${c_value}"
    return 1
  fi

  eval export "${c_key}='${c_value}'"
  printf "\e[4m\e[32m%s\e[0m\n" "Using ${c_value} for ${c_key} (export ${c_key}=${c_value})"
  return 0
}

compilers=(
  'CC  maybe cc  clang   gcc'
  'CXX maybe c++ clang++ g++'
)
set +e
for c in "${compilers[@]}"; do
  c_list=(${c})
  c_key="${c_list[0]}"

  for c_value in ${c_list[@]:2}; do
    chk_compiler "${c_key}" "${c_value}" "${c_list[1]}"
    if [ "${?}" == "0" ]; then { break; } fi
  done
done
set -e
