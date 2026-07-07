# fmt: off

import sys
from pathlib import Path

sys.dont_write_bytecode = True

_this_file = (Path(__file__).absolute().resolve())
sys.path.append(
    (_this_file.parents[1]).as_posix()
); import x_utils as x

if __name__ == "__main__": x.loge_usage()
# ----------------------------
from typing import Callable, cast
from build_v2 import BuildCtx
ctx = cast(BuildCtx, globals()["ctx"])
# ----------------------------
def build_steps() -> "list[Callable[[], None]]":
    return [
        _fetch_source,
        _build_step_0,
        _build_step_1,
        _build_step_2,
    ]
# ----------------------------
def get_build_env() -> "dict[str, str]":
    env = x.ENVIRON
    if ctx.args.target_plat == 'win-msvc':
        env = ctx.args.win32_msvc_env_target
        env['CFLAGS'] = '/utf-8'
        env['CXXFLAGS'] = env['CFLAGS']
    return env
# ----------------------------
def _fetch_source():
    ctx.fetch_source_from_git('refs/heads/mbedtls-3.6', 'https://github.com/Mbed-TLS/mbedtls.git',
        submodules=[
            {
                'repo': 'framework',
                'path': 'framework',
                'cwd':  ctx.subproj_src_dir(),
                'url':  '../mbedtls-framework.git',
            },
        ],
    )


    x.runpy_pip(['jsonschema', 'jinja2'])
    config_py = ctx.subproj_src_dir('scripts', 'config.py').as_posix()

    x.runpy([config_py, 'set', 'MBEDTLS_HAVE_SSE2'])
    if ctx.args.target_arch == 'arm64':
        x.runpy([config_py, 'set', 'MBEDTLS_SHA256_USE_ARMV8_A_CRYPTO_ONLY'])
        x.runpy([config_py, 'set', 'MBEDTLS_SHA512_USE_A64_CRYPTO_ONLY'])

    x.runpy([config_py, 'set', 'MBEDTLS_SSL_DTLS_SRTP'])
    x.runpy([config_py, 'set', 'MBEDTLS_SSL_PROTO_TLS1_3'])
    x.runpy([config_py, 'set', 'MBEDTLS_SSL_TLS1_3_COMPATIBILITY_MODE'])

    x.runpy([config_py, 'unset', 'MBEDTLS_DEBUG_C'])
    x.runpy([config_py, 'unset', 'MBEDTLS_SELF_TEST'])
    x.runpy([config_py, 'unset', 'MBEDTLS_SSL_RENEGOTIATION'])

    if ctx.args.target_plat != 'win-msvc':
        x.runpy([config_py, 'set', 'MBEDTLS_DEPRECATED_WARNING'])
def _build_step_0():
    args = [
        'cmake', *(ctx.args.extra_cmake),
        '-S',   ctx.subproj_src_dir().as_posix(),
        '-D', f'BUILD_SHARED_LIBS:BOOL={x.feature_build_shared()}',
        '-D', f'USE_STATIC_MBEDTLS_LIBRARY:BOOL={"0" if (x.feature_build_shared() == "1") else "1"}',
        '-D', f'USE_SHARED_MBEDTLS_LIBRARY:BOOL={x.feature_build_shared()}',
        '-D',  'CMAKE_BUILD_TYPE=Release',
        '-D',  'MBEDTLS_AS_SUBPROJECT:BOOL=0',
        '-D',  'ENABLE_PROGRAMS:BOOL=0',
        '-D',  'ENABLE_TESTING:BOOL=0',
        '-D',  'DISABLE_PACKAGE_CONFIG_AND_INSTALL:BOOL=1',
        '-D',  'GEN_FILES:BOOL=1',
    ]
    if (x.feature_build_shared() == '1') and (ctx.args.target_plat == 'win-msvc'):
        # Bug Tracking:
        #  - https://github.com/Mbed-TLS/mbedtls/issues/470
        #  - https://github.com/Mbed-TLS/mbedtls/issues/1130
        args.extend(['-D', 'CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS:BOOL=1'])
    x.run_as_subprocess(env=get_build_env(), args=args)
def _build_step_1():
    x.run_as_subprocess(env=get_build_env(), args=['cmake', '--build', ctx.args.pkg_buld_dir, '-j', f'{x.detect_cpu_count()}'])
def _build_step_2():
    x.run_as_subprocess(env=get_build_env(), args=['cmake', '--install', ctx.args.pkg_buld_dir, '--strip'])

    _pkgconf_content = '''\
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
    if ctx.args.target_plat == 'win-mingw':
        _pkgconf_extra_libs = '-lws2_32 -lbcrypt'
    _pkgconf_content = _pkgconf_content.replace('@PKGCONFIG_EXTRA_LIBS@', _pkgconf_extra_libs)
    _pkgconf_content = _pkgconf_content.replace('@PKGCONFIG_VERSION@', ctx.subproj_src_ver())

    _pkgconf = (Path(ctx.args.pkg_inst_dir) / 'lib' / 'pkgconfig' / 'mbedtls3.pc'); \
        _pkgconf.parent.mkdir(parents=True, exist_ok=True)
    _ = _pkgconf.write_text(_pkgconf_content)
    (_pkgconf.parent / 'mbedtls.pc').symlink_to(_pkgconf.name, target_is_directory=False)
