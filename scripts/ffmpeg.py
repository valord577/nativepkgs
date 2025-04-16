#!/usr/bin/env python3

# fmt: off

import os
import shutil


_env: dict = {}
_ctx: dict = {
    'PKG_INST_STRIP': '',
    'PKG_3RD_DEPS_SHARED': [],
    'PKG_3RD_DEPS_STATIC': [],
    'PKG_CONFIG_PATH': [],
    'BUILD_ENV': os.environ.copy(),

    'EXTRA_ARGS_CONFIGURE': [],
}

def module_init(env: dict) -> list:
    global _env; _env = env
    return [
        _source_dl_3rd_deps,
        _source_download,
        _source_apply_patches,
        _build_step_00,
        _build_step_01,
        _build_step_02,
    ]



def _source_dl_3rd_deps():
    _env['FUNC_PKGC'](_ctx, _env, 'dav1d',
        '42b2b24', 'static'); _ctx['EXTRA_ARGS_CONFIGURE'].append('--enable-libdav1d')
    _env['FUNC_PKGC'](_ctx, _env, 'mbedtls',
        '22098d4', 'static'); _ctx['EXTRA_ARGS_CONFIGURE'].append('--enable-mbedtls')

    if _env['PKG_PLATFORM'] == 'macosx':
        _env['FUNC_PKGC'](_ctx, _env, 'sdl2', 'fa24d86', 'static')
def _source_download():
    _git_target = 'refs/heads/release/7.1'
    if not os.path.exists(os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], '.git'))):
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=['git', 'init'])
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=['git', 'remote', 'add', 'x', 'https://git.ffmpeg.org/ffmpeg.git'])
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=['git', 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{_git_target}'])
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=['git', 'checkout', 'FETCH_HEAD'])
    if file_ver := os.getenv('DEPS_VER'):
        with open(file_ver, 'w') as f:
            f.write('release' + _git_target.split('/')[-1])
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
    _extra_args_configure: list[str] = _ctx['EXTRA_ARGS_CONFIGURE']

    if _env['PKG_TYPE'] == 'static':
        _extra_args_configure.extend([])
    if _env['PKG_TYPE'] == 'shared':
        _env['FUNC_EXIT'](f'unsupported pkg type: {_env["PKG_TYPE"]}')  # exited
        _extra_args_configure.extend(['--disable-static', '--enable-shared'])

    if _env['LIB_RELEASE'] == '0':
        _ctx['PKG_INST_STRIP'] = '--disable-stripping'
        _extra_args_configure.extend(['--disable-optimizations', '--enable-extra-warnings'])
    if _env['LIB_RELEASE'] == '1':
        _extra_args_configure.extend(['--disable-debug', '--disable-logging'])

    args = [
         os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], 'configure')),
        f'--prefix={_env["PKG_INST_DIR"]}',
         '--enable-version3',
         '--fatal-warnings',
         '--disable-doc',
         '--disable-devices',
         '--enable-indev=lavfi',
         '--enable-pic',
         '--disable-libxcb',
         '--disable-xlib',
         '--disable-vaapi',
    ]
    args.extend(_extra_args_configure)
    if _cc  := _env.get('CC'):
        args.append(f"--cc={_cc}")
    if _cxx := _env.get('CXX'):
        args.append(f"--cxx={_cxx}")
    if _pkgconf := _env.get('CROSS_PKGCONFIG_BIN'):
        args.append(f"--pkg-config={_pkgconf}")

    if _env.get('PLATFORM_APPLE', False):
        args.extend([
            '--enable-cross-compile',
            '--target-os=darwin',
            '--disable-coreimage',
            f'--arch={_env["PKG_ARCH"]}',
            f'--extra-ldflags={_env["CROSS_FLAGS"]}',
        ])
        if _env['PKG_PLATFORM'] != 'macosx':
            args.extend(['--disable-programs'])
    if _env['PKG_PLATFORM'] == 'linux':
        _rpath = '\\$\\$ORIGIN:\\$\\$ORIGIN/../lib'
        args.append(f"--extra-ldsoflags=-Wl,-rpath,'{_rpath}'")
        args.append(f"--extra-ldexeflags=-Wl,-rpath,'{_rpath}'")
        if _env['CROSS_BUILD_ENABLED']:
            args.extend([
                '--enable-cross-compile',
                '--target-os=linux',
                f'--arch={_env["PKG_ARCH"]}',
                f'--host-cc={_env["HOSTCC"]}',
                f'--extra-ldflags={_env["CROSS_LDFLAGS"]}',
                f'--nm={_env["NM"]}',
                f'--ar={_env["AR"]}',
                f'--ranlib={_env["RANLIB"]}',
                f'--strip={_env["STRIP"]}',
            ])
    if _env['PKG_PLATFORM'] == 'win-mingw':
        args.extend([
            '--enable-cross-compile',
            '--target-os=mingw64',
            f'--arch={_env["PKG_ARCH"]}',
            f'--host-cc={_env["HOSTCC"]}',
            f'--windres={_env["WINDRES"]}',
            f'--nm={_env["NM"]}',
            f'--ar={_env["AR"]}',
            f'--ranlib={_env["RANLIB"]}',
            f'--strip={_env["STRIP"]}',
        ])

    _env['PKG_BULD_DIR'] = _env['SUBPROJ_SRC'] if os.getenv('CLANGD_CODE_COMPLETION', '') == '1' else _env['PKG_BULD_DIR']
    _ctx['BUILD_ENV']['PKG_CONFIG_PATH'] = f"{os.pathsep.join(_ctx['PKG_CONFIG_PATH'])}{os.pathsep}{os.getenv('PKG_CONFIG_PATH', '')}"
    _env['FUNC_PROC'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=args)
def _build_step_01():
    args = ['make', '-j', _env['PARALLEL_JOBS']]
    if shutil.which('bear'):
        args = [shutil.which('bear'), '--'] + args
    _env['FUNC_PROC'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=args)
def _build_step_02():
    if (_env['PKG_PLATFORM'] == 'iphoneos') or (_env['PKG_PLATFORM'] == 'iphonesimulator'):
        _env['FUNC_PROC'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=['make', 'install-headers'])
        _env['FUNC_PROC'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=['make', 'install-libs'])
    else:
        _env['FUNC_PROC'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=['make', 'install-progs'])
        if _env['PKG_TYPE'] == 'shared':
            _env['FUNC_PROC'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=['make', 'install-libs'])
