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
_target_archlibc = ''

_3rd_deps_dir = ''
_pkg_buld_dir = ''
_pkg_inst_dir = ''

_extra_sysroot = ''
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
        _source_set_features,
        _build_step_00,
        _build_step_01,
        _build_step_02,
    ]




def _source_download():
    _git_target = 'refs/tags/v3.6.6'
    if not (Path(_subproj_src) / '.git').exists():
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'init'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'remote', 'add', 'x', 'https://github.com/Mbed-TLS/mbedtls.git'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{_git_target}'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'checkout', 'FETCH_HEAD'])

        _git_submodules = [
            {
                'repo': 'framework',
                'path': 'framework',
                'cwd':  _subproj_src,
                'url':  '../mbedtls-framework.git',
            },
        ]
        x._util_source_sync_submodules(_git_submodules)
    x._util_put_pkg_version_desc(_target_pkg_name, x._util_func__subprocess(cwd=_subproj_src, collect_stdout=True, args=['git', 'describe', '--always', '--abbrev=7']))
    x._util_source_cleanup(_subproj_src)
def _source_set_features():
    _config_script = (Path(_subproj_src) / 'scripts' / 'config.py').absolute().as_posix()

    x._util_func__exec_python([_config_script, 'set', 'MBEDTLS_HAVE_SSE2'])
    if _target_arch == 'arm64':
        x._util_func__exec_python([_config_script, 'set', 'MBEDTLS_SHA256_USE_ARMV8_A_CRYPTO_ONLY'])
        x._util_func__exec_python([_config_script, 'set', 'MBEDTLS_SHA512_USE_A64_CRYPTO_ONLY'])

    x._util_func__exec_python([_config_script, 'set', 'MBEDTLS_PSA_P256M_DRIVER_ENABLED'])
    if _target_arch != 'armv7':
        x._util_func__exec_python([_config_script, 'set', 'MBEDTLS_ECDH_VARIANT_EVEREST_ENABLED'])

    x._util_func__exec_python([_config_script, 'set', 'MBEDTLS_SSL_DTLS_SRTP'])
    x._util_func__exec_python([_config_script, 'set', 'MBEDTLS_SSL_PROTO_TLS1_3'])
    x._util_func__exec_python([_config_script, 'set', 'MBEDTLS_SSL_TLS1_3_COMPATIBILITY_MODE'])

    x._util_func__exec_python([_config_script, 'unset', 'MBEDTLS_DEBUG_C'])
    x._util_func__exec_python([_config_script, 'unset', 'MBEDTLS_SELF_TEST'])
    x._util_func__exec_python([_config_script, 'unset', 'MBEDTLS_SSL_RENEGOTIATION'])

    if _target_platform != 'win-msvc':
        x._util_func__exec_python([_config_script, 'set', 'MBEDTLS_DEPRECATED_WARNING'])
def _build_step_00():
    args = [BUILD_CMD, *_extra_args_build,
        '-S',   _subproj_src,
        '-D',  'BUILD_SHARED_LIBS:BOOL=0',
        '-D',  'USE_STATIC_MBEDTLS_LIBRARY:BOOL=1',
        '-D',  'USE_SHARED_MBEDTLS_LIBRARY:BOOL=0',
        '-D',  'CMAKE_BUILD_TYPE=RelWithDebInfo',
        '-D',  'MBEDTLS_AS_SUBPROJECT:BOOL=0',
        '-D',  'ENABLE_PROGRAMS:BOOL=0',
        '-D',  'ENABLE_TESTING:BOOL=0',
        '-D',  'DISABLE_PACKAGE_CONFIG_AND_INSTALL:BOOL=1',
    ]
    x._util_func__subprocess(env=BUILD_ENV, args=args)
def _build_step_01():
    args = f"{BUILD_CMD} --build {_pkg_buld_dir} -j {x.CPU_COUNT}"
    x._util_func__subprocess(env=BUILD_ENV, args=shlex.split(args))
def _build_step_02():
    args = f"{BUILD_CMD} --install {_pkg_buld_dir}"
    x._util_func__subprocess(env=BUILD_ENV, args=shlex.split(args))


    _pkgconf_content = '''
prefix=${pcfiledir}/../..
includedir=${prefix}/include
libdir=${prefix}/lib

Name: Mbed TLS
Description: Mbed TLS is a C library that implements cryptographic primitives, X.509 certificate manipulation and the SSL/TLS and DTLS protocols. Its small code footprint makes it suitable for embedded systems.
URL: https://www.trustedfirmware.org/projects/mbed-tls/
Version: @PKGCONFIG_VERSION@
Requires:
Cflags: -I${includedir}
Libs: -L${libdir} -lmbedtls -lmbedx509 -lmbedcrypto -leverest -lp256m @PKGCONFIG_EXTRA_LIBS@
'''
    _pkgconf_extra_libs = ''
    if _target_platform == 'win-mingw':
        _pkgconf_extra_libs = '-lws2_32 -lbcrypt'
    _pkgconf_content = _pkgconf_content.replace('@PKGCONFIG_EXTRA_LIBS@', _pkgconf_extra_libs)
    _pkgconf_content = _pkgconf_content.replace('@PKGCONFIG_VERSION@', x._util_get_pkg_version_desc(_target_pkg_name))

    _pkgconf = (Path(_pkg_inst_dir) / 'lib' / 'pkgconfig' / 'mbedtls.pc'); \
        _pkgconf.parent.mkdir(parents=True, exist_ok=True)
    _pkgconf.write_text(_pkgconf_content)
