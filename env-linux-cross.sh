#!/usr/bin/env bash
set -e

TARGET_ARCH=${1}
TARGET_LIBC=${2}

case ${TARGET_ARCH} in
  "arm64")
    __TARGET_ARCH__="aarch64"
    __TARGET_TRIPLE__="aarch64-unknown-linux-${TARGET_LIBC}"
    ;;
  "amd64")
    __TARGET_ARCH__="x86_64"
    __TARGET_TRIPLE__="x86_64-pc-linux-${TARGET_LIBC}"
    ;;
  *)
    printf "\e[1m\e[31m%s\e[0m\n" "Unsupported TARGET ARCH: '${TARGET_ARCH}'."
    exit 1
    ;;
esac
BUILTIN_CROSS_TOOLCHAIN_FILE_CMAKE="${PROJ_ROOT}/cross/toolchain-cmake-template.${__TARGET_TRIPLE__}"
cat ${PROJ_ROOT}/cross/toolchain-cmake-template \
  | sed "s@__TARGET_ARCH__@${__TARGET_ARCH__}@g"     \
  | sed "s@__TARGET_TRIPLE__@${__TARGET_TRIPLE__}@g" \
  > ${BUILTIN_CROSS_TOOLCHAIN_FILE_CMAKE}
if [ -n "${CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE}" ]; then
  CROSS_TOOLCHAIN_FILE_CMAKE="${CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE}.${__TARGET_TRIPLE__}"
else
  CROSS_TOOLCHAIN_FILE_CMAKE="${BUILTIN_CROSS_TOOLCHAIN_FILE_CMAKE}"
fi

pushd ${PROJ_ROOT}/cross; { ln -sfn "pkgconf-wrapper" "pkgconf-wrapper.${__TARGET_TRIPLE__}"; }; popd
BUILTIN_CROSS_TOOLCHAIN_PKGCONF="${PROJ_ROOT}/cross/pkgconf-wrapper.${__TARGET_TRIPLE__}"
if [ -n "${CROSS_TOOLCHAIN_PKGCONF_PREFIX}" ]; then
  export CROSS_TOOLCHAIN_PKGCONF="${CROSS_TOOLCHAIN_PKGCONF_PREFIX}.${__TARGET_TRIPLE__}"
else
  export CROSS_TOOLCHAIN_PKGCONF="${BUILTIN_CROSS_TOOLCHAIN_PKGCONF}"
fi

CROSS_TOOLCHAIN_ROOT=${CROSS_TOOLCHAIN_ROOT:-""}
if [ -z "${CROSS_TOOLCHAIN_ROOT}" ]; then
  printf "\e[1m\e[31m%s\e[0m\n" "Blank CROSS_TOOLCHAIN_ROOT: '${CROSS_TOOLCHAIN_ROOT}'."
  exit 1
fi
export SYSROOT="${CROSS_TOOLCHAIN_ROOT}/${__TARGET_TRIPLE__}/sysroot"

export PARALLEL_JOBS="$(nproc)"
export CMAKE_EXTRA_ARGS="${CMAKE_EXTRA_ARGS} -D CMAKE_TOOLCHAIN_FILE=${CROSS_TOOLCHAIN_FILE_CMAKE}"

# for cross-compiling, cmake sets compiler vars by toolchain file, so keep CC/CXX.
export CROSS_FLAGS="--target=${__TARGET_TRIPLE__} --gcc-toolchain=${CROSS_TOOLCHAIN_ROOT}"
export CC="/usr/bin/clang ${CROSS_FLAGS}"; export CXX="/usr/bin/clang++ ${CROSS_FLAGS}"; export HOSTCC="/usr/bin/clang"
export LD="/usr/bin/ld.lld"; export NM="/usr/bin/llvm-nm"; export AR="/usr/bin/llvm-ar"; export AS="/usr/bin/llvm-as";
export RANLIB="/usr/bin/llvm-ranlib"; export STRIP="/usr/bin/llvm-strip";
if command -v ccache >/dev/null 2>&1 ; then
  export CCACHE_SRC="$(command -v ccache)"

  export CMAKE_EXTRA_ARGS="${CMAKE_EXTRA_ARGS} -D CMAKE_C_COMPILER_LAUNCHER=ccache"
  export CMAKE_EXTRA_ARGS="${CMAKE_EXTRA_ARGS} -D CMAKE_CXX_COMPILER_LAUNCHER=ccache"
fi
