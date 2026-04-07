#!/usr/bin/env python3

import os
import sys
sys.dont_write_bytecode = True
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..')),
)

# fmt: off

from scripts import utils as x


if __name__ == "__main__":
    _github_env = os.getenv('GITHUB_ENV', '')
    if not _github_env:
        raise RuntimeError('This script should be run on Github Action')

    _pkg_version = x._util_get_pkg_version_desc()
    _target_arch_libc = os.getenv('TARGET_ARCH_LIBC', '')

    _pkg_name = sys.argv[1]
    _pkg_plat = sys.argv[2]
    _pkg_type = sys.argv[3]

    _pkg_zipname = f'{_pkg_name}_{_pkg_plat}_{_target_arch_libc}_{_pkg_version}_{_pkg_type}'

    def _setenv(f, k, v):
        x.print_stderr(f'{k}: {v}'); f.write(f'{k}={v}\n')

    with open(_github_env, 'a') as f:
        _setenv(f, 'PKG_VERSION', _pkg_version)
        _setenv(f, 'PKG_ZIPNAME', _pkg_zipname)
