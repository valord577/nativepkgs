#!/usr/bin/env bash
set -e

if [ -n "${CROSS_TOOLCHAIN_PKGCONF}" ]; then
  export PKG_CONFIG_EXEC="${CROSS_TOOLCHAIN_PKGCONF}"
fi

dep_libs_dir="${PROJ_ROOT}/lib"
if [ ! -e "${dep_libs_dir}" ]; then { mkdir -p "${dep_libs_dir}"; } fi

function dl_pkgc() {
  if [ ! -e "${dep_libs_dir}/${1}" ]; then
    (
      pkg_name="${1}"
      pkg_version="${2}"
      pkg_type="${3}"
      pkg_extra="${4}"

      pushd -- "${dep_libs_dir}"
      {
        if [ "${GITHUB_ACTIONS}" == "true" ]; then
          (
            dl_filename="${pkg_name}_${PKG_PLATFORM}_${PKG_ARCH_LIBC}_${pkg_version}_${pkg_type}"
            if [ -n "${pkg_extra}" ]; then { dl_filename="${dl_filename}_${pkg_extra}"; } fi
            printf "\e[1m\e[36m%s\e[0m\n" "dl_filename='${dl_filename}.zip'"

            ${PROJ_ROOT}/.github/oss_v4.py pull "${pkg_name}/${pkg_version}/${dl_filename}.zip" "${pkg_name}.zip"
            unzip -q "${pkg_name}.zip"
          )
        else
          (
            set -x
            ln -sfn ../out/${pkg_name}/${PKG_PLATFORM}/${PKG_ARCH_LIBC} ${pkg_name}
            set +x
          )
        fi
      }
      popd
    )
  fi

  export PKG_DEPS_ARGS="${PKG_DEPS_ARGS} ${5}"
  export PKG_CONFIG_PATH="${dep_libs_dir}/${1}/lib/pkgconfig:${PKG_CONFIG_PATH}"

  # mark libraries (shared static)
  #  - PKG_DEPS_SHARED
  #  - PKG_DEPS_STATIC
  _pkg_type_=$(echo ${3} | tr "[:lower:]" "[:upper:]") # fixed: run on macos zsh
  eval export "PKG_DEPS_${_pkg_type_}=\"\${PKG_DEPS_${_pkg_type_}} ${dep_libs_dir}/${1}\""

  # https://cmake.org/cmake/help/latest/variable/CMAKE_MODULE_PATH.html
  cmake_search_path="${dep_libs_dir}/${1}"
  if [ -n "${6}" ]; then
    cmake_search_path="${dep_libs_dir}/${1}/${6}"
  fi
  export PKG_DEPS_CMAKE="${cmake_search_path};${PKG_DEPS_CMAKE}"

  # for shared library's own dependencies
  if [ -n "${7}" ]; then
    triplet_values=(${7//:/ })
    for path in ${triplet_values[@]}; do
      export LD_LIBRARY_PATH="${dep_libs_dir}/${1}/${path}:${LD_LIBRARY_PATH}"
    done
  fi
}
