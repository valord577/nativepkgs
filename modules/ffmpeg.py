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
        _3rd_included,
        _fetch_source,
        _build_step_0,
        _build_step_1,
        #_build_step_2,
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
build_env = get_build_env()
extra_args: "list[str]" = []
pkg_buld_dir = ctx.args.pkg_buld_dir
# ----------------------------
def _3rd_included():
    from build_v2 import DependencySpec

    _3rd_deps: list[DependencySpec] = [
        {
            'name': 'dav1d',
            'type': 'static',
            'vers': 'b546257',
            'args': '--enable-libdav1d',
        },
        {
            'name': 'mbedtls3',
            'type': 'static',
            'vers': '52beeef',
            'args': '--enable-mbedtls',
        },
    ]
    if ctx.args.target_plat not in {'macosx', 'iphoneos', 'iphonesimulator'}:
        _3rd_deps.extend([
            {
                'name': 'zlib-ng',
                'type': 'static',
                'vers': '1273109',
                'args': '',
            },
        ])
    if ctx.args.target_plat in {'macosx', 'win-mingw'}:
        _3rd_deps.extend([
            {
                'name': 'sdl2',
                'type': 'static',
                'vers': '2e5b9a8',
                'args': '',
            },
        ])

    for dep in _3rd_deps:
        dep_path = ctx.include_3rd_dependencies(dep)
        if args := dep['args']: extra_args.append(args)
        x.append_pkgconf_search_path(build_env, (dep_path / 'lib' / 'pkgconfig'))
def _fetch_source():
    ctx.fetch_source_from_git('refs/heads/release/8.1', 'https://git.ffmpeg.org/ffmpeg.git')
def _build_step_0():
    args = [
        ctx.subproj_src_dir('configure').as_posix(),
        *extra_args,
        f'--prefix={pkg_buld_dir}',
        f'--disable-stripping',
        f'--enable-version3',
        f'--fatal-warnings',
        f'--disable-doc',
        f'--disable-devices',
        f'--enable-indev=lavfi',
        f'--enable-pic',
        f'--disable-libxcb',
        f'--disable-xlib',
        f'--disable-vaapi',
        f'--disable-unstable',
        f'--disable-symver',
        f'--disable-large-tests',
        f'--disable-cuda-llvm',
        f'--disable-v4l2-m2m',
    ]
    if ctx.args.target_plat != 'win-msvc':
        args.append('--toolchain=clang-')
    if ctx.args.target_plat in {'iphoneos', 'iphonesimulator'}:
        args.append('--disable-programs')
    if ctx.args.target_plat in {'macosx', 'iphoneos', 'iphonesimulator'}:
        args.append('--disable-coreimage')

    _ffmpeg_cross_os = {
        'linux':           'linux',
        'win-mingw':       'mingw64',
        'android':         'android',
        'macosx':          'darwin',
        'iphoneos':        'darwin',
        'iphonesimulator': 'darwin',
    }[ctx.args.target_plat]
    args.extend([
        f'--enable-cross-compile',
        f'--target-os={_ffmpeg_cross_os}',
        f'--arch={ctx.args.target_arch}',
        f'--host-cc=clang',
        f'--cc={" ".join(ctx.args.cc)}',
        f'--cxx={" ".join(ctx.args.cc)} --driver-mode=g++',
        f'--nm={" ".join(ctx.args.nm)}',
        f'--ar={" ".join(ctx.args.ar)}',
        f'--pkg-config={" ".join(ctx.args.pkgconf)}',
        f'--extra-ldflags={" ".join(ctx.args.ldflags)}',
    ])
    if ctx.args.target_plat == 'win-mingw':
        args.append(f'--windres={" ".join(ctx.args.windres)}')

    x.run_as_subprocess(env=build_env, cwd=pkg_buld_dir, args=args)
def _build_step_1():
    import subprocess as sp

    args = ['make', '-j', f'{x.detect_cpu_count()}']
    x.run_as_subprocess(env=build_env, cwd=pkg_buld_dir, args=args, stdout=sp.DEVNULL)
def _build_step_2():
    x.run_as_subprocess(env=get_build_env(), args=['cmake', '--install', ctx.args.pkg_buld_dir, '--strip'])
