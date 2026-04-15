#!/usr/bin/env python3

# fmt: off

import sys
sys.dont_write_bytecode = True

from scripts import utils as x
# ----------------------------


import datetime as dt
import os
import shutil
import sys
import tempfile

from pathlib import Path
from typing import NoReturn, Union

if sys.version_info < (3, 6):
    raise RuntimeError(f'Required Python Interpreter ≥ 3.6')
if sys.prefix == sys.base_prefix:
    raise RuntimeError(f'Please run this script in a [virtual environment](https://docs.python.org/3/library/venv.html)')
if not os.getenv('VIRTUAL_ENV'):
    raise RuntimeError(f'Please activate the virtual environment first')



# ----------------------------
# optimize
#  - RelWithDebInfo (default)
#
# (Modules make their own decisions.)
# ----------------------------
# static or shared
# ----------------------------
PKG_TYPE = os.getenv('PKG_TYPE', 'static')
if PKG_TYPE not in ['static']: PKG_TYPE = 'shared'
# ----------------------------


class _ctx:
    def __init__(self, module: str):
        self.module = module

        self.target_plat = ''
        self.target_arch = ''
        self.target_libc = ''

        self.env_passthrough = {}

        self.android_api_level = os.getenv('ANDROID_API_LEVEL') or '30'

        self.win32_msvc_env_native: dict[str, str] = {}
        self.win32_msvc_env_target: dict[str, str] = {}

        self.extra_cmake: list[str] = []
        self.extra_meson: list[str] = []
        self.cross_build_enabled = False
        self.cross_target_triple = ''
        self.cross_pkgconfig_bin = ''

        self.cc = ''
        self.cxx = ''
        self.cpp = ''
        self.host_cc = ''
        self.host_cxx = ''
        self.host_cpp = ''
        self.cross_ldflags = ''
        self.sysroot = ''
        self._winres = ''
        self._ld = ''
        self._nm = ''
        self._ar = ''
        self._as = ''
        self._ranlib  = ''
        self._strip   = ''
        self._objcopy = ''

        self.extra_cmake.extend(['-D', 'CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON'])
        self.extra_cmake.extend(['-D', 'CMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON'])
        self.extra_cmake.extend(['-D', 'CMAKE_INSTALL_LIBDIR:PATH=lib'])

        self.extra_meson.extend(['--pkgconfig.relocatable'])
        self.extra_meson.extend(['--libdir', 'lib'])
        self.extra_meson.extend(['--python.install-env', 'venv'])
        self.extra_meson.extend(['--wrap-mode', 'nofallback'])
        self.extra_meson.extend(['-Db_pie=true'])
        self.extra_meson.extend(['-Db_ndebug=true'])

        self.ccache = shutil.which('ccache') or ''
        if self.ccache:
            self.extra_cmake.extend(['-D', 'CMAKE_C_COMPILER_LAUNCHER=ccache'])
            self.extra_cmake.extend(['-D', 'CMAKE_CXX_COMPILER_LAUNCHER=ccache'])

    def getenv(self) -> dict:
        _target_archlibc = self.target_arch
        if self.target_libc:
            _target_archlibc = f'{self.target_arch}-{self.target_libc}'
        _3rd_deps_dir = (Path(x.PROJ_ROOT) / f'.lib.{self.target_plat}.{_target_archlibc}').absolute().as_posix()
        _pkg_buld_dir = (Path(x.PROJ_ROOT) / 'tmp' / self.module / self.target_plat / _target_archlibc).absolute().as_posix()
        _pkg_inst_dir = (Path(x.PROJ_ROOT) / 'out' / self.module / self.target_plat / _target_archlibc).absolute().as_posix()
        if x.ON_GITLAB_CI or x.ON_GITHUB_CI:
            _pkg_inst_dir = os.getenv('INST_DIR') or _pkg_inst_dir

        _subproj_src = (Path(x.PROJ_ROOT) / '.deps' / self.module).absolute().as_posix()
        _subproj_src_patches = (Path(x.PROJ_ROOT) / 'patches' / self.module).absolute().as_posix()


        self.extra_cmake.extend(['-B', _pkg_buld_dir])
        self.extra_cmake.extend(['-D', f'CMAKE_INSTALL_PREFIX={_pkg_inst_dir}'])

        self.extra_meson.extend(['--prefix', _pkg_inst_dir])

        return {
            **self.env_passthrough,
            **{
                'PKG_NAME': self.module,
                'PKG_TYPE': PKG_TYPE,
                'PKG_PLATFORM': self.target_plat,
                'PKG_ARCH': self.target_arch,
                'PKG_LIBC': self.target_libc,
                'PKG_ARCH_LIBC': _target_archlibc,

                'EXTRA_CMAKE': self.extra_cmake,
                'EXTRA_MESON': self.extra_meson,

                'CROSS_PKGCONFIG_BIN': self.cross_pkgconfig_bin,
                'CROSS_BUILD_ENABLED': self.cross_build_enabled,
                'CROSS_TARGET_TRIPLE': self.cross_target_triple,

                '3RD_DEPS_DIR': _3rd_deps_dir,
                'PKG_BULD_DIR': _pkg_buld_dir,
                'PKG_INST_DIR': _pkg_inst_dir,

                'SUBPROJ_SRC': _subproj_src,
                'SUBPROJ_SRC_PATCHES': _subproj_src_patches,


                'ANDROID_API_LEVEL': self.android_api_level,

                'WIN32_MSVC_ENV_NATIVE': self.win32_msvc_env_native,
                'WIN32_MSVC_ENV_TARGET': self.win32_msvc_env_target,


                'CC': self.cc,
                'CXX': self.cxx,
                'CPP': self.cpp,
                'HOSTCC': self.host_cc,
                'HOSTCXX': self.host_cxx,
                'HOSTCPP': self.host_cpp,
                'CROSS_LDFLAGS': self.cross_ldflags,
                'SYSROOT': self.sysroot,
                'WINDRES': self._winres,
                'LD': self._ld,
                'NM': self._nm,
                'AR': self._ar,
                'AS': self._as,
                'RANLIB': self._ranlib,
                'STRIP': self._strip,
                'OBJCOPY': self._objcopy,
            },
        }


