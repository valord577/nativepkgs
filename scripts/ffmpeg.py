#!/usr/bin/env python3

# fmt: off

import os
import shlex
import shutil


_env: dict = {}
_ctx: dict = {
    'PKG_VERSION': 'unknown',
    'PKG_INST_STRIP': '',
    'BUILD_ENV': os.environ.copy(),

    'EXTRA_ARGS_CONFIGURE': [],
}

def module_init(env: dict) -> list:
    global _env; _env = env
    return [
        _source_dl_3rd_deps,
        _source_download,
        _source_apply_patches,
        _build_clangd_dev,
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
        _env['FUNC_PKGC'](_ctx, _env, 'sdl2', 'v2.32.4', 'static')
def _source_download():
    _git_target = 'refs/heads/release/7.1'
    _ctx['PKG_VERSION'] = f'release{_git_target.split("/")[-1]}'

    if not os.path.exists(os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], '.git'))):
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'init'])
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'remote', 'add', 'x', 'https://git.ffmpeg.org/ffmpeg.git'])
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{_git_target}'])
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'checkout', 'FETCH_HEAD'])
    if file_ver := os.getenv('DEPS_VER', ''):
        with open(file_ver, 'w') as f:
            f.write(_ctx['PKG_VERSION'])
def _source_apply_patches():
    if not os.path.exists(_env['SUBPROJ_SRC_PATCHES']):
        return
    _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'reset', '--hard', 'HEAD'])
    _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'clean', '-d', '-f', '-q'])
    with os.scandir(_env['SUBPROJ_SRC_PATCHES']) as it:
        entries = sorted(it, key=lambda e: e.name)
        for entry in entries:
            if not entry.is_file():
                continue
            _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'],
                args=[shutil.which('git'), 'apply', '--verbose', '--ignore-space-change', '--ignore-whitespace', entry.path])


def _build_clangd_dev():
    if _env['ON_CLANGD_CK']:
        _env['PKG_BULD_DIR'] = _env['SUBPROJ_SRC']
def _build_step_00():
    _extra_args_configure: list[str] = _ctx['EXTRA_ARGS_CONFIGURE']

    # if _env['PKG_TYPE'] == 'static':
    #     _extra_args_configure.extend([])
    # if _env['PKG_TYPE'] == 'shared':
    #     _extra_args_configure.extend(['--disable-static', '--enable-shared'])

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

    _ctx['BUILD_ENV']['PKG_CONFIG_PATH'] = \
        f"{os.pathsep.join(_ctx['PKG_CONFIG_PATH'])}{os.pathsep}{os.getenv('PKG_CONFIG_PATH', '')}"
    _env['FUNC_SHELL_DEVNUL'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=args)
def _build_step_01():
    args = [shutil.which('make'), '-j', _env['PARALLEL_JOBS']]
    if shutil.which('bear'):
        args = [shutil.which('bear'), '--'] + args
    _env['FUNC_SHELL_DEVNUL'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=args)
