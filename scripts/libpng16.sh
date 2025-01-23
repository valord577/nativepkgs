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
    PKG_TYPE_FLAG="--enable-shared=no"
    ;;
  *)
    printf "\e[1m\e[31m%s\e[0m\n" "Invalid PKG TYPE: '${PKG_TYPE}'."
    exit 1
    ;;
esac
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
  ${PKG_TYPE_FLAG}  \
  ${PKG_BULD_TYPE}  \
  ${PKG_INST_STRIP} \
  --enable-pic=yes \
  --disable-tests  \
  --disable-tools  \
  --enable-werror  \
  --without-binconfigs \
  --disable-dependency-tracking \
  --enable-hardware-optimizations=yes \
  ${PKG_DEPS_ARGS}
EOF
)

case ${PKG_PLATFORM} in
  "macosx" | "iphoneos" | "iphonesimulator")
    CONFIGURE_COMMAND="${CONFIGURE_COMMAND} --host=${PKG_ARCH}"
    ;;
  "linux" | "win-mingw")
    export CPPFLAGS="$(${PKG_CONFIG_EXEC} --cflags zlib)"
    export LDFLAGS="${CROSS_LDFLAGS} $(${PKG_CONFIG_EXEC} --libs-only-L zlib)"
    CONFIGURE_COMMAND="${CONFIGURE_COMMAND} --host='${TARGET_TRIPLE}'"
    ;;
  *)
    ;;
esac

printf "\e[1m\e[36m%s\e[0m\n" "${CONFIGURE_COMMAND}"
pushd -- "${PKG_BULD_DIR}"; eval ${CONFIGURE_COMMAND}; popd

# build & install
MAKE_COMMAND="make -j ${PARALLEL_JOBS}"
MAKE_COMMAND="${MAKE_COMMAND}; make install-libLTLIBRARIES"
MAKE_COMMAND="${MAKE_COMMAND}; make install-pkgconfigDATA"
MAKE_COMMAND="${MAKE_COMMAND}; make install-nodist_pkgincludeHEADERS"
MAKE_COMMAND="${MAKE_COMMAND}; make install-pkgincludeHEADERS"
MAKE_COMMAND="${MAKE_COMMAND}; make install-header-links"
MAKE_COMMAND="${MAKE_COMMAND}; make install-libpng-pc"
MAKE_COMMAND="${MAKE_COMMAND}; make install-library-links"

if command -v bear >/dev/null 2>&1 ; then
  MAKE_COMMAND="bear -- ${MAKE_COMMAND}"
fi
printf "\e[1m\e[36m%s\e[0m\n" "${MAKE_COMMAND}"
pushd -- "${PKG_BULD_DIR}"; eval ${MAKE_COMMAND}; popd

rm -rf ${PKG_INST_DIR}/lib/*.la
