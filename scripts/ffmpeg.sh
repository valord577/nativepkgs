#!/usr/bin/env bash
set -e

# ----------------------------
# packages
# ----------------------------
source "${PROJ_ROOT}/pkg-conf.sh"
dl_pkgc mbedtls  '107ea89'   static '' '--enable-mbedtls'

if [ "${PKG_PLATFORM}" == "macosx" ]; then
  dl_pkgc sdl2   'fa24d86'   static
fi

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
if [ "${CLANGD_CODE_COMPLETION}" == "1" ]; then
  PKG_BULD_DIR="${PROJ_ROOT}"
else
  { rm -rf ${PKG_BULD_DIR}; mkdir -p "${PKG_BULD_DIR}"; }
  { rm -rf ${PKG_INST_DIR}; mkdir -p "${PKG_INST_DIR}"; }
fi

CONFIGURE_COMMAND=$(cat <<- EOF
${SUBPROJ_SRC}/configure     \
  --prefix='${PKG_INST_DIR}' \
  --cc='${CC}'   \
  --cxx='${CXX}' \
  ${PKG_TYPE_FLAG}  \
  ${PKG_BULD_TYPE}  \
  ${PKG_INST_STRIP} \
  --enable-gpl \
  --enable-version3 \
  --fatal-warnings \
  --disable-doc \
  --disable-devices \
  --enable-indev=lavfi \
  --enable-pic \
  --disable-libxcb \
  --disable-xlib  \
  --disable-vaapi \
  ${PKG_DEPS_ARGS}
EOF
)
if [ -n "${PKG_CONFIG_EXEC}" ]; then
  CONFIGURE_COMMAND="${CONFIGURE_COMMAND} --pkg-config='${PKG_CONFIG_EXEC}'"
fi

case ${PKG_PLATFORM} in
  "macosx" | "iphoneos" | "iphonesimulator")
    CONFIGURE_COMMAND="${CONFIGURE_COMMAND} \
      --enable-cross-compile --target-os=darwin --arch=${PKG_ARCH} \
      --disable-coreimage --extra-ldflags='${CROSS_FLAGS}'"
    [ "${PKG_PLATFORM}" != "macosx" ] && { CONFIGURE_COMMAND="${CONFIGURE_COMMAND} --disable-programs"; }
    ;;
  "linux")
    if [ "${CROSS_BUILD_ENABLED}" == "1" ]; then
      CONFIGURE_COMMAND="${CONFIGURE_COMMAND} \
        --enable-cross-compile --target-os=linux --arch=${PKG_ARCH} \
        --host-cc='${HOSTCC}' --extra-ldflags='${CROSS_LDFLAGS}' \
        --nm='${NM}' --ar='${AR}' --ranlib='${RANLIB}' --strip='${STRIP}'"
    fi
    ;;
  "win-mingw")
    CONFIGURE_COMMAND="${CONFIGURE_COMMAND} \
      --enable-cross-compile --target-os=mingw64 --arch=${PKG_ARCH} \
      --host-cc='${HOSTCC}' --windres='${WINDRES}' \
      --nm='${NM}' --ar='${AR}' --ranlib='${RANLIB}' --strip='${STRIP}'"
    ;;
  *)
    ;;
esac

printf "\e[1m\e[36m%s\e[0m\n" "${CONFIGURE_COMMAND}"
pushd -- "${PKG_BULD_DIR}"; eval ${CONFIGURE_COMMAND}; popd

# build & install
MAKE_COMMAND="make -j ${PARALLEL_JOBS}"
if [ "${PKG_PLATFORM}" == "iphoneos" ] || \
  [ "${PKG_PLATFORM}" == "iphonesimulator" ]; then
  MAKE_COMMAND="${MAKE_COMMAND}; make install-headers; make install-libs"
else
  MAKE_COMMAND="${MAKE_COMMAND}; make install-progs"
  if [ "${PKG_TYPE}" == "shared" ]; then
    MAKE_COMMAND="${MAKE_COMMAND}; make install-libs"
  fi
fi

if command -v bear >/dev/null 2>&1 ; then
  MAKE_COMMAND="bear -- ${MAKE_COMMAND}"
fi
printf "\e[1m\e[36m%s\e[0m\n" "${MAKE_COMMAND}"
pushd -- "${PKG_BULD_DIR}"; eval ${MAKE_COMMAND}; popd