def _build_step_02():
    if not (_env['PKG_PLATFORM'] in ['iphoneos', 'iphonesimulator']):
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=[shutil.which('make'), 'install-progs'])
    _env['FUNC_SHELL_DEVNUL'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=[shutil.which('make'), 'install-headers'])
    _env['FUNC_SHELL_DEVNUL'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=[shutil.which('make'), 'install-libs'])


    if _env.get('PLATFORM_APPLE', False) or _env['PKG_PLATFORM'] in ['linux', 'win-mingw']:
        # symbols list
        _ffmpeg_libs_dir = []
        with os.scandir(_env['SUBPROJ_SRC']) as it:
            entries = sorted(it, key=lambda e: e.name)
            _ffmpeg_libs_dir.extend([d.path for d in entries if d.is_dir() and d.name.startswith('lib')])

        _ffmpeg_symbol_v = []
        for _lib_dir in _ffmpeg_libs_dir:
            with os.scandir(_lib_dir) as it:
                entries = sorted(it, key=lambda e: e.name)
                _ffmpeg_symbol_v.extend([v.path for v in entries if v.name.endswith('.v')])

        _ffmpeg_mergeso_sym_l = []
        for _v in _ffmpeg_symbol_v:
            with open(_v, 'r') as f:
                _x = f.read()
                _l = _x[_x.index('global:'):_x.index('local:')]
                for _s in _l.splitlines():
                    if not _s.endswith(';'):
                        continue
                    _ret = _s.strip()[:-1]
                    if _ret not in _ffmpeg_mergeso_sym_l:
                        _ffmpeg_mergeso_sym_l.append(_ret)

        _ffmpeg_mergeso_sym_v = os.path.abspath(os.path.join(_env['PKG_INST_DIR'], 'lib', 'libffmpeg.v'))
        with open(_ffmpeg_mergeso_sym_v, 'w') as f:
            if _env.get('PLATFORM_APPLE', False):
                for x in _ffmpeg_mergeso_sym_l:
                    f.write(f'_{x}\n')
            if _env['PKG_PLATFORM'] == 'linux':
                f.write('{\n')
                f.write('  global:\n')
                for x in _ffmpeg_mergeso_sym_l:
                    f.write(f'    {x};\n')
                f.write('  local:\n')
                f.write('    *;\n')
                f.write('};')
            if _env['PKG_PLATFORM'] == 'win-mingw':
                _dll_sym_arg = f"{_env['NM']} -a lib/*.a | grep ' T ' | cut -d ' ' -f 3"
                _dll_sym_all = _env['FUNC_SHELL_STDOUT'](cwd=_env['PKG_INST_DIR'], env=_ctx['BUILD_ENV'], shell=True, args=_dll_sym_arg)
                f.write('LIBRARY libffmpeg\n')
                f.write('EXPORTS\n')
                for x in shlex.split(_dll_sym_all):
                    for rule in _ffmpeg_mergeso_sym_l:
                        _rule = rule[:-1] if rule.endswith('*') else rule
                        if x.startswith(_rule):
                            f.write(f'  {x}\n')
                            break


        _ffmpeg_pkgconf_dir = os.path.abspath(os.path.join(_env['PKG_INST_DIR'], 'lib', 'pkgconfig'))
        _ctx['BUILD_ENV']['PKG_CONFIG_PATH'] = f"{_ffmpeg_pkgconf_dir}{os.pathsep}{os.getenv('PKG_CONFIG_PATH', '')}"

        _pkgconf_bin = _env.get('CROSS_PKGCONFIG_BIN', '')
        if not _pkgconf_bin:
            _pkgconf_bin = shutil.which('pkgconf') or 'pkg-config'
        _ffmpeg_mergeso_lib0 = _env['FUNC_SHELL_STDOUT'](env=_ctx['BUILD_ENV'], args=[_pkgconf_bin, '--libs', 'libavdevice'])
        _ffmpeg_mergeso_lib1 = shlex.split(_ffmpeg_mergeso_lib0)
        _ffmpeg_mergeso_libdir = []
        _ffmpeg_mergeso_libffm = []
        _ffmpeg_mergeso_libmac = []
        _ffmpeg_mergeso_libext = []
        _ffmpeg_mergeso_libstd = []
        i = 0; c = len(_ffmpeg_mergeso_lib1)
        while i < c:
            x = _ffmpeg_mergeso_lib1[i]; i += 1
            if False:
                pass
            elif x.startswith('-L'):
                if x not in _ffmpeg_mergeso_libdir: _ffmpeg_mergeso_libdir.append(x)
            elif x.startswith('-lav') or x.startswith('-lsw'):
                if x not in _ffmpeg_mergeso_libffm: _ffmpeg_mergeso_libffm.append(x)
            elif x in ['-lm', '-ldl', '-latomic']:
                if x not in _ffmpeg_mergeso_libstd: _ffmpeg_mergeso_libstd.append(x)
            elif x in ['-framework']:
                f = _ffmpeg_mergeso_lib1[i]; i += 1
                if f not in _ffmpeg_mergeso_libmac: _ffmpeg_mergeso_libmac.append(f)
            else:
                if x not in _ffmpeg_mergeso_libext: _ffmpeg_mergeso_libext.append(x)


        _ffmpeg_mergeso_out = ''; _ffmpeg_mergeso_cmd = []
        _ffmpeg_mergeso_cmd.extend(shlex.split(f"{_env.get('CC', 'clang')} {_env.get('CROSS_LDFLAGS', '')}"))
        if 'ccache' in _ffmpeg_mergeso_cmd[0]:
            _ffmpeg_mergeso_cmd = _ffmpeg_mergeso_cmd[1:]
        _ffmpeg_mergeso_cmd.extend(['-shared', '-v'])
        if _env.get('PLATFORM_APPLE', False):
            _ffmpeg_mergeso_out = 'lib/libffmpeg.dylib'
            _ffmpeg_mergeso_cmd.extend(['-o', _ffmpeg_mergeso_out, '-install_name', _ffmpeg_mergeso_out.split("/")[-1]])
            _ffmpeg_mergeso_cmd.extend(['-Wl,-exported_symbols_list', _ffmpeg_mergeso_sym_v])
            _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libdir)
            for x in _ffmpeg_mergeso_libffm:
                _ffmpeg_mergeso_cmd.extend(['-Wl,-force_load', f'lib/lib{x[2:]}.a'])
            _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libext)
            _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libstd)
            for x in _ffmpeg_mergeso_libmac:
                _ffmpeg_mergeso_cmd.extend(['-framework', x])
        if _env['PKG_PLATFORM'] == 'linux':
            _ffmpeg_mergeso_out = 'lib/libffmpeg.so'
            _ffmpeg_mergeso_cmd.extend(['-o', _ffmpeg_mergeso_out, f'-Wl,--soname={_ffmpeg_mergeso_out.split("/")[-1]}'])
            _ffmpeg_mergeso_cmd.extend([f'-Wl,--version-script={_ffmpeg_mergeso_sym_v}'])
            _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libdir)
            _ffmpeg_mergeso_cmd.extend(['-Wl,--whole-archive'])
            _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libffm)
            _ffmpeg_mergeso_cmd.extend(['-Wl,--no-whole-archive'])
            _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libext)
            _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libstd)
        if _env['PKG_PLATFORM'] == 'win-mingw':
            _ffmpeg_mergeso_out = 'lib/libffmpeg.dll'
            _ffmpeg_mergeso_cmd.extend(['-o', _ffmpeg_mergeso_out])
            _ffmpeg_mergeso_cmd.extend([f'-Wl,--Xlink=/DEF:{_ffmpeg_mergeso_sym_v}'])
            _ffmpeg_mergeso_cmd.extend([f'-Wl,--output-def={_ffmpeg_mergeso_out.split(".")[0]}.def'])
            _ffmpeg_mergeso_cmd.extend([f'-Wl,--out-implib={_ffmpeg_mergeso_out.split(".")[0]}.lib'])
            _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libdir)
            _ffmpeg_mergeso_cmd.extend(['-Wl,--whole-archive'])
            _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libffm)
            _ffmpeg_mergeso_cmd.extend(['-Wl,--no-whole-archive'])
            _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libext)
            _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libstd)
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['PKG_INST_DIR'], env=_ctx['BUILD_ENV'], args=_ffmpeg_mergeso_cmd)

        if _env['LIB_RELEASE'] == '1':
            _ffmpeg_mergeso_cmd = [_env.get('STRIP', 'strip')]
            if _env.get('PLATFORM_APPLE', False):
                _ffmpeg_mergeso_cmd.append('-x')
            if _env['PKG_PLATFORM'] in ['linux', 'win-mingw']:
                _ffmpeg_mergeso_cmd.append('--strip-all')
            _ffmpeg_mergeso_cmd.append(_ffmpeg_mergeso_out)
            _env['FUNC_SHELL_DEVNUL'](cwd=_env['PKG_INST_DIR'], env=_ctx['BUILD_ENV'], args=_ffmpeg_mergeso_cmd)

        _env['FUNC_SHELL_DEVNUL'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=[shutil.which('make'), 'uninstall-libs'])
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=[shutil.which('make'), 'uninstall-pkgconfig'])

        with open(os.path.abspath(os.path.join(_ffmpeg_pkgconf_dir, 'libffmpeg.pc')), 'w') as f:
            f.write("prefix=${pcfiledir}/../..\n")
            f.write("includedir=${prefix}/include\n")
            f.write("libdir=${prefix}/lib\n")
            f.write("\n")
            f.write("Name: libffmpeg\n")
            f.write("Description: LGPL FFMPEG Library\n")
            f.write(f"Version: {_ctx['PKG_VERSION']}\n")
            f.write("Libs: -L${libdir} -lffmpeg\n")
            f.write("Cflags: -I${includedir}\n")