def _setctx_linux(
    ctx: _ctx, _native: bool, _tuple: tuple[str, ...],
):
    def _get_linux_libc_type() -> str:
        import mmap

        _libc_type = ''
        with open(sys.executable, 'rb') as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
                if -1 != m.find(b'GLIBC_'):
                    _libc_type = 'gnu'
                elif -1 != m.find(b'musl-'):
                    _libc_type = 'musl'
        if not _libc_type:
            raise NotImplementedError(f'unknown the implementation of libc')
        return _libc_type


    ctx.host_cc  = shutil.which('clang')
    ctx.host_cxx = shutil.which('clang++')
    ctx.host_cpp = shutil.which('clang-cpp')
    if (not ctx.host_cc) or (not ctx.host_cxx) or (not ctx.host_cpp):
        raise NotImplementedError(f'only supports the LLVM toolchain')

    ctx.cc  = f'{ctx.ccache} {ctx.host_cc}'
    ctx.cxx = f'{ctx.ccache} {ctx.host_cxx}'
    ctx.cpp = f'{ctx.host_cpp}'
    ctx._ld = shutil.which('ld.lld')
    ctx._nm = shutil.which('llvm-nm')
    ctx._ar = shutil.which('llvm-ar')
    ctx._as = shutil.which('llvm-as')
    ctx._ranlib  = shutil.which('llvm-ranlib')
    ctx._strip   = shutil.which('llvm-strip')
    ctx._objcopy = shutil.which('llvm-objcopy')

    if _native:
        ctx.target_arch = x.NATIVE_ARCH
        if not (ctx.target_arch in ['arm64', 'amd64']):
            raise NotImplementedError(f'unsupported target arch: {ctx.target_arch}')
        ctx.target_libc = _get_linux_libc_type()
    else:
        CROSS_TOOLCHAIN_ROOT = x._util_get_cross_toolchain_dir()

        ctx.cross_build_enabled = True
        ctx.target_arch = _tuple[2]
        ctx.target_libc = _tuple[3]
        if ctx.target_arch == 'arm64':
            ctx.cross_target_triple = f'aarch64-unknown-linux-{ctx.target_libc}'
        if ctx.target_arch == 'amd64':
            ctx.cross_target_triple = f'x86_64-pc-linux-{ctx.target_libc}'
        if ctx.target_arch == 'armv7':
            ctx.cross_target_triple = f'arm-unknown-linux-{ctx.target_libc}'
        ctx.sysroot = (Path(CROSS_TOOLCHAIN_ROOT) / ctx.cross_target_triple).absolute().as_posix()

        _cflags = f'--target={ctx.cross_target_triple} --gcc-toolchain={ctx.sysroot}/usr --sysroot={ctx.sysroot}'
        if ctx.target_arch == 'armv7':
            _cflags += ' -march=armv7-a -mfpu=neon-vfpv4'
        ctx.cc  += f' {_cflags}'
        ctx.cxx += f' {_cflags}'
        ctx.cpp += f' {_cflags}'

        ctx.cross_ldflags = f'-fuse-ld=lld --sysroot={ctx.sysroot}'


        # cmake toolchain file
        CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE = os.getenv('CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE')
        if not CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE:
            CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE = (Path(CROSS_TOOLCHAIN_ROOT) / 'toolchain-cmake-template').absolute().as_posix()
        CROSS_TOOLCHAIN_FILE_CMAKE = f'{CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE}.{ctx.cross_target_triple}'
        ctx.extra_cmake.extend(["-D", f"CMAKE_TOOLCHAIN_FILE={CROSS_TOOLCHAIN_FILE_CMAKE}"])
        # meson toolchain file
        CROSS_TOOLCHAIN_FILE_PREFIX_MESON = os.getenv('CROSS_TOOLCHAIN_FILE_PREFIX_MESON')
        if not CROSS_TOOLCHAIN_FILE_PREFIX_MESON:
            CROSS_TOOLCHAIN_FILE_PREFIX_MESON = (Path(CROSS_TOOLCHAIN_ROOT) / 'toolchain-meson-template').absolute().as_posix()
        CROSS_TOOLCHAIN_FILE_MESON = f'{CROSS_TOOLCHAIN_FILE_PREFIX_MESON}.{ctx.cross_target_triple}'
        ctx.extra_meson.extend(["--cross-file", CROSS_TOOLCHAIN_FILE_MESON])
        # pkgconf bin
        CROSS_TOOLCHAIN_PKGCONF_PREFIX = os.getenv('CROSS_TOOLCHAIN_PKGCONF_PREFIX')
        if not CROSS_TOOLCHAIN_PKGCONF_PREFIX:
            CROSS_TOOLCHAIN_PKGCONF_PREFIX = (Path(CROSS_TOOLCHAIN_ROOT) / 'pkgconf-wrapper').absolute().as_posix()
        ctx.cross_pkgconfig_bin = f'{CROSS_TOOLCHAIN_PKGCONF_PREFIX}.{ctx.cross_target_triple}'
