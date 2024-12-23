# ----------------------------
# if (-not (Test-Path -PathType Container -Path "${env:PROJ_ROOT}\.env")) {
#   Push-Location "${env:PROJ_ROOT}"; python -m venv .env; Pop-Location
# }
# & ${env:PROJ_ROOT}\.env\Scripts\activate.ps1
# python -m pip install ${env:PYPI_MIRROR} --upgrade pip
# python -m pip install ${env:PYPI_MIRROR} --upgrade ninja
# ----------------------------
# static or shared
# ----------------------------
switch ($env:PKG_TYPE) {
  'static' {
    $PKG_TYPE_FLAG = "-D LLVM_BUILD_LLVM_DYLIB:BOOL=0"
    break
  }
  'shared' {
    $PKG_TYPE_FLAG = "-D LLVM_BUILD_LLVM_DYLIB:BOOL=1"
    break
  }
  default {
    Write-Host -ForegroundColor Red "Invalid PKG TYPE: '${PKG_TYPE}'."
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
  Write-Host -ForegroundColor Red "Unsupported LIB_RELEASE: '${LIB_RELEASE}'."
  exit 1
}
# ----------------------------
# compile :p
# ----------------------------
Remove-Item "${env:PKG_INST_DIR}" -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "${env:PKG_INST_DIR}" *> $null

Remove-Item "${env:PKG_BULD_DIR}" -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "${env:PKG_BULD_DIR}" *> $null

${env:CFLAGS} = "/utf-8"
${env:CXXFLAGS} = "/utf-8"

$CMAKE_COMMAND = @"
cmake -G Ninja ``
  -S "${env:SUBPROJ_SRC}\llvm" -B "${env:PKG_BULD_DIR}" ``
  -D CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON ``
  -D CMAKE_INSTALL_PREFIX="${env:PKG_INST_DIR}" ``
  -D CMAKE_INSTALL_LIBDIR:PATH=lib ``
  ${PKG_BULD_TYPE} ``
  ${PKG_TYPE_FLAG} ``
  ${env:CMAKE_EXTRA} ``
  -D LLVM_ENABLE_PROJECTS="clang;clang-tools-extra;lldb" ``
  -D CLANG_PLUGIN_SUPPORT:BOOL=0 ``
  -D LLVM_APPEND_VC_REV:BOOL=0 ``
  -D LLVM_ENABLE_BINDINGS:BOOL=0 ``
  -D LLVM_INCLUDE_BENCHMARKS:BOOL=0 ``
  -D LLVM_INCLUDE_EXAMPLES:BOOL=0 ``
  -D LLVM_INCLUDE_TESTS:BOOL=0 ``
  -D LLVM_INCLUDE_DOCS:BOOL=0 ``
  -D LLVM_INCLUDE_UTILS:BOOL=0 ``
  -D LLVM_TARGETS_TO_BUILD="AArch64;ARM;RISCV;WebAssembly;X86" ``
  -D LLDB_USE_SYSTEM_DEBUGSERVER:BOOL=1
"@
Write-Host -ForegroundColor Cyan "${CMAKE_COMMAND}"
Invoke-Expression -Command "${CMAKE_COMMAND}"

# build & install
cmake --build "${env:PKG_BULD_DIR}" -j ${env:PARALLEL_JOBS} `
  --target 'clangd;lldb;lldb-dap;lldb-server;lldb-instr;llvm-symbolizer'
cmake --install "${env:PKG_BULD_DIR}\tools" ${PKG_INST_STRIP} --component llvm-symbolizer
cmake --install "${env:PKG_BULD_DIR}\tools\lldb\tools" ${PKG_INST_STRIP} --component lldb
cmake --install "${env:PKG_BULD_DIR}\tools\lldb\tools" ${PKG_INST_STRIP} --component lldb-argdumper
cmake --install "${env:PKG_BULD_DIR}\tools\lldb\tools" ${PKG_INST_STRIP} --component lldb-dap
cmake --install "${env:PKG_BULD_DIR}\tools\lldb\tools" ${PKG_INST_STRIP} --component lldb-instr
cmake --install "${env:PKG_BULD_DIR}\tools\lldb\tools" ${PKG_INST_STRIP} --component lldb-server
cmake --install "${env:PKG_BULD_DIR}\tools\lldb"  ${PKG_INST_STRIP} --component liblldb
cmake --install "${env:PKG_BULD_DIR}\tools\clang" ${PKG_INST_STRIP} --component clangd
cmake --install "${env:PKG_BULD_DIR}\tools\clang" ${PKG_INST_STRIP} --component clang-resource-headers
