${global:dep_libs_dir}="${global:PROJ_ROOT}\lib"
if (-not (Test-Path -PathType Container -Path "${global:dep_libs_dir}")) {
  New-Item -ItemType Directory -Path "${global:dep_libs_dir}" *> $null
}

${global:dl_pkgc} = {
  param (
    [Parameter(Mandatory=$true)][string]$pkg_name,
    [Parameter(Mandatory=$true)][string]$pkg_version,
    [Parameter(Mandatory=$true)][string]$pkg_type,

    [Parameter(Mandatory=$false)][string]$pkg_extra = "",
    [Parameter(Mandatory=$false)][string]$pkg_deps_args = "",
    [Parameter(Mandatory=$false)][string]$cmake_search_path = "",
    [Parameter(Mandatory=$false)][string]$pkg_cmake_name = ""
  )

  ${script:_this_lib_dir_} = "${global:dep_libs_dir}\${pkg_name}"

  Push-Location "${global:dep_libs_dir}"
  if (${env:GITHUB_ACTIONS} -ieq "true") {
    ${script:dl_filename} = "${pkg_name}_${global:PKG_PLATFORM}_${global:PKG_ARCH}_${pkg_version}_${pkg_type}"
    if (${pkg_extra} -ne "") { ${script:dl_filename} = "${script:dl_filename}_${pkg_extra}" }
    Write-Host -ForegroundColor Cyan "dl_filename='${script:dl_filename}.zip'"

    python3 ${global:PROJ_ROOT}/.github/oss_v4.py pull "${pkg_name}/${pkg_version}/${script:dl_filename}.zip" "${pkg_name}.zip"
    Expand-Archive -Path ".\${pkg_name}.zip" -DestinationPath "."
  } else {
    New-Item -Force -ItemType SymbolicLink -Path ".\${pkg_name}" `
      -Target "${global:PROJ_ROOT}\out\${pkg_name}\${global:PKG_PLATFORM}\${global:PKG_ARCH}"
  }
  Pop-Location

  ${global:PKG_DEPS_ARGS} = "${global:PKG_DEPS_ARGS} ${pkg_deps_args}"

  # mark libraries (shared static)
  #  - PKG_DEPS_SHARED
  #  - PKG_DEPS_STATIC
  ${script:_pkg_type_} = ${pkg_type}.Toupper()
  Invoke-Expression -Command `
    "`${global:PKG_DEPS_${script:_pkg_type_}} = `"`${global:PKG_DEPS_${script:_pkg_type_}} ${script:_this_lib_dir_}`""

  # https://cmake.org/cmake/help/latest/variable/CMAKE_MODULE_PATH.html
  ${script:_cmake_search_path} = "${script:_this_lib_dir_}"
  if (${cmake_search_path} -ne "") {
    ${script:_cmake_search_path} = "${script:_this_lib_dir_}\${cmake_search_path}"
  }
  ${global:PKG_DEPS_CMAKE} = "${script:_cmake_search_path};${global:PKG_DEPS_CMAKE}"
  if (${pkg_cmake_name} -ne "") {
    Invoke-Expression -Command "`${env:${pkg_cmake_name}_LIBRARY} = `"${script:_this_lib_dir_}\lib`""
    Invoke-Expression -Command "`${env:${pkg_cmake_name}_INCLUDE_DIR} = `"${script:_this_lib_dir_}\include`""
    Invoke-Expression -Command "`${env:${pkg_cmake_name}_ROOT} = `"${script:_this_lib_dir_}`""
  }
}
