#!/usr/bin/env python3

# fmt: off

from scripts import utils as x
# ----------------------------

import os
import shlex

from pathlib import Path


BUILD_CMD = 'cmake'
BUILD_ENV = os.environ.copy()

_subproj_src = ''
_subproj_src_patches = ''

_target_pkg_type = ''
_target_platform = ''
_target_archlibc = ''

_3rd_deps_dir = ''
_pkg_buld_dir = ''
_pkg_inst_dir = ''

_extra_sysroot = ''
_extra_args_build: list[str] = []

def module_init(env: dict) -> list:
    global _target_pkg_type; \
        _target_pkg_type = env['PKG_TYPE']
    global _subproj_src; \
        _subproj_src = env['SUBPROJ_SRC']
    global _subproj_src_patches; \
        _subproj_src_patches = env['SUBPROJ_SRC_PATCHES']
    global _target_platform; \
        _target_platform = env['PKG_PLATFORM']
    global _target_archlibc; \
        _target_archlibc = env['PKG_ARCH_LIBC']
    global _3rd_deps_dir; \
        _3rd_deps_dir = env['3RD_DEPS_DIR']
    global _pkg_buld_dir; \
        _pkg_buld_dir = env['PKG_BULD_DIR']
    global _pkg_inst_dir; \
        _pkg_inst_dir = env['PKG_INST_DIR']
    global _extra_sysroot; \
        _extra_sysroot = env.get('SYSROOT', '')
    global _extra_args_build; \
        _extra_args_build = env[f'EXTRA_{BUILD_CMD.upper()}']

    if _target_pkg_type != 'static':
        raise NotImplementedError(f'unsupported PKG_TYPE: {_target_pkg_type}')


    global BUILD_ENV

    if _target_platform == 'android':
        BUILD_ENV['ANDROID_API_LEVEL'] = env['ANDROID_API_LEVEL']
    elif _target_platform == 'win-msvc':
        BUILD_ENV = env['WIN32_MSVC_ENV_TARGET']
        BUILD_ENV['CFLAGS']   = '/utf-8 /wd5105'
        BUILD_ENV['CXXFLAGS'] = BUILD_ENV['CFLAGS']
        _extra_args_build.extend(['-D', 'CMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded'])

    return [
        _source_download,
        _source_apply_patches,
        _build_step_00,
        _build_step_01,
        _build_step_02,
    ]



def _source_download():
    _git_target = 'refs/tags/2.2.5'
    if not (Path(_subproj_src) / '.git').exists():
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'init'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'remote', 'add', 'x', 'https://github.com/zlib-ng/zlib-ng.git'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{_git_target}'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'checkout', 'FETCH_HEAD'])
    x._util_put_pkg_version_desc(x._util_func__subprocess(cwd=_subproj_src, collect_stdout=True, args=['git', 'describe', '--always', '--abbrev=7']))
def _source_apply_patches():
    if not (Path(_subproj_src_patches)).exists():
        return
    x._util_func__subprocess(cwd=_subproj_src, args=['git', 'reset', '--hard', 'HEAD'])
    x._util_func__subprocess(cwd=_subproj_src, args=['git', 'clean', '-d', '-f', '-q'])
    for it in Path(_subproj_src_patches).iterdir():
        if not it.is_file():
            continue
        x._util_func__subprocess(cwd=_subproj_src, args=[
            'git', 'apply', '--verbose', '--ignore-space-change', '--ignore-whitespace', it.absolute().as_posix(),
        ])


def _build_step_00():
    args = [BUILD_CMD, *_extra_args_build,
        '-S',   _subproj_src,
        '-D',  'CMAKE_BUILD_TYPE=RelWithDebInfo',
        '-D',  'BUILD_SHARED_LIBS:BOOL=0',
        '-D',  'ZLIB_COMPAT:BOOL=1',
        '-D',  'WITH_GTEST:BOOL=0',
        '-D',  'WITH_GZFILEOP:BOOL=0',
        '-D',  'WITH_OPTIM:BOOL=1',
        '-D',  'WITH_INFLATE_STRICT:BOOL=1',
        '-D',  'ZLIB_ENABLE_TESTS:BOOL=0',
        '-D',  'ZLIBNG_ENABLE_TESTS:BOOL=0',
    ]
    x._util_func__subprocess(env=BUILD_ENV, args=args)
def _build_step_01():
    args = f"{BUILD_CMD} --build {_pkg_buld_dir} -j {x.CPU_COUNT}"
    x._util_func__subprocess(env=BUILD_ENV, args=shlex.split(args))
def _build_step_02():
    args = f"{BUILD_CMD} --install {_pkg_buld_dir}"
    x._util_func__subprocess(env=BUILD_ENV, args=shlex.split(args))
