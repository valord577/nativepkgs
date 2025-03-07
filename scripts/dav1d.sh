#!/usr/bin/env bash
set -e

# ----------------------------
if [ ! -e "${PROJ_ROOT}/.env" ]; then
  pushd -- ${PROJ_ROOT}; python3 -m venv .env; popd
fi
source ${PROJ_ROOT}/.env/bin/activate
python3 -m pip install ${PYPI_MIRROR} --upgrade pip
python3 -m pip install ${PYPI_MIRROR} --upgrade meson ninja
# ----------------------------
# static or shared
# ----------------------------
case ${PKG_TYPE} in
  "static")
    PKG_TYPE_FLAG="--default-library static"
    ;;
  "shared")
    PKG_TYPE_FLAG="--default-library shared"
    ;;
  *)
    printf "\e[1m\e[31m%s\e[0m\n" "Invalid PKG TYPE: '${PKG_TYPE}'."
    exit 1
    ;;
esac
# ----------------------------
# optimize
#  - 0 DEBUG
#  - 1 RELEASE (default)
# ----------------------------
LIB_RELEASE=${LIB_RELEASE:-"1"}
if [ "${LIB_RELEASE}" == "1" ]; then
  PKG_BUILD_TYPE="--buildtype release"
  PKG_INSTALL_STRIP="--strip"
else
  PKG_BUILD_TYPE="--buildtype debug"
  PKG_INSTALL_STRIP=""
fi
# ----------------------------
# compile :p
# ----------------------------
{ rm -rf ${PKG_BULD_DIR}; mkdir -p "${PKG_BULD_DIR}"; }
{ rm -rf ${PKG_INST_DIR}; mkdir -p "${PKG_INST_DIR}"; }

# https://mesonbuild.com/Feature-autodetection.html#ccache
unset CC; unset CXX;

MESON_COMMAND=$(cat <<- EOF
meson setup \
  --prefix ${PKG_INST_DIR} \
  --libdir lib \
  --python.install-env venv \
  --pkgconfig.relocatable   \
  ${PKG_BUILD_TYPE} ${PKG_TYPE_FLAG}  \
  --wrap-mode nofallback -Db_pie=true \
  -Denable_docs=false \
  -Denable_examples=false \
  -Denable_seek_stress=false \
  -Denable_tests=false \
  -Denable_tools=false \
  ${MESON_EXTRA} ${PKG_BULD_DIR} ${SUBPROJ_SRC}
EOF
)
printf "\e[1m\e[36m%s\e[0m\n" "${MESON_COMMAND}"; eval ${MESON_COMMAND}

# build & install
meson compile -C "${PKG_BULD_DIR}" -j ${PARALLEL_JOBS}
meson install -C "${PKG_BULD_DIR}" --no-rebuild ${PKG_INSTALL_STRIP}

# rm -rf ${PKG_INST_DIR}/{bin,libexec,share}
# sed -i 's@^prefix=.*@prefix=${pcfiledir}/../..@g' ${PKG_INST_DIR}/lib/pkgconfig/**
