#!/usr/bin/env bash
set -e

TARGET_PLATFORM=${1}
TARGET_ARCH=${2}

export PARALLEL_JOBS="$(nproc)"

function chk_compiler() {
  if ! command -v ccache >/dev/null 2>&1 ; then { return 0; } fi

  local c_key="${1}"
  local c_value=$(eval echo "\${${c_key}}")
  if [ -z "${c_value}" ]; then { c_value="${2}"; } fi
  if ! command -v ${c_value} >/dev/null 2>&1 ; then
    printf "\e[4m\e[33m%s\e[0m\n" "Not found ${c_key} compiler: ${c_value}"
    return 1
  fi

  eval export "${c_key}='ccache ${c_value}'"
  export CMAKE_EXTRA_ARGS="${CMAKE_EXTRA_ARGS} -D ${3}=ccache"
  printf "\e[4m\e[32m%s\e[0m\n" "Use ccache for ${c_key}: ${c_value}"
  return 0
}

# https://cmake.org/cmake/help/latest/command/enable_language.html
# https://cmake.org/cmake/help/latest/envvar/CMAKE_LANG_COMPILER_LAUNCHER.html
compilers=(
  'CC  CMAKE_C_COMPILER_LAUNCHER   cc  clang   gcc'
  'CXX CMAKE_CXX_COMPILER_LAUNCHER c++ clang++ g++'
  'ASM CMAKE_ASM_COMPILER_LAUNCHER cc  clang   gcc'
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
