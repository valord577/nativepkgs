# ----------------------------
# init submodules
# ----------------------------
Push-Location "${SUBPROJ_SRC}"

git submodule update --init --depth=1 --single-branch -f  -- src/expat

Pop-Location
# ----------------------------
# packages
# ----------------------------
. "${PROJ_ROOT}/pkg-conf.ps1"

Invoke-Command -ScriptBlock ${dl_pkgc} `
  -ArgumentList 'libpng16', '0024abd', 'static'
Invoke-Command -ScriptBlock ${dl_pkgc} `
  -ArgumentList 'zlib-ng',  'cbb6ec1', 'static'
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
  $_build_config = "Release"
  $PKG_BULD_TYPE = @"
``
  -D CMAKE_BUILD_TYPE=${_build_config} ``
  -D CMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded
"@
  $PKG_INST_STRIP = "--strip"
} else {
  <#
  $_build_config = "Debug"
  $PKG_BULD_TYPE = @"
``
  -D CMAKE_BUILD_TYPE=${_build_config} ``
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
  -S "${SUBPROJ_SRC}" -B "${PKG_BULD_DIR}" ``
  -D CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON   ``
  -D CMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON ``
  -D CMAKE_INSTALL_PREFIX="${PKG_INST_DIR}" ``
  -D CMAKE_INSTALL_LIBDIR:PATH=lib ``
  -D CMAKE_PREFIX_PATH="${PKG_DEPS_CMAKE}" ``
  -D CMAKE_FIND_ROOT_PATH="${SYSROOT};${PKG_DEPS_CMAKE}" ``
  ${PKG_BULD_TYPE} ${PKG_TYPE_FLAG} ${CMAKE_EXTRA} ``
  -D CMAKE_CONFIGURATION_TYPES="${_build_config}" ``
  -D wxBUILD_CXX_STANDARD=11 ``
  -D wxBUILD_MONOLITHIC=ON   ``
  -D wxBUILD_USE_STATIC_RUNTIME=ON ``
  -D wxUSE_UNICODE_UTF8=ON  ``
  -D THIRDPARTY_DEFAULT=sys ``
  -D wxUSE_REGEX=OFF   ``
  -D wxUSE_LIBJPEG=OFF ``
  -D wxUSE_LIBTIFF=OFF ``
  -D wxUSE_NANOSVG=OFF ``
  -D wxUSE_OPENGL=OFF  ``
  -D wxUSE_STC=OFF     ``
  -D wxUSE_WEBVIEW=OFF ``
  -D wxUSE_WEBVIEW_WEBKIT=OFF ``
  -D wxUSE_WEBVIEW_IE=OFF     ``
  -D wxUSE_WEBVIEW_EDGE=OFF   ``
  -D wxBUILD_COMPATIBILITY=3.1
"@

switch ($PKG_PLATFORM) {
  'win-msvc' {
    if ($PKG_ARCH -ieq "amd64") { $WIN32_ARCH = "x64" }
    if ($PKG_ARCH -ieq "arm64") { $WIN32_ARCH = "arm64" }
    $CMAKE_COMMAND = "${CMAKE_COMMAND} -D wxUSE_EXPAT=builtin ``
      -D wxUSE_WINRT=OFF -D wxUSE_ACCESSIBILITY=OFF ``
      -D CMAKE_VS_PLATFORM_NAME='${WIN32_ARCH}' -D wxUSE_WINSOCK2=ON"
    break
  }
  default {}
}

Write-Host -ForegroundColor Cyan "${CMAKE_COMMAND}"
Invoke-Expression -Command "${CMAKE_COMMAND}"
if (($LASTEXITCODE -ne $null) -and ($LASTEXITCODE -ne 0)) { exit $LASTEXITCODE }

# build & install
cmake --build "${PKG_BULD_DIR}" -j ${PARALLEL_JOBS} --config ${_build_config}
if (($LASTEXITCODE -ne $null) -and ($LASTEXITCODE -ne 0)) { exit $LASTEXITCODE }

cmake --install "${PKG_BULD_DIR}" ${PKG_INST_STRIP}
