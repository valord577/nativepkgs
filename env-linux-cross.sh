#!/usr/bin/env bash
set -e

TARGET_ARCH=${1}

case ${TARGET_ARCH} in
  "arm64")
    __TARGET_ARCH__="aarch64"
    __TARGET_TRIPLE__="aarch64-unknown-linux-gnu"
    ;;
  *)
    printf "\e[1m\e[31m%s\e[0m\n" "Unsupported TARGET ARCH: '${TARGET_ARCH}'."
    exit 1
    ;;
esac
BUILTIN_CROSS_TOOLCHAIN_FILE="${PROJ_ROOT}/cross/toolchain-cmake-template.${TARGET_ARCH}"
cat ${PROJ_ROOT}/cross/toolchain-cmake-template \
  | sed "s@__TARGET_ARCH__@${__TARGET_ARCH__}@g"     \
  | sed "s@__TARGET_TRIPLE__@${__TARGET_TRIPLE__}@g" \
  > ${BUILTIN_CROSS_TOOLCHAIN_FILE}

pushd ${PROJ_ROOT}/cross; { ln -sfn "pkgconf-wrapper" "pkgconf-wrapper.${__TARGET_TRIPLE__}"; }; popd
export CROSS_TOOLCHAIN_PKGCONF="${PROJ_ROOT}/cross/pkgconf-wrapper.${__TARGET_TRIPLE__}"


CROSS_TOOLCHAIN_ROOT=${CROSS_TOOLCHAIN_ROOT:-""}
if [ -z "${CROSS_TOOLCHAIN_ROOT}" ]; then
  printf "\e[1m\e[31m%s\e[0m\n" "Blank CROSS_TOOLCHAIN_ROOT: '${CROSS_TOOLCHAIN_ROOT}'."
  exit 1
fi
CROSS_TOOLCHAIN_FILE=${CROSS_TOOLCHAIN_FILE:-${BUILTIN_CROSS_TOOLCHAIN_FILE}}
export SYSROOT="${CROSS_TOOLCHAIN_ROOT}/${__TARGET_TRIPLE__}/sysroot"

export PARALLEL_JOBS="$(nproc)"
export CMAKE_EXTRA_ARGS="${CMAKE_EXTRA_ARGS} -D CMAKE_TOOLCHAIN_FILE=${CROSS_TOOLCHAIN_FILE}"

# for cross-compiling, cmake sets compiler vars by toolchain file, so keep CC/CXX.
export CROSS_FLAGS="--target=${__TARGET_TRIPLE__} --gcc-toolchain=${CROSS_TOOLCHAIN_ROOT}"
export CC="/usr/bin/clang ${CROSS_FLAGS}"; export CXX="/usr/bin/clang++ ${CROSS_FLAGS}";
export LD="/usr/bin/ld.lld"; export NM="/usr/bin/llvm-nm"; export AR="/usr/bin/llvm-ar"; export AS="/usr/bin/llvm-as";
export RANLIB="/usr/bin/llvm-ranlib"; export STRIP="/usr/bin/llvm-strip";
if command -v ccache >/dev/null 2>&1 ; then
  export CCACHE_SRC="$(command -v ccache)"

  export CMAKE_EXTRA_ARGS="${CMAKE_EXTRA_ARGS} -D CMAKE_C_COMPILER_LAUNCHER=ccache"
  export CMAKE_EXTRA_ARGS="${CMAKE_EXTRA_ARGS} -D CMAKE_CXX_COMPILER_LAUNCHER=ccache"
fi