def _setctx_apple(
    ctx: _ctx, _native: bool, _tuple: tuple[str, ...],
):
    if ctx.ccache:
        ctx.extra_cmake.extend(['-D', 'CMAKE_OBJC_COMPILER_LAUNCHER=ccache'])
        ctx.extra_cmake.extend(['-D', 'CMAKE_OBJCXX_COMPILER_LAUNCHER=ccache'])

    if _native:
        ctx.target_arch = x.NATIVE_PLAT
        if not (ctx.target_arch in ['arm64', 'amd64']):
            raise NotImplementedError(f'unsupported target arch: {ctx.target_arch}')
    else:
        ctx.target_plat = _tuple[0]
        ctx.target_arch = _tuple[1]
        ctx.cross_build_enabled = True

    _target_arch = ctx.target_arch
    if _target_arch == 'amd64':
        _target_arch = 'x86_64'

    _min_version_deployment = '11'
    if ctx.target_plat != 'macosx':
        _min_version_deployment = '12'

    _min_version_target_flag = ''
    if ctx.target_plat == 'macosx':
        _min_version_target_flag = 'macosx'
        ctx.extra_cmake.extend(['-D', 'CMAKE_SYSTEM_NAME=Darwin'])
    elif ctx.target_plat == 'iphoneos':
        _min_version_target_flag = 'iphoneos'
        ctx.extra_cmake.extend(['-D', 'CMAKE_SYSTEM_NAME=iOS'])
    elif ctx.target_plat == 'iphonesimulator':
        _min_version_target_flag = 'ios-simulator'
        ctx.extra_cmake.extend(['-D', 'CMAKE_SYSTEM_NAME=iOS'])

    ctx.host_cc  = x._util_func__subprocess(collect_stdout=True, args=['xcrun', '-f', 'clang'])[:-1]
    ctx.host_cxx = x._util_func__subprocess(collect_stdout=True, args=['xcrun', '-f', 'clang++'])[:-1]

    ctx.sysroot = x._util_func__subprocess(collect_stdout=True, args=['xcrun', '--sdk', ctx.target_plat, '--show-sdk-path'])[:-1]
    ctx.cross_ldflags = f'-arch {_target_arch} -m{_min_version_target_flag}-version-min={_min_version_deployment}'
    ctx.cc  = f"{ctx.ccache} {ctx.host_cc}  {ctx.cross_ldflags} -isysroot {ctx.sysroot}"
    ctx.cxx = f"{ctx.ccache} {ctx.host_cxx} {ctx.cross_ldflags} -isysroot {ctx.sysroot}"


    crossfiles_dir = (Path(x.PROJ_ROOT) / 'crossfiles' / 'apple').absolute().as_posix()
    # pkgconf bin
    ctx.cross_pkgconfig_bin = (Path(crossfiles_dir) / 'pkgconf-wrapper').absolute().as_posix()
    # meson toolchain file
    CROSS_TOOLCHAIN_FILE_MESON_DST = (Path(crossfiles_dir) / f'toolchain-meson-template.{ctx.target_plat}-{_target_arch}').absolute().as_posix()
    CROSS_TOOLCHAIN_FILE_MESON_SRC = f'{CROSS_TOOLCHAIN_FILE_MESON_DST}.tmpl'
    _content = Path(CROSS_TOOLCHAIN_FILE_MESON_SRC).read_text()
    _content = _content.replace('__SYSROOT__', ctx.sysroot)
    _content = _content.replace('__EXTRA_FLAGS__', f"'-m{_min_version_target_flag}-version-min={_min_version_deployment}'")
    Path(CROSS_TOOLCHAIN_FILE_MESON_DST).write_text(_content)
    ctx.extra_meson.extend(["--cross-file", CROSS_TOOLCHAIN_FILE_MESON_DST])
    # cmake toolchain file
    ctx.extra_cmake.extend(['-D',  'CMAKE_CROSSCOMPILING:BOOL=TRUE'])
    ctx.extra_cmake.extend(['-D', f'CMAKE_C_COMPILER={ctx.host_cc}'])
    ctx.extra_cmake.extend(['-D', f'CMAKE_CXX_COMPILER={ctx.host_cxx}'])
    ctx.extra_cmake.extend(['-D', f'CMAKE_OBJC_COMPILER={ctx.host_cc}'])
    ctx.extra_cmake.extend(['-D', f'CMAKE_OBJCXX_COMPILER={ctx.host_cxx}'])
    ctx.extra_cmake.extend(['-D', f'CMAKE_SYSTEM_PROCESSOR={_target_arch}'])
    ctx.extra_cmake.extend(['-D', f'CMAKE_OSX_ARCHITECTURES={_target_arch}'])
    ctx.extra_cmake.extend(['-D', f'CMAKE_OSX_SYSROOT={ctx.target_plat}'])
    ctx.extra_cmake.extend(['-D', f'CMAKE_OSX_DEPLOYMENT_TARGET={_min_version_deployment}'])
    ctx.extra_cmake.extend(['-D',  'CMAKE_MACOSX_BUNDLE:BOOL=0'])
    ctx.extra_cmake.extend(['-D', f'PKG_CONFIG_EXECUTABLE={ctx.cross_pkgconfig_bin}'])

