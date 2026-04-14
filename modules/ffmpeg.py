#!/usr/bin/env python3

# fmt: off

from scripts import utils as x
# ----------------------------

import os
import shlex
import shutil

from pathlib import Path


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

_cc = ''
_cxx = ''

_cross_build_on_linux = False
_host_cc = ''
_windres = ''
_pkgconf_bin = ''
_cross_ldflags = ''
_nm = ''
_ar = ''
_ranlib = ''
_strip = ''

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

    global _cc; \
        _cc = env['CC']
    global _cxx; \
        _cxx = env['CXX']

    if _target_platform == 'linux':
        global _cross_build_on_linux; \
            _cross_build_on_linux = env['CROSS_BUILD_ENABLED']
    global _host_cc; \
        _host_cc = env.get('HOSTCC', '')
    global _windres; \
        _windres = env.get('WINDRES', '')
    global _pkgconf_bin; \
        _pkgconf_bin = env.get('CROSS_PKGCONFIG_BIN', '')
    global _cross_ldflags; \
        _cross_ldflags = env.get('CROSS_LDFLAGS', '')
    global _nm; \
        _nm = env.get('NM', '')
    global _ar; \
        _ar = env.get('AR', '')
    global _ranlib; \
        _ranlib = env.get('RANLIB', '')
    global _strip; \
        _strip = env.get('STRIP', '')

    if _target_pkg_type != 'shared':
        raise NotImplementedError(f'unsupported PKG_TYPE: {_target_pkg_type}')


    return [
        _source_dl_3rd_deps,
        _source_download,
        _build_on_code_edit,
        _build_step_00,
        _build_step_01,
        # _build_step_02,
    ]



def _source_dl_3rd_deps():
    _3rd_deps = [
        {
            'name': 'dav1d',
            'type': 'static',
            'vers': '',
            'args': '--enable-libdav1d',
        },
        {
            'name': 'mbedtls3',
            'type': 'static',
            'vers': '',
            'args': '--enable-mbedtls',
        },
    ]
    if _target_platform in ['linux', 'win-mingw', 'android']:
        _3rd_deps.extend([
            {
                'name': 'zlib-ng',
                'type': 'static',
                'vers': '',
                'args': '',
            },
        ])
    if _target_platform in ['macosx', 'win-mingw']:
        _3rd_deps.extend([
            {
                'name': 'sdl2',
                'type': 'static',
                'vers': '',
                'args': '',
            },
        ])

    _get_prebuilt_script = (Path(x.PROJ_ROOT) / 'scripts' / 'get_prebuilt.py').absolute().as_posix()
    for dep in _3rd_deps:
        _name = dep['name']; _type = dep['type']; _vers = dep['vers']; _args = dep['args']
        x._util_func__exec_python([_get_prebuilt_script, _target_archlibc, _name, _target_platform, _vers, _type, '', _3rd_deps_dir])

        if _args: _extra_args_build.append(_args)

        old_pkgconf_path = BUILD_ENV.get('PKG_CONFIG_PATH', '')
        new_pkgconf_path = (Path(_3rd_deps_dir) / _name / 'lib' / 'pkgconfig').absolute().as_posix()
        BUILD_ENV['PKG_CONFIG_PATH'] = new_pkgconf_path + os.pathsep + old_pkgconf_path
def _source_download():
    _git_target = 'refs/heads/release/8.1'
    if not (Path(_subproj_src) / '.git').exists():
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'init'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'remote', 'add', 'x', 'https://git.ffmpeg.org/ffmpeg.git'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{_git_target}'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'checkout', 'FETCH_HEAD'])
    x._util_put_pkg_version_desc(_target_pkg_name, x._util_func__subprocess(cwd=_subproj_src, collect_stdout=True, args=['git', 'describe', '--always', '--abbrev=7']))
    x._util_source_apply_patches(_subproj_src, _subproj_src_patches)
def _build_on_code_edit():
    if x.ON_CODE_EDIT:
        global _pkg_buld_dir; \
            _pkg_buld_dir = _subproj_src
