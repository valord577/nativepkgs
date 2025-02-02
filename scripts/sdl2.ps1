# ----------------------------
# static or shared
# ----------------------------
switch ($global:PKG_TYPE) {
  'static' {
    $PKG_TYPE_FLAG = "-D BUILD_SHARED_LIBS:BOOL=0"
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
  -D WITH_OPTIM:BOOL=1 ``
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
  -S "${global:SUBPROJ_SRC}" -B "${global:PKG_BULD_DIR}" ``
  -D CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON   ``
  -D CMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON ``
  -D CMAKE_INSTALL_PREFIX="${global:PKG_INST_DIR}" ``
  -D CMAKE_INSTALL_LIBDIR:PATH=lib ``
  ${PKG_BULD_TYPE} ${PKG_TYPE_FLAG} ${global:CMAKE_EXTRA} ``
  -D SDL_CCACHE:BOOL=0 -D SDL_TEST:BOOL=0 ``
  -D SDL2_DISABLE_SDL2MAIN:BOOL=1
"@
Write-Host -ForegroundColor Cyan "${CMAKE_COMMAND}"
Invoke-Expression -Command "${CMAKE_COMMAND}"

# build & install
cmake --build "${global:PKG_BULD_DIR}" -j ${global:PARALLEL_JOBS}
cmake --install "${global:PKG_BULD_DIR}" ${PKG_INST_STRIP}