def _setctx_win32_mingw(
    ctx: _ctx, _native: bool, _tuple: tuple[str, ...],
):
    CROSS_TOOLCHAIN_ROOT = x._util_get_cross_toolchain_dir()

    ctx.cross_build_enabled = True
    ctx.target_arch = _tuple[1]
    if ctx.target_arch == 'arm64':
        ctx.cross_target_triple = f'aarch64-w64-mingw32'
    if ctx.target_arch == 'amd64':
        ctx.cross_target_triple = f'x86_64-w64-mingw32'
    _target_arch = ctx.cross_target_triple[:-len('-w64-mingw32')]
    ctx.sysroot = (Path(CROSS_TOOLCHAIN_ROOT) / ctx.cross_target_triple).absolute().as_posix()

    ctx.host_cc  = (Path(CROSS_TOOLCHAIN_ROOT) / 'bin' / 'clang').absolute().as_posix()
    ctx.host_cxx = (Path(CROSS_TOOLCHAIN_ROOT) / 'bin' / 'clang++').absolute().as_posix()
    ctx.host_cpp = (Path(CROSS_TOOLCHAIN_ROOT) / 'bin' / 'clang-cpp').absolute().as_posix()
    ctx.cc  = f"{ctx.ccache} {(Path(CROSS_TOOLCHAIN_ROOT) / 'bin' / f'{ctx.cross_target_triple}-clang').absolute().as_posix()}"
    ctx.cxx = f"{ctx.ccache} {(Path(CROSS_TOOLCHAIN_ROOT) / 'bin' / f'{ctx.cross_target_triple}-clang++').absolute().as_posix()}"
    ctx._winres  = (Path(CROSS_TOOLCHAIN_ROOT) / 'bin' / f'{ctx.cross_target_triple}-windres').absolute().as_posix()

    ctx._ld = (Path(CROSS_TOOLCHAIN_ROOT) / 'bin' / f'{ctx.cross_target_triple}-ld').absolute().as_posix()
    ctx._nm = (Path(CROSS_TOOLCHAIN_ROOT) / 'bin' / f'{ctx.cross_target_triple}-nm').absolute().as_posix()
    ctx._ar = (Path(CROSS_TOOLCHAIN_ROOT) / 'bin' / f'{ctx.cross_target_triple}-ar').absolute().as_posix()
    ctx._as = (Path(CROSS_TOOLCHAIN_ROOT) / 'bin' / f'{ctx.cross_target_triple}-as').absolute().as_posix()
    ctx._ranlib  = (Path(CROSS_TOOLCHAIN_ROOT) / 'bin' / f'{ctx.cross_target_triple}-ranlib').absolute().as_posix()
    ctx._strip   = (Path(CROSS_TOOLCHAIN_ROOT) / 'bin' / f'{ctx.cross_target_triple}-strip').absolute().as_posix()
    ctx._objcopy = (Path(CROSS_TOOLCHAIN_ROOT) / 'bin' / f'{ctx.cross_target_triple}-objcopy').absolute().as_posix()


    # cmake toolchain file
    CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE = os.getenv('CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE')
    if not CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE:
        CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE = (Path(CROSS_TOOLCHAIN_ROOT) / 'toolchain-cmake-template').absolute().as_posix()
    CROSS_TOOLCHAIN_FILE_CMAKE = f'{CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE}.{_target_arch}'
    ctx.extra_cmake.extend(["-D", f"CMAKE_TOOLCHAIN_FILE={CROSS_TOOLCHAIN_FILE_CMAKE}"])
    # meson toolchain file
    CROSS_TOOLCHAIN_FILE_PREFIX_MESON = os.getenv('CROSS_TOOLCHAIN_FILE_PREFIX_MESON')
    if not CROSS_TOOLCHAIN_FILE_PREFIX_MESON:
        CROSS_TOOLCHAIN_FILE_PREFIX_MESON = (Path(CROSS_TOOLCHAIN_ROOT) / 'toolchain-meson-template').absolute().as_posix()
    CROSS_TOOLCHAIN_FILE_MESON = f'{CROSS_TOOLCHAIN_FILE_PREFIX_MESON}.{_target_arch}'
    ctx.extra_meson.extend(["--cross-file", CROSS_TOOLCHAIN_FILE_MESON])
    # pkgconf bin
    CROSS_TOOLCHAIN_PKGCONF_PREFIX = os.getenv('CROSS_TOOLCHAIN_PKGCONF_PREFIX')
    if not CROSS_TOOLCHAIN_PKGCONF_PREFIX:
        CROSS_TOOLCHAIN_PKGCONF_PREFIX = (Path(CROSS_TOOLCHAIN_ROOT) / 'pkgconf-wrapper').absolute().as_posix()
    ctx.cross_pkgconfig_bin = f'{CROSS_TOOLCHAIN_PKGCONF_PREFIX}.{_target_arch}'
