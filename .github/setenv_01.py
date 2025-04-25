#!/usr/bin/env python3

# fmt: off

import os
import sys
from typing import NoReturn


def _print(msg: str):
    print(msg, file=sys.stderr)
def show_errmsg(errmsg: str) -> NoReturn:
    _print(f'[e] {errmsg}')
    sys.exit(1)


if __name__ == "__main__":
    _github_env = os.getenv('GITHUB_ENV', '')
    if not _github_env:
        show_errmsg('This script should be run on Github Action')

    _pkg_version = ''
    with open(os.getenv('DEPS_VER', ''), 'r') as f:
        _pkg_version = f.read()
    _target_arch_libc = os.getenv('TARGET_ARCH_LIBC', '')

    _pkg_name = sys.argv[1]
    _pkg_plat = sys.argv[2]
    _pkg_type = sys.argv[3]

    _pkg_zipname = f'{_pkg_name}_{_pkg_plat}_{_target_arch_libc}_{_pkg_version}_{_pkg_type}'

    def _setenv(f, k, v):
        _print(f'{k}: {v}'); f.write(f'{k}={v}\n')

    with open(_github_env, 'a') as f:
        _setenv(f, 'PKG_VERSION', _pkg_version)
        _setenv(f, 'PKG_ZIPNAME', _pkg_zipname)
