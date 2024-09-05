#!/usr/bin/env bash
set -e

# ----------------------------
# packages
# ----------------------------
source "${PROJ_ROOT}/pkg-conf.sh"
dl_pkgc mbedtls  '71c569d'   static '' '--enable-mbedtls'
dl_pkgc sdl2     'ba2f78a'   static '' ''

printf "\e[1m\e[35m%s\e[0m\n" "${PKG_CONFIG_PATH}"
# ----------------------------
# static or shared
# ----------------------------
case ${PKG_TYPE} in
  "static")
    PKG_TYPE_FLAG=""
    ;;
  # "shared")
  #   PKG_TYPE_FLAG="--disable-static --enable-shared"
  #   ;;
  *)
    printf "\e[1m\e[31m%s\e[0m\n" "Invalid PKG TYPE: '${PKG_TYPE}'."
    exit 1
    ;;
esac
# ----------------------------
# optimize
#  - 0 DEBUG
#  - 1 RELEASE (default)
# ----------------------------
LIB_RELEASE=${LIB_RELEASE:-"1"}
if [ "${LIB_RELEASE}" == "1" ]; then
  PKG_BULD_TYPE="--disable-debug --disable-logging"
  PKG_INST_STRIP=""
else
  PKG_BULD_TYPE="--disable-optimizations --enable-extra-warnings"
  PKG_INST_STRIP="--disable-stripping"
fi
# ----------------------------
# compile :p
# ----------------------------
{ rm -rf ${PKG_BULD_DIR}; mkdir -p "${PKG_BULD_DIR}"; }
{ rm -rf ${PKG_INST_DIR}; mkdir -p "${PKG_INST_DIR}"; }

if [ "${CLANGD_CODE_COMPLETION}" == "1" ]; then { PKG_BULD_DIR="${SUBPROJ_SRC}"; } fi

pushd -- "${PKG_BULD_DIR}"
CONFIGURE_COMMAND=$(cat <<- EOF
${SUBPROJ_SRC}/configure     \
  --prefix='${PKG_INST_DIR}' \
  --cc='${CCACHE_SRC} ${CC}'   \
  --cxx='${CCACHE_SRC} ${CXX}' \
  ${PKG_TYPE_FLAG}  \
  ${PKG_BULD_TYPE}  \
  ${PKG_INST_STRIP} \
  --pkg-config='${PKG_CONFIG_EXEC}' \
  --enable-gpl \
  --enable-version3 \
  --fatal-warnings \
  --disable-doc \
  --disable-devices \
  --enable-indev=lavfi \
  --enable-pic \
  --disable-libxcb \
  --disable-xlib
  ${PKG_DEPS_ARGS}
EOF
)
case ${PKG_PLATFORM} in
  "macosx" | "iphoneos" | "iphonesimulator")
    CONFIGURE_COMMAND="${CONFIGURE_COMMAND} \
      --enable-cross-compile --sysroot='${SYSROOT}' --target-os=darwin --arch=${PKG_ARCH} --disable-coreimage \
      --extra-cflags='${CROSS_FLAGS}' --extra-cxxflags='${CROSS_FLAGS}' --extra-ldflags='${CROSS_FLAGS}'"
    if [ "${PKG_PLATFORM}" != "macosx" ]; then { CONFIGURE_COMMAND="${CONFIGURE_COMMAND} --disable-programs"; } fi
    ;;
  "linux")
    if [ "${CROSS_BUILD_ENABLED}" == "1" ]; then
      CONFIGURE_COMMAND="${CONFIGURE_COMMAND} \
        --enable-cross-compile --sysroot='${SYSROOT}' --target-os=linux --arch=${PKG_ARCH} \
        --extra-ldflags='-fuse-ld=${LD}' --nm='${NM}' --ar='${AR}' --ranlib='${RANLIB}' --strip='${STRIP}'"
    fi
    ;;
  *)
    ;;
esac

printf "\e[1m\e[36m%s\e[0m\n" "${CONFIGURE_COMMAND}"; eval ${CONFIGURE_COMMAND}
popd

# build & install
pushd -- "${PKG_BULD_DIR}"
MAKE_COMMAND="make -j ${PARALLEL_JOBS}; make install"
if command -v bear >/dev/null 2>&1 ; then
  MAKE_COMMAND="bear -- ${MAKE_COMMAND}"
fi
eval ${MAKE_COMMAND}
popd

if [ "${PKG_PLATFORM}" == "macosx" ]; then
  rm -rf ${PKG_INST_DIR}/{include,lib,share}
  xattr -dr com.apple.quarantine ${PKG_INST_DIR}/bin/*
fi

if command -v tree >/dev/null 2>&1 ; then
  tree -L 3 ${PKG_INST_DIR}
else
  ls -alh -- ${PKG_INST_DIR}
fi
BUILD_DATE=$(date -u '+%Y-%m-%dT%H:%M:%SZ%:z')
printf "\e[1m\e[35m%s\e[0m\n" "${SUBPROJ_SRC} - Build Done @${BUILD_DATE}"
