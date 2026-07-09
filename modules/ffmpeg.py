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
        _build_step_2,
    ]
# ----------------------------
def get_build_env() -> "dict[str, str]":
    env = x.ENVIRON
    if ctx.args.target_plat == 'win-msvc':
        env.update(ctx.args.win32_msvc_env_target)
        env['CFLAGS'] = '/utf-8'
        env['CXXFLAGS'] = env['CFLAGS']
    return env
# ----------------------------
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
        x.append_pkgconf_search_path((dep_path / 'lib' / 'pkgconfig'))
def _fetch_source():
    ctx.fetch_source_from_git('refs/heads/release/8.1', 'https://git.ffmpeg.org/ffmpeg.git')
def _build_step_0():
    args = [
        ctx.subproj_src_dir('configure').as_posix(),
        *extra_args,
        f'--prefix={ctx.args.pkg_inst_dir}',
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

    if x.feature('ENABLE_CLANGD_FOR_LEGACY_TOOLCHAIN') != '0':
        global pkg_buld_dir; \
            pkg_buld_dir = ctx.subproj_src_dir().as_posix()
    else:
        args.append('--disable-logging')
    x.run_as_subprocess(env=get_build_env(), cwd=pkg_buld_dir, args=args)
def _build_step_1():
    import shutil
    import subprocess as sp

    bear: list[str] = []
    if x.feature('ENABLE_CLANGD_FOR_LEGACY_TOOLCHAIN') != '0':
        if bear_exec := shutil.which('bear'): bear.append(bear_exec)

    args = ['make', '-j', f'{x.detect_cpu_count()}']
    x.run_as_subprocess(env=get_build_env(), cwd=pkg_buld_dir, args=(bear + args), stdout=sp.DEVNULL)
def _build_step_2():
    import shlex

    args = ['make', 'install-headers', 'install-libs']
    if ctx.args.target_plat not in {'iphoneos', 'iphonesimulator'}:
        args.append('install-progs')
    x.run_as_subprocess(env=get_build_env(), cwd=pkg_buld_dir, args=args)

    if ctx.args.target_plat == 'win-msvc':
        return


    exported_symbols: "set[str]" = set()
    for _v in ctx.subproj_src_dir().glob('**/*.v'):
        _x = _v.read_text()
        _l = _x[_x.index('global:'):_x.index('local:')]
        for _s in _l.splitlines():
            if not _s.endswith(';'):
                continue
            exported_symbols.add(_s.strip()[:-1])
    x.logv(f'exported symbols: {exported_symbols}')

    ffmpeg_symbol_v = (Path(ctx.args.pkg_inst_dir) / 'lib' / 'libffmpeg.v')
    with ffmpeg_symbol_v.open('w', encoding='utf-8') as f:
        if ctx.args.target_plat in {'linux', 'android'}:
            _ = f.write('{\n')
            _ = f.write('  global:\n')
            for symbol in exported_symbols:
                _ = f.write(f'    {symbol};\n')
            _ = f.write('  local:\n')
            _ = f.write('    *;\n')
            _ = f.write('};\n')
        elif ctx.args.target_plat == 'win-mingw':
            _dll_sym_arg = f"{' '.join(ctx.args.nm)} -a lib/*.a | grep ' T ' | cut -d ' ' -f 3"
            _dll_sym_all = x.run_as_subprocess(env=get_build_env(), cwd=ctx.args.pkg_inst_dir,
                collect_stdout=True, args=_dll_sym_arg, shell=True)
            _ = f.write('LIBRARY libffmpeg\n')
            _ = f.write('EXPORTS\n')
            for symbol in shlex.split(_dll_sym_all):
                if any(
                    (
                        (symbol == rule) or
                        (rule.endswith('*') and symbol.startswith(rule[:-1]))
                    ) for rule in exported_symbols
                ): _ = f.write(f'  {symbol}\n')
        else: # apple platform
            for symbol in exported_symbols:
                _ = f.write(f'_{symbol}\n')


    ffmpeg_pkgconf_search = (Path(ctx.args.pkg_inst_dir) / 'lib' / 'pkgconfig')
    x.append_pkgconf_search_path(ffmpeg_pkgconf_search)
    ffmpeg_self_libraries = shlex.split(
        x.run_as_subprocess(env=get_build_env(), collect_stdout=True, args=[' '.join(ctx.args.pkgconf), '--libs', 'libavdevice'])
    )

    ffmpeg_mergeso_libdir: list[str] = []
    ffmpeg_mergeso_libffm: list[str] = []
    ffmpeg_mergeso_libmac: list[str] = []
    ffmpeg_mergeso_libext: list[str] = []
    ffmpeg_mergeso_libstd: list[str] = []
    i = 0; c = len(ffmpeg_self_libraries)
    while i < c:
        _lib = ffmpeg_self_libraries[i]; i += 1
        if False:
            pass  # pyright: ignore[reportUnreachable]
        elif _lib.startswith('-L'):
            if _lib not in ffmpeg_mergeso_libdir: ffmpeg_mergeso_libdir.append(_lib)
        elif _lib in {'-lavdevice', '-lavfilter', '-lswscale', '-lavformat', '-lavcodec', '-lswresample', '-lavutil'}:
            if _lib not in ffmpeg_mergeso_libffm: ffmpeg_mergeso_libffm.append(_lib)
        elif _lib in {'-lm', '-ldl', '-latomic', '-pthread'}:
            if _lib not in ffmpeg_mergeso_libstd: ffmpeg_mergeso_libstd.append(_lib)
        elif _lib in {'-framework'}:
            _lib = ffmpeg_self_libraries[i]; i += 1
            if _lib not in ffmpeg_mergeso_libmac: ffmpeg_mergeso_libmac.append(_lib)
        else:
            if _lib not in ffmpeg_mergeso_libext: ffmpeg_mergeso_libext.append(_lib)

    merged = Path(ctx.args.pkg_inst_dir)
    cmdlink: list[str] = []
    cmdlink.extend(ctx.args.cc)
    cmdlink.extend(ctx.args.ldflags)
    cmdlink.extend(['-shared', '-v'])
    if ctx.args.target_plat in {'linux', 'android'}:
        merged = (merged / 'lib' / 'libffmpeg.so'); \
            merged.parent.mkdir(parents=True, exist_ok=True)
        cmdlink.extend([
            f'-Wl,-rpath,$ORIGIN',
            f'-Wl,--version-script={ffmpeg_symbol_v.as_posix()}',
            f'-o', merged.as_posix(),
            f'-Wl,--soname={merged.name}',
        ])
        cmdlink.extend(ffmpeg_mergeso_libdir)
        cmdlink.extend(['-Wl,--whole-archive'])
        cmdlink.extend(ffmpeg_mergeso_libffm)
        cmdlink.extend(['-Wl,--no-whole-archive'])
        cmdlink.extend(ffmpeg_mergeso_libext)
        cmdlink.extend(ffmpeg_mergeso_libstd)
    elif ctx.args.target_plat == 'win-mingw':
        merged = (merged / 'lib' / 'libffmpeg.dll'); \
            merged.parent.mkdir(parents=True, exist_ok=True)
        cmdlink.extend(['-o', merged.as_posix()])
        cmdlink.extend([f'-Wl,--Xlink=/DEF:{ffmpeg_symbol_v.as_posix()}'])
        cmdlink.extend([f'-Wl,--output-def={(merged.parent / merged.stem).as_posix()}.def'])
        cmdlink.extend([f'-Wl,--out-implib={(merged.parent / merged.stem).as_posix()}.lib'])
        cmdlink.extend(ffmpeg_mergeso_libdir)
        cmdlink.extend(['-Wl,--whole-archive'])
        cmdlink.extend(ffmpeg_mergeso_libffm)
        cmdlink.extend(['-Wl,--no-whole-archive'])
        cmdlink.extend(ffmpeg_mergeso_libext)
        cmdlink.extend(ffmpeg_mergeso_libstd)
    else: # apple platform
        merged = (merged / 'lib' / 'libffmpeg.dylib'); \
            merged.parent.mkdir(parents=True, exist_ok=True)
        cmdlink.extend(['-o', merged.as_posix(), '-install_name', merged.name])
        cmdlink.extend(['-Wl,-exported_symbols_list', ffmpeg_symbol_v.as_posix()])
        cmdlink.extend(ffmpeg_mergeso_libdir)
        for _lib in ffmpeg_mergeso_libffm:
            cmdlink.extend(['-Wl,-force_load', f'lib/lib{_lib[2:]}.a'])
        cmdlink.extend(ffmpeg_mergeso_libext)
        cmdlink.extend(ffmpeg_mergeso_libstd)
        for _lib in ffmpeg_mergeso_libmac:
            cmdlink.extend(['-framework', _lib])
    x.run_as_subprocess(env=get_build_env(), cwd=ctx.args.pkg_inst_dir, args=cmdlink)


    dbgsym = f'{merged.as_posix()}.dbgsym'
    if ctx.args.target_plat in {'linux', 'win-mingw', 'android'}:
        x.run_as_subprocess(env=get_build_env(), cwd=ctx.args.pkg_inst_dir,
            args=(ctx.args.objcopy + ['--only-keep-debug', merged.as_posix(), dbgsym]))
        x.run_as_subprocess(env=get_build_env(), cwd=ctx.args.pkg_inst_dir,
            args=(ctx.args.objcopy + ['--strip-debug', '--strip-unneeded', merged.as_posix()]))
        x.run_as_subprocess(env=get_build_env(), cwd=ctx.args.pkg_inst_dir,
            args=(ctx.args.objcopy + [f'--add-gnu-debuglink={dbgsym}', merged.as_posix()]))
    x.run_as_subprocess(env=get_build_env(), cwd=pkg_buld_dir,
        args=['make', 'uninstall-libs', 'uninstall-pkgconfig'])


    # export pkgconf search file
    _pkgconf_content = '''\
prefix=${pcfiledir}/../..
includedir=${prefix}/include
libdir=${prefix}/lib

Name: libffmpeg
Description: libffmpeg under lgpl
URL: https://github.com/valord577/nativepkgs
Version: @PACKAGE_VERSION@
Requires:
Cflags: -I${includedir}
Libs: -L${libdir} -lffmpeg
'''
    _pkgconf_content = _pkgconf_content.replace('@PACKAGE_VERSION@', ctx.subproj_src_ver())
    _pkgconf = (ffmpeg_pkgconf_search / 'libffmpeg.pc'); \
        _pkgconf.parent.mkdir(parents=True, exist_ok=True)
    _ = _pkgconf.write_text(_pkgconf_content)
