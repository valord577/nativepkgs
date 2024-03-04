#!/usr/bin/env bash
set -e

# ----------------------------
# static or shared
# ----------------------------
case ${PKG_TYPE} in
  "static")
    PKG_TYPE_FLAG=""
    ;;
  "shared")
    PKG_TYPE_FLAG="--disable-static --enable-shared"
    ;;
  ?)
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
  PKG_BUILD_TYPE="--disable-debug"
  PKG_INSTALL_STRIP=""
else
  PKG_BUILD_TYPE="--disable-optimizations"
  PKG_INSTALL_STRIP="--disable-stripping"
fi
# ----------------------------
# compile :p
# ----------------------------
{ rm -rf ${PKG_BULD_DIR}; mkdir -p "${PKG_BULD_DIR}"; }
{ rm -rf ${PKG_INST_DIR}; mkdir -p "${PKG_INST_DIR}"; }

function ffm_deps() {
  local FFM_DEPS_NAME="${1}"
  local FFM_DEPS_PATH="${PROJ_ROOT}/out/${FFM_DEPS_NAME}/${PKG_PLATFORM}/${PKG_ARCH}"
  export CFLAGS="-I${FFM_DEPS_PATH}/include ${CFLAGS}"
  export CXXFLAGS="-I${FFM_DEPS_PATH}/include ${CXXFLAGS}"
  export LDFLAGS="-L${FFM_DEPS_PATH}/lib ${LDFLAGS}"
}
# ffm_deps "${PROJ_ROOT}/../librga/out"
# ffm_deps "${PROJ_ROOT}/../libyuv/out"

if command -v pkgconf >/dev/null 2>&1 ; then
  PKG_CONFIG_BIN="--pkg-config=pkgconf"
fi
function ffm_pkgc() {
  local FFM_DEPS_NAME="${1}"
  local FFM_DEPS_PATH="${PROJ_ROOT}/out/${FFM_DEPS_NAME}/${PKG_PLATFORM}/${PKG_ARCH}"
  export PKG_CONFIG_PATH="${FFM_DEPS_PATH}/lib/pkgconfig:${PKG_CONFIG_PATH}"

  FF_CONFIGURE_EXTRA="${FF_CONFIGURE_EXTRA} ${2}"
}
ffm_pkgc mbedtls '--enable-mbedtls'

case ${PKG_PLATFORM} in
  "macosx")
    ;;
  "iphoneos" | "iphonesimulator")
    FF_CONFIGURE_EXTRA="${FF_CONFIGURE_EXTRA} --disable-programs"
    ;;
  ?)
    ;;
esac

pushd -- "${PKG_BULD_DIR}"
CONFIGURE_COMMAND=$(cat <<- EOF
${SUBPROJ_SRC}/configure    \
  --prefix='${PKG_INST_DIR}' \
  --cc='${CC}' --cxx='${CXX}' \
  --enable-cross-compile \
  --sysroot='${SYSROOT_PATH}' \
  --target-os=darwin --arch=${PKG_ARCH} \
  --extra-cflags='${CFLAGS_EXTRA}'  \
  --extra-cxxflags='${CXXFLAGS_EXTRA}'  \
  --extra-ldflags='${LDFLAGS_EXTRA}' \
  ${PKG_TYPE_FLAG}     \
  ${PKG_BUILD_TYPE}    \
  ${PKG_INSTALL_STRIP} \
  ${PKG_CONFIG_BIN}    \
  --disable-logging \
  --disable-coreimage \
  --enable-version3 \
  --fatal-warnings \
  --disable-doc \
  --disable-devices \
  --enable-indev=lavfi \
  --enable-pic \
  --disable-symver \
  ${FF_CONFIGURE_EXTRA}
EOF
)
printf "\e[1m\e[36m%s\e[0m\n" "${CONFIGURE_COMMAND}" && eval ${CONFIGURE_COMMAND}
popd

# build & install
pushd -- "${PKG_BULD_DIR}"
MAKE_COMMAND="make -j ${PARALLEL_JOBS}"
if command -v bear >/dev/null 2>&1 ; then
  MAKE_COMMAND="bear -- ${MAKE_COMMAND}"
fi
eval ${MAKE_COMMAND}

make install
popd

if command -v tree >/dev/null 2>&1 ; then
  tree ${PKG_INST_DIR}
else
  ls -alh -- ${PKG_INST_DIR}
fi
BUILD_DATE=$(date -u '+%Y-%m-%dT%H:%M:%SZ%:z')
printf "\e[1m\e[35m%s\e[0m\n" "${SUBPROJ_SRC} - Build Done @${BUILD_DATE}"
