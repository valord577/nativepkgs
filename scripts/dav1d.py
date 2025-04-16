#!/usr/bin/env python3

# fmt: off

import os
import shutil
import sys


_env: dict = {}
_ctx: dict = {
    'PKG_INST_STRIP': '',
    'MESON_CMD': '',
    'BUILD_ENV': os.environ.copy(),
}

def module_init(env: dict) -> list:
    global _env; _env = env
    return [
        _source_download,
        _source_apply_patches,
        _build_tools_setup,
        _build_step_00,
        _build_step_01,
        _build_step_02,
    ]



def _source_download():
    _git_target = '42b2b24fb8819f1ed3643aa9cf2a62f03868e3aa'
    if not os.path.exists(os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], '.git'))):
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=['git', 'init'])
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=['git', 'remote', 'add', 'x', 'https://github.com/videolan/dav1d.git'])
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=['git', 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{_git_target}'])
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=['git', 'checkout', 'FETCH_HEAD'])
    if file_ver := os.getenv('DEPS_VER'):
        with open(file_ver, 'w') as f:
            f.write(_git_target[:7])
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


def _build_tools_setup():
    _env['FUNC_PYPI'](['pip', 'meson', 'ninja'])
    _ctx['MESON_CMD'] = shutil.which('meson') or _ctx['MESON_CMD']
    if not _ctx['MESON_CMD']:
        _binary_dirname = 'Scripts' if sys.platform == 'win32' else 'bin'
        _binary_dirpath = os.path.abspath(os.path.join(sys.prefix, _binary_dirname))

        _ctx['MESON_CMD'] = os.path.join(_binary_dirpath, 'meson')
        _ctx['BUILD_ENV']['PATH'] = f"{_binary_dirpath}{os.pathsep}{os.getenv('PATH', '')}"
def _build_step_00():
    _extra_args_meson: list[str] = _env['EXTRA_MESON']

    if _env['PKG_TYPE'] == 'static':
        _extra_args_meson.extend(['--default-library', 'static'])
    if _env['PKG_TYPE'] == 'shared':
        _extra_args_meson.extend(['--default-library', 'shared'])

    if _env['LIB_RELEASE'] == '0':
        _extra_args_meson.extend(['--buildtype', 'debug'])
    if _env['LIB_RELEASE'] == '1':
        _ctx['PKG_INST_STRIP'] = '--strip'
        _extra_args_meson.extend(['--buildtype', 'release'])

    args = [
        _ctx['MESON_CMD'], 'setup',
        '--prefix', _env['PKG_INST_DIR'],
        '--pkgconfig.relocatable',
        '--libdir', 'lib', '--python.install-env', 'venv',
        '--wrap-mode', 'nofallback', '-Db_pie=true',

        '-Denable_docs=false',
        '-Denable_examples=false',
        '-Denable_seek_stress=false',
        '-Denable_tests=false',
        '-Denable_tools=false',
    ]
    args.extend(_extra_args_meson)
    args.extend([_env['PKG_BULD_DIR'], _env['SUBPROJ_SRC']])
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args)
def _build_step_01():
    args = [_ctx['MESON_CMD'], 'compile', '-C', _env['PKG_BULD_DIR'], '-j', _env['PARALLEL_JOBS']]
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args)
def _build_step_02():
    args = [_ctx['MESON_CMD'], 'install', '-C', _env['PKG_BULD_DIR'], '--no-rebuild']
    if _ctx['PKG_INST_STRIP']:
        args.append( _ctx['PKG_INST_STRIP'])
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args)