def _setctx_win32_msvc(
    ctx: _ctx, _native: bool, _tuple: tuple[str, ...],
):
    ctx.extra_cmake.extend(['-G', 'Ninja'])

    ctx.target_arch = x.NATIVE_ARCH
    if not _native:
        ctx.target_arch = _tuple[1]
    ctx.cross_build_enabled = (ctx.target_arch != x.NATIVE_ARCH)
    if ctx.target_arch == 'arm64':
        ctx.cross_target_triple = f'aarch64-pc-windows-msvc'
    if ctx.target_arch == 'amd64':
        ctx.cross_target_triple = f'x86_64-pc-windows-msvc'


    def _msvc_env_json_dump(dst: str, vs_path: str, _vs_devshell_dll: str, target_arch: str):
        # Only supports access to the VS DevShell from PowerShell
        #  - https://learn.microsoft.com/visualstudio/ide/reference/command-prompt-powershell#developer-powershell
        _vs_devshell_arg = f'-host_arch={x.NATIVE_ARCH} -arch={target_arch}'

        _pwsh_script_blk  = f'Import-Module "{_vs_devshell_dll}"; '
        _pwsh_script_blk += f'Enter-VsDevShell -VsInstallPath "{vs_path}" -SkipAutomaticLocation -DevCmdArguments "{_vs_devshell_arg}"; '
        _pwsh_script_blk += f'Get-ChildItem Env: | Select-Object -Property Name,Value | ConvertTo-Json -Depth 1  1>{dst}; '
        x._util_func__subprocess(['pwsh',
            '-WorkingDirectory', x.PROJ_ROOT,
            '-NonInteractive',
            '-NoProfileLoadTime',
            '-ExecutionPolicy', 'Bypass',
            '-Command', _pwsh_script_blk
        ])

    _vs_search_path: list[str] = []
    if _user_def := os.getenv('MSVC_INSTALL_DIR', ''):
        _vs_search_path.append(_user_def)
    else:
        # auto search vs install dir
        _msvc_install_dir = [
            'C:/Program Files/Microsoft Visual Studio',
            'C:/Program Files (x86)/Microsoft Visual Studio',
        ]
        _msvc_product_arr = [
            '2022/BuildTools',    '2019/BuildTools',
            '2022/Community',     '2019/Community',
            '2022/Professional',  '2019/Professional',
            '2022/Enterprise',    '2019/Enterprise',
        ]
        for _dir in _msvc_install_dir:
            for _product in _msvc_product_arr:
                _vs_search_path.append(f'{_dir}/{_product}')


    _vs_path = ''; _vs_devshell_dll = ''
    for _dir in _vs_search_path:
        _dll = (Path(_dir) / 'Common7' / 'Tools' / 'Microsoft.VisualStudio.DevShell.dll')
        if _dll.exists():
            _vs_path = _dir; _vs_devshell_dll = _dll.absolute().as_posix()
            break
    if (not _vs_path) or (not _vs_devshell_dll):
        raise NotImplementedError('Failed to search MSVC environment')

    _msvc_env_json_native = (Path(x.PROJ_ROOT) / '.msvc_env_native.json').absolute().as_posix()
    _msvc_env_json_target = (Path(x.PROJ_ROOT) / '.msvc_env_target.json').absolute().as_posix()
    _msvc_env_json_dump(_msvc_env_json_native, _vs_path, _vs_devshell_dll, x.NATIVE_ARCH)
    _msvc_env_json_dump(_msvc_env_json_target, _vs_path, _vs_devshell_dll, ctx.target_arch)


    def _msvc_env_json2dict(_dict: dict[str, str], src: str):
        _list = x._util_load_json_from_file(src)
        for _kv in _list:
            _dict[_kv['Name']] = _kv['Value']
    _msvc_env_json2dict(ctx.win32_msvc_env_native, _msvc_env_json_native)
    _msvc_env_json2dict(ctx.win32_msvc_env_target, _msvc_env_json_target)

    _msvc_native_toolchain_dir = ctx.win32_msvc_env_native['VCToolsInstallDir']; \
        _msvc_native_arch = ctx.win32_msvc_env_native['VSCMD_ARG_HOST_ARCH']
    ctx.host_cc = ctx.host_cxx = (
        Path(_msvc_native_toolchain_dir) / 'bin' / f'host{_msvc_native_arch}' / _msvc_native_arch / 'cl.exe'
    ).absolute().as_posix()
