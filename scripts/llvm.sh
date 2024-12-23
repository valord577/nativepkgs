#!/usr/bin/env bash
set -e

# ----------------------------
if [ ! -e "${PROJ_ROOT}/.env" ]; then
  pushd -- ${PROJ_ROOT}; python3 -m venv .env; popd
fi
source ${PROJ_ROOT}/.env/bin/activate
python3 -m pip install ${PYPI_MIRROR} --upgrade pip
python3 -m pip install ${PYPI_MIRROR} --upgrade ninja
# ----------------------------
# packages
# ----------------------------
source "${PROJ_ROOT}/pkg-conf.sh"
dl_pkgc zlib-ng  'c939498'   static

printf "\e[1m\e[35m%s\e[0m\n" "${PKG_CONFIG_PATH}"
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
{ rm -rf ${PKG_INST_DIR}; mkdir -p "${PKG_INST_DIR}"; }
{ rm -rf ${PKG_BULD_DIR}; mkdir -p "${PKG_BULD_DIR}"; }

CMAKE_COMMAND=$(cat <<- EOF
cmake -G Ninja \
  -S "${SUBPROJ_SRC}/llvm" -B "${PKG_BULD_DIR}" \
  -D CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON  \
  -D CMAKE_INSTALL_PREFIX="${PKG_INST_DIR}" \
  -D CMAKE_INSTALL_LIBDIR:PATH=lib \
  -D CMAKE_PREFIX_PATH="${PKG_DEPS_CMAKE}" \
  -D CMAKE_FIND_ROOT_PATH="${SYSROOT};${PKG_DEPS_CMAKE}" \
  ${PKG_BULD_TYPE} ${PKG_TYPE_FLAG} ${CMAKE_EXTRA} \
  -D LLVM_ENABLE_PROJECTS="clang;clang-tools-extra;lldb" \
  -D CLANG_PLUGIN_SUPPORT:BOOL=0 \
  -D LLVM_APPEND_VC_REV:BOOL=0   \
  -D LLVM_ENABLE_BINDINGS:BOOL=0 \
  -D LLVM_INCLUDE_BENCHMARKS:BOOL=0 \
  -D LLVM_INCLUDE_EXAMPLES:BOOL=0   \
  -D LLVM_INCLUDE_TESTS:BOOL=0 \
  -D LLVM_INCLUDE_DOCS:BOOL=0  \
  -D LLVM_INCLUDE_UTILS:BOOL=0 \
  -D LLVM_ENABLE_ZLIB="FORCE_ON" \
  -D LLVM_TARGETS_TO_BUILD="AArch64;ARM;RISCV;WebAssembly;X86" \
  -D LLDB_USE_SYSTEM_DEBUGSERVER:BOOL=1
EOF
)
if [ "${CROSS_BUILD_ENABLED}" == "1" ]; then
  [ "${PKG_ARCH}" == "amd64" ] && { LLVM_ARCH="X86"; }
  [ "${PKG_ARCH}" == "arm64" ] && { LLVM_ARCH="AArch64"; }
  [ "${PKG_ARCH}" == "armv7" ] && { LLVM_ARCH="ARM"; }
  CMAKE_COMMAND="${CMAKE_COMMAND} -D LLVM_HOST_TRIPLE=${TARGET_TRIPLE} -D LLVM_TARGET_ARCH=${LLVM_ARCH} \
    -D CMAKE_C_HOST_COMPILER='${HOSTCC}' -D CMAKE_CXX_HOST_COMPILER='${HOSTCXX}'"
fi
printf "\e[1m\e[36m%s\e[0m\n" "${CMAKE_COMMAND}"; eval ${CMAKE_COMMAND}

# build & install
cmake --build "${PKG_BULD_DIR}" -j ${PARALLEL_JOBS} \
  --target 'clangd;lldb;lldb-dap;lldb-server;lldb-instr'
cmake --install "${PKG_BULD_DIR}/tools/lldb/tools" ${PKG_INST_STRIP} --component lldb
cmake --install "${PKG_BULD_DIR}/tools/lldb/tools" ${PKG_INST_STRIP} --component lldb-argdumper
cmake --install "${PKG_BULD_DIR}/tools/lldb/tools" ${PKG_INST_STRIP} --component lldb-dap
cmake --install "${PKG_BULD_DIR}/tools/lldb/tools" ${PKG_INST_STRIP} --component lldb-instr
cmake --install "${PKG_BULD_DIR}/tools/lldb/tools" ${PKG_INST_STRIP} --component lldb-server
cmake --install "${PKG_BULD_DIR}/tools/lldb"  ${PKG_INST_STRIP} --component liblldb
cmake --install "${PKG_BULD_DIR}/tools/clang" ${PKG_INST_STRIP} --component clangd
cmake --install "${PKG_BULD_DIR}/tools/clang" ${PKG_INST_STRIP} --component clang-resource-headers
