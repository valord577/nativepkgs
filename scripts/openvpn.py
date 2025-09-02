#!/usr/bin/env python3

# fmt: off

import os
import sys
import shutil


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
        _build_step_msvc,
        _build_step_00,
        _build_step_01,
        _build_step_02,
    ]



def _source_dl_3rd_deps():
    _env['FUNC_PKGC'](_ctx, _env, 'mbedtls', '?', 'static')
def _source_download():
    _git_target = 'refs/tags/upstream/2.6.14'
    if not os.path.exists(os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], '.git'))):
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=['git', 'init'])
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=['git', 'remote', 'add', 'x', 'https://salsa.debian.org/debian/openvpn.git'])
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=['git', 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{_git_target}'])
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=['git', 'checkout', 'FETCH_HEAD'])
    if file_ver := os.getenv('DEPS_VER', ''):
        with open(file_ver, 'w') as f:
            f.write(f'v{_git_target.split("/")[-1]}')
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
         '--disable-lzo',
         '--disable-lz4',
         '--disable-plugins',
         '--enable-pic=yes',
         '--disable-unit-tests',
         '--with-openssl-engine=no',
         '--with-crypto-library=mbedtls',
    ]
    args.extend(_extra_args_configure)


    if _cc  := _env.get('CC'):  _ctx['BUILD_ENV']['CC']  = _cc
    if _cxx := _env.get('CXX'): _ctx['BUILD_ENV']['CXX'] = _cxx

    if _env.get('PLATFORM_APPLE', False):
        _ctx['BUILD_ENV']['LDFLAGS'] = _env['CROSS_FLAGS']
        args.extend([
           f'--host={_env["PKG_ARCH"]}-apple-darwin',
            '--disable-dco',
        ])
    if _env['PKG_PLATFORM'] == 'linux':
        pass
    if _env['PKG_PLATFORM'] == 'win-mingw':
        pass


    _pkgconf_bin = _env.get('CROSS_PKGCONFIG_BIN', '')
    if not _pkgconf_bin:
        _pkgconf_bin = shutil.which('pkgconf') or 'pkg-config'
    _ctx['BUILD_ENV']['SYSROOT'] = _env['SYSROOT']
    _ctx['BUILD_ENV']['PKG_CONFIG'] = _pkgconf_bin
    _ctx['BUILD_ENV']['PKG_CONFIG_PATH'] = \
        f"{os.pathsep.join(_ctx['PKG_CONFIG_PATH'])}{os.pathsep}{os.getenv('PKG_CONFIG_PATH', '')}"
    _ctx['BUILD_ENV']['MBEDTLS_CFLAGS'] = \
        _env['FUNC_SHELL_STDOUT'](env=_ctx['BUILD_ENV'], args=[_pkgconf_bin, '--cflags', 'mbedtls'])[:-1]
    _ctx['BUILD_ENV']['MBEDTLS_LIBS'] = \
        _env['FUNC_SHELL_STDOUT'](env=_ctx['BUILD_ENV'], args=[_pkgconf_bin, '--libs', 'mbedtls'])[:-1]
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