def _setctx_android(
    ctx: _ctx, _native: bool, _tuple: tuple[str, ...],
):
    ANDROID_FLEXIBLE_PAGE_SIZES = os.getenv('ANDROID_FLEXIBLE_PAGE_SIZES', '')
    if ANDROID_FLEXIBLE_PAGE_SIZES:
        ANDROID_FLEXIBLE_PAGE_SIZES_ALLOWED = ['16k']
        if ANDROID_FLEXIBLE_PAGE_SIZES in ANDROID_FLEXIBLE_PAGE_SIZES_ALLOWED:
            ctx.target_libc = ANDROID_FLEXIBLE_PAGE_SIZES
            ANDROID_FLEXIBLE_PAGE_SIZES = f'.{ANDROID_FLEXIBLE_PAGE_SIZES}'
        else:
            raise RuntimeError(f'unknown page sizes: `{ANDROID_FLEXIBLE_PAGE_SIZES}`, allowed: `{ANDROID_FLEXIBLE_PAGE_SIZES_ALLOWED}`')

    CROSS_TOOLCHAIN_ROOT = x._util_get_cross_toolchain_dir()
    _toolchains_dir = (Path(CROSS_TOOLCHAIN_ROOT) / 'toolchains' / 'llvm' / 'prebuilt' / 'linux-x86_64').absolute().as_posix()


    ctx.cross_build_enabled = True
    ctx.target_arch = _tuple[1]
    if ctx.target_arch == 'arm64':
        if int(ctx.android_api_level) < 21: ctx.android_api_level = '21'
        ctx.cross_target_triple = f'aarch64-linux-android{ctx.android_api_level}'
    if ctx.target_arch == 'armv7':
        ctx.cross_target_triple = f'armv7a-linux-androideabi{ctx.android_api_level}'
    if ctx.target_arch == 'amd64':
        if int(ctx.android_api_level) < 21: ctx.android_api_level = '21'
        ctx.cross_target_triple = f'x86_64-linux-android{ctx.android_api_level}'
    ctx.sysroot = (Path(_toolchains_dir) / 'sysroot').absolute().as_posix()


    ctx.cross_ldflags = ''
    if ANDROID_FLEXIBLE_PAGE_SIZES == '.16k':
        ctx.cross_ldflags += ' -Wl,-z,max-page-size=16384'
    _cflags = ''
    if ctx.target_arch == 'armv7':
        _cflags += ' -march=armv7-a -mfpu=neon-vfpv4'

    ctx.host_cc  = (Path(_toolchains_dir) / 'bin' / 'clang').absolute().as_posix()
    ctx.host_cxx = (Path(_toolchains_dir) / 'bin' / 'clang++').absolute().as_posix()
    ctx.host_cpp = (Path(_toolchains_dir) / 'bin' / 'clang-cpp').absolute().as_posix()
    ctx.cc  = f"{ctx.ccache} {(Path(_toolchains_dir) / 'bin' / f'{ctx.cross_target_triple}-clang').absolute().as_posix()}   {_cflags}"
    ctx.cxx = f"{ctx.ccache} {(Path(_toolchains_dir) / 'bin' / f'{ctx.cross_target_triple}-clang++').absolute().as_posix()} {_cflags}"

    ctx._ld = (Path(_toolchains_dir) / 'bin' / 'ld.lld').absolute().as_posix()
    ctx._nm = (Path(_toolchains_dir) / 'bin' / 'llvm-nm').absolute().as_posix()
    ctx._ar = (Path(_toolchains_dir) / 'bin' / 'llvm-ar').absolute().as_posix()
    ctx._as = (Path(_toolchains_dir) / 'bin' / 'llvm-as').absolute().as_posix()
    ctx._ranlib  = (Path(_toolchains_dir) / 'bin' / 'llvm-ranlib').absolute().as_posix()
    ctx._strip   = (Path(_toolchains_dir) / 'bin' / 'llvm-strip').absolute().as_posix()
    ctx._objcopy = (Path(_toolchains_dir) / 'bin' / 'llvm-objcopy').absolute().as_posix()


    # pkgconf bin
    CROSS_TOOLCHAIN_PKGCONF_PREFIX = os.getenv('CROSS_TOOLCHAIN_PKGCONF_PREFIX')
    if not CROSS_TOOLCHAIN_PKGCONF_PREFIX:
        CROSS_TOOLCHAIN_PKGCONF_PREFIX = (Path(CROSS_TOOLCHAIN_ROOT) / 'pkgconf-wrapper').absolute().as_posix()
    ctx.cross_pkgconfig_bin = f'{CROSS_TOOLCHAIN_PKGCONF_PREFIX}.{ctx.cross_target_triple[:-len(ctx.android_api_level)]}'
    # cmake toolchain file
    CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE = os.getenv('CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE')
    if not CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE:
        CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE = (Path(CROSS_TOOLCHAIN_ROOT) / 'toolchain-cmake-template').absolute().as_posix()
    CROSS_TOOLCHAIN_FILE_CMAKE = f'{CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE}{ANDROID_FLEXIBLE_PAGE_SIZES}.{ctx.target_arch}'
    ctx.extra_cmake.extend(["-D", f"CMAKE_TOOLCHAIN_FILE={CROSS_TOOLCHAIN_FILE_CMAKE}"])
    # ******* ******* ******* ******* ******* ******* ******* ******* *******
    #ctx.extra_cmake.extend(["-D", f"CMAKE_SYSTEM_NAME=Android"])
    #ctx.extra_cmake.extend(["-D", f"CMAKE_SYSTEM_VERSION={ctx.android_api_level}"])
    #ctx.extra_cmake.extend(["-D", f"CMAKE_ANDROID_ARCH_ABI=armeabi-v7a"])
    #ctx.extra_cmake.extend(["-D", f"CMAKE_ANDROID_NDK={CROSS_TOOLCHAIN_ROOT}"])
    #if ctx.target_arch == 'armv7':
    #    ctx.extra_cmake.extend(["-D", "CMAKE_ANDROID_ARM_MODE:BOOL=1"])
    #    ctx.extra_cmake.extend(["-D", "CMAKE_ANDROID_ARM_NEON:BOOL=1"])
    #ctx.extra_cmake.extend(['-D', f"PKG_CONFIG_EXECUTABLE={ctx.cross_pkgconfig_bin}"])
    # ******* ******* ******* ******* ******* ******* ******* ******* *******
    # meson toolchain file
    CROSS_TOOLCHAIN_FILE_PREFIX_MESON = os.getenv('CROSS_TOOLCHAIN_FILE_PREFIX_MESON')
    if not CROSS_TOOLCHAIN_FILE_PREFIX_MESON:
        CROSS_TOOLCHAIN_FILE_PREFIX_MESON = (Path(CROSS_TOOLCHAIN_ROOT) / 'toolchain-meson-template').absolute().as_posix()
    CROSS_TOOLCHAIN_FILE_MESON_SRC = f'{CROSS_TOOLCHAIN_FILE_PREFIX_MESON}{ANDROID_FLEXIBLE_PAGE_SIZES}.{ctx.target_arch}.tmpl'
    CROSS_TOOLCHAIN_FILE_MESON_DST = (Path(tempfile.gettempdir()) / f'{ctx.target_plat}-toolchain-meson-template{ANDROID_FLEXIBLE_PAGE_SIZES}.{ctx.target_arch}').absolute().as_posix()
    _content = Path(CROSS_TOOLCHAIN_FILE_MESON_SRC).read_text()
    _content = _content.replace('__CROSS_TOOLCHAIN_ROOT__', CROSS_TOOLCHAIN_ROOT)
    _content = _content.replace('__ANDROID_API_LEVEL__', ctx.android_api_level)
    Path(CROSS_TOOLCHAIN_FILE_MESON_DST).write_text(_content)
    ctx.extra_meson.extend(["--cross-file", CROSS_TOOLCHAIN_FILE_MESON_DST])


