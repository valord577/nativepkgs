#!/usr/bin/env bash
set -e

TARGET_PLATFORM=${1}
TARGET_ARCH=${2}

export PARALLEL_JOBS="$(nproc)"

function chk_compiler() {
  if ! command -v ccache >/dev/null 2>&1 ; then { return 0; } fi

  local c_key="${1}"
  local c_value=$(eval echo "\${${c_key}}")
  if [ -n "${c_value}" ]; then
    eval export "${c_key}='ccache ${c_value}'"
    return 0
  fi

  c_value="${2}"
  if command -v ${c_value} >/dev/null 2>&1 ; then
    eval export "${c_key}='ccache ${c_value}'"
    return 0
  fi
  return 1
}
function chk_compiler_cc() {
  chk_compiler 'CC' "${1}"
}
function chk_compiler_asm() {
  chk_compiler 'ASM' "${1}"
}
function chk_compiler_cxx() {
  chk_compiler 'CXX' "${1}"
}

set +e
chk_compiler_cc 'cc'
flag="${?}"
if [ "${flag}" != "0" ]; then
  chk_compiler_cc 'clang'
  flag="${?}"
fi
if [ "${flag}" != "0" ]; then
  chk_compiler_cc 'gcc'
  flag="${?}"
fi

chk_compiler_asm 'cc'
flag="${?}"
if [ "${flag}" != "0" ]; then
  chk_compiler_asm 'clang'
  flag="${?}"
fi
if [ "${flag}" != "0" ]; then
  chk_compiler_asm 'gcc'
  flag="${?}"
fi

chk_compiler_cxx 'c++'
flag="${?}"
if [ "${flag}" != "0" ]; then
  chk_compiler_cxx 'clang++'
  flag="${?}"
fi
if [ "${flag}" != "0" ]; then
  chk_compiler_cxx 'g++'
  flag="${?}"
fi
set -e
