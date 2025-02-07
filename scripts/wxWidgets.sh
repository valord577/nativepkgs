#!/usr/bin/env bash
set -e

# ----------------------------
# packages
# ----------------------------
source "${PROJ_ROOT}/pkg-conf.sh"
dl_pkgc libpng16  '0024abd'   static

[ "${PLATFORM_APPLE}" != "1" ] && \
  {
    dl_pkgc libexpat '2691aff'   static
    dl_pkgc zlib-ng  'cbb6ec1'   static
  }

printf "\e[1m\e[35m%s\e[0m\n" "${PKG_CONFIG_PATH}"
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
  -D CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON   \
  -D CMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON \
  -D CMAKE_INSTALL_PREFIX="${PKG_INST_DIR}"  \
  -D CMAKE_INSTALL_LIBDIR:PATH=lib \
  -D CMAKE_PREFIX_PATH="${PKG_DEPS_CMAKE}" \
  -D CMAKE_FIND_ROOT_PATH="${SYSROOT};${PKG_DEPS_CMAKE}" \
  ${PKG_BULD_TYPE} ${PKG_TYPE_FLAG} ${CMAKE_EXTRA} \
  -D wxBUILD_CXX_STANDARD=11 \
  -D wxBUILD_MONOLITHIC=ON   \
  -D wxBUILD_USE_STATIC_RUNTIME=ON \
  -D wxUSE_UNICODE_UTF8=ON  \
  -D THIRDPARTY_DEFAULT=sys \
  -D wxUSE_REGEX=OFF   \
  -D wxUSE_LIBJPEG=OFF \
  -D wxUSE_LIBTIFF=OFF \
  -D wxUSE_NANOSVG=OFF \
  -D wxBUILD_COMPATIBILITY=3.1
EOF
)

case ${PKG_PLATFORM} in
  "win-mingw")
    CMAKE_COMMAND="${CMAKE_COMMAND} \
      -D CMAKE_C_FLAGS_INIT='-Wno-unused-command-line-argument' \
      -D CMAKE_CXX_FLAGS_INIT='-Wno-unused-command-line-argument'"
    ;;
  *)
    ;;
esac

printf "\e[1m\e[36m%s\e[0m\n" "${CMAKE_COMMAND}"; eval ${CMAKE_COMMAND}

# build & install
cmake --build "${PKG_BULD_DIR}" -j ${PARALLEL_JOBS}
cmake --install "${PKG_BULD_DIR}" ${PKG_INST_STRIP}
