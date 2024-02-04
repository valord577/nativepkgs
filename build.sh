#!/usr/bin/env bash
set -e

PROJ_ROOT=$(cd "$(dirname ${BASH_SOURCE[0]})"; pwd)

basename="${BASH_SOURCE[0]##*/}"
triplet="${basename%\.sh}"
triplet_values=(${triplet//-/ })
triplet_length=${#triplet_values[@]}
if [ $triplet_length -eq 3 ]; then
  TARGET_PLATFORM="${triplet_values[1]}"
  TARGET_ARCH="${triplet_values[2]}"
else
  TARGET_PLATFORM="macosx"
  TARGET_ARCH="$(uname -m)"
fi

SUPPORTED_TARGET=$(cat <<- 'EOF'
macosx/x86_64
macosx/arm64
iphoneos/armv7
iphoneos/arm64
iphonesimulator/x86_64
iphonesimulator/arm64
EOF
)

UNSUPPORTED_ERR="1"
for t in ${SUPPORTED_TARGET[@]}; do
  if [ "${t}" == "${TARGET_PLATFORM}/${TARGET_ARCH}" ]; then
    UNSUPPORTED_ERR="0"
    source "${PROJ_ROOT}/env-apple.sh" ${TARGET_PLATFORM} ${TARGET_ARCH}
  fi
done

if [ "${UNSUPPORTED_ERR}" == "1" ]; then
  printf "\e[1m\e[31m%s\e[0m\n" "Invalid PKG TARGET: '${TARGET_PLATFORM}/${TARGET_ARCH}'."
  exit 1
fi

function compile() {
  (
    export PROJ_ROOT="${PROJ_ROOT}"

    export SUBPROJ="${1}"
    export SUBPROJ_SRC="${PROJ_ROOT}/${SUBPROJ}"

    export PKG_TYPE="${2}"
    export PKG_PLATFORM="${3}"
    export PKG_ARCH="${4}"

    export PKG_BULD_DIR="${PROJ_ROOT}/tmp/${SUBPROJ}/${PKG_PLATFORM}/${PKG_ARCH}"
    export PKG_INST_DIR="${PROJ_ROOT}/out/${SUBPROJ}/${PKG_PLATFORM}/${PKG_ARCH}"

    if [ ! -e "${SUBPROJ_SRC}/.git" ]; then
      pushd -- "${PROJ_ROOT}"
      git submodule init -- "deps/${SUBPROJ}"
      git submodule update -- "deps/${SUBPROJ}"
      popd
    fi
    if [ -e "${PROJ_ROOT}/patchs/${SUBPROJ}" ]; then
      pushd -- "${SUBPROJ_SRC}"
      for patch in $(ls -- "${PROJ_ROOT}/patchs/${SUBPROJ}"); do
        git reset --hard HEAD
        git apply "${PROJ_ROOT}/patchs/${SUBPROJ}/${patch}"
      done
      popd
    fi

    bash "${PROJ_ROOT}/scripts/${SUBPROJ}.sh"
  )
}

export CC=${CC:-"clang"}
export CXX=${CXX:-"clang++"}
if command -v ccache >/dev/null 2>&1 ; then
  export CC="ccache ${CC}"
  export CXX="ccache ${CXX}"
fi

compile mbedtls static                   ${TARGET_PLATFORM} ${TARGET_ARCH}
compile ffmpeg  ${FF_PKG_TYPE:-"static"} ${TARGET_PLATFORM} ${TARGET_ARCH}
