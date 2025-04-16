#!/usr/bin/env python3

# fmt: off

import os
import shutil


_env: dict = {}
_ctx: dict = {
    'PKG_INST_STRIP': '',
    'CMAKE_CMD': 'cmake',
    'BUILD_ENV': os.environ.copy(),
}

def module_init(env: dict) -> list:
    global _env; _env = env
    return [
        _source_download,
        _source_apply_patches,
        _build_step_00,
        _build_step_01,
        _build_step_02,
    ]



def _source_download():
    _git_target = 'refs/tags/release-2.32.4'
    if not os.path.exists(os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], '.git'))):
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=['git', 'init'])
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=['git', 'remote', 'add', 'x', 'https://github.com/libsdl-org/SDL.git'])
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=['git', 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{_git_target}'])
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=['git', 'checkout', 'FETCH_HEAD'])
    if file_ver := os.getenv('DEPS_VER'):
        with open(file_ver, 'w') as f:
            f.write('v' + _git_target.split('-')[-1])
def _source_apply_patches():
    if not os.path.exists(_env['SUBPROJ_SRC_PATCHES']):
        return
    _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=['git', 'reset', '--hard', 'HEAD'])
    _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=['git', 'clean', '-d', '-f', '-q'])
    with os.scandir(_env['SUBPROJ_SRC_PATCHES']) as it:
        entries = sorted(it, key=lambda e: e.name)
        for entry in entries:
            if not entry.is_file():
                continue
            _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'],
                args=['git', 'apply', '--verbose', '--ignore-space-change', '--ignore-whitespace', entry.path])


def _build_step_00():
    _extra_args_cmake: list[str] = _env['EXTRA_CMAKE']

    if _env['PKG_TYPE'] == 'static':
        _extra_args_cmake.extend(['-D', 'BUILD_SHARED_LIBS:BOOL=0'])
    if _env['PKG_TYPE'] == 'shared':
        _extra_args_cmake.extend(['-D', 'BUILD_SHARED_LIBS:BOOL=1'])

    if _env['LIB_RELEASE'] == '0':
        _extra_args_cmake.extend(['-D', 'CMAKE_BUILD_TYPE=Debug'])
    if _env['LIB_RELEASE'] == '1':
        _ctx['PKG_INST_STRIP'] = '--strip'
        _extra_args_cmake.extend(['-D', 'CMAKE_BUILD_TYPE=Release'])

    args = [
        _ctx['CMAKE_CMD'],
        '-S',  _env['SUBPROJ_SRC'],
        '-B',  _env['PKG_BULD_DIR'],
        '-D',  'CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON',
        '-D',  'CMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON',
        '-D', f'CMAKE_INSTALL_PREFIX={_env["PKG_INST_DIR"]}',
        '-D',  'CMAKE_INSTALL_LIBDIR:PATH=lib',
        '-D',  'SDL_CCACHE:BOOL=0',
        '-D',  'SDL_TEST:BOOL=0',
        '-D',  'SDL2_DISABLE_SDL2MAIN:BOOL=1',
    ]
    args.extend(_extra_args_cmake)
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args)
def _build_step_01():
    args = [_ctx['CMAKE_CMD'], '--build', _env['PKG_BULD_DIR'], '-j', _env['PARALLEL_JOBS']]
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args)
def _build_step_02():
    args = [_ctx['CMAKE_CMD'], '--install', _env['PKG_BULD_DIR']]
    if _ctx['PKG_INST_STRIP']:
        args.append( _ctx['PKG_INST_STRIP'])
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args)
