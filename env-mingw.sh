#!/usr/bin/env bash
set -e

__TARGET_ARCH__=${1}
__TARGET_TRIPLE__="${__TARGET_ARCH__}-w64-mingw32"

BUILTIN_CROSS_TOOLCHAIN_FILE_CMAKE="${PROJ_ROOT}/cross/mingw/toolchain-cmake-template.${__TARGET_TRIPLE__}"
cat ${PROJ_ROOT}/cross/mingw/toolchain-cmake-template \
  | sed "s@__TARGET_ARCH__@${__TARGET_ARCH__}@g"     \
  | sed "s@__TARGET_TRIPLE__@${__TARGET_TRIPLE__}@g" \
  > ${BUILTIN_CROSS_TOOLCHAIN_FILE_CMAKE}
if [ -n "${CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE}" ]; then
  CROSS_TOOLCHAIN_FILE_CMAKE="${CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE}.${__TARGET_TRIPLE__}"
else
  CROSS_TOOLCHAIN_FILE_CMAKE="${BUILTIN_CROSS_TOOLCHAIN_FILE_CMAKE}"
fi

pushd ${PROJ_ROOT}/cross/mingw; { ln -sfn "pkgconf-wrapper" "pkgconf-wrapper.${__TARGET_TRIPLE__}"; }; popd
BUILTIN_CROSS_TOOLCHAIN_PKGCONF="${PROJ_ROOT}/cross/mingw/pkgconf-wrapper.${__TARGET_TRIPLE__}"
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
export SYSROOT="${CROSS_TOOLCHAIN_ROOT}/${__TARGET_TRIPLE__}"

export PARALLEL_JOBS="$(nproc)"
export CMAKE_EXTRA="${CMAKE_EXTRA} -D CMAKE_TOOLCHAIN_FILE=${CROSS_TOOLCHAIN_FILE_CMAKE}"

# for cross-compiling, cmake sets compiler vars by toolchain file, so keep CC/CXX.
export CC="${CROSS_TOOLCHAIN_ROOT}/bin/${__TARGET_TRIPLE__}-clang"
export CXX="${CROSS_TOOLCHAIN_ROOT}/bin/${__TARGET_TRIPLE__}-clang++"
export WINDRES="${CROSS_TOOLCHAIN_ROOT}/bin/${__TARGET_TRIPLE__}-windres"
export LD="${CROSS_TOOLCHAIN_ROOT}/bin/${__TARGET_TRIPLE__}-ld"
export NM="${CROSS_TOOLCHAIN_ROOT}/bin/${__TARGET_TRIPLE__}-nm"
export AR="${CROSS_TOOLCHAIN_ROOT}/bin/${__TARGET_TRIPLE__}-ar"
export AS="${CROSS_TOOLCHAIN_ROOT}/bin/${__TARGET_TRIPLE__}-as"
export RANLIB="${CROSS_TOOLCHAIN_ROOT}/bin/${__TARGET_TRIPLE__}-ranlib"
export STRIP="${CROSS_TOOLCHAIN_ROOT}/bin/${__TARGET_TRIPLE__}-strip"
if command -v ccache >/dev/null 2>&1 ; then
  export CCACHE_SRC="$(command -v ccache)"

  export CMAKE_EXTRA="${CMAKE_EXTRA} -D CMAKE_C_COMPILER_LAUNCHER=ccache"
  export CMAKE_EXTRA="${CMAKE_EXTRA} -D CMAKE_CXX_COMPILER_LAUNCHER=ccache"
fi
