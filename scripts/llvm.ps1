<#

# ----------------------------
if (-not (Test-Path -PathType Container -Path "${global:PROJ_ROOT}\.env")) {
  Push-Location "${global:PROJ_ROOT}"; python -m venv .env; Pop-Location
}
& ${global:PROJ_ROOT}\.env\Scripts\activate.ps1
python -m pip install ${global:PYPI_MIRROR} --upgrade pip
python -m pip install ${global:PYPI_MIRROR} --upgrade ninja

#>



# ----------------------------
# packages
# ----------------------------
. "${PROJ_ROOT}/pkg-conf.ps1"

Invoke-Command -ScriptBlock ${global:dl_pkgc} `
  -ArgumentList 'zlib-ng', 'cbb6ec1', 'static'
# ----------------------------
# static or shared
# ----------------------------
switch ($global:PKG_TYPE) {
  'static' {
    $PKG_TYPE_FLAG = "-D LLVM_BUILD_LLVM_DYLIB:BOOL=0"
    break
  }
  'shared' {
    $PKG_TYPE_FLAG = "-D LLVM_BUILD_LLVM_DYLIB:BOOL=1"
    break
  }
  default {
    Write-Error -Message "Invalid PKG TYPE: '${global:PKG_TYPE}'."
    exit 1
  }
}
# ----------------------------
# optimize
#  - 0 DEBUG
#  - 1 RELEASE (default)
# ----------------------------
$LIB_RELEASE = ${env:LIB_RELEASE}
if ($LIB_RELEASE -eq $null) {
  $LIB_RELEASE = "1"
}
if ($LIB_RELEASE -ieq "1") {
  $PKG_BULD_TYPE = @"
``
  -D CMAKE_BUILD_TYPE=Release ``
  -D CMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded
"@
  $PKG_INST_STRIP = "--strip"
} else {
  <#
  $PKG_BULD_TYPE = @"
``
  -D CMAKE_BUILD_TYPE=Debug ``
  -D CMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebug ``
  -D CMAKE_EXE_LINKER_FLAGS_DEBUG="/debug /INCREMENTAL:NO" ``
  -D CMAKE_SHARED_LINKER_FLAGS_DEBUG="/debug /INCREMENTAL:NO" ``
  -D CMAKE_MODULE_LINKER_FLAGS_DEBUG="/debug /INCREMENTAL:NO"
"@
  $PKG_INST_STRIP = ""
  #>
  Write-Error -Message "Unsupported LIB_RELEASE: '${LIB_RELEASE}'."
  exit 1
}
# ----------------------------
# compile :p
# ----------------------------
Remove-Item "${global:PKG_INST_DIR}" -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "${global:PKG_INST_DIR}" *> $null

Remove-Item "${global:PKG_BULD_DIR}" -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "${global:PKG_BULD_DIR}" *> $null

${env:CFLAGS} = "/utf-8"
${env:CXXFLAGS} = "${env:CFLAGS}"

$CMAKE_COMMAND = @"
cmake -G Ninja ``
  -S "${global:SUBPROJ_SRC}\llvm" -B "${global:PKG_BULD_DIR}" ``
  -D CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON ``
  -D CMAKE_INSTALL_PREFIX="${global:PKG_INST_DIR}" ``
  -D CMAKE_INSTALL_LIBDIR:PATH=lib ``
  -D CMAKE_PREFIX_PATH="${global:PKG_DEPS_CMAKE}" ``
  -D CMAKE_FIND_ROOT_PATH="${global:SYSROOT};${global:PKG_DEPS_CMAKE}" ``
  ${PKG_BULD_TYPE} ${PKG_TYPE_FLAG} ${global:CMAKE_EXTRA} ``
  -D LLVM_ENABLE_PROJECTS="clang;clang-tools-extra;lldb" ``
  -D CLANG_PLUGIN_SUPPORT:BOOL=0 ``
  -D LLVM_APPEND_VC_REV:BOOL=0   ``
  -D LLVM_ENABLE_BINDINGS:BOOL=0 ``
  -D LLVM_INCLUDE_BENCHMARKS:BOOL=0 ``
  -D LLVM_INCLUDE_EXAMPLES:BOOL=0   ``
  -D LLVM_INCLUDE_TESTS:BOOL=0 ``
  -D LLVM_INCLUDE_DOCS:BOOL=0  ``
  -D LLVM_INCLUDE_UTILS:BOOL=0 ``
  -D LLVM_ENABLE_ZLIB="FORCE_ON" ``
  -D LLVM_ENABLE_ZSTD="OFF"      ``
  -D LLDB_ENABLE_SWIG:BOOL=0     ``
  -D LLDB_ENABLE_LIBEDIT:BOOL=0  ``
  -D LLDB_ENABLE_CURSES:BOOL=0   ``
  -D LLDB_ENABLE_LUA:BOOL=0      ``
  -D LLDB_ENABLE_PYTHON:BOOL=0   ``
  -D LLDB_ENABLE_LIBXML2:BOOL=0  ``
  -D LLDB_ENABLE_FBSDVMCORE:BOOL=0  ``
  -D LLVM_TARGETS_TO_BUILD="AArch64;ARM;RISCV;WebAssembly;X86" ``
  -D LLDB_USE_SYSTEM_DEBUGSERVER:BOOL=1 ``
  -D LLVM_NATIVE_TOOL_DIR=${global:HOST_LLVM_BIN}
"@

switch ($global:PKG_PLATFORM) {
  'win-msvc' {
    if (${global:PKG_ARCH} -ieq "amd64") { ${script:LLVM_ARCH} = "X86" }
    if (${global:PKG_ARCH} -ieq "arm64") { ${script:LLVM_ARCH} = "AArch64" }
    $CMAKE_COMMAND = "${CMAKE_COMMAND} ``
      -D LLVM_HOST_TRIPLE=${global:TARGET_TRIPLE} -D LLVM_TARGET_ARCH=${script:LLVM_ARCH} ``
      -D CMAKE_CROSSCOMPILING:BOOL=TRUE -D CMAKE_SYSTEM_NAME=Windows ``
      -D CMAKE_C_HOST_COMPILER='${global:HOSTCC}' -D CMAKE_CXX_HOST_COMPILER='${global:HOSTCC}'"
    break
  }
  default {}
}

Write-Host -ForegroundColor Cyan "${CMAKE_COMMAND}"
Invoke-Expression -Command "${CMAKE_COMMAND}"
if (($LASTEXITCODE -ne $null) -and ($LASTEXITCODE -ne 0)) { exit $LASTEXITCODE }

# build & install
cmake --build "${global:PKG_BULD_DIR}" -j ${global:PARALLEL_JOBS} `
  --target 'clangd;lldb;lldb-dap;lldb-server;lldb-instr;llvm-symbolizer'