def _build_step_00():
    args = [(Path(_subproj_src) / 'configure').absolute().as_posix(),
        f'--prefix={_pkg_inst_dir}', *_extra_args_build,
        '--disable-stripping',
        '--enable-version3',
        '--fatal-warnings',
        '--disable-doc',
        '--disable-devices',
        '--enable-indev=lavfi',
        '--enable-pic',
        '--disable-libxcb',
        '--disable-xlib',
        '--disable-vaapi',
        f'--cc={_cc}', f'--cxx={_cxx}',
    ]
    if _pkgconf_bin:
        args.append(f'--pkg-config={_pkgconf_bin}')

    if _target_platform in ['linux', 'android']:
        _rpath = '\\$\\$ORIGIN:\\$\\$ORIGIN/../lib'
        args.extend([
            f"--extra-ldsoflags=-Wl,-rpath,'{_rpath}'",
            f"--extra-ldexeflags=-Wl,-rpath,'{_rpath}'",
        ])

    _ffmpeg_target_os = _target_platform
    if _target_platform == 'win-mingw':
        _ffmpeg_target_os = 'mingw64'
    elif _target_platform in ['macosx', 'iphoneos', 'iphonesimulator']:
        _ffmpeg_target_os = 'darwin'
        args.append('--disable-coreimage')

    if _target_platform != 'linux' or _cross_build_on_linux:
        args.extend([
            '--enable-cross-compile',
            f'--target-os={_ffmpeg_target_os}',
            f'--arch={_target_arch}',
        ])
        if _target_platform in ['linux', 'win-mingw', 'android']:
            args.extend([
                f'--host-cc={_host_cc}',
                f'--nm={_nm}',
                f'--ar={_ar}',
                f'--ranlib={_ranlib}',
                f'--strip={_strip}',
            ])
        if _target_platform == 'android':
            args.extend([
                '--enable-jni',
                '--enable-mediacodec',
            ])
        if _target_platform == 'win-mingw':
            args.extend([
                f'--windres={_windres}',
            ])
        else:
            args.extend([
                f'--extra-ldflags={_cross_ldflags}',
            ])

    x._util_func__subprocess(cwd=_pkg_buld_dir, env=BUILD_ENV, args=args)
def _build_step_01():
    args = f"make -j {x.CPU_COUNT} 1>/dev/null"
    if bear := shutil.which('bear'): args = f"{bear} -- " + args
    x._util_func__subprocess(cwd=_pkg_buld_dir, env=BUILD_ENV, args=args, shell=True)







def _module_init(env: dict) -> list:
    return [
        _source_dl_3rd_deps,
        _source_download,
        _source_apply_patches,
        _build_clangd_dev,
        _build_step_00,
        _build_step_01,
        _build_step_02,
    ]



def __source_dl_3rd_deps():
    _env['FUNC_PKGC'](_ctx, _env, 'dav1d',
        '42b2b24', 'static'); _ctx['EXTRA_ARGS_CONFIGURE'].append('--enable-libdav1d')
    _env['FUNC_PKGC'](_ctx, _env, 'mbedtls',
        'e185d7f', 'static'); _ctx['EXTRA_ARGS_CONFIGURE'].append('--enable-mbedtls')

    if _env['PKG_PLATFORM'] in ['macosx', 'win-mingw']:
        _env['FUNC_PKGC'](_ctx, _env, 'sdl2',    '5d24957', 'static')
    if not _env.get('PLATFORM_APPLE', False):
        _env['FUNC_PKGC'](_ctx, _env, 'zlib-ng', '4254390', 'static')
def __source_download():
    _git_target = 'refs/heads/release/8.0'
    if not os.path.exists(os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], '.git'))):
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'init'])
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'remote', 'add', 'x', 'https://git.ffmpeg.org/ffmpeg.git'])
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{_git_target}'])
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'checkout', 'FETCH_HEAD'])

    _git_ver = _env['FUNC_SHELL_STDOUT'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'describe', '--always', '--abbrev=7'])[:-1]
    _ctx['PKG_VERSION'] = f'v{_git_target.split("/")[-1]}-{_git_ver}'
    if file_ver := os.getenv('DEPS_VER', ''):
        Path(file_ver).write_text(_ctx['PKG_VERSION'])
def __source_apply_patches():
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


def __build_clangd_dev():
    if x.ON_CODE_EDIT:
        _env['PKG_BULD_DIR'] = _env['SUBPROJ_SRC']
