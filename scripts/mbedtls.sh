#!/usr/bin/env bash
set -ex

# ----------------------------
# init submodules
# ----------------------------
pushd -- "${SUBPROJ_SRC}"
git submodule set-url -- framework ../mbedtls-framework

git submodule update --init --depth=1 --single-branch -f  -- framework
popd
# ----------------------------
# preset features
# ----------------------------
python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_PEM_PARSE_C
python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_PEM_WRITE_C

python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_HAVE_SSE2
python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_SHA256_USE_A64_CRYPTO_IF_PRESENT
python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_SHA512_USE_A64_CRYPTO_IF_PRESENT
python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_DEPRECATED_WARNING
python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_DEPRECATED_REMOVED

python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_PSA_P256M_DRIVER_ENABLED
python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_ECDH_VARIANT_EVEREST_ENABLED

python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_SSL_PROTO_TLS1_3
python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_SSL_TLS1_3_COMPATIBILITY_MODE

python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_VERSION_C
python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_VERSION_FEATURES
python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_DEBUG_C
python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_SELF_TEST
python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_SSL_SRV_C
python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_SSL_RENEGOTIATION
# ----------------------------
# static or shared
# ----------------------------
case ${PKG_TYPE} in
  "static")
    PKG_TYPE_FLAG="-D USE_STATIC_MBEDTLS_LIBRARY:BOOL=1 -D USE_SHARED_MBEDTLS_LIBRARY:BOOL=0"
    PKG_LIBRARY_DEPS="-lmbedtls -lmbedx509 -lmbedcrypto -lp256m -leverest"
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

# use CMAKE_<LANG>_COMPILER_LAUNCHER
if [ -n "${CC}" ]; then { export CC="${CC##*ccache }"; } fi
if [ -n "${CXX}" ]; then { export CXX="${CXX##*ccache }"; } fi
if [ -n "${OBJC}" ]; then { export OBJC="${OBJC##*ccache }"; } fi
if [ -n "${OBJCXX}" ]; then { export OBJCXX="${OBJCXX##*ccache }"; } fi

CMAKE_COMMAND=$(cat <<- EOF
cmake -S "${SUBPROJ_SRC}" -B "${PKG_BULD_DIR}" \
  -D CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON \
  -D CMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON \
  -D CMAKE_INSTALL_PREFIX="${PKG_INST_DIR}" \
  -D CMAKE_INSTALL_LIBDIR:PATH=lib \
  ${PKG_BULD_TYPE} ${PKG_TYPE_FLAG} \
  -D MBEDTLS_AS_SUBPROJECT:BOOL=1 ${CMAKE_EXTRA_ARGS} \
  -D ENABLE_PROGRAMS:BOOL=0 -D ENABLE_TESTING:BOOL=0
EOF
)
printf "\e[1m\e[36m%s\e[0m\n" "${CMAKE_COMMAND}" && eval ${CMAKE_COMMAND}

# build & install
cmake --build "${PKG_BULD_DIR}" -j ${PARALLEL_JOBS}
cmake --install "${PKG_BULD_DIR}" ${PKG_INST_STRIP}

PKG_CONFIG_FILE="${PKG_INST_DIR}/lib/pkgconfig/mbedtls.pc"
mkdir -p -- "$(dirname ${PKG_CONFIG_FILE})"
cat > "${PKG_CONFIG_FILE}" <<- EOF
prefix=\${pcfiledir}/../..
libdir=\${prefix}/lib
includedir=\${prefix}/include

Name: mbedtls
Description: An open source, portable, easy to use, readable and flexible TLS library
Version:
Libs: -L\${libdir} ${PKG_LIBRARY_DEPS}
Cflags: -I\${includedir}
EOF

if command -v tree >/dev/null 2>&1 ; then
  tree -L 3 ${PKG_INST_DIR}
else
  ls -alh -- ${PKG_INST_DIR}
fi
BUILD_DATE=$(date -u '+%Y-%m-%dT%H:%M:%SZ%:z')
printf "\e[1m\e[35m%s\e[0m\n" "${SUBPROJ_SRC} - Build Done @${BUILD_DATE}"
