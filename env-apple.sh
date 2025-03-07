#!/usr/bin/env bash
set -e

TARGET_PLATFORM=${1}
TARGET_ARCH=${2}

export PARALLEL_JOBS="$(sysctl -n hw.ncpu)"
export PLATFORM_APPLE="1"

crossfiles_dir="${PROJ_ROOT}/crossfiles/apple"


if command -v ccache >/dev/null 2>&1 ; then
  export CCACHE_SRC="$(command -v ccache)"

  export CMAKE_EXTRA="${CMAKE_EXTRA} -D CMAKE_C_COMPILER_LAUNCHER=ccache"
  export CMAKE_EXTRA="${CMAKE_EXTRA} -D CMAKE_CXX_COMPILER_LAUNCHER=ccache"
  export CMAKE_EXTRA="${CMAKE_EXTRA} -D CMAKE_OBJC_COMPILER_LAUNCHER=ccache"
  export CMAKE_EXTRA="${CMAKE_EXTRA} -D CMAKE_OBJCXX_COMPILER_LAUNCHER=ccache"
fi

case ${TARGET_PLATFORM} in
  "macosx")
    TARGET_FLAG="macosx"
    export CMAKE_EXTRA="-D CMAKE_SYSTEM_NAME=Darwin ${CMAKE_EXTRA}"
    ;;
  "iphoneos")
    TARGET_FLAG="iphoneos"
    export CMAKE_EXTRA="-D CMAKE_SYSTEM_NAME=iOS ${CMAKE_EXTRA}"
    ;;
  "iphonesimulator")
    TARGET_FLAG="ios-simulator"
    export CMAKE_EXTRA="-D CMAKE_SYSTEM_NAME=iOS ${CMAKE_EXTRA}"
    ;;
  *)
    printf "\e[1m\e[31m%s\e[0m\n" "Unsupported TARGET PLATFORM: '${TARGET_PLATFORM}'."
    exit 1
    ;;
esac

[ "${TARGET_PLATFORM}" == "macosx" ] \
  && { TARGET_DEPLOYMENT="10.15"; } || { TARGET_DEPLOYMENT="12"; }
export SYSROOT="$(xcrun --sdk ${TARGET_PLATFORM} --show-sdk-path)"
export CROSS_FLAGS="-arch ${TARGET_ARCH} -m${TARGET_FLAG}-version-min=${TARGET_DEPLOYMENT}"

export HOSTCC="$(xcrun -f clang)"; export HOSTCXX="$(xcrun -f clang++)"
export CC=" ${CCACHE_SRC} ${HOSTCC}  ${CROSS_FLAGS} --sysroot=${SYSROOT}"
export CXX="${CCACHE_SRC} ${HOSTCXX} ${CROSS_FLAGS} --sysroot=${SYSROOT}"
export OBJC="${CC}"; export OBJCXX="${CXX}";


export CMAKE_EXTRA=$(cat <<- EOF
-D CMAKE_C_COMPILER=${HOSTCC}       \
-D CMAKE_CXX_COMPILER=${HOSTCXX}    \
-D CMAKE_OBJC_COMPILER=${HOSTCC}    \
-D CMAKE_OBJCXX_COMPILER=${HOSTCXX} \
-D CMAKE_CROSSCOMPILING:BOOL=TRUE   \
-D CMAKE_SYSTEM_PROCESSOR=${TARGET_ARCH}  \
-D CMAKE_OSX_ARCHITECTURES=${TARGET_ARCH} \
-D CMAKE_OSX_SYSROOT=${TARGET_PLATFORM} \
-D CMAKE_OSX_DEPLOYMENT_TARGET=${TARGET_DEPLOYMENT} \
-D CMAKE_MACOSX_BUNDLE:BOOL=0 ${CMAKE_EXTRA}
EOF
)



# pkgconf bin
export CROSS_TOOLCHAIN_PKGCONF="${crossfiles_dir}/pkgconf-wrapper"
# meson toolchain file
CROSS_TOOLCHAIN_FILE_MESON="${crossfiles_dir}/toolchain-meson-template.${TARGET_PLATFORM}-${TARGET_ARCH}"
cat "${CROSS_TOOLCHAIN_FILE_MESON}.tmpl" | \
  sed "s@__SYSROOT__@${SYSROOT}@g" | \
  sed "s@__EXTRA_FLAGS__@'-m${TARGET_FLAG}-version-min=${TARGET_DEPLOYMENT}'@g" \
  > "${CROSS_TOOLCHAIN_FILE_MESON}"
export MESON_EXTRA="${MESON_EXTRA} --cross-file ${CROSS_TOOLCHAIN_FILE_MESON}"
