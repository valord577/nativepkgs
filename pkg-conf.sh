#!/usr/bin/env bash
set -e

export PKG_CONFIG_EXEC="pkg-config"
if command -v pkgconf >/dev/null 2>&1 ; then
  export PKG_CONFIG_EXEC="pkgconf"
fi

if [ -z "${PROJ_ROOT}" ]; then
  PROJ_ROOT=$(cd "$(dirname ${BASH_SOURCE[0]})"; pwd)
fi
export PKG_DEPS_PATH="${PROJ_ROOT}/lib"
{ rm -rf "${PKG_DEPS_PATH}"; mkdir -p "${PKG_DEPS_PATH}"; }

function dl_pkgc() {
  (
    pkg_name="${1}"
    pkg_version="${2}"
    pkg_type="${3}"
    pkg_extra="${4}"

    pushd -- "${PKG_DEPS_PATH}"
    {
      if [ "${GITHUB_ACTIONS}" == "true" ]; then
        {
          dl_filename="${pkg_name}_${PKG_PLATFORM}_${PKG_ARCH}_${pkg_version}_${pkg_type}.zip"
          if [ -n "${pkg_extra}" ]; then
            dl_filename="${pkg_name}_${PKG_PLATFORM}_${PKG_ARCH}_${pkg_version}_${pkg_type}_${pkg_extra}.zip"
          fi
          printf "\e[1m\e[36m%s\e[0m\n" "dl_filename='${dl_filename}'"

          set -x
          ossutil cp \
            oss://${GH_OSSUTIL_BUCKET}/${GH_OSSUTIL_PKGS}/${pkg_name}/${pkg_version}/${dl_filename} \
            ./${pkg_name}.zip \
            -c ${GH_OSSUTIL_CONF_PATH}
          set +x
          unzip -q "${pkg_name}.zip"
        }
      else
        {
          set -x
          ln -sfn ../out/${pkg_name}/${PKG_PLATFORM}/${PKG_ARCH} ${pkg_name}
          set +x
        }
      fi
    }
    popd
  )

  export PKG_DEPS_ARGS="${PKG_DEPS_ARGS} ${5}"
  if [ "${3}" == "shared" ]; then { export PKG_DEPS_SHARED="${PKG_DEPS_SHARED} ${1}"; } fi

  export PKG_DEPS_CMAKE="${PKG_DEPS_PATH}/${1};${PKG_DEPS_CMAKE}"
  export PKG_CONFIG_PATH="${PKG_DEPS_PATH}/${1}/lib/pkgconfig:${PKG_CONFIG_PATH}"
}
