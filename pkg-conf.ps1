$dep_libs_dir = "${PROJ_ROOT}\lib"
if (-not (Test-Path -PathType Container -Path "${dep_libs_dir}")) {
  New-Item -ItemType Directory -Path "${dep_libs_dir}" *> $null
}

$dl_pkgc = {
  param (
    [Parameter(Mandatory=$true)][string]${private:pkg_name},
    [Parameter(Mandatory=$true)][string]${private:pkg_version},
    [Parameter(Mandatory=$true)][string]${private:pkg_type},

    [Parameter(Mandatory=$false)][string]${private:pkg_extra} = "",
    [Parameter(Mandatory=$false)][string]${private:pkg_deps_args} = "",
    [Parameter(Mandatory=$false)][string]${private:cmake_search_path} = "",
    [Parameter(Mandatory=$false)][string]${private:pkg_cmake_name} = ""
  )

  ${private:_this_lib_dir_} = "${dep_libs_dir}\${pkg_name}"

  Push-Location "${dep_libs_dir}"
  if (${env:GITHUB_ACTIONS} -ieq "true") {
    ${private:dl_filename} = "${pkg_name}_${PKG_PLATFORM}_${PKG_ARCH}_${pkg_version}_${pkg_type}"
    if (${pkg_extra} -ne "") { ${dl_filename} = "${dl_filename}_${pkg_extra}" }
    Write-Host -ForegroundColor Cyan "dl_filename='${dl_filename}.zip'"

    python3 ${PROJ_ROOT}/.github/oss_v4.py pull `
      "${pkg_name}/${pkg_version}/${dl_filename}.zip" "${pkg_name}.zip"
    Expand-Archive -Path ".\${pkg_name}.zip" -DestinationPath "."
  } else {
    New-Item -Force -ItemType SymbolicLink -Path ".\${pkg_name}" `
      -Target "${PROJ_ROOT}\out\${pkg_name}\${PKG_PLATFORM}\${PKG_ARCH}"
  }
  Pop-Location

  ${script:PKG_DEPS_ARGS} = "${script:PKG_DEPS_ARGS} ${pkg_deps_args}"

  # mark libraries (shared static)
  #  - PKG_DEPS_SHARED
  #  - PKG_DEPS_STATIC
  ${private:_pkg_type_} = ${pkg_type}.Toupper()
  Invoke-Expression -Command `
    "`${script:PKG_DEPS_${_pkg_type_}} = `"`${script:PKG_DEPS_${_pkg_type_}} ${_this_lib_dir_}`""

  # https://cmake.org/cmake/help/latest/variable/CMAKE_MODULE_PATH.html
  ${private:_cmake_search_path} = "${_this_lib_dir_}"
  if (${cmake_search_path} -ne "") {
    ${_cmake_search_path} = "${_this_lib_dir_}\${cmake_search_path}"
  }
  ${script:PKG_DEPS_CMAKE} = "${_cmake_search_path};${PKG_DEPS_CMAKE}"
  if (${pkg_cmake_name} -ne "") {
    Invoke-Expression -Command "`${env:${pkg_cmake_name}_LIBRARY} = `"${_this_lib_dir_}\lib`""
    Invoke-Expression -Command "`${env:${pkg_cmake_name}_INCLUDE_DIR} = `"${_this_lib_dir_}\include`""
    Invoke-Expression -Command "`${env:${pkg_cmake_name}_ROOT} = `"${_this_lib_dir_}`""
  }
}
