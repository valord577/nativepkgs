#!/usr/bin/env python3

# fmt: off

import os
import shutil
import sys


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
        _source_set_features,
        _build_step_msvc,
        _build_step_00,
        _build_step_01,
        _build_step_02,
    ]



def _source_download():
    _git_target = '22098d41c6620ce07cf8a0134d37302355e1e5ef'
    if not os.path.exists(os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], '.git'))):
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=['git', 'init'])
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=['git', 'remote', 'add', 'x', 'https://github.com/Mbed-TLS/mbedtls.git'])
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
def _source_set_features():
    _config_script = os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], 'scripts', 'config.py'))

    _env['FUNC_PROC'](args=[sys.executable, _config_script, 'unset', 'MBEDTLS_PEM_PARSE_C'])
    _env['FUNC_PROC'](args=[sys.executable, _config_script, 'unset', 'MBEDTLS_PEM_WRITE_C'])

    _env['FUNC_PROC'](args=[sys.executable, _config_script, 'set', 'MBEDTLS_HAVE_SSE2'])
    _env['FUNC_PROC'](args=[sys.executable, _config_script, 'set', 'MBEDTLS_DEPRECATED_WARNING'])
    _env['FUNC_PROC'](args=[sys.executable, _config_script, 'set', 'MBEDTLS_DEPRECATED_REMOVED'])

    _env['FUNC_PROC'](args=[sys.executable, _config_script, 'set', 'MBEDTLS_SHA256_USE_A64_CRYPTO_IF_PRESENT'])
    _env['FUNC_PROC'](args=[sys.executable, _config_script, 'set', 'MBEDTLS_SHA512_USE_A64_CRYPTO_IF_PRESENT'])
    _env['FUNC_PROC'](args=[sys.executable, _config_script, 'set', 'MBEDTLS_PSA_P256M_DRIVER_ENABLED'])
    _env['FUNC_PROC'](args=[sys.executable, _config_script, 'set', 'MBEDTLS_ECDH_VARIANT_EVEREST_ENABLED'])

    _env['FUNC_PROC'](args=[sys.executable, _config_script, 'set', 'MBEDTLS_SSL_PROTO_TLS1_3'])
    _env['FUNC_PROC'](args=[sys.executable, _config_script, 'set', 'MBEDTLS_SSL_TLS1_3_COMPATIBILITY_MODE'])

    _env['FUNC_PROC'](args=[sys.executable, _config_script, 'unset', 'MBEDTLS_DEBUG_C'])
    _env['FUNC_PROC'](args=[sys.executable, _config_script, 'unset', 'MBEDTLS_SELF_TEST'])
    _env['FUNC_PROC'](args=[sys.executable, _config_script, 'unset', 'MBEDTLS_SSL_SRV_C'])
    _env['FUNC_PROC'](args=[sys.executable, _config_script, 'unset', 'MBEDTLS_SSL_RENEGOTIATION'])

    if _env['PKG_PLATFORM'] == 'win-msvc':
        _env['FUNC_PROC'](args=[sys.executable, _config_script, 'unset', 'MBEDTLS_DEPRECATED_WARNING'])
    if _env['PKG_PLATFORM'] == 'win-mingw':
        _env['FUNC_PROC'](args=[sys.executable, _config_script, 'unset', 'MBEDTLS_SHA256_USE_A64_CRYPTO_IF_PRESENT'])
        _env['FUNC_PROC'](args=[sys.executable, _config_script, 'unset', 'MBEDTLS_SHA512_USE_A64_CRYPTO_IF_PRESENT'])
    if _env['PKG_PLATFORM'] == 'linux':
        if _env['PKG_ARCH'] == 'armv7':
            _env['FUNC_PROC'](args=[sys.executable, _config_script, 'unset', 'MBEDTLS_ECDH_VARIANT_EVEREST_ENABLED'])


def _build_step_msvc():
    if _env['PKG_PLATFORM'] != 'win-msvc':
        return
    _ctx['BUILD_ENV'] = _env['WIN32_MSVC_ENV_TARGET']
    _ctx['BUILD_ENV']['CFLAGS']   = '/utf-8 /wd4146'
    _ctx['BUILD_ENV']['CXXFLAGS'] = _ctx['BUILD_ENV']['CFLAGS']

    if _env['LIB_RELEASE'] == '0':
        _env['FUNC_EXIT'](f'unsupported LIB_RELEASE: {_env["LIB_RELEASE"]}')  # exited
    if _env['LIB_RELEASE'] == '1':
        _env['EXTRA_CMAKE'].extend(['-D', 'CMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded'])
def _build_step_00():
    _extra_args_cmake: list[str] = _env['EXTRA_CMAKE']

    if _env['PKG_TYPE'] == 'static':
        _extra_args_cmake.extend(['-D', 'USE_STATIC_MBEDTLS_LIBRARY:BOOL=1'])
        _extra_args_cmake.extend(['-D', 'USE_SHARED_MBEDTLS_LIBRARY:BOOL=0'])
    if _env['PKG_TYPE'] == 'shared':
        _env['FUNC_EXIT'](f'unsupported pkg type: {_env["PKG_TYPE"]}')  # exited

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
        '-D',  'MBEDTLS_AS_SUBPROJECT:BOOL=0',
        '-D',  'ENABLE_PROGRAMS:BOOL=0',
        '-D',  'ENABLE_TESTING:BOOL=0',
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
