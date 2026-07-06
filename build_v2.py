#!/usr/bin/env python3

# fmt: off

import sys
from pathlib import Path

sys.dont_write_bytecode = True

_this_file = (Path(__file__).absolute().resolve())
sys.path.append(
    (_this_file.parents[0]).as_posix()
); import x_utils as x

if sys.version_info < (3, 8):
    x.loge('Required Python Interpreter ≥ 3.8')  # pyright: ignore[reportUnreachable]
# ----------------------------

import copy
import json
import os
import runpy
import shutil
import time

from dataclasses import dataclass
from typing import Callable, TypedDict, cast


if sys.prefix == sys.base_prefix:
    x.loge(f'Please run this script in a [virtual environment](https://docs.python.org/3/library/venv.html)')
if not x.ENVIRON.get('VIRTUAL_ENV'):
    x.loge(f'Please activate the virtual environment first')
# ----------------------------
@dataclass
class BuildCtxArgs:
    module: "str"

    target_plat: "str"
    target_arch: "str"
    target_info: "str"

    target_archinfo: "str"

    win32_msvc_env_native: "dict[str, str]"
    win32_msvc_env_target: "dict[str, str]"

    extra_cmake: "list[str]"
    extra_meson: "list[str]"

    cc: "list[str]"
    ar: "list[str]"
    ldflags: "list[str]"
    objcopy: "list[str]"

    pkg_buld_dir: "str"
    pkg_inst_dir: "str"

