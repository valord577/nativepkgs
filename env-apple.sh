#!/usr/bin/env bash
set -e

TARGET_PLATFORM=${1}
TARGET_ARCH=${2}

TARGET_DEPLOYMENT="10"
if [ "${TARGET_PLATFORM}" == "macosx" ]; then
  TARGET_DEPLOYMENT="10.15"
fi

export PARALLEL_JOBS="$(sysctl -n hw.ncpu)"
if command -v ccache >/dev/null 2>&1 ; then
  export CC="ccache clang"
  export CXX="ccache clang++"

  export OBJC="ccache clang"
  export OBJCXX="ccache clang++"
fi
# ----------------------------
# cmake
# ----------------------------
export CMAKE_EXTRA_ARGS=$(cat <<- EOF
-D CMAKE_OSX_ARCHITECTURES=${TARGET_ARCH} \
-D CMAKE_OSX_SYSROOT=${TARGET_PLATFORM} \
-D CMAKE_OSX_DEPLOYMENT_TARGET=${TARGET_DEPLOYMENT} \
-D CMAKE_MACOSX_BUNDLE:BOOL=0
EOF
)
if [ "${TARGET_PLATFORM}" == "iphoneos" ] || \
  [ "${TARGET_PLATFORM}" == "iphonesimulator" ]; then
  export CMAKE_EXTRA_ARGS="-D CMAKE_SYSTEM_NAME=iOS ${CMAKE_EXTRA_ARGS}"
fi
# ----------------------------
# gnu autotools
# ----------------------------
case ${TARGET_PLATFORM} in
  "macosx")
    TARGET_FLAG="macosx"
    ;;
  "iphoneos")
    TARGET_FLAG="iphoneos"
    ;;
  "iphonesimulator")
    TARGET_FLAG="ios-simulator"
    ;;
  ?)
    ;;
esac

export SYSROOT="$(xcrun --sdk ${TARGET_PLATFORM} --show-sdk-path)"
export ECFLAGS="  -arch ${TARGET_ARCH} -m${TARGET_FLAG}-version-min=${TARGET_DEPLOYMENT}"
export ECXXFLAGS="-arch ${TARGET_ARCH} -m${TARGET_FLAG}-version-min=${TARGET_DEPLOYMENT}"
export ELDFLAGS=" -arch ${TARGET_ARCH} -m${TARGET_FLAG}-version-min=${TARGET_DEPLOYMENT}"
