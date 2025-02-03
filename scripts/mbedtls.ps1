# ----------------------------
# init submodules
# ----------------------------
Push-Location "${SUBPROJ_SRC}"
git submodule set-url -- framework ../mbedtls-framework

git submodule update --init --depth=1 --single-branch -f  -- framework
Pop-Location
# ----------------------------
# preset features
# ----------------------------
python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_PEM_PARSE_C
python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_PEM_WRITE_C

python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_HAVE_SSE2
python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_DEPRECATED_REMOVED

python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_PSA_P256M_DRIVER_ENABLED
python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_ECDH_VARIANT_EVEREST_ENABLED

python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_SSL_PROTO_TLS1_3
python3 ${SUBPROJ_SRC}/scripts/config.py set MBEDTLS_SSL_TLS1_3_COMPATIBILITY_MODE

python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_DEBUG_C
python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_SELF_TEST
python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_SSL_SRV_C
python3 ${SUBPROJ_SRC}/scripts/config.py unset MBEDTLS_SSL_RENEGOTIATION
# ----------------------------
# static or shared
# ----------------------------
switch ($PKG_TYPE) {
  'static' {
    $PKG_TYPE_FLAG = "-D USE_STATIC_MBEDTLS_LIBRARY:BOOL=1 -D USE_SHARED_MBEDTLS_LIBRARY:BOOL=0"
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
New-Item -ItemType Directory -Path "${PKG_INST_DIR}" *> $null

Remove-Item "${PKG_BULD_DIR}" -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "${PKG_BULD_DIR}" *> $null

${env:CFLAGS} = "/utf-8 /wd4146"
${env:CXXFLAGS} = "${env:CFLAGS}"

$CMAKE_COMMAND = @"
cmake -G Ninja ``
  -S "${SUBPROJ_SRC}" -B "${PKG_BULD_DIR}" ``
  -D CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON   ``
  -D CMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON ``
  -D CMAKE_INSTALL_PREFIX="${PKG_INST_DIR}" ``
  -D CMAKE_INSTALL_LIBDIR:PATH=lib ``
  ${PKG_BULD_TYPE} ${PKG_TYPE_FLAG} ``
  -D MBEDTLS_AS_SUBPROJECT:BOOL=0 ${CMAKE_EXTRA} ``
  -D ENABLE_PROGRAMS:BOOL=0 -D ENABLE_TESTING:BOOL=0
"@
Write-Host -ForegroundColor Cyan "${CMAKE_COMMAND}"
Invoke-Expression -Command "${CMAKE_COMMAND}"
if (($LASTEXITCODE -ne $null) -and ($LASTEXITCODE -ne 0)) { exit $LASTEXITCODE }

# build & install
cmake --build "${PKG_BULD_DIR}" -j ${PARALLEL_JOBS}
if (($LASTEXITCODE -ne $null) -and ($LASTEXITCODE -ne 0)) { exit $LASTEXITCODE }

cmake --install "${PKG_BULD_DIR}" ${PKG_INST_STRIP}
