#!/usr/bin/env bash
set -e

# ----------------------------
# packages
# ----------------------------
source "${PROJ_ROOT}/pkg-conf.sh"
[ "${PLATFORM_APPLE}" != "1" ] && \
  {
    dl_pkgc zlib-ng  'cbb6ec1'   static
  }

printf "\e[1m\e[35m%s\e[0m\n" "${PKG_CONFIG_PATH}"
# ----------------------------
# static or shared
# ----------------------------
case ${PKG_TYPE} in
  "static")
    PKG_TYPE_FLAG="-D PNG_SHARED:BOOL=0 -D PNG_STATIC:BOOL=1"
    ;;
  "shared")
    PKG_TYPE_FLAG="-D PNG_SHARED:BOOL=1 -D PNG_STATIC:BOOL=0"
    ;;
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
  PKG_BUILD_TYPE="-D CMAKE_BUILD_TYPE=Release"
  PKG_INSTALL_STRIP="--strip"
else
  PKG_BUILD_TYPE="-D CMAKE_BUILD_TYPE=Debug -D PNG_DEBUG:BOOL=1"
  PKG_INSTALL_STRIP=""
fi
# ----------------------------
# compile :p
# ----------------------------
{ rm -rf ${PKG_BULD_DIR}; mkdir -p "${PKG_BULD_DIR}"; }
{ rm -rf ${PKG_INST_DIR}; mkdir -p "${PKG_INST_DIR}"; }

CMAKE_COMMAND=$(cat <<- EOF
cmake -S "${SUBPROJ_SRC}" -B "${PKG_BULD_DIR}" \
  -D CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON   \
  -D CMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON \
  -D CMAKE_INSTALL_PREFIX="${PKG_INST_DIR}"  \
  -D CMAKE_INSTALL_LIBDIR:PATH=lib \
  -D CMAKE_PREFIX_PATH="${PKG_DEPS_CMAKE}" \
  -D CMAKE_FIND_ROOT_PATH="${SYSROOT};${PKG_DEPS_CMAKE}" \
  -D PNG_FRAMEWORK:BOOL=0  \
  -D PNG_TESTS:BOOL=0 -D PNG_TOOLS:BOOL=0 \
  ${PKG_BUILD_TYPE} ${PKG_TYPE_FLAG} ${CMAKE_EXTRA}
EOF
)
printf "\e[1m\e[36m%s\e[0m\n" "${CMAKE_COMMAND}"; eval ${CMAKE_COMMAND}

# build & install
cmake --build "${PKG_BULD_DIR}" -j ${PARALLEL_JOBS}
cmake --install "${PKG_BULD_DIR}" ${PKG_INSTALL_STRIP}
