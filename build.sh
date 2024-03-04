#!/usr/bin/env bash
set -e

PROJ_ROOT=$(cd "$(dirname ${BASH_SOURCE[0]})"; pwd)

basename="${BASH_SOURCE[0]##*/}"
triplet="${basename%%\.*}"
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
iphoneos/arm64
iphonesimulator/x86_64
iphonesimulator/arm64
EOF
)

UNSUPPORTED_ERR="1"
for t in ${SUPPORTED_TARGET[@]}; do
  if [ "${t}" == "${TARGET_PLATFORM}/${TARGET_ARCH}" ]; then
    UNSUPPORTED_ERR="0"

    case ${TARGET_PLATFORM} in
      "macosx" | "iphoneos" | "iphonesimulator")
        source "${PROJ_ROOT}/env-apple.sh" ${TARGET_PLATFORM} ${TARGET_ARCH}
        ;;
      ?)
        ;;
    esac
  fi
done

if [ "${UNSUPPORTED_ERR}" == "1" ]; then
  printf "\e[1m\e[31m%s\e[0m\n" "Invalid PKG TARGET: '${TARGET_PLATFORM}/${TARGET_ARCH}'."
  exit 1
fi

function compile() {
  (
    export PROJ_ROOT="${PROJ_ROOT}"

    export PKG_NAME="${1}"
    export SUBPROJ_SRC="${PROJ_ROOT}/deps/${PKG_NAME}"

    export PKG_TYPE="${2}"
    export PKG_PLATFORM="${3}"
    export PKG_ARCH="${4}"

    export PKG_BULD_DIR=${BULD_DIR:-"${PROJ_ROOT}/tmp/${PKG_NAME}/${PKG_PLATFORM}/${PKG_ARCH}"}
    export PKG_INST_DIR=${INST_DIR:-"${PROJ_ROOT}/out/${PKG_NAME}/${PKG_PLATFORM}/${PKG_ARCH}"}

    if [ ! -e "${SUBPROJ_SRC}/.git" ]; then
      pushd -- "${PROJ_ROOT}"
      git submodule update --init --depth 1 -- "deps/${PKG_NAME}"
      popd
    fi
    pushd -- "${SUBPROJ_SRC}"
    export PKG_VERSION="$(git describe --tags --always --dirty --abbrev=${GIT_ABBREV:-"7"})"
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

export CC=${CC:-"clang"}
export CXX=${CXX:-"clang++"}
if command -v ccache >/dev/null 2>&1 ; then
  export CC="ccache ${CC}"
  export CXX="ccache ${CXX}"
fi

if [ ! ${GITHUB_ACTIONS} ]; then
  printf "\e[1m\e[35m%s\e[0m\n" "Uncomment the following  to compile."

  # compile mbedtls static ${TARGET_PLATFORM} ${TARGET_ARCH}
  # compile ffmpeg  static ${TARGET_PLATFORM} ${TARGET_ARCH}
fi
