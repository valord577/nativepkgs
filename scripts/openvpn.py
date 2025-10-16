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
        _source_dl_3rd_deps,
        _source_download,
        _source_apply_patches,
        _build_tools_setup,
        _build_step_msvc,
        _build_step_00,
        _build_step_01,
        _build_step_02,
    ]



def _source_dl_3rd_deps():
    _env['FUNC_PKGC'](_ctx, _env, 'mbedtls', 'e185d7f', 'static')
    _env['FUNC_PKGC'](_ctx, _env, 'liblz4',  'ebb370c', 'static')
    _env['FUNC_PKGC'](_ctx, _env, 'liblzo2', 'b196b87', 'static')
def _source_download():
    _git_target = 'refs/tags/v2.6.15'
    if not os.path.exists(os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], '.git'))):
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=['git', 'init'])
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=['git', 'remote', 'add', 'x', 'https://github.com/OpenVPN/openvpn.git'])
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=['git', 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{_git_target}'])
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=['git', 'checkout', 'FETCH_HEAD'])
    if file_ver := os.getenv('DEPS_VER', ''):
        Path(file_ver).write_text(f'{_git_target.split("/")[-1]}')
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


def _build_tools_setup():
    _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=[
        'brew', 'install', 'autoconf', 'automake', 'libtool', 'libltdl'
    ])
def _build_step_msvc():
    if _env['PKG_PLATFORM'] == 'win-msvc':
        raise NotImplementedError(f'unsupported PKG_PLATFORM: {_env["PKG_PLATFORM"]}')
def _build_step_00():
    _extra_args_configure: list[str] = []

    if _env['PKG_TYPE'] == 'static':
        _extra_args_configure.extend(['--enable-shared=no'])
    if _env['PKG_TYPE'] == 'shared':
        raise NotImplementedError(f'unsupported pkg type: {_env["PKG_TYPE"]}')

    if _env['LIB_RELEASE'] == '0':
        _extra_args_configure.extend(['--disable-debug=no'])
    if _env['LIB_RELEASE'] == '1':
        _extra_args_configure.extend(['--disable-debug'])

    args = [
         os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], 'configure')),
        f'--prefix={_env["PKG_INST_DIR"]}',
         '--disable-plugins',
         '--enable-pic=yes',
         '--disable-unit-tests',
         '--with-openssl-engine=no',
         '--with-crypto-library=mbedtls',
    ]
    args.extend(_extra_args_configure)


    _env_passthrough = ['CC', 'CXX', 'SYSROOT']
    for _k in _env_passthrough:
        if _v := _env.get(_k):  _ctx['BUILD_ENV'][_k]  = _v

    if _env.get('PLATFORM_APPLE', False):
        _ctx['BUILD_ENV']['LDFLAGS'] = _env['CROSS_FLAGS']
        args.extend([
           f'--host={_env["PKG_ARCH"]}-apple-darwin',
            '--disable-dco',
        ])
    if _env['PKG_PLATFORM'] == 'linux':
        args.extend([
            '--disable-dco',
        ])
        if _env['CROSS_BUILD_ENABLED']:
            _ctx['BUILD_ENV']['LDFLAGS'] = _env["CROSS_LDFLAGS"]
            args.extend([
               f'--host={_env["CROSS_TARGET_TRIPLE"]}',
            ])


    _pkgconf_bin = _env.get('CROSS_PKGCONFIG_BIN', '')
    if not _pkgconf_bin:
        _pkgconf_bin = shutil.which('pkgconf') or 'pkg-config'
    _ctx['BUILD_ENV']['PKG_CONFIG'] = _pkgconf_bin
    _ctx['BUILD_ENV']['PKG_CONFIG_PATH'] = \
        f"{os.pathsep.join(_ctx['PKG_CONFIG_PATH'])}{os.pathsep}{os.getenv('PKG_CONFIG_PATH', '')}"
    _ctx['BUILD_ENV']['MBEDTLS_CFLAGS'] = \
        _env['FUNC_SHELL_STDOUT'](env=_ctx['BUILD_ENV'], args=[_pkgconf_bin, '--cflags', 'mbedtls'])[:-1]
    _ctx['BUILD_ENV']['MBEDTLS_LIBS'] = \
        _env['FUNC_SHELL_STDOUT'](env=_ctx['BUILD_ENV'], args=[_pkgconf_bin, '--libs', 'mbedtls'])[:-1]
    _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'],  env=_ctx['BUILD_ENV'], args=['autoreconf', '-v', '-i'])
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
