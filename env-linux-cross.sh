#!/usr/bin/env bash
set -e

TARGET_ARCH=${1}
TARGET_LIBC=${2}

export PARALLEL_JOBS="$(nproc)"

if command -v ccache >/dev/null 2>&1 ; then
  export CCACHE_SRC="$(command -v ccache)"

  export CMAKE_EXTRA="${CMAKE_EXTRA} -D CMAKE_C_COMPILER_LAUNCHER=ccache"
  export CMAKE_EXTRA="${CMAKE_EXTRA} -D CMAKE_CXX_COMPILER_LAUNCHER=ccache"
fi

case ${TARGET_ARCH} in
  "amd64")
    export TARGET_TRIPLE="x86_64-pc-linux-${TARGET_LIBC}"
    ;;
  "arm64")
    export TARGET_TRIPLE="aarch64-unknown-linux-${TARGET_LIBC}"
    ;;
  "armv7")
    export TARGET_TRIPLE="arm-unknown-linux-${TARGET_LIBC}"
    ;;
  *)
    printf "\e[1m\e[31m%s\e[0m\n" "Unsupported TARGET ARCH: '${TARGET_ARCH}'."
    exit 1
    ;;
esac

CROSS_TOOLCHAIN_ROOT=${CROSS_TOOLCHAIN_ROOT:-""}
if [ -z "${CROSS_TOOLCHAIN_ROOT}" ]; then
  printf "\e[1m\e[31m%s\e[0m\n" "Blank CROSS_TOOLCHAIN_ROOT: '${CROSS_TOOLCHAIN_ROOT}'."
  exit 1
fi
export SYSROOT="${CROSS_TOOLCHAIN_ROOT}/${TARGET_TRIPLE}/sysroot"

# cmake toolchain file
if [ -z "${CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE}" ]; then
  CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE="${CROSS_TOOLCHAIN_ROOT}/toolchain-cmake-template"
fi
CROSS_TOOLCHAIN_FILE_CMAKE="${CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE}.${TARGET_TRIPLE}"
export CMAKE_EXTRA="${CMAKE_EXTRA} -D CMAKE_TOOLCHAIN_FILE=${CROSS_TOOLCHAIN_FILE_CMAKE}"
# pkgconf bin
if [ -z "${CROSS_TOOLCHAIN_PKGCONF_PREFIX}" ]; then
  CROSS_TOOLCHAIN_PKGCONF_PREFIX="${CROSS_TOOLCHAIN_ROOT}/pkgconf-wrapper"
fi
export CROSS_TOOLCHAIN_PKGCONF="${CROSS_TOOLCHAIN_PKGCONF_PREFIX}.${TARGET_TRIPLE}"

# for cross-compiling, cmake sets compiler vars by toolchain file, so keep CC/CXX here.
export HOSTCC="$(command -v clang)"
export HOSTCXX="$(command -v clang++)"
export LD="$(command -v ld.lld)";
export NM="$(command -v llvm-nm)";
export AR="$(command -v llvm-ar)";
export AS="$(command -v llvm-as)";
export RANLIB="$(command -v llvm-ranlib)";
export STRIP="$(command -v llvm-strip)";

export CROSS_FLAGS="--target=${TARGET_TRIPLE} --gcc-toolchain=${CROSS_TOOLCHAIN_ROOT} -Wno-unused-command-line-argument -fuse-ld=${LD} --sysroot=${SYSROOT}"
export CC="$(command -v clang) ${CROSS_FLAGS}";
export CXX="$(command -v clang++) ${CROSS_FLAGS}";
export CPP="$(command -v clang-cpp) ${CROSS_FLAGS}";
