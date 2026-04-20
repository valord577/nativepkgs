#!/usr/bin/env python3

# fmt: off

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.append(
    (Path(__file__).parent / '..').absolute().as_posix()
)
from scripts import utils as x
# ----------------------------

import os


_github_env = os.getenv('GITHUB_ENV')
if not _github_env:
    raise RuntimeError('This script should be run on Github Action')

_pkg_name = sys.argv[1]
_pkg_plat = sys.argv[2]
_pkg_type = sys.argv[3]


_pkg_version = x._util_get_pkg_version_desc(_pkg_name)
_target_arch_libc = os.getenv('TARGET_ARCH_LIBC')

_pkg_zipname = f'{_pkg_name}_{_pkg_plat}_{_target_arch_libc}_{_pkg_version}_{_pkg_type}'

with open(_github_env, 'a') as f:
    x._util_append_ci_env(f, 'PKG_VERSION', _pkg_version)
    x._util_append_ci_env(f, 'PKG_ZIPNAME', _pkg_zipname)
