#!/usr/bin/env bash
set -e

# ----------------------------
# static or shared
# ----------------------------
case ${PKG_TYPE} in
  "static")
    PKG_TYPE_FLAG="-D BUILD_SHARED_LIBS:BOOL=0"
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
  PKG_BULD_TYPE="-D CMAKE_BUILD_TYPE=Release"
  PKG_INST_STRIP="--strip"
else
  PKG_BULD_TYPE="-D CMAKE_BUILD_TYPE=Debug"
  PKG_INST_STRIP=""
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
  ${PKG_BULD_TYPE} ${PKG_TYPE_FLAG} ${CMAKE_EXTRA_ARGS} \
  -D SDL_CCACHE:BOOL=0 -D SDL_TEST:BOOL=0 \
  -D SDL2_DISABLE_SDL2MAIN:BOOL=1
EOF
)
printf "\e[1m\e[36m%s\e[0m\n" "${CMAKE_COMMAND}" && eval ${CMAKE_COMMAND}

# build & install
cmake --build "${PKG_BULD_DIR}" -j ${PARALLEL_JOBS}
cmake --install "${PKG_BULD_DIR}" ${PKG_INST_STRIP}

if command -v tree >/dev/null 2>&1 ; then
  tree ${PKG_INST_DIR}
else
  ls -alh -- ${PKG_INST_DIR}
fi
BUILD_DATE=$(date -u '+%Y-%m-%dT%H:%M:%SZ%:z')
printf "\e[1m\e[35m%s\e[0m\n" "${SUBPROJ_SRC} - Build Done @${BUILD_DATE}"
