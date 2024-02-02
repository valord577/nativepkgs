#!/usr/bin/env bash
set -e

TARGET_PLATFORM=${1}
TARGET_ARCH=${2}

TARGET_DEPLOYMENT="10"
if [ "${TARGET_PLATFORM}" == "macosx" ]; then
  TARGET_DEPLOYMENT="10.15"
fi
# ----------------------------
# cmake
# ----------------------------
export CMAKE_EXTRA=$(cat <<- EOF
-D CMAKE_OSX_ARCHITECTURES=${TARGET_ARCH} \
-D CMAKE_OSX_SYSROOT=${TARGET_PLATFORM} \
-D CMAKE_OSX_DEPLOYMENT_TARGET=${TARGET_DEPLOYMENT} \
-D CMAKE_MACOSX_BUNDLE:BOOL=0
EOF
)
if [ "${TARGET_PLATFORM}" == "iphoneos" ] || \
  [ "${TARGET_PLATFORM}" == "iphonesimulator" ]; then
  export CMAKE_EXTRA="-D CMAKE_SYSTEM_NAME=iOS ${CMAKE_EXTRA}"
fi
# ----------------------------
# flags (legacy)
# ----------------------------
case ${TARGET_PLATFORM} in
  "macosx")
    TARGET_DEPLOYMENT_FLAG="-mmacosx-version-min=${TARGET_DEPLOYMENT}"
    ;;
  "iphoneos")
    TARGET_DEPLOYMENT_FLAG="-miphoneos-version-min=${TARGET_DEPLOYMENT}"
    ;;
  "iphonesimulator")
    TARGET_DEPLOYMENT_FLAG="-mios-simulator-version-min=${TARGET_DEPLOYMENT}"
    ;;
  ?)
    ;;
esac

export SYSROOT_PATH="$(xcrun --sdk ${TARGET_PLATFORM} --show-sdk-path)"
export CFLAGS_EXTRA="-arch ${TARGET_ARCH} ${TARGET_DEPLOYMENT_FLAG}"
export CXXFLAGS_EXTRA="-arch ${TARGET_ARCH} ${TARGET_DEPLOYMENT_FLAG}"
export LDFLAGS_EXTRA="-arch ${TARGET_ARCH} ${TARGET_DEPLOYMENT_FLAG}"
