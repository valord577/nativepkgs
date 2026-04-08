#!/usr/bin/env python3

# fmt: off

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.append(
    (Path(__file__).parent / '..').resolve().as_posix()
)
from scripts import utils as x
# ----------------------------

import os


_github_env = os.getenv('GITHUB_ENV', '')
if not _github_env:
    raise RuntimeError('This script should be run on Github Action')

_pkg_name = sys.argv[1]
_pkg_plat = sys.argv[2]
_pkg_arch = sys.argv[3]
_pkg_libc = sys.argv[4]
_pkg_type = sys.argv[5]

with open(_github_env, 'a') as f:
    x._util_append_ci_env(f, 'PKG_TYPE', _pkg_type)

    _inst_dir = (Path(x.PROJ_ROOT) / _pkg_name).resolve().as_posix()
    x._util_append_ci_env(f, 'INST_DIR', _inst_dir)
    _deps_ver = f'{_inst_dir}.ver'
    x._util_append_ci_env(f, 'DEPS_VER', _deps_ver)

    _target_arch_libc = f'{_pkg_arch}'
    if _pkg_plat in ['linux', 'android'] and _pkg_libc:
        _target_arch_libc = f'{_pkg_arch}-{_pkg_libc}'
    x._util_append_ci_env(f, 'TARGET_ARCH_LIBC', _target_arch_libc)

    # ccache
    _ccache_dir = (Path(x.PROJ_ROOT) / '.ccache').resolve().as_posix()
    x._util_append_ci_env(f, 'CCACHE_DIR', _ccache_dir)
    _ccache_key = f'{_pkg_name}-{_pkg_type}-{_pkg_plat}-{_target_arch_libc}'
    x._util_append_ci_env(f, 'CCACHE_KEY', _ccache_key)
