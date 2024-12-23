#!/usr/bin/env bash
set -e

TARGET_PLATFORM=${1}
TARGET_ARCH=${2}

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

TARGET_DEPLOYMENT="10"
if [ "${TARGET_PLATFORM}" == "macosx" ]; then
  TARGET_DEPLOYMENT="10.15"
fi
export SYSROOT="$(xcrun --sdk ${TARGET_PLATFORM} --show-sdk-path)"
export CROSS_FLAGS="-arch ${TARGET_ARCH} -m${TARGET_FLAG}-version-min=${TARGET_DEPLOYMENT}"

export CC="clang"; export CXX="clang++"; export OBJC="clang"; export OBJCXX="clang++";
export HOSTCC="clang"; export HOSTCXX="clang++"
export PARALLEL_JOBS="$(sysctl -n hw.ncpu)"
if command -v ccache >/dev/null 2>&1 ; then
  export CCACHE_SRC="$(command -v ccache)"

  export CMAKE_EXTRA="${CMAKE_EXTRA} -D CMAKE_C_COMPILER_LAUNCHER=ccache"
  export CMAKE_EXTRA="${CMAKE_EXTRA} -D CMAKE_CXX_COMPILER_LAUNCHER=ccache"
  export CMAKE_EXTRA="${CMAKE_EXTRA} -D CMAKE_OBJC_COMPILER_LAUNCHER=ccache"
  export CMAKE_EXTRA="${CMAKE_EXTRA} -D CMAKE_OBJCXX_COMPILER_LAUNCHER=ccache"
fi

export CMAKE_EXTRA=$(cat <<- EOF
-D CMAKE_CROSSCOMPILING:BOOL=TRUE \
-D CMAKE_SYSTEM_PROCESSOR=${TARGET_ARCH}  \
-D CMAKE_OSX_ARCHITECTURES=${TARGET_ARCH} \
-D CMAKE_OSX_SYSROOT=${TARGET_PLATFORM} \
-D CMAKE_OSX_DEPLOYMENT_TARGET=${TARGET_DEPLOYMENT} \
-D CMAKE_MACOSX_BUNDLE:BOOL=0 ${CMAKE_EXTRA}
EOF
)
