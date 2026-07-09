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

import os
import runpy
import shutil
import time

from dataclasses import dataclass
from typing import Callable, Literal, TypedDict, cast
from urllib.parse import urljoin


if sys.prefix == sys.base_prefix:
    x.loge(f'Please run this script in a [virtual environment](https://docs.python.org/3/library/venv.html)')
if not x.ENVIRON.get('VIRTUAL_ENV'):
    x.loge(f'Please activate the virtual environment first')
# ----------------------------
class GitSubmoduleSpec(TypedDict):
    repo: "str"
    path: "str"
    cwd:  "str | Path"
    url:  "str"

class DependencySpec(TypedDict):
    name: "str"
    type: "Literal['static', 'shared']"
    vers: "str"
    args: "str"

@dataclass
class BuildCtxArgs:
    module: "str"

    target_plat: "str"
    target_arch: "str"
    target_info: "str"

    llvm_triple: "str"

    target_archinfo: "str"

    win32_msvc_env_native: "dict[str, str]"
    win32_msvc_env_target: "dict[str, str]"

    extra_cmake: "list[str]"
    extra_meson: "list[str]"

    cc: "list[str]"
    ar: "list[str]"
    nm: "list[str]"
    ldflags: "list[str]"
    objcopy: "list[str]"
    windres: "list[str]"
    pkgconf: "list[str]"

    pkg_buld_dir: "str"
    pkg_inst_dir: "str"

class BuildCtx:
    def __init__(self, args: "BuildCtxArgs"):
        self.args: "BuildCtxArgs" = args

        self._3rd_deps_dir: "Path" = (Path(x.PROJ_ROOT) / f'.lib.{self.args.target_plat}.{self.args.target_archinfo}')
        self._subproj_src:  "Path" = (Path(x.PROJ_ROOT) /  '.deps' / f'{self.args.module}')
        self._subproj_ver:  "Path" = (Path(x.PROJ_ROOT) /  '.deps' / f'{self.args.module}.ver')
        self._subproj_src_patches: "Path" = (Path(x.PROJ_ROOT) / 'patches' / self.args.module)

    @staticmethod
    def git_src_factory_reset(cwd: "str | Path"):
        x.run_as_subprocess(cwd=cwd,
            args=['git', 'reset', '--hard', 'HEAD'])
        x.run_as_subprocess(cwd=cwd,
            args=['git', 'clean', '-d', '-f', '-q'])

    @staticmethod
    def git_src_apply_patches(cwd: "str | Path", patches_dir: "Path"):
        __class__.git_src_factory_reset(cwd)

        if not patches_dir.exists():
            return
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
        hash: "str", url: "str",
        submodules: "list[GitSubmoduleSpec] | None" = None,
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
            for submodule in (submodules or []):
                x.run_as_subprocess(cwd=submodule["cwd"],
                    args=['git', 'config', '--local', f'submodule.{submodule["repo"]}.url', urljoin(url + '/', submodule["url"])])
                x.run_as_subprocess(cwd=submodule["cwd"],
                    args=['git', 'submodule', 'update', '--init', '--depth=1', '--single-branch', '-f', '--', submodule["path"]])
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

    def subproj_src_ver(self) -> str:
        return self._subproj_ver.read_text()

    def include_3rd_dependencies(self, dep: "DependencySpec") -> Path:
        this_lib_dir = (self._3rd_deps_dir / dep['name']); \
            this_lib_dir.parent.mkdir(parents=True, exist_ok=True)
        if False:
            pass  # pyright: ignore[reportUnreachable]
        elif x.ON_GITLAB_CI:
            pass
        elif x.ON_GITHUB_CI:
            zipname = f"{dep['name']}_{self.args.target_plat}_{self.args.target_archinfo}_{dep['vers']}_{dep['type']}"
            x.run_as_subprocess(args=[x.RCLONE_EXEC.as_posix(),
                'copy', f"r2:{x.feature('S3_R2_STORAGE_BUCKET')}/packages/{dep['name']}/{dep['vers']}/{zipname}.zip", this_lib_dir.parent.as_posix()])
            x.unzip_with_softlink(this_lib_dir.parent / f'{zipname}.zip')
        else:
            this_lib_dir.unlink(missing_ok=True)
            src = (Path(x.PROJ_ROOT) / 'out' / dep['name'] / self.args.target_plat / self.args.target_archinfo)
            this_lib_dir.symlink_to(src, target_is_directory=True)
        return this_lib_dir

