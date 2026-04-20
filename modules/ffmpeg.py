#!/usr/bin/env python3

# fmt: off

from scripts import utils as x
# ----------------------------

import os
import shlex
import shutil
import subprocess as sp

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
_extra_args_enable_log = False

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
_objcopy = ''

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
        _extra_sysroot = env['SYSROOT']

    global _cc; \
        _cc = env['CC']
    global _cxx; \
        _cxx = env['CXX']

    if _target_platform == 'linux':
        global _cross_build_on_linux; \
            _cross_build_on_linux = env['CROSS_BUILD_ENABLED']
    global _host_cc; \
        _host_cc = env['HOSTCC']
    global _windres; \
        _windres = env['WINDRES']
    global _pkgconf_bin; \
        _pkgconf_bin = env['CROSS_PKGCONFIG_BIN'] or shutil.which('pkgconf') or 'pkg-config'
    global _cross_ldflags; \
        _cross_ldflags = env['CROSS_LDFLAGS']
    global _nm; \
        _nm = env['NM']
    global _ar; \
        _ar = env['AR']
    global _ranlib; \
        _ranlib = env['RANLIB']
    global _strip; \
        _strip = env['STRIP']
    global _objcopy; \
        _objcopy = env['OBJCOPY']

    if _target_pkg_type != 'shared':
        raise NotImplementedError(f'unsupported PKG_TYPE: {_target_pkg_type}')


    return [
        _source_dl_3rd_deps,
        _source_download,
        _build_on_code_edit,
        _build_step_00,
        _build_step_01,
        _build_step_02,
    ]