if (($LASTEXITCODE -ne $null) -and ($LASTEXITCODE -ne 0)) { exit $LASTEXITCODE }

cmake --install "${global:PKG_BULD_DIR}\tools" ${PKG_INST_STRIP} --component llvm-symbolizer
cmake --install "${global:PKG_BULD_DIR}\tools\lldb\tools" ${PKG_INST_STRIP} --component lldb
cmake --install "${global:PKG_BULD_DIR}\tools\lldb\tools" ${PKG_INST_STRIP} --component lldb-argdumper
cmake --install "${global:PKG_BULD_DIR}\tools\lldb\tools" ${PKG_INST_STRIP} --component lldb-dap
cmake --install "${global:PKG_BULD_DIR}\tools\lldb\tools" ${PKG_INST_STRIP} --component lldb-instr
cmake --install "${global:PKG_BULD_DIR}\tools\lldb\tools" ${PKG_INST_STRIP} --component lldb-server
cmake --install "${global:PKG_BULD_DIR}\tools\lldb"  ${PKG_INST_STRIP} --component liblldb
cmake --install "${global:PKG_BULD_DIR}\tools\clang" ${PKG_INST_STRIP} --component clangd
cmake --install "${global:PKG_BULD_DIR}\tools\clang" ${PKG_INST_STRIP} --component clang-resource-headers