_targets = {
    'linux': {
        'native': True,
        'hostos': ('linux', ),
        'setctx': _setctx_linux,
        'tuples': [
            ('linux', 'crossbuild', 'amd64', 'gnu'),
            ('linux', 'crossbuild', 'arm64', 'gnu'),
            ('linux', 'crossbuild', 'armv7', 'gnueabihf'),
            ('linux', 'crossbuild', 'amd64', 'musl'),
            ('linux', 'crossbuild', 'arm64', 'musl'),
            ('linux', 'crossbuild', 'armv7', 'musleabihf'),
        ],
    },
    'macosx': {
        'native': True,
        'hostos': ('darwin', ),
        'setctx': _setctx_apple,
        'tuples': [
            ('macosx', 'arm64'),
            ('macosx', 'amd64'),
        ],
    },
    'iphoneos': {
        'native': False,
        'hostos': ('darwin', ),
        'setctx': _setctx_apple,
        'tuples': [
            ('iphoneos', 'arm64'),
        ],
    },
    'iphonesimulator': {
        'native': False,
        'hostos': ('darwin', ),
        'setctx': _setctx_apple,
        'tuples': [
            ('iphonesimulator', 'arm64'),
            ('iphonesimulator', 'amd64'),
        ],
    },
    'win-msvc': {
        'native': True,
        'hostos': ('windows', ),
        'setctx': _setctx_win32_msvc,
        'tuples': [
            ('win-msvc', 'arm64'),
            ('win-msvc', 'amd64'),
        ],
    },
    'win-mingw': {
        'native': False,
        'hostos': ('linux', ),
        'setctx': _setctx_win32_mingw,
        'tuples': [
            ('win-mingw', 'arm64'),
            ('win-mingw', 'amd64'),
        ],
    },
    'android': {
        'native': False,
        'hostos': ('linux', 'amd64'),
        'setctx': _setctx_android,
        'tuples': [
            ('android', 'arm64'),
            ('android', 'armv7'),
            ('android', 'amd64'),
        ],
    },
}

