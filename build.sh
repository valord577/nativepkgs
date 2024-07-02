#!/usr/bin/env bash
set -e

PROJ_ROOT=$(cd "$(dirname ${BASH_SOURCE[0]})"; pwd)

basename="${BASH_SOURCE[0]##*/}"
triplet="${basename%%\.*}"
triplet_values=(${triplet//_/ })
triplet_length=${#triplet_values[@]}
if [ $triplet_length -lt 3 ]; then
  printf "\e[1m\e[31m%s\e[0m\n" \
    "Please use wrapper to build the project, such as 'build_\${platform}_\${arch}.sh'."
  exit 1
fi
TARGET_PLATFORM="${triplet_values[1]}"
prefix="${triplet_values[0]}_${triplet_values[1]}_"
TARGET_ARCH="${triplet#${prefix}}"

case ${TARGET_PLATFORM} in
  "linux")
    source "${PROJ_ROOT}/env-linux.sh" ${TARGET_PLATFORM} ${TARGET_ARCH}
    ;;
  "macosx" | "iphoneos" | "iphonesimulator")
    source "${PROJ_ROOT}/env-apple.sh" ${TARGET_PLATFORM} ${TARGET_ARCH}
    ;;
  ?)
    ;;
esac

function compile() {
  (
    export PROJ_ROOT="${PROJ_ROOT}"
    export PYPI_MIRROR="-i https://mirrors.bfsu.edu.cn/pypi/web/simple"

    export PKG_NAME="${1}"
    export SUBPROJ_SRC="${PROJ_ROOT}/deps/${PKG_NAME}"

    export PKG_TYPE="${2}"
    export PKG_PLATFORM="${3}"
    export PKG_ARCH="${4}"

    export PKG_BULD_DIR="${PROJ_ROOT}/tmp/${PKG_NAME}/${PKG_PLATFORM}/${PKG_ARCH}"
    export PKG_INST_DIR="${PROJ_ROOT}/out/${PKG_NAME}/${PKG_PLATFORM}/${PKG_ARCH}"
    if [ "${GITHUB_ACTIONS}" == "true" ]; then
      if [ -n "${BULD_DIR}" ]; then { export PKG_BULD_DIR="${BULD_DIR}"; } fi
      if [ -n "${INST_DIR}" ]; then { export PKG_INST_DIR="${INST_DIR}"; } fi
    fi

    if [ ! -e "${SUBPROJ_SRC}/.git" ]; then
      pushd -- "${PROJ_ROOT}"
      git submodule update --init -f -- "deps/${PKG_NAME}"
      popd
    fi
    pushd -- "${SUBPROJ_SRC}"
    export PKG_VERSION="$(git describe --tags --always --dirty --abbrev=7)"
    popd

    if [ -e "${PROJ_ROOT}/patchs/${PKG_NAME}" ]; then
      pushd -- "${SUBPROJ_SRC}"
      git reset --hard HEAD

      for patch in $(ls -- "${PROJ_ROOT}/patchs/${PKG_NAME}"); do
        git apply "${PROJ_ROOT}/patchs/${PKG_NAME}/${patch}"
      done
      popd
    fi
    bash "${PROJ_ROOT}/scripts/${PKG_NAME}.sh"
  )
}

if [ "${GITHUB_ACTIONS}" != "true" ]; then
  if [ -z ${1} ]; then
    printf "\e[1m\e[31m%s\e[0m\n" "Please declare the module to be compiled."
    exit 1
  fi
  compile ${1} ${2:-"static"} ${TARGET_PLATFORM} ${TARGET_ARCH}
fi
