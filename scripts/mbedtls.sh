#!/usr/bin/env bash
set -e

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
python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_DEPRECATED_WARNING
python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_DEPRECATED_REMOVED

python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_SHA256_USE_A64_CRYPTO_IF_PRESENT
python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_SHA512_USE_A64_CRYPTO_IF_PRESENT
python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_PSA_P256M_DRIVER_ENABLED
python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_ECDH_VARIANT_EVEREST_ENABLED

python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_SSL_PROTO_TLS1_3
python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_SSL_TLS1_3_COMPATIBILITY_MODE

python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_DEBUG_C
python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_SELF_TEST
python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_SSL_SRV_C
python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_SSL_RENEGOTIATION


case ${PKG_PLATFORM} in
  "win-mingw")
    if [ "${PKG_ARCH}" == "aarch64" ]; then
      python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_SHA256_USE_A64_CRYPTO_IF_PRESENT
      python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_SHA512_USE_A64_CRYPTO_IF_PRESENT
    fi
    ;;
  "linux")
    if [ "${PKG_ARCH}" == "armv7" ]; then
      python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_ECDH_VARIANT_EVEREST_ENABLED
    fi
    ;;
  *)
    ;;
esac
# ----------------------------
# static or shared
# ----------------------------
case ${PKG_TYPE} in
  "static")
    PKG_TYPE_FLAG="-D USE_STATIC_MBEDTLS_LIBRARY:BOOL=1 -D USE_SHARED_MBEDTLS_LIBRARY:BOOL=0"
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
  -D CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON \
  -D CMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON \
  -D CMAKE_INSTALL_PREFIX="${PKG_INST_DIR}" \
  -D CMAKE_INSTALL_LIBDIR:PATH=lib \
  ${PKG_BULD_TYPE} ${PKG_TYPE_FLAG} \
  -D MBEDTLS_AS_SUBPROJECT:BOOL=0 ${CMAKE_EXTRA} \
  -D ENABLE_PROGRAMS:BOOL=0 -D ENABLE_TESTING:BOOL=0
EOF
)
printf "\e[1m\e[36m%s\e[0m\n" "${CMAKE_COMMAND}"; eval ${CMAKE_COMMAND}

# build & install
cmake --build "${PKG_BULD_DIR}" -j ${PARALLEL_JOBS}
cmake --install "${PKG_BULD_DIR}" ${PKG_INST_STRIP}
