#!/usr/bin/env bash
set -e

# ----------------------------
# prepare env
# ----------------------------
if [ ! -e "${SUBPROJ_SRC}/.env" ]; then
  pushd -- "${SUBPROJ_SRC}"
  {
    python3 -m venv .env
    .env/bin/python3 -m pip install ${PYPI_MIRROR} --upgrade pip
    .env/bin/python3 -m pip install ${PYPI_MIRROR} ninja
  }
  popd
fi
source ${SUBPROJ_SRC}/.env/bin/activate
# ----------------------------
# static or shared
# ----------------------------
case ${PKG_TYPE} in
  "static")
    PKG_TYPE_FLAG="-D LLVM_BUILD_LLVM_DYLIB:BOOL=0"
    ;;
  "shared")
    PKG_TYPE_FLAG="-D LLVM_BUILD_LLVM_DYLIB:BOOL=1"
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
{ rm -rf ${PKG_INST_DIR}; mkdir -p "${PKG_INST_DIR}"; }
{ rm -rf ${PKG_BULD_DIR}; mkdir -p "${PKG_BULD_DIR}"; }

case ${PKG_ARCH} in
  "amd64" | "x86_64")
    LLVM_TARGET="X86"
    ;;
  "arm64")
    LLVM_TARGET="AArch64"
    ;;
  ?)
    printf "\e[1m\e[31m%s\e[0m\n" "Invalid PKG_ARCH: '${PKG_ARCH}'."
    exit 1
    ;;
esac

# use CMAKE_<LANG>_COMPILER_LAUNCHER
if [ -n "${CC}" ]; then { export CC="${CC##*ccache }"; } fi
if [ -n "${CXX}" ]; then { export CXX="${CXX##*ccache }"; } fi

CMAKE_COMMAND=$(cat <<- EOF
cmake -G Ninja \
  -S "${SUBPROJ_SRC}/llvm" -B "${PKG_BULD_DIR}" \
  -D CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON \
  -D CMAKE_INSTALL_PREFIX="${PKG_INST_DIR}" \
  -D CMAKE_INSTALL_LIBDIR:PATH=lib \
  ${PKG_BULD_TYPE} ${PKG_TYPE_FLAG} ${CMAKE_EXTRA_ARGS} \
  -D LLVM_ENABLE_PROJECTS="clang;clang-tools-extra;lldb" \
  -D CLANG_PLUGIN_SUPPORT:BOOL=0 \
  -D LLVM_APPEND_VC_REV:BOOL=0 \
  -D LLVM_ENABLE_BINDINGS:BOOL=0 \
  -D LLVM_INCLUDE_BENCHMARKS:BOOL=0 \
  -D LLVM_INCLUDE_EXAMPLES:BOOL=0 \
  -D LLVM_INCLUDE_TESTS:BOOL=0 \
  -D LLVM_INCLUDE_DOCS:BOOL=0 \
  -D LLVM_INCLUDE_UTILS:BOOL=0 \
  -D LLVM_TARGETS_TO_BUILD="${LLVM_TARGET}" \
  -D LLDB_USE_SYSTEM_DEBUGSERVER:BOOL=1
EOF
)
printf "\e[1m\e[36m%s\e[0m\n" "${CMAKE_COMMAND}" && eval ${CMAKE_COMMAND}

# build & install
cmake --build "${PKG_BULD_DIR}"
cmake --install "${PKG_BULD_DIR}" ${PKG_INST_STRIP}

if command -v tree >/dev/null 2>&1 ; then
  tree ${PKG_INST_DIR}
else
  ls -alh -- ${PKG_INST_DIR}
fi
BUILD_DATE=$(date -u '+%Y-%m-%dT%H:%M:%SZ%:z')
printf "\e[1m\e[35m%s\e[0m\n" "${SUBPROJ_SRC} - Build Done @${BUILD_DATE}"