class BuildCtx:
    def __init__(self, args: "BuildCtxArgs"):
        self.args: "BuildCtxArgs" = args

        self._subproj_src: "Path" = (Path(x.PROJ_ROOT) / '.deps' / f'{self.args.module}')
        self._subproj_ver: "Path" = (Path(x.PROJ_ROOT) / '.deps' / f'{self.args.module}.ver')
        self._subproj_src_patches: "Path" = (Path(x.PROJ_ROOT) / 'patches' / self.args.module)

    @staticmethod
    def git_src_factory_reset(cwd: "str | Path"):
        x.run_as_subprocess(cwd=cwd,
            args=['git', 'reset', '--hard', 'HEAD'])
        x.run_as_subprocess(cwd=cwd,
            args=['git', 'clean', '-d', '-f', '-q'])

    @staticmethod
    def git_src_apply_patches(cwd: "str | Path", patches_dir: "Path"):
        if not patches_dir.exists():
            return
        __class__.git_src_factory_reset(cwd)

        patches: list[Path] = []
        for it in patches_dir.iterdir():
            if not it.is_file():
                continue
            patches.append(it)
        patches_sorted = sorted(patches, key=lambda p: p.name)
        for it in patches_sorted:
            x.run_as_subprocess(cwd=cwd,
                args=['git', 'apply', '--verbose', '--ignore-space-change', '--ignore-whitespace', it.absolute().as_posix()])

    def fetch_source_from_git(self,
        hash: "str", url: "str"
    ):
        self._subproj_src.mkdir(parents=True, exist_ok=True)
        if not (self._subproj_src / '.git').exists():
            x.run_as_subprocess(cwd=self._subproj_src,
                args=['git', 'init'])
            x.run_as_subprocess(cwd=self._subproj_src,
                args=['git', 'remote', 'add', 'x', url])
            x.run_as_subprocess(cwd=self._subproj_src,
                args=['git', 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{hash}'])
            x.run_as_subprocess(cwd=self._subproj_src,
                args=['git', 'checkout', 'FETCH_HEAD'])
        __class__.git_src_apply_patches(self._subproj_src, self._subproj_src_patches)

        ver = x.run_as_subprocess(cwd=self._subproj_src,
            collect_stdout=True, args=['git', 'describe', '--always', '--abbrev=7']).strip()
        _ = self._subproj_ver.write_text(ver)

        x.gha_append_env({
            'PKG_VERSION': ver,
            'PKG_ZIPNAME': f'{self.args.module}_{self.args.target_plat}_{self.args.target_archinfo}_{ver}_{x.feature("PKG_TYPE")}',
        })

    def subproj_src_dir(self, *subdir: "str | Path") -> Path:
        if not subdir:
            return self._subproj_src
        return self._subproj_src.joinpath(*subdir)

class _state:
    def __init__(self,
        is_native_build: "bool",
        build_target: "tuple[str, ...]",
    ):
        self.target_plat: "str" = build_target[0]
        self.target_arch: "str" = ''
        self.target_info: "str" = ''

        #  - API Level 30: android.media.MediaCodec#CONFIGURE_FLAG_USE_BLOCK_MODEL
        #  - API Level 31: android.media.MediaCodec#getSupportedVendorParameters()
        #  - API Level 35: android.media.MediaCodec#PARAMETER_KEY_QP_OFFSET_MAP
        self.android_api_level: "int" = 28

        self.win32_msvc_env_native: "dict[str, str]" = {}
        self.win32_msvc_env_target: "dict[str, str]" = {}

        self.extra_cmake: "list[str]" = []
        self.extra_meson: "list[str]" = []

        self.cc: "list[str]" = []
        self.ar: "list[str]" = []
        self.ldflags: "list[str]" = []
        self.objcopy: "list[str]" = []

        CLI_SUPPORTED_TARGETS[self.target_plat]['setctx'](self, is_native_build, build_target)


        self.target_archinfo: "str" = self.target_arch
        if self.target_info:
            self.target_archinfo = f'{self.target_arch}-{self.target_info}'
        self.pkg_buld_dir: "str" = ''
        self.pkg_inst_dir: "str" = ''


    def build_v2(self, module: "str"):
        self.pkg_buld_dir = (Path(x.PROJ_ROOT) / 'tmp' / module / self.target_plat / self.target_archinfo).absolute().as_posix()
        self.pkg_inst_dir = (Path(x.PROJ_ROOT) / 'out' / module / self.target_plat / self.target_archinfo).absolute().as_posix()
        if (not x.ON_CODE_EDIT) and (_pkg_inst_dir_ci := x.ENVIRON.get('INST_DIR')):
            self.pkg_inst_dir = Path(_pkg_inst_dir_ci).absolute().as_posix()

        shutil.rmtree(self.pkg_buld_dir, ignore_errors=True); \
            os.makedirs(self.pkg_buld_dir, exist_ok=True)
        shutil.rmtree(self.pkg_inst_dir, ignore_errors=True); \
            os.makedirs(self.pkg_inst_dir, exist_ok=True)

        self.extra_cmake.extend([
            '-D', 'CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON',
            '-D', 'CMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON',
            '-D', 'CMAKE_INSTALL_LIBDIR:PATH=lib',
            '-D', 'CMAKE_PLATFORM_NO_VERSIONED_SONAME:BOOL=ON',
            #'-D', 'CMAKE_VERBOSE_MAKEFILE:BOOL=ON',
            '-B', self.pkg_buld_dir,
            '-D', f'CMAKE_INSTALL_PREFIX={self.pkg_inst_dir}',
        ])
        self.extra_meson.extend([
            '--pkgconfig.relocatable',
            '--libdir', 'lib',
            '--python.install-env', 'venv',
            '--wrap-mode', 'nofallback',
            '-Db_pie=true',
            '-Db_ndebug=true',
            '--prefix', self.pkg_inst_dir,
        ])

        args = BuildCtxArgs(
            module = module,

            target_plat=self.target_plat,
            target_arch=self.target_arch,
            target_info=self.target_info,

            target_archinfo=self.target_archinfo,

            win32_msvc_env_native=self.win32_msvc_env_native,
            win32_msvc_env_target=self.win32_msvc_env_target,

            extra_cmake=self.extra_cmake,
            extra_meson=self.extra_meson,

            cc=self.cc,
            ar=self.ar,
            ldflags=self.ldflags,
            objcopy=self.objcopy,

            pkg_buld_dir=self.pkg_buld_dir,
            pkg_inst_dir=self.pkg_inst_dir,
        )
        m = (Path(x.PROJ_ROOT) / 'modules' / f'{module}.py')
        if (not m.exists()) or (not m.is_file()):
            x.loge(f'failed to load module: {module}')
        build_steps = cast("Callable[[], list[Callable[[], None]]]",
            runpy.run_path(m.as_posix(), init_globals={'ctx': BuildCtx(args)})['build_steps'])
        for func in (build_steps() or []):
            func()

    def describe(self):
        x.logv(f'')
        x.logv(f'')

        x.logv(f'Project Root: {x.PROJ_ROOT}')
        x.logv(f'Build TMP Dir: {self.pkg_buld_dir}')
        x.logv(f'Build OUT Dir: {self.pkg_inst_dir}')

        x.logv(f'')

# ----------------------------
def _setctx_linux(
    state: _state, _native: "bool", _tuple: "tuple[str, ...]",
):
    if _native:
        if not x.ON_CODE_EDIT:
            x.loge(f'unsupported native build on the CI runner')
        state.target_arch = x.NATIVE_ARCH
        if state.target_arch not in ['arm64', 'amd64']:
            x.loge(f'unsupported target arch: {state.target_arch}')
        state.target_info = x.detect_libc_runtime()

        state.cc.extend(['clang'])
        state.ar.extend(['llvm-ar'])
        state.ldflags.extend(['-fuse-ld=lld'])
        state.objcopy.extend(['llvm-objcopy'])
    else:
        CROSS_TOOLCHAIN_ROOT = x.get_cross_toolchain_dir(state.target_plat)

        state.target_arch = _tuple[2]
        state.target_info = _tuple[3]
        _target_triple = {
            'arm64': f'aarch64-unknown-linux-{state.target_info}',
            'amd64': f'x86_64-pc-linux-{state.target_info}',
            'armv7': f'arm-unknown-linux-{state.target_info}',
        }[state.target_arch]
        _sysroot = (Path(CROSS_TOOLCHAIN_ROOT) / _target_triple).absolute().resolve().as_posix()

        state.cc.extend([
            f'clang',
            f'--target={_target_triple}',
            f'--gcc-toolchain={_sysroot}/usr',
            f'--sysroot={_sysroot}'
        ])
        if state.target_arch == 'amd64':
            state.cc.extend(['-march=x86-64-v2'])
        if state.target_arch == 'arm64':
            state.cc.extend(['-march=armv8-a'])
        if state.target_arch == 'armv7':
            state.cc.extend(['-march=armv7-a', '-mfpu=neon-vfpv4', '-mfloat-abi=hard'])
        state.ar.extend(['llvm-ar'])
        state.ldflags.extend(['-fuse-ld=lld'])
        state.objcopy.extend(['llvm-objcopy'])

        # cmake toolchain file
        state.extra_cmake.extend(["-D", f"CMAKE_TOOLCHAIN_FILE={(Path(CROSS_TOOLCHAIN_ROOT) / f'crossfile.cmake.{_target_triple}').absolute().as_posix()}"])
def _setctx_win32_msvc(
    state: _state, _native: "bool", _tuple: "tuple[str, ...]",
):
    state.target_arch = x.NATIVE_ARCH if _native else _tuple[1]

    msvc_dir, msvc_devshell = x.win32_msvc_detect()
    state.win32_msvc_env_native = x.win32_msvc_dump_env(msvc_dir, msvc_devshell, x.NATIVE_ARCH)
    state.win32_msvc_env_target = x.win32_msvc_dump_env(msvc_dir, msvc_devshell, state.target_arch)

    # cmake toolchain file
    state.extra_cmake.extend(['-G', 'Ninja'])
def _setctx_android(
    state: _state, _native: "bool", _tuple: "tuple[str, ...]",
):
    state.target_arch = _tuple[1]
    state.target_info = _tuple[2]
    if (state.target_arch in ['arm64', 'amd64']
        and state.android_api_level < 21
    ): state.android_api_level = 21
    if (state.android_api_level < 30):
        state.ldflags.extend(['-Wl,--no-rosegment'])
    if (23 <= state.android_api_level) and (state.android_api_level < 28):
        state.ldflags.extend(['-Wl,--pack-dyn-relocs=android'])
    elif (28 <= state.android_api_level) and (state.android_api_level < 30):
        state.ldflags.extend(['-Wl,--pack-dyn-relocs=android+relr', '-Wl,--use-android-relr-tags'])
    elif (30 <= state.android_api_level):
        state.ldflags.extend(['-Wl,--pack-dyn-relocs=android+relr'])


    _target_triple = {
        'arm64': f'aarch64-linux-android{state.android_api_level}',
        'armv7': f'armv7a-linux-androideabi{state.android_api_level}',
        'amd64': f'x86_64-linux-android{state.android_api_level}',
    }[state.target_arch]

    ANDROID_NDK_ROOT = x.get_cross_toolchain_dir(state.target_plat)
    CROSS_TOOLCHAIN_ROOT = (Path(ANDROID_NDK_ROOT) / 'toolchains' / 'llvm' / 'prebuilt' / 'linux-x86_64').absolute()

    state.cc.extend([
        f"{(CROSS_TOOLCHAIN_ROOT / 'bin' / f'{_target_triple}-clang').as_posix()}",
        f"-no-canonical-prefixes",
        f"--sysroot={(CROSS_TOOLCHAIN_ROOT / 'sysroot').as_posix()}",
    ])
    if state.target_arch == 'amd64':
        state.cc.extend(['-march=x86-64-v2'])
    if state.target_arch == 'arm64':
        state.cc.extend(['-march=armv8-a'])
    if state.target_arch == 'armv7':
        state.cc.extend(['-march=armv7-a', '-mfpu=neon', '-mfloat-abi=softfp'])
    state.ar.extend([f"{(CROSS_TOOLCHAIN_ROOT / 'bin' / 'llvm-ar').as_posix()}"])
    state.ldflags.extend(['-fuse-ld=lld'])
    state.objcopy.extend([f"{(CROSS_TOOLCHAIN_ROOT / 'bin' / 'llvm-objcopy').as_posix()}"])


    flexible_page_sizes = int(_tuple[2][:-1])
    x.logv(f'ANDROID_FLEXIBLE_PAGE_SIZES: {flexible_page_sizes} KiB')
    state.cc.append('-D__BIONIC_NO_PAGE_SIZE_MACRO')
    flexible_page_ldflags = [
        f'-Wl,-z,max-page-size={1024 * flexible_page_sizes}',
        f'-Wl,-z,max-page-size={1024 * flexible_page_sizes}',
    ]
    state.ldflags.extend(flexible_page_ldflags)

    # cmake toolchain file
    _cmake_arch_abi = {
        'arm64': 'arm64-v8a',
        'armv7': 'armeabi-v7a',
        'amd64': 'x86_64',
    }[state.target_arch]
    state.extra_cmake.extend([
        "-D",  "CMAKE_CROSSCOMPILING:BOOL=TRUE",
        "-D",  "CMAKE_SYSTEM_NAME=Android",
        "-D", f"CMAKE_SYSTEM_VERSION={state.android_api_level}",
        "-D", f"CMAKE_ANDROID_ARCH_ABI={_cmake_arch_abi}",
        "-D", f"CMAKE_ANDROID_NDK={ANDROID_NDK_ROOT}",
        "-D", f"CMAKE_C_COMPILER_TARGET={_target_triple}",
        "-D", f"CMAKE_CXX_COMPILER_TARGET={_target_triple}",
        "-D", f"CMAKE_EXE_LINKER_FLAGS_INIT='{' '.join(flexible_page_ldflags)}'",
        "-D", f"CMAKE_MODULE_LINKER_FLAGS_INIT='{' '.join(flexible_page_ldflags)}'",
        "-D", f"CMAKE_SHARED_LINKER_FLAGS_INIT='{' '.join(flexible_page_ldflags)}'",
    ])
    if state.target_arch == 'armv7':
        state.extra_cmake.extend([
            "-D", "CMAKE_ANDROID_ARM_MODE:BOOL=1",
            "-D", "CMAKE_ANDROID_ARM_NEON:BOOL=1",
        ])
    #ctx.extra_cmake.extend(['-D', f"PKG_CONFIG_EXECUTABLE={ctx.cross_pkgconfig_bin}"])
# ----------------------------
class TargetSpec(TypedDict):
    native: "bool"
    hostos: "tuple[str, ...]"
    setctx: "Callable[[_state, bool, tuple[str, ...]], None]"
    tuples: "list[tuple[str, ...]]"

CLI_SUPPORTED_TARGETS: "dict[str, TargetSpec]" = {
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
    'win-msvc': {
        'native': True,
        'hostos': ('windows', ),
        'setctx': _setctx_win32_msvc,
        'tuples': [
            ('win-msvc', 'arm64'),
            ('win-msvc', 'amd64'),
        ],
    },
    'android': {
        'native': False,
        'hostos': ('linux', 'amd64'),
        'setctx': _setctx_android,
        'tuples': [
            ('android', 'arm64', '4k'),
            ('android', 'arm64', '16k'),
            ('android', 'armv7', '4k'),
            ('android', 'amd64', '4k'),
        ],
    },
}

CLI_SUPPORTED_CONTROL: "dict[str, tuple[str, str]]" = {
    'describe': ('0', '# if not 0, show detailed project information'),
}
def control(key: str) -> str:
    return x.ENVIRON.get(key) or CLI_SUPPORTED_CONTROL[key][0]

def show_help(exitcode: int = 1):
    _native_flag_width = 0
    for k, v in CLI_SUPPORTED_TARGETS.items():
        _width = len(k) + 1
        if v['native'] and (_width > _native_flag_width):
            _native_flag_width = _width
    _targets_help_str = ''
    for k, v in CLI_SUPPORTED_TARGETS.items():
        _targets_help_str += f'    {k.ljust(_native_flag_width)}{"(* native)" if v["native"] else ""}\n'
        for tgt in v['tuples']:
            _targets_help_str += f'        {" ".join(tgt[1:])}\n'

    _control_flag_width = 0
    for k, v in CLI_SUPPORTED_CONTROL.items():
        _width = len(k) + 1 + len(v[0])
        if _width > _control_flag_width:
            _control_flag_width = _width
    _controls_help_str = ''
    for k, v in CLI_SUPPORTED_CONTROL.items():
        _control_flag = f'{k}[={v[0]}]'
        _controls_help_str += f'    {_control_flag.ljust(_control_flag_width)}  {v[1]}\n'

    help_str  = f''
    help_str += f'Usage: {sys.argv[0]} <module> [target] [-- <control>...]\n\n'
    help_str += f'Supported Targets:\n{_targets_help_str}\n'
    help_str += f'Supported Control:\n{_controls_help_str}\n'
    print(help_str[:-1], file=sys.stderr)
    sys.exit(exitcode)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if ('-h' in argv) or ('--help' in argv):
        show_help(0)  # exited

    argv_sep_0: "list[str]"
    argv_sep_1: "list[str]"
    if '--' in argv:
        idx = argv.index('--')
        argv_sep_0 = argv[:idx]
        argv_sep_1 = argv[(idx+1):]
    else:
        argv_sep_0 = argv[:]
        argv_sep_1 = []

    for item in argv_sep_1:
        if '=' not in item:
            continue
        key, value = item.split('=', 1)
        if not value:
            continue
        if key in CLI_SUPPORTED_CONTROL.keys():
            CLI_SUPPORTED_CONTROL[key] = (value, '')

    if len(argv_sep_0) < 1:
        show_help(1)  # exited
    module = argv_sep_0[0]
    argv_sep_0 = argv_sep_0[1:]


    target_palt = x.NATIVE_PLAT
    if len(argv_sep_0) > 0:
        target_palt = argv_sep_0[0]

    _target = CLI_SUPPORTED_TARGETS.get(target_palt)
    if not _target:
        x.loge(f'unsupported target platform: {target_palt}')
    # check hostos
    _hostos = (x.NATIVE_PLAT, x.NATIVE_ARCH); \
        _hostos_required = _target['hostos']
    if (
        len(_hostos_required) not in (1, 2)
        or _hostos_required != _hostos[:len(_hostos_required)]
    ):
        x.loge(f'unsupported host os: {_hostos}, required: {_hostos_required}')
    # check target tuple
    _target_tuple: "tuple[str, ...] | None" = None
    _prefer_native_build: "bool" = (len(argv_sep_0) in (0, 1))
    if _prefer_native_build:
        if not _target['native']:
            x.loge(f'unsupported native build: {target_palt}')
        _target_tuple = tuple([target_palt])
    else:
        _target_tuple = tuple(argv_sep_0)
        if _target_tuple not in _target['tuples']:
            x.loge(f'unsupported target tuple: {_target_tuple}')


    time_s = time.perf_counter()

    state = _state(_prefer_native_build, _target_tuple)
    if control('describe') != '0':
        state.describe()
    else:
        state.build_v2(module)

    time_e = time.perf_counter()

    if not x.ON_CODE_EDIT:
        x.runpy([(Path(x.PROJ_ROOT) / 'x_tree.py').as_posix(), state.pkg_inst_dir, '2'])
    x.logv(f'──── cost time: {(time_e - time_s):.3f} s ────')
