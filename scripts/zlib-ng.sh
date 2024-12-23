#!/usr/bin/env bash
set -e

# ----------------------------
# static or shared
# ----------------------------
case ${PKG_TYPE} in
  "static")
    PKG_TYPE_FLAG="-D BUILD_SHARED_LIBS:BOOL=0"
    ;;
  "shared")
    PKG_TYPE_FLAG="-D BUILD_SHARED_LIBS:BOOL=1"
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
  PKG_BUILD_TYPE="-D CMAKE_BUILD_TYPE=Release -D WITH_OPTIM:BOOL=1"
  PKG_INSTALL_STRIP="--strip"
else
  PKG_BUILD_TYPE="-D CMAKE_BUILD_TYPE=Debug -D WITH_OPTIM:BOOL=0"
  PKG_INSTALL_STRIP=""
fi
# ----------------------------
# compile :p
# ----------------------------
{ rm -rf ${PKG_BULD_DIR}; mkdir -p "${PKG_BULD_DIR}"; }
{ rm -rf ${PKG_INST_DIR}; mkdir -p "${PKG_INST_DIR}"; }

CMAKE_COMMAND=$(cat <<- EOF
cmake -S "${SUBPROJ_SRC}" -B "${PKG_BULD_DIR}" \
  -D CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON \
  -D CMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON \
  -D CMAKE_INSTALL_PREFIX="${PKG_INST_DIR}" \
  -D CMAKE_INSTALL_LIBDIR:PATH=lib \
  -D ZLIB_COMPAT:BOOL=1   \
  -D WITH_GTEST:BOOL=0    \
  -D WITH_GZFILEOP:BOOL=0 \
  -D ZLIB_ENABLE_TESTS:BOOL=0   \
  -D ZLIBNG_ENABLE_TESTS:BOOL=0 \
  ${PKG_BUILD_TYPE} ${PKG_TYPE_FLAG} ${CMAKE_EXTRA}
EOF
)
printf "\e[1m\e[36m%s\e[0m\n" "${CMAKE_COMMAND}"; eval ${CMAKE_COMMAND}

# build & install
cmake --build "${PKG_BULD_DIR}" -j ${PARALLEL_JOBS}
cmake --install "${PKG_BULD_DIR}" ${PKG_INSTALL_STRIP}