def show_help(exitcode = 1) -> NoReturn:
    _native_flag_width = 0
    for k, v in _targets.items():
        _width = len(k) + 1
        if v['native'] and (_width > _native_flag_width):
            _native_flag_width = _width

    _targets_help_str = ''
    for k, v in _targets.items():
        _targets_help_str += f'    {k.ljust(_native_flag_width)}{"(* native)" if v["native"] else ""}\n'
        for tgt in v['tuples']:
            _targets_help_str += f'        {" ".join(tgt[1:])}\n'

    help_str  = f'Usage: {sys.argv[0]} -h|--help\n'
    help_str += f'Usage: {sys.argv[0]} [target] -m|--module <module>\n\n'
    help_str += f'Target Options:\n{_targets_help_str}\n'
    x.print_stderr(help_str[:-1])
    sys.exit(exitcode)


if __name__ == "__main__":
    argv_tgt: list[str] = []; argv_mod: str = ''
    argv = sys.argv[1:]; argc = len(argv); i = 0
    while i < argc:
        arg = argv[i]; i += 1
        if False:
            pass
        elif arg.startswith('-h') or arg.startswith('--help'):
            show_help(0)  # exited
        elif arg.startswith('-m') or arg.startswith('--module'):
            argv_mod = argv[i]; i += 1
        else:
            argv_tgt.append(arg)
    if not argv_mod:
        raise RuntimeError(f'Please declare the module to be built')

    argc_tgt = len(argv_tgt)
    if argc_tgt < 1:
        if False:
            pass
        elif x.NATIVE_PLAT == 'linux':
            argc_tgt +=1; argv_tgt.append('linux')
        elif x.NATIVE_PLAT == 'darwin':
            argc_tgt +=1; argv_tgt.append('macosx')
        elif x.NATIVE_PLAT == 'windows':
            argc_tgt +=1; argv_tgt.append('win-msvc')

    ctx = _ctx(module=argv_mod)
    ctx.target_plat = argv_tgt[0]
    _target = _targets.get(ctx.target_plat)
    if not _target:
        raise NotImplementedError(f'unsupported target platform: {ctx.target_plat}')
    _hostos = _target['hostos']
    if not isinstance(_hostos, tuple) \
        or \
        (len(_hostos) not in [1, 2]) \
        or \
        ((len(_hostos) == 1) and (
            _hostos[0] != x.NATIVE_PLAT
        )) \
        or \
        ((len(_hostos) == 2) and (
            _hostos[0] != x.NATIVE_PLAT or _hostos[1] != x.NATIVE_ARCH
        )):
        raise NotImplementedError(f'unsupported host os: {_hostos}')


    _tuple: Union[tuple[str, ...], None] = None
    if argc_tgt > 1:
        # check target tuple
        _tuple = tuple(argv_tgt)
        if not (_tuple in _target['tuples']):
            raise NotImplementedError(f'unsupported target tuple: {_tuple}')
    _is_native_build = ((argc_tgt == 1) and (_target['native']))
    if (not _is_native_build) and (not _tuple):
        raise NotImplementedError(f'unsupported native build: {ctx.target_plat}')
    _target['setctx'](ctx, _is_native_build, _tuple)


    build_env = ctx.getenv()
    _subproj_src  = build_env['SUBPROJ_SRC']
    _pkg_buld_dir = build_env['PKG_BULD_DIR']
    _pkg_inst_dir = build_env['PKG_INST_DIR']

    if _subproj_src:
        os.makedirs(_subproj_src, exist_ok=True)
    shutil.rmtree(_pkg_buld_dir, ignore_errors=True); \
        os.makedirs(_pkg_buld_dir, exist_ok=True)
    shutil.rmtree(_pkg_inst_dir, ignore_errors=True); \
        os.makedirs(_pkg_inst_dir, exist_ok=True)

    build_steps = x._util_load_module(f'modules.{argv_mod}', ['module_init']).module_init(build_env)
    for func in build_steps:
        func()
    if not x.ON_CODE_EDIT:
        x._util_func__exec_python([
            (Path(x.PROJ_ROOT) / 'scripts' / 'tree.py').absolute().as_posix(), _pkg_inst_dir, '3'
        ])
    x.print_stderr(f'──── Build Done @{dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")} ────')
