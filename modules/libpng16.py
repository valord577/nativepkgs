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
_target_archlibc = ''

_3rd_deps_dir = ''
_pkg_buld_dir = ''
_pkg_inst_dir = ''

_extra_sysroot = ''
_extra_args_build: list[str] = []
_extra_search_dir: list[str] = []

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
    global _target_archlibc; \
        _target_archlibc = env['PKG_ARCH_LIBC']
    global _3rd_deps_dir; \
        _3rd_deps_dir = env['3RD_DEPS_DIR']
    global _pkg_buld_dir; \
        _pkg_buld_dir = env['PKG_BULD_DIR']
    global _pkg_inst_dir; \
        _pkg_inst_dir = env['PKG_INST_DIR']
    global _extra_sysroot; \
        _extra_sysroot = env['SYSROOT']
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
        _source_dl_3rd_deps,
        _source_download,
        _build_step_00,
        _build_step_01,
        _build_step_02,
    ]



def _source_dl_3rd_deps():
    _3rd_deps: list[dict[str, str]] = []
    if _target_platform not in ['macosx', 'iphoneos', 'iphonesimulator']:
        _3rd_deps.extend([
            {
                'name': 'zlib-ng',
                'type': 'static',
                'vers': '1273109',
            },
        ])

    _get_prebuilt_script = (Path(x.PROJ_ROOT) / 'scripts' / 'get_prebuilt.py').absolute().as_posix()
    for dep in _3rd_deps:
        _name = dep['name']; _type = dep['type']; _vers = dep['vers']
        x._util_func__exec_python([_get_prebuilt_script, _target_archlibc, _name, _target_platform, _vers, _type, '', _3rd_deps_dir])

        _extra_search_dir.append((Path(_3rd_deps_dir) / _name).absolute().as_posix())
def _source_download():
    _git_target = 'refs/heads/libpng16'
    if not (Path(_subproj_src) / '.git').exists():
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'init'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'remote', 'add', 'x', 'https://github.com/pnggroup/libpng.git'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{_git_target}'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'checkout', 'FETCH_HEAD'])
    x._util_put_pkg_version_desc(_target_pkg_name, x._util_func__subprocess(cwd=_subproj_src, collect_stdout=True, args=['git', 'describe', '--always', '--abbrev=7']))
    x._util_source_apply_patches(_subproj_src, _subproj_src_patches)
def _build_step_00():
    _cmake_search_dir = ';'.join(_extra_search_dir)
    args = [BUILD_CMD, *_extra_args_build,
        '-S',   _subproj_src,
        '-D',  'CMAKE_BUILD_TYPE=RelWithDebInfo',
        '-D', f'CMAKE_PREFIX_PATH={_cmake_search_dir}',
        '-D', f'CMAKE_FIND_ROOT_PATH={_extra_sysroot};{_cmake_search_dir}',
        '-D',  'PNG_FRAMEWORK:BOOL=0',
        '-D',  'PNG_TESTS:BOOL=0',
        '-D',  'PNG_TOOLS:BOOL=0',
    ]
    if _target_pkg_type == 'static':
        args.extend(['-D', 'PNG_SHARED:BOOL=0', '-D', 'PNG_STATIC:BOOL=1'])
    if _target_pkg_type == 'shared':
        args.extend(['-D', 'PNG_SHARED:BOOL=1', '-D', 'PNG_STATIC:BOOL=0'])

    x._util_func__subprocess(env=BUILD_ENV, args=args)
def _build_step_01():
    args = f"{BUILD_CMD} --build {_pkg_buld_dir} -j {x.CPU_COUNT}"
    x._util_func__subprocess(env=BUILD_ENV, args=shlex.split(args))
def _build_step_02():
    args = f"{BUILD_CMD} --install {_pkg_buld_dir}"
    x._util_func__subprocess(env=BUILD_ENV, args=shlex.split(args))