def _source_dl_3rd_deps():
    _3rd_deps = [
        {
            'name': 'dav1d',
            'type': 'static',
            'vers': 'b546257',
            'args': '--enable-libdav1d',
        },
        {
            'name': 'mbedtls3',
            'type': 'static',
            'vers': '0bebf8b',
            'args': '--enable-mbedtls',
        },
    ]
    if _target_platform not in ['macosx', 'iphoneos', 'iphonesimulator']:
        _3rd_deps.extend([
            {
                'name': 'zlib-ng',
                'type': 'static',
                'vers': '1273109',
            },
        ])
    if _target_platform in ['macosx', 'win-mingw']:
        _3rd_deps.extend([
            {
                'name': 'sdl2',
                'type': 'static',
                'vers': '1549cd3',
            },
        ])

    _get_prebuilt_script = (Path(x.PROJ_ROOT) / 'scripts' / 'get_prebuilt.py').absolute().as_posix()
    for dep in _3rd_deps:
        _name = dep['name']; _type = dep['type']; _vers = dep['vers']; _args = dep.get('args', '')
        x._util_func__exec_python([_get_prebuilt_script, _target_archlibc, _name, _target_platform, _vers, _type, '', _3rd_deps_dir])

        if _args: _extra_args_build.append(_args)
        x._util_append_env_pkgconf_path(BUILD_ENV, (Path(_3rd_deps_dir) / _name / 'lib' / 'pkgconfig'))
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
        global _extra_args_enable_log; \
            _extra_args_enable_log = True
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
        f'--pkg-config={_pkgconf_bin}',
    ]
    if not _extra_args_enable_log:
        args.append('--disable-logging')

    if _target_platform in ['linux', 'android']:
        _rpath = '\\$\\$ORIGIN:\\$\\$ORIGIN/../lib'
        args.extend([
            f"--extra-ldsoflags=-Wl,-rpath,'{_rpath}'",
            f"--extra-ldexeflags=-Wl,-rpath,'{_rpath}'",
        ])

    _ffmpeg_target_os = _target_platform
    if _target_platform == 'win-mingw':
        _ffmpeg_target_os = 'mingw64'
    if _target_platform in ['macosx', 'iphoneos', 'iphonesimulator']:
        _ffmpeg_target_os = 'darwin'
        args.append('--disable-coreimage')
        if _target_platform != 'macosx':
            args.append('--disable-programs')
    else:
        args.append(f'--host-cc={_host_cc}')

    if _target_platform == 'win-msvc':
        pass
    elif _target_platform != 'linux' or _cross_build_on_linux:
        args.extend([
            '--enable-cross-compile',
            f'--target-os={_ffmpeg_target_os}',
            f'--arch={_target_arch}',
        ])
        if _target_platform in ['linux', 'win-mingw', 'android']:
            args.extend([
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
    args = f"make -j {x.CPU_COUNT}"
    if bear := shutil.which('bear'): args = f"{bear} -- " + args
    x._util_func__subprocess(cwd=_pkg_buld_dir, env=BUILD_ENV, args=shlex.split(args), stdout=sp.DEVNULL)
def _build_step_02():
    if _target_platform not in ['iphoneos', 'iphonesimulator']:
        x._util_func__subprocess(cwd=_pkg_buld_dir, env=BUILD_ENV, args=['make', 'install-progs'])
    x._util_func__subprocess(cwd=_pkg_buld_dir, env=BUILD_ENV, args=['make', 'install-headers'])
    x._util_func__subprocess(cwd=_pkg_buld_dir, env=BUILD_ENV, args=['make', 'install-libs'])

    if _target_platform == 'win-msvc':
        return

    _ffmpeg_mergeso_sym_map: dict[str, None] = {}
    _ffmpeg_symbol_v = (Path(_subproj_src)).glob('**/*.v')
    for _v in _ffmpeg_symbol_v:
        _x = _v.read_text()
        _l = _x[_x.index('global:'):_x.index('local:')]
        for _s in _l.splitlines():
            if not _s.endswith(';'):
                continue
            _ffmpeg_mergeso_sym_map[_s.strip()[:-1]] = None
    _ffmpeg_mergeso_sym_l = _ffmpeg_mergeso_sym_map.keys()
    x.print_stderr(f'>>>> exported symbols: {_ffmpeg_mergeso_sym_l}')

    _ffmpeg_mergeso_sym_v = (Path(_pkg_inst_dir) / 'lib' / 'libffmpeg.v')
    with _ffmpeg_mergeso_sym_v.open('w', encoding='utf-8') as f:
        if _target_platform in ['linux', 'android']:
            f.write('{\n')
            f.write('  global:\n')
            for _rule in _ffmpeg_mergeso_sym_l:
                f.write(f'    {_rule};\n')
            f.write('  local:\n')
            f.write('    *;\n')
            f.write('};\n')
        elif _target_platform == 'win-mingw':
            _dll_sym_arg = f"{_nm} -a lib/*.a | grep ' T ' | cut -d ' ' -f 3"
            _dll_sym_all = x._util_func__subprocess(cwd=_pkg_inst_dir, collect_stdout=True, args=_dll_sym_arg, shell=True)
            f.write('LIBRARY libffmpeg\n')
            f.write('EXPORTS\n')
            for _sym in shlex.split(_dll_sym_all):
                if any(
                    ((_sym == _rule) or (_rule.endswith('*') and _sym.startswith(_rule[:-1]))) \
                        for _rule in _ffmpeg_mergeso_sym_l
                ): f.write(f'  {_sym}\n')
        else: # apple platform
            for _rule in _ffmpeg_mergeso_sym_l:
                f.write(f'_{_rule}\n')


    _ffmpeg_pkgconf_dir = (Path(_pkg_inst_dir) / 'lib' / 'pkgconfig')
    x._util_append_env_pkgconf_path(BUILD_ENV, (_ffmpeg_pkgconf_dir))
    _ffmpeg_mergeso_lib0 = x._util_func__subprocess(env=BUILD_ENV, collect_stdout=True, args=[_pkgconf_bin, '--libs', 'libavdevice'])
    _ffmpeg_mergeso_lib1 = shlex.split(_ffmpeg_mergeso_lib0)

    _ffmpeg_mergeso_libdir: list[str] = []
    _ffmpeg_mergeso_libffm: list[str] = []
    _ffmpeg_mergeso_libmac: list[str] = []
    _ffmpeg_mergeso_libext: list[str] = []
    _ffmpeg_mergeso_libstd: list[str] = []
    i = 0; c = len(_ffmpeg_mergeso_lib1)
    while i < c:
        _lib = _ffmpeg_mergeso_lib1[i]; i += 1
        if False:
            pass
        elif _lib.startswith('-L'):
            if _lib not in _ffmpeg_mergeso_libdir: _ffmpeg_mergeso_libdir.append(_lib)
        elif _lib in ['-lavdevice', '-lavfilter', '-lswscale', '-lavformat', '-lavcodec', '-lswresample', '-lavutil']:
            if _lib not in _ffmpeg_mergeso_libffm: _ffmpeg_mergeso_libffm.append(_lib)
        elif _lib in ['-lm', '-ldl', '-latomic', '-pthread']:
            if _lib not in _ffmpeg_mergeso_libstd: _ffmpeg_mergeso_libstd.append(_lib)
        elif _lib in ['-framework']:
            _lib = _ffmpeg_mergeso_lib1[i]; i += 1
            if _lib not in _ffmpeg_mergeso_libmac: _ffmpeg_mergeso_libmac.append(_lib)
        else:
            if _lib not in _ffmpeg_mergeso_libext: _ffmpeg_mergeso_libext.append(_lib)


    _ffmpeg_mergeso_out = ''; _ffmpeg_mergeso_cmd = []
    _ffmpeg_mergeso_cmd.extend(shlex.split(f"{_cc} {_cross_ldflags}"))
    if 'ccache' in _ffmpeg_mergeso_cmd[0]:
        _ffmpeg_mergeso_cmd = _ffmpeg_mergeso_cmd[1:]
    _ffmpeg_mergeso_cmd.extend(['-shared', '-v'])
    if _target_platform in ['linux', 'android']:
        _ffmpeg_mergeso_out = 'lib/libffmpeg.so'
        _ffmpeg_mergeso_cmd.extend(['-o', _ffmpeg_mergeso_out, f'-Wl,--soname={_ffmpeg_mergeso_out.split("/")[-1]}'])
        _ffmpeg_mergeso_cmd.extend([f'-Wl,--version-script={_ffmpeg_mergeso_sym_v.absolute().as_posix()}'])
        _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libdir)
        _ffmpeg_mergeso_cmd.extend(['-Wl,--whole-archive'])
        _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libffm)
        _ffmpeg_mergeso_cmd.extend(['-Wl,--no-whole-archive'])
        _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libext)
        _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libstd)
    elif _target_platform == 'win-mingw':
        _ffmpeg_mergeso_out = 'lib/libffmpeg.dll'
        _ffmpeg_mergeso_cmd.extend(['-o', _ffmpeg_mergeso_out])
        _ffmpeg_mergeso_cmd.extend([f'-Wl,--Xlink=/DEF:{_ffmpeg_mergeso_sym_v.absolute().as_posix()}'])
        _ffmpeg_mergeso_cmd.extend([f'-Wl,--output-def={_ffmpeg_mergeso_out.split(".")[0]}.def'])
        _ffmpeg_mergeso_cmd.extend([f'-Wl,--out-implib={_ffmpeg_mergeso_out.split(".")[0]}.lib'])
        _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libdir)
        _ffmpeg_mergeso_cmd.extend(['-Wl,--whole-archive'])
        _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libffm)
        _ffmpeg_mergeso_cmd.extend(['-Wl,--no-whole-archive'])
        _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libext)
        _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libstd)
    else: # apple platform
        _ffmpeg_mergeso_out = 'lib/libffmpeg.dylib'
        _ffmpeg_mergeso_cmd.extend(['-o', _ffmpeg_mergeso_out, '-install_name', _ffmpeg_mergeso_out.split("/")[-1]])
        _ffmpeg_mergeso_cmd.extend(['-Wl,-exported_symbols_list', _ffmpeg_mergeso_sym_v.absolute().as_posix()])
        _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libdir)
        for _lib in _ffmpeg_mergeso_libffm:
            _ffmpeg_mergeso_cmd.extend(['-Wl,-force_load', f'lib/lib{_lib[2:]}.a'])
        _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libext)
        _ffmpeg_mergeso_cmd.extend(_ffmpeg_mergeso_libstd)
        for _lib in _ffmpeg_mergeso_libmac:
            _ffmpeg_mergeso_cmd.extend(['-framework', _lib])
    x._util_func__subprocess(cwd=_pkg_inst_dir, env=BUILD_ENV, args=_ffmpeg_mergeso_cmd)

    _ffmpeg_dbgsym_out = f'{_ffmpeg_mergeso_out}.dbgsym'
    if _target_platform in ['linux', 'win-mingw', 'android']:
        x._util_func__subprocess(cwd=_pkg_inst_dir, env=BUILD_ENV, args=[
            _objcopy, '--only-keep-debug', _ffmpeg_mergeso_out, _ffmpeg_dbgsym_out
        ])
        x._util_func__subprocess(cwd=_pkg_inst_dir, env=BUILD_ENV, args=[
            _objcopy, '--strip-debug', '--strip-unneeded', _ffmpeg_mergeso_out
        ])
        x._util_func__subprocess(cwd=_pkg_inst_dir, env=BUILD_ENV, args=[
            _objcopy, f'--add-gnu-debuglink={_ffmpeg_dbgsym_out}', _ffmpeg_mergeso_out
        ])
    x._util_func__subprocess(cwd=_pkg_buld_dir, env=BUILD_ENV, args=['make', 'uninstall-libs'])
    x._util_func__subprocess(cwd=_pkg_buld_dir, env=BUILD_ENV, args=['make', 'uninstall-pkgconfig'])

    _pkgconf_content = '''
prefix=${pcfiledir}/../..
includedir=${prefix}/include
libdir=${prefix}/lib

Name: libffmpeg
Description: libffmpeg under lgpl
URL: https://github.com/valord577/nativepkgs
Version: @PKGCONFIG_VERSION@
Requires:
Cflags: -I${includedir}
Libs: -L${libdir} -lffmpeg
'''
    _pkgconf_content = _pkgconf_content.replace('@PKGCONFIG_VERSION@', x._util_get_pkg_version_desc(_target_pkg_name))

    _pkgconf = (Path(_ffmpeg_pkgconf_dir) / 'libffmpeg.pc'); \
        _pkgconf.parent.mkdir(parents=True, exist_ok=True)
    _pkgconf.write_text(_pkgconf_content)
