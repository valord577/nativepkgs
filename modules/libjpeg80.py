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

_target_pkg_name = ''
_target_pkg_type = ''
_target_platform = ''
_target_arch = ''

_pkg_buld_dir = ''
_pkg_inst_dir = ''

_extra_args_build: list[str] = []

def module_init(env: dict) -> list:
    global _target_pkg_name; \
        _target_pkg_name = env['PKG_NAME']
    global _target_pkg_type; \
        _target_pkg_type = env['PKG_TYPE']
    global _subproj_src; \
        _subproj_src = env['SUBPROJ_SRC']
    global _subproj_src_patches; \
        _subproj_src_patches = env['SUBPROJ_SRC_PATCHES']
    global _target_platform; \
        _target_platform = env['PKG_PLATFORM']
    global _target_arch; \
        _target_arch = env['PKG_ARCH']
    global _pkg_buld_dir; \
        _pkg_buld_dir = env['PKG_BULD_DIR']
    global _pkg_inst_dir; \
        _pkg_inst_dir = env['PKG_INST_DIR']
    global _extra_args_build; \
        _extra_args_build = env[f'EXTRA_{BUILD_CMD.upper()}']

    #if _target_pkg_type != 'static':
    #    raise NotImplementedError(f'unsupported PKG_TYPE: {_target_pkg_type}')


    global BUILD_ENV

    if _target_platform == 'android':
        BUILD_ENV['ANDROID_API_LEVEL'] = env['ANDROID_API_LEVEL']
    if _target_platform == 'win-msvc':
        BUILD_ENV = env['WIN32_MSVC_ENV_TARGET']
        BUILD_ENV['CFLAGS']   = '/utf-8'
        BUILD_ENV['CXXFLAGS'] = BUILD_ENV['CFLAGS']
        _extra_args_build.extend(['-D', 'CMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded'])

    return [
        _source_download,
        _build_step_00,
        _build_step_01,
        _build_step_02,
    ]



def _source_download():
    _git_target = 'refs/heads/3.1.x'
    if not (Path(_subproj_src) / '.git').exists():
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'init'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'remote', 'add', 'x', 'https://github.com/libjpeg-turbo/libjpeg-turbo.git'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{_git_target}'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'checkout', 'FETCH_HEAD'])
    x._util_put_pkg_version_desc(_target_pkg_name, x._util_func__subprocess(cwd=_subproj_src, collect_stdout=True, args=['git', 'describe', '--always', '--abbrev=7']))
    x._util_source_apply_patches(_subproj_src, _subproj_src_patches)
def _build_step_00():
    args = [BUILD_CMD, *_extra_args_build,
        '-S',   _subproj_src,
        '-D',  'CMAKE_BUILD_TYPE=RelWithDebInfo',
        '-D',  'WITH_JPEG8:BOOL=1',
        '-D',  'WITH_TURBOJPEG:BOOL=0',
        '-D',  'WITH_TOOLS:BOOL=0',
    ]
    if _target_pkg_type == 'static':
        args.extend(['-D', 'ENABLE_SHARED:BOOL=0', '-D', 'ENABLE_STATIC:BOOL=1'])
    if _target_pkg_type == 'shared':
        args.extend(['-D', 'ENABLE_SHARED:BOOL=1', '-D', 'ENABLE_STATIC:BOOL=0'])

    if _target_platform == 'win-msvc':
        args.extend([
            '-D',  'CMAKE_SYSTEM_NAME=Windows',
            '-D',  'CMAKE_CROSSCOMPILING:BOOL=TRUE',
            '-D', f'CMAKE_SYSTEM_PROCESSOR={_target_arch}',
        ])

    x._util_func__subprocess(env=BUILD_ENV, args=args)
def _build_step_01():
    args = f"{BUILD_CMD} --build {_pkg_buld_dir} -j {x.CPU_COUNT}"
    x._util_func__subprocess(env=BUILD_ENV, args=shlex.split(args))
def _build_step_02():
    args = f"{BUILD_CMD} --install {_pkg_buld_dir}"
    x._util_func__subprocess(env=BUILD_ENV, args=shlex.split(args))
