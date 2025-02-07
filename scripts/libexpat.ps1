# ----------------------------
# static or shared
# ----------------------------
switch ($PKG_TYPE) {
  'static' {
    $PKG_TYPE_FLAG = "-D EXPAT_SHARED_LIBS:BOOL=0"
    break
  }
  'shared' {
    $PKG_TYPE_FLAG = "-D EXPAT_SHARED_LIBS:BOOL=1"
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

${env:CFLAGS} = "/utf-8"
${env:CXXFLAGS} = "${env:CFLAGS}"

$CMAKE_COMMAND = @"
cmake -G Ninja ``
  -S "${SUBPROJ_SRC}\expat" -B "${PKG_BULD_DIR}" ``
  -D CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON   ``
  -D CMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON ``
  -D CMAKE_INSTALL_PREFIX="${PKG_INST_DIR}" ``
  -D CMAKE_INSTALL_LIBDIR:PATH=lib   ``
  -D EXPAT_WARNINGS_AS_ERRORS:BOOL=1 ``
  -D EXPAT_MSVC_STATIC_CRT:BOOL=1    ``
  -D EXPAT_BUILD_TOOLS:BOOL=0    ``
  -D EXPAT_BUILD_EXAMPLES:BOOL=0 ``
  -D EXPAT_BUILD_TESTS:BOOL=0    ``
  -D EXPAT_BUILD_DOCS:BOOL=0     ``
  -D EXPAT_BUILD_FUZZERS:BOOL=0  ``
  -D EXPAT_OSSFUZZ_BUILD:BOOL=0  ``
  -D EXPAT_WITH_LIBBSD:BOOL=0    ``
  ${PKG_BULD_TYPE} ${PKG_TYPE_FLAG} ${CMAKE_EXTRA}
"@
Write-Host -ForegroundColor Cyan "${CMAKE_COMMAND}"
Invoke-Expression -Command "${CMAKE_COMMAND}"
if (($LASTEXITCODE -ne $null) -and ($LASTEXITCODE -ne 0)) { exit $LASTEXITCODE }

# build & install
cmake --build "${PKG_BULD_DIR}" -j ${PARALLEL_JOBS}
if (($LASTEXITCODE -ne $null) -and ($LASTEXITCODE -ne 0)) { exit $LASTEXITCODE }

cmake --install "${PKG_BULD_DIR}" ${PKG_INST_STRIP}
