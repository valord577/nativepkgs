#!/usr/bin/env python3

# fmt: off

import os
import shutil

from pathlib import Path


_env: dict = {}
_ctx: dict = {
    'PKG_INST_STRIP': '',
    'BUILD_ENV': os.environ.copy(),
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
    _git_target = 'refs/tags/upstream/2.10'
    if not os.path.exists(os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], '.git'))):
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=['git', 'init'])
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=['git', 'remote', 'add', 'x', 'https://salsa.debian.org/debian/lzo2.git'])
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=['git', 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{_git_target}'])
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=['git', 'checkout', 'FETCH_HEAD'])
    if file_ver := os.getenv('DEPS_VER', ''):
        _git_ver = _env['FUNC_SHELL_STDOUT'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'describe', '--always', '--abbrev=7'])[:-1]
        Path(file_ver).write_text(f'{_git_ver}')
def _source_apply_patches():
    if not os.path.exists(_env['SUBPROJ_SRC_PATCHES']):
        return
    _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=['git', 'reset', '--hard', 'HEAD'])
    _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=['git', 'clean', '-d', '-f', '-q'])
    with os.scandir(_env['SUBPROJ_SRC_PATCHES']) as it:
        entries = sorted(it, key=lambda e: e.name)
        for entry in entries:
            if not entry.is_file():
                continue
            _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'],
                args=['git', 'apply', '--verbose', '--ignore-space-change', '--ignore-whitespace', entry.path])


def _build_step_msvc():
    if _env['PKG_PLATFORM'] == 'win-msvc':
        raise NotImplementedError(f'unsupported PKG_PLATFORM: {_env["PKG_PLATFORM"]}')
def _build_step_00():
    _extra_args_configure: list[str] = []

    if _env['PKG_TYPE'] == 'static':
        _extra_args_configure.extend(['--enable-static=yes', '--enable-shared=no'])
    if _env['PKG_TYPE'] == 'shared':
        raise NotImplementedError(f'unsupported pkg type: {_env["PKG_TYPE"]}')

    args = [
         os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], 'configure')),
        f'--prefix={_env["PKG_INST_DIR"]}',
         '--with-pic=yes',
    ]
    args.extend(_extra_args_configure)


    if _cc  := _env.get('CC'):  _ctx['BUILD_ENV']['CC']  = _cc
    if _cxx := _env.get('CXX'): _ctx['BUILD_ENV']['CXX'] = _cxx

    LIBLZO2_ARCH = _env['PKG_ARCH']
    if LIBLZO2_ARCH == 'arm64': LIBLZO2_ARCH = 'aarch64'
    if _env.get('PLATFORM_APPLE', False):
        _ctx['BUILD_ENV']['LDFLAGS'] = _env['CROSS_FLAGS']
        args.extend([
           f'--host={LIBLZO2_ARCH}-apple-darwin',
        ])
    if _env['PKG_PLATFORM'] == 'linux':
        pass
    if _env['PKG_PLATFORM'] == 'win-mingw':
        pass


    _env['FUNC_SHELL_DEVNUL'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=args)
def _build_step_01():
    args = f"make -j {_env['PARALLEL_JOBS']}"
    if shutil.which('bear'): args = f"bear -- " + args
    _env['FUNC_SHELL_DEVNUL'](
        cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], shell=True, args=args
    )
def _build_step_02():
    _env['FUNC_SHELL_DEVNUL'](
        cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], shell=True, args='make install'
    )

    liblzo2_datadir = os.path.abspath(os.path.join(_env['PKG_INST_DIR'], 'share')); \
        shutil.rmtree(liblzo2_datadir, ignore_errors=True)
    os.remove(os.path.abspath(os.path.join(_env['PKG_INST_DIR'], 'lib', 'liblzo2.la')))