class _state:
    def __init__(self,
        is_native_build: "bool",
        build_target: "tuple[str, ...]",
    ):
        self.target_plat: "str" = build_target[0]
        self.target_arch: "str" = ''
        self.target_info: "str" = ''

        self.llvm_triple: "str" = ''

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
        self.nm: "list[str]" = []
        self.ldflags: "list[str]" = []
        self.objcopy: "list[str]" = []
        self.windres: "list[str]" = []
        self.pkgconf: "list[str]" = []

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

            llvm_triple=self.llvm_triple,

            target_archinfo=self.target_archinfo,

            win32_msvc_env_native=self.win32_msvc_env_native,
            win32_msvc_env_target=self.win32_msvc_env_target,

            extra_cmake=self.extra_cmake,
            extra_meson=self.extra_meson,

            cc=self.cc,
            ar=self.ar,
            nm=self.nm,
            ldflags=self.ldflags,
            objcopy=self.objcopy,
            windres=self.windres,
            pkgconf=self.pkgconf,

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
        state.nm.extend(['llvm-nm'])
        state.ldflags.extend(['-fuse-ld=lld'])
        state.objcopy.extend(['llvm-objcopy'])

        x.ENVIRON['CC']  = 'clang'
        x.ENVIRON['CXX'] = 'clang++'
        x.ENVIRON['LDFLAGS'] = '-fuse-ld=lld'
    else:
        CROSS_TOOLCHAIN_ROOT = x.get_cross_toolchain_dir(state.target_plat)

        state.target_arch = _tuple[2]
        state.target_info = _tuple[3]
        state.llvm_triple = {
            'arm64': f'aarch64-unknown-linux-{state.target_info}',
            'amd64': f'x86_64-pc-linux-{state.target_info}',
            'armv7': f'arm-unknown-linux-{state.target_info}',
        }[state.target_arch]
        _sysroot = (Path(CROSS_TOOLCHAIN_ROOT) / state.llvm_triple).absolute().resolve().as_posix()

        state.cc.extend([
            f'clang',
            f'--target={state.llvm_triple}',
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
        state.nm.extend(['llvm-nm'])
        state.ldflags.extend(['-fuse-ld=lld'])
        state.objcopy.extend(['llvm-objcopy'])

        # pkgconf
        state.pkgconf.extend([f'{CROSS_TOOLCHAIN_ROOT}/pkgconf-wrapper.{state.llvm_triple}'])
        # cmake toolchain file
        state.extra_cmake.extend(["-D", f"CMAKE_TOOLCHAIN_FILE='{CROSS_TOOLCHAIN_ROOT}/crossfile.cmake.{state.llvm_triple}'"])
        # meson toolchain file
        state.extra_meson.extend(["--cross-file", f"{CROSS_TOOLCHAIN_ROOT}/crossfile.meson.{state.llvm_triple}"])
def _setctx_apple(
    state: _state, _native: "bool", _tuple: "tuple[str, ...]",
):
    state.target_arch = x.NATIVE_ARCH if _native else _tuple[1]
    state.llvm_triple = f'{state.target_arch}-apple-darwin'

    _apple_arch = {
        'arm64': 'arm64',
        'amd64': 'x86_64',
    }[state.target_arch]

    _apple_sdk_name = {
        'macosx':          'MacOSX',
        'iphoneos':        'iPhoneOS',
        'iphonesimulator': 'iPhoneSimulator',
    }[state.target_plat]
    _apple_sdk_path = f'/Applications/Xcode.app/Contents/Developer/Platforms/{_apple_sdk_name}.platform/Developer/SDKs/{_apple_sdk_name}.sdk'

    _apple_deployment_name = {
        'macosx':          'macosx',
        'iphoneos':        'iphoneos',
        'iphonesimulator': 'ios-simulator',
    }[state.target_plat]
    _apple_deployment_vers = {
        'macosx':          '11',
        'iphoneos':        '12',
        'iphonesimulator': '12',
    }[state.target_plat]

    state.cc.extend([
        f'clang', '-arch', _apple_arch,
        f'-m{_apple_deployment_name}-version-min={_apple_deployment_vers}',
        f'-isysroot', _apple_sdk_path,
    ])
    state.ar.extend(['ar'])
    state.nm.extend(['nm'])
    state.objcopy.extend(['objcopy'])

    pkgconf_wrapper, meson_crossfile = x.apple_crossfiles_generate(
        state.target_plat, state.target_arch, _apple_arch, _apple_sdk_path, _apple_deployment_name, _apple_deployment_vers)

    # pkgconf
    state.pkgconf.extend([pkgconf_wrapper.as_posix()])
    # cmake toolchain file
    _cmake_os_name = {
        'macosx':          'Darwin',
        'iphoneos':        'iOS',
        'iphonesimulator': 'iOS',
    }[state.target_plat]
    state.extra_cmake.extend(['-D',  'CMAKE_CROSSCOMPILING:BOOL=TRUE'])
    state.extra_cmake.extend(['-D', f'CMAKE_SYSTEM_NAME={_cmake_os_name}'])
    state.extra_cmake.extend(['-D', f'CMAKE_SYSTEM_PROCESSOR={_apple_arch}'])
    state.extra_cmake.extend(['-D', f'CMAKE_OSX_ARCHITECTURES={_apple_arch}'])
    state.extra_cmake.extend(['-D', f'CMAKE_OSX_SYSROOT={state.target_plat}'])
    state.extra_cmake.extend(['-D', f'CMAKE_OSX_DEPLOYMENT_TARGET={_apple_deployment_vers}'])
    state.extra_cmake.extend(['-D',  'CMAKE_MACOSX_BUNDLE:BOOL=0'])
    state.extra_cmake.extend(['-D', f'PKG_CONFIG_EXECUTABLE={pkgconf_wrapper.as_posix()}'])
    # meson toolchain file
    state.extra_meson.extend(["--cross-file", meson_crossfile.as_posix()])
def _setctx_win32_mingw(
    state: _state, _native: "bool", _tuple: "tuple[str, ...]",
):
    CROSS_TOOLCHAIN_ROOT = x.get_cross_toolchain_dir(state.target_plat)
    MINGW_ROOT = (Path(CROSS_TOOLCHAIN_ROOT)).absolute()

    state.target_arch = _tuple[1]

    state.llvm_triple = {
        'arm64': f'aarch64-w64-mingw32',
        'amd64': f'x86_64-w64-mingw32',
    }[state.target_arch]

    state.cc.extend([
        f"{(MINGW_ROOT / 'bin' / f'{state.llvm_triple}-clang').as_posix()}",
        f"-no-canonical-prefixes",
    ])
    if state.target_arch == 'amd64':
        state.cc.extend(['-march=x86-64-v2'])
    if state.target_arch == 'arm64':
        state.cc.extend(['-march=armv8-a'])
    state.ar.extend([f"{(MINGW_ROOT / 'bin' / f'{state.llvm_triple}-ar').as_posix()}"])
    state.nm.extend([f"{(MINGW_ROOT / 'bin' / f'{state.llvm_triple}-nm').as_posix()}"])
    state.ldflags.extend(['-fuse-ld=lld'])
    state.objcopy.extend([f"{(MINGW_ROOT / 'bin' / f'{state.llvm_triple}-objcopy').as_posix()}"])
    state.windres.extend([f"{(MINGW_ROOT / 'bin' / f'{state.llvm_triple}-windres').as_posix()}"])

    # pkgconf
    state.pkgconf.extend([f'{CROSS_TOOLCHAIN_ROOT}/pkgconf-wrapper.{state.target_arch}'])
    # cmake toolchain file
    state.extra_cmake.extend(["-D", f"CMAKE_TOOLCHAIN_FILE='{CROSS_TOOLCHAIN_ROOT}/crossfile.cmake.{state.target_arch}'"])
    # meson toolchain file
    state.extra_meson.extend(["--cross-file", f"{CROSS_TOOLCHAIN_ROOT}/crossfile.meson.{state.target_arch}"])
def _setctx_win32_msvc(
    state: _state, _native: "bool", _tuple: "tuple[str, ...]",
):
    state.target_arch = x.NATIVE_ARCH if _native else _tuple[1]

    msvc_dir, msvc_devshell = x.win32_msvc_detect()
    state.win32_msvc_env_native = x.win32_msvc_dump_env(msvc_dir, msvc_devshell, x.NATIVE_ARCH)
    state.win32_msvc_env_target = x.win32_msvc_dump_env(msvc_dir, msvc_devshell, state.target_arch)

    state.llvm_triple = {
        'arm64': f'aarch64-pc-windows-msvc',
        'amd64': f'x86_64-pc-windows-msvc',
    }[state.target_arch]

    # cmake toolchain file
    state.extra_cmake.extend([
        '-G',  'Ninja',
        '-D',  'CMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded',
        "-D", f"CMAKE_C_COMPILER='clang-cl.exe'",
        "-D", f"CMAKE_CXX_COMPILER='clang-cl.exe'",
        "-D", f"CMAKE_C_COMPILER_TARGET={state.llvm_triple}",
        "-D", f"CMAKE_CXX_COMPILER_TARGET={state.llvm_triple}",
    ])
def _setctx_android(
    state: _state, _native: "bool", _tuple: "tuple[str, ...]",
):
    state.target_arch = _tuple[1]
    state.target_info = _tuple[2]
    if (state.target_arch in ['arm64', 'amd64']
        and state.android_api_level < 21
    ): state.android_api_level = 21
    x.ENVIRON['ANDROID_API_LEVEL'] = f'{state.android_api_level}' # for pkgconf wrapper
    if (state.android_api_level < 30):
        state.ldflags.extend(['-Wl,--no-rosegment'])
    if (23 <= state.android_api_level) and (state.android_api_level < 28):
        state.ldflags.extend(['-Wl,--pack-dyn-relocs=android'])
    elif (28 <= state.android_api_level) and (state.android_api_level < 30):
        state.ldflags.extend(['-Wl,--pack-dyn-relocs=android+relr', '-Wl,--use-android-relr-tags'])
    elif (30 <= state.android_api_level):
        state.ldflags.extend(['-Wl,--pack-dyn-relocs=android+relr'])


    _target_triple = {
        'arm64': f'aarch64-linux-android',
        'armv7': f'armv7a-linux-androideabi',
        'amd64': f'x86_64-linux-android',
    }[state.target_arch]
    state.llvm_triple = f'{_target_triple}{state.android_api_level}'

    ANDROID_NDK_ROOT = x.get_cross_toolchain_dir(state.target_plat)
    CROSS_TOOLCHAIN_ROOT = (Path(ANDROID_NDK_ROOT) / 'toolchains' / 'llvm' / 'prebuilt' / 'linux-x86_64').absolute()

    state.cc.extend([
        f"{(CROSS_TOOLCHAIN_ROOT / 'bin' / f'{state.llvm_triple}-clang').as_posix()}",
        f"-no-canonical-prefixes",
    ])
    if state.target_arch == 'amd64':
        state.cc.extend(['-march=x86-64-v2'])
    if state.target_arch == 'arm64':
        state.cc.extend(['-march=armv8-a'])
    if state.target_arch == 'armv7':
        state.cc.extend(['-march=armv7-a', '-mfpu=neon', '-mfloat-abi=softfp'])
    state.ar.extend([f"{(CROSS_TOOLCHAIN_ROOT / 'bin' / 'llvm-ar').as_posix()}"])
    state.nm.extend([f"{(CROSS_TOOLCHAIN_ROOT / 'bin' / 'llvm-nm').as_posix()}"])
    state.ldflags.extend(['-fuse-ld=lld'])
    state.objcopy.extend([f"{(CROSS_TOOLCHAIN_ROOT / 'bin' / 'llvm-objcopy').as_posix()}"])


    flexible_page_sizes = int(_tuple[2][:-1])
    x.logv(f'ANDROID_FLEXIBLE_PAGE_SIZES: {flexible_page_sizes} KiB')
    state.cc.append('-D__BIONIC_NO_PAGE_SIZE_MACRO')
    flexible_page_ldflags = [
        f'-Wl,-z,max-page-size={1024 * flexible_page_sizes}',
        f'-Wl,-z,common-page-size={1024 * flexible_page_sizes}',
    ]
    state.ldflags.extend(flexible_page_ldflags)

    # pkgconf
    state.pkgconf.extend([f'{ANDROID_NDK_ROOT}/pkgconf-wrapper.{state.target_arch}'])
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
        "-D", f"CMAKE_ANDROID_API={state.android_api_level}",
        "-D", f"CMAKE_ANDROID_API_MIN={state.android_api_level}",
        "-D", f"CMAKE_ANDROID_ARCH_ABI={_cmake_arch_abi}",
        "-D", f"CMAKE_ANDROID_NDK={ANDROID_NDK_ROOT}",
        "-D", f"CMAKE_C_COMPILER_TARGET={state.llvm_triple}",
        "-D", f"CMAKE_CXX_COMPILER_TARGET={state.llvm_triple}",
        "-D", f"CMAKE_EXE_LINKER_FLAGS_INIT='{' '.join(flexible_page_ldflags)}'",
        "-D", f"CMAKE_MODULE_LINKER_FLAGS_INIT='{' '.join(flexible_page_ldflags)}'",
        "-D", f"CMAKE_SHARED_LINKER_FLAGS_INIT='{' '.join(flexible_page_ldflags)}'",
    ])
    if state.target_arch == 'armv7':
        state.extra_cmake.extend([
            "-D", "CMAKE_ANDROID_ARM_MODE:BOOL=1",
            "-D", "CMAKE_ANDROID_ARM_NEON:BOOL=1",
        ])
    state.extra_cmake.extend(['-D', f"PKG_CONFIG_EXECUTABLE:STRING='{' '.join(state.pkgconf)}'"])
    # meson toolchain file
    state.extra_meson.extend(["--cross-file", f"{ANDROID_NDK_ROOT}/crossfile.meson.{state.target_arch}-{state.target_info}"])
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
    'macosx': {
        'native': True,
        'hostos': ('macosx', ),
        'setctx': _setctx_apple,
        'tuples': [
            ('macosx', 'arm64'),
            ('macosx', 'amd64'),
        ],
    },
    'iphoneos': {
        'native': False,
        'hostos': ('macosx', ),
        'setctx': _setctx_apple,
        'tuples': [
            ('iphoneos', 'arm64'),
        ],
    },
    'iphonesimulator': {
        'native': False,
        'hostos': ('macosx', ),
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
    if target_palt == 'windows':
        target_palt = 'win-msvc'
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
