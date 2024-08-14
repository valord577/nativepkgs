# ----------------------------
# prepare env
# ----------------------------
# if (-not (Test-Path -PathType Container -Path "${env:SUBPROJ_SRC}\.env")) {
#   Push-Location "${env:SUBPROJ_SRC}"
#   python -m venv .env

#   .\.env\Scripts\python -m pip install ${env:PYPI_MIRROR} --upgrade pip
#   .\.env\Scripts\python -m pip install ${env:PYPI_MIRROR} ninja
#   Pop-Location
# }
# & ${env:SUBPROJ_SRC}\.env\Scripts\activate.ps1
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
  $PKG_BULD_TYPE = @"
``
  -D CMAKE_BUILD_TYPE=Debug ``
  -D CMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebug ``
  -D CMAKE_EXE_LINKER_FLAGS_DEBUG="/debug /INCREMENTAL:NO" ``
  -D CMAKE_SHARED_LINKER_FLAGS_DEBUG="/debug /INCREMENTAL:NO" ``
  -D CMAKE_MODULE_LINKER_FLAGS_DEBUG="/debug /INCREMENTAL:NO"
"@
  $PKG_INST_STRIP = ""
}
# ----------------------------
# compile :p
# ----------------------------
Remove-Item "${env:PKG_INST_DIR}" -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "${env:PKG_INST_DIR}" *> $null

Remove-Item "${env:PKG_BULD_DIR}" -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "${env:PKG_BULD_DIR}" *> $null

switch ($env:PKG_ARCH) {
  'amd64' {
    $LLVM_TARGET = "X86"
    break
  }
  default {
    Write-Host -ForegroundColor Red "Invalid PKG_ARCH: '${PKG_ARCH}'."
    exit 1
  }
}

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
  ${env:CMAKE_EXTRA_ARGS} ``
  -D LLVM_ENABLE_PROJECTS="clang;clang-tools-extra;lldb" ``
  -D CLANG_PLUGIN_SUPPORT:BOOL=0 ``
  -D LLVM_APPEND_VC_REV:BOOL=0 ``
  -D LLVM_ENABLE_BINDINGS:BOOL=0 ``
  -D LLVM_INCLUDE_BENCHMARKS:BOOL=0 ``
  -D LLVM_INCLUDE_EXAMPLES:BOOL=0 ``
  -D LLVM_INCLUDE_TESTS:BOOL=0 ``
  -D LLVM_INCLUDE_DOCS:BOOL=0 ``
  -D LLVM_INCLUDE_UTILS:BOOL=0 ``
  -D LLVM_TARGETS_TO_BUILD="${LLVM_TARGET}" ``
  -D LLDB_USE_SYSTEM_DEBUGSERVER:BOOL=1
"@
Write-Host -ForegroundColor Cyan "${CMAKE_COMMAND}"
Invoke-Expression -Command "${CMAKE_COMMAND}"

# build & install
cmake --build "${env:PKG_BULD_DIR}"
cmake --install "${env:PKG_BULD_DIR}" ${PKG_INST_STRIP}

Get-ChildItem "${env:PKG_INST_DIR}"
$BUILD_DATE = (Get-Date -UFormat "+%Y-%m-%dT%H:%M:%S %Z")
Write-Host -ForegroundColor Magenta "${env:SUBPROJ_SRC} - Build Done @${BUILD_DATE}"