def __build_step_00():
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
    if _env['PKG_PLATFORM'] == 'android':
        args.extend([
            '--enable-cross-compile',
            '--target-os=android',
           f'--arch={_env["PKG_ARCH"]}',
           f'--host-cc={_env["HOSTCC"]}',
           f'--extra-ldflags={_env["CROSS_LDFLAGS"]}',
           f'--nm={_env["NM"]}',
           f'--ar={_env["AR"]}',
           f'--ranlib={_env["RANLIB"]}',
           f'--strip={_env["STRIP"]}',
            '--enable-jni',
            '--enable-mediacodec',
        ])

    _ctx['BUILD_ENV']['PKG_CONFIG_PATH'] = \
        f"{os.pathsep.join(_ctx['PKG_CONFIG_PATH'])}{os.pathsep}{os.getenv('PKG_CONFIG_PATH', '')}"
    _env['FUNC_SHELL_DEVNUL'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=args)
def __build_step_01():
    args = f"{shutil.which('make')} -j {_env['PARALLEL_JOBS']} 1>/dev/null"
    if bear := shutil.which('bear'): args = f"{bear} -- " + args
    _env['FUNC_SHELL_DEVNUL'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], shell=True, args=args)
def __build_step_02():
    if not (_env['PKG_PLATFORM'] in ['iphoneos', 'iphonesimulator']):
        _env['FUNC_SHELL_DEVNUL'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=[shutil.which('make'), 'install-progs'])
    _env['FUNC_SHELL_DEVNUL'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=[shutil.which('make'), 'install-headers'])
    _env['FUNC_SHELL_DEVNUL'](cwd=_env['PKG_BULD_DIR'], env=_ctx['BUILD_ENV'], args=[shutil.which('make'), 'install-libs'])


    if _env.get('PLATFORM_APPLE', False) or _env['PKG_PLATFORM'] in ['linux', 'win-mingw', 'android']:
        # symbols list
        #_ffmpeg_libs_dir = []
        #with os.scandir(_env['SUBPROJ_SRC']) as it:
        #    entries = sorted(it, key=lambda e: e.name)
        #    _ffmpeg_libs_dir.extend([d.path for d in entries if d.is_dir() and d.name.startswith('lib')])
        #
        #_ffmpeg_symbol_v = []
        #for _lib_dir in _ffmpeg_libs_dir:
        #    with os.scandir(_lib_dir) as it:
        #        entries = sorted(it, key=lambda e: e.name)
        #        _ffmpeg_symbol_v.extend([v.path for v in entries if v.name.endswith('.v')])
        #print('debug >>>>>>', _ffmpeg_symbol_v)

        _ffmpeg_symbol_v = glob.glob(os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], 'lib*', '*.v')))

        _ffmpeg_mergeso_sym_l = []
        for _v in _ffmpeg_symbol_v:
            _x = Path(os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], _v))).read_text()
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
            if _env['PKG_PLATFORM'] in ['linux', 'android']:
                f.write('{\n')
                f.write('  global:\n')
                for x in _ffmpeg_mergeso_sym_l:
                    f.write(f'    {x};\n')
                f.write('  local:\n')
                f.write('    *;\n')
                f.write('};\n')
            if _env['PKG_PLATFORM'] in ['win-mingw']:
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
            elif x in ['-lm', '-ldl', '-latomic', '-pthread']:
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
        if _env['PKG_PLATFORM'] in ['linux', 'android']:
            _ffmpeg_mergeso_out = 'lib/libffmpeg.so'
            _ffmpeg_mergeso_cmd.extend(['-o', _ffmpeg_mergeso_out, f'-Wl,--soname={_ffmpeg_mergeso_out.split("/")[-1]}'])
            _ffmpeg_mergeso_cmd.extend([f'-Wl,--version-script={_ffmpeg_mergeso_sym_v}'])
            _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libdir)
            _ffmpeg_mergeso_cmd.extend(['-Wl,--whole-archive'])
            _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libffm)
            _ffmpeg_mergeso_cmd.extend(['-Wl,--no-whole-archive'])
            _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libext)
            _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libstd)
        if _env['PKG_PLATFORM'] in ['win-mingw']:
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
            if _env['PKG_PLATFORM'] in ['linux', 'win-mingw', 'android']:
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
