#!/usr/bin/env python3

# fmt: off

import os
import shutil


_env: dict = {}
_ctx: dict = {
    'PKG_INST_STRIP': '',
    'CMAKE_CMD': 'cmake',
    'BUILD_ENV': os.environ.copy(),
    'SHELL_REQ': False,
}

def module_init(env: dict) -> list:
    global _env; _env = env
    return [
        _source_download,
        _source_apply_patches,
        _build_step_msvc,
        _build_step_00,
        _build_step_01,
        _build_step_02,
    ]



def _source_download():
    _git_target = 'refs/tags/R_2_7_1'
    if not os.path.exists(os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], '.git'))):
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'init'])
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'remote', 'add', 'x', 'https://github.com/libexpat/libexpat.git'])
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{_git_target}'])
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'checkout', 'FETCH_HEAD'])
    if file_ver := os.getenv('DEPS_VER', ''):
        with open(file_ver, 'w') as f:
            f.write(f'{_git_target.split("/")[-1]}')
def _source_apply_patches():
    if not os.path.exists(_env['SUBPROJ_SRC_PATCHES']):
        return
    _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'reset', '--hard', 'HEAD'])
    _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'clean', '-d', '-f', '-q'])
    with os.scandir(_env['SUBPROJ_SRC_PATCHES']) as it:
        entries = sorted(it, key=lambda e: e.name)
        for entry in entries:
            if not entry.is_file():
                continue
            _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'],
                args=[shutil.which('git'), 'apply', '--verbose', '--ignore-space-change', '--ignore-whitespace', entry.path])


def _build_step_msvc():
    if _env['PKG_PLATFORM'] != 'win-msvc':
        return
    _ctx['BUILD_ENV'] = _env['WIN32_MSVC_ENV_TARGET']
    _ctx['BUILD_ENV']['CFLAGS']   = '/utf-8'
    _ctx['BUILD_ENV']['CXXFLAGS'] = _ctx['BUILD_ENV']['CFLAGS']
    _ctx['SHELL_REQ'] = True

    if _env['LIB_RELEASE'] == '0':
        _env['FUNC_EXIT'](f'unsupported LIB_RELEASE: {_env["LIB_RELEASE"]}')  # exited
    if _env['LIB_RELEASE'] == '1':
        _env['EXTRA_CMAKE'].extend(['-D', 'CMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded'])
def _build_step_00():
    _extra_args_cmake: list[str] = _env['EXTRA_CMAKE']

    if _env['PKG_TYPE'] == 'static':
        _extra_args_cmake.extend(['-D', 'EXPAT_SHARED_LIBS:BOOL=0'])
    if _env['PKG_TYPE'] == 'shared':
        _extra_args_cmake.extend(['-D', 'EXPAT_SHARED_LIBS:BOOL=1'])

    if _env['LIB_RELEASE'] == '0':
        _extra_args_cmake.extend(['-D', 'CMAKE_BUILD_TYPE=Debug'])
    if _env['LIB_RELEASE'] == '1':
        _ctx['PKG_INST_STRIP'] = '--strip'
        _extra_args_cmake.extend(['-D', 'CMAKE_BUILD_TYPE=Release'])

    args = [
        _ctx['CMAKE_CMD'],
        '-S',  os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], 'expat')),
        '-D',  'EXPAT_WARNINGS_AS_ERRORS:BOOL=1',
        '-D',  'EXPAT_MSVC_STATIC_CRT:BOOL=1',
        '-D',  'EXPAT_BUILD_TOOLS:BOOL=0',
        '-D',  'EXPAT_BUILD_EXAMPLES:BOOL=0',
        '-D',  'EXPAT_BUILD_TESTS:BOOL=0',
        '-D',  'EXPAT_BUILD_DOCS:BOOL=0',
        '-D',  'EXPAT_BUILD_FUZZERS:BOOL=0',
        '-D',  'EXPAT_OSSFUZZ_BUILD:BOOL=0',
        '-D',  'EXPAT_WITH_LIBBSD:BOOL=0',
    ]
    args.extend(_extra_args_cmake)
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args, shell=_ctx['SHELL_REQ'])
def _build_step_01():
    args = [_ctx['CMAKE_CMD'], '--build', _env['PKG_BULD_DIR'], '-j', _env['PARALLEL_JOBS']]
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args, shell=_ctx['SHELL_REQ'])
def _build_step_02():
    args = [_ctx['CMAKE_CMD'], '--install', _env['PKG_BULD_DIR']]
    if _ctx['PKG_INST_STRIP']:
        args.append( _ctx['PKG_INST_STRIP'])
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args, shell=_ctx['SHELL_REQ'])
