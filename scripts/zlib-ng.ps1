# ----------------------------
# static or shared
# ----------------------------
switch ($PKG_TYPE) {
  'static' {
    $PKG_TYPE_FLAG = "-D BUILD_SHARED_LIBS:BOOL=0"
    break
  }
  'shared' {
    $PKG_TYPE_FLAG = "-D BUILD_SHARED_LIBS:BOOL=1"
    break
  }
  default {
    Write-Error -Message "Invalid PKG TYPE: '${PKG_TYPE}'."
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
Remove-Item "${PKG_INST_DIR}" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "${PKG_BULD_DIR}" -Recurse -Force -ErrorAction SilentlyContinue

${env:CFLAGS} = "/utf-8 /wd5105"
${env:CXXFLAGS} = "${env:CFLAGS}"

$CMAKE_COMMAND = @"
cmake -G Ninja ``
  -S "${SUBPROJ_SRC}" -B "${PKG_BULD_DIR}" ``
  -D CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON   ``
  -D CMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON ``
  -D CMAKE_INSTALL_PREFIX="${PKG_INST_DIR}" ``
  -D CMAKE_INSTALL_LIBDIR:PATH=lib ``
  -D ZLIB_COMPAT:BOOL=1   ``
  -D WITH_GTEST:BOOL=0    ``
  -D WITH_GZFILEOP:BOOL=0 ``
  -D ZLIB_ENABLE_TESTS:BOOL=0   ``
  -D ZLIBNG_ENABLE_TESTS:BOOL=0 ``
  ${PKG_BULD_TYPE} ${PKG_TYPE_FLAG} ${CMAKE_EXTRA}
"@
Write-Host -ForegroundColor Cyan "${CMAKE_COMMAND}"
Invoke-Expression -Command "${CMAKE_COMMAND}"
if (($LASTEXITCODE -ne $null) -and ($LASTEXITCODE -ne 0)) { exit $LASTEXITCODE }

# build & install
cmake --build "${PKG_BULD_DIR}" -j ${PARALLEL_JOBS}
if (($LASTEXITCODE -ne $null) -and ($LASTEXITCODE -ne 0)) { exit $LASTEXITCODE }

cmake --install "${PKG_BULD_DIR}" ${PKG_INST_STRIP}
