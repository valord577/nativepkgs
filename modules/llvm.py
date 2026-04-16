#!/usr/bin/env python3

# fmt: off

from scripts import utils as x
# ----------------------------

import os
import shlex
import shutil

from pathlib import Path


BUILD_CMD = 'cmake'
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

_cross_build_enabled = False
_cross_target_triple = ''
_extra_sysroot = ''
_extra_args_build: list[str] = []
_extra_search_dir: list[str] = []

_host_cc  = ''
_host_cxx = ''

_win32_msvc_env_native: dict[str, str] = {}

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
    global _cross_build_enabled; \
        _cross_build_enabled = env['CROSS_BUILD_ENABLED']
    global _cross_target_triple; \
        _cross_target_triple = env['CROSS_TARGET_TRIPLE']
    global _extra_sysroot; \
        _extra_sysroot = env['SYSROOT']
    global _extra_args_build; \
        _extra_args_build = env[f'EXTRA_{BUILD_CMD.upper()}']
    global _host_cc; \
        _host_cc = env['HOSTCC']
    global _host_cxx; \
        _host_cxx = env['HOSTCXX']
    global _win32_msvc_env_native; \
        _win32_msvc_env_native = env['WIN32_MSVC_ENV_NATIVE']

    if _target_pkg_type != 'static':
        raise NotImplementedError(f'unsupported PKG_TYPE: {_target_pkg_type}')


    global BUILD_ENV

    if _target_platform == 'android':
        BUILD_ENV['ANDROID_API_LEVEL'] = env['ANDROID_API_LEVEL']
    if _target_platform == 'win-msvc':
        BUILD_ENV = env['WIN32_MSVC_ENV_TARGET']
        BUILD_ENV['CFLAGS']   = '/utf-8'
        BUILD_ENV['CXXFLAGS'] = BUILD_ENV['CFLAGS']
        _extra_args_build.extend(['-D', 'CMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded'])
    if _target_platform != 'win-msvc':
        x._util_func__pip_install(['ninja'])
        _extra_args_build.extend(['-G', 'Ninja'])

    return [
        _source_dl_3rd_deps,
        _source_download,
        _build_step_00,
        _build_step_01,
        _build_step_02,
    ]



def _source_dl_3rd_deps():
    _3rd_deps: list[dict[str, str]] = []
    if _target_platform not in ['macosx', 'iphoneos', 'iphonesimulator']:
        _3rd_deps.extend([
            {
                'name': 'zlib-ng',
                'type': 'static',
                'vers': '1273109',
            },
        ])

    _get_prebuilt_script = (Path(x.PROJ_ROOT) / 'scripts' / 'get_prebuilt.py').absolute().as_posix()
    for dep in _3rd_deps:
        _name = dep['name']; _type = dep['type']; _vers = dep['vers']
        x._util_func__exec_python([_get_prebuilt_script, _target_archlibc, _name, _target_platform, _vers, _type, '', _3rd_deps_dir])

        _extra_search_dir.append((Path(_3rd_deps_dir) / _name).absolute().as_posix())
def _source_download():
    _git_target = 'refs/heads/main'
    if not (Path(_subproj_src) / '.git').exists():
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'init'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'remote', 'add', 'x', 'https://github.com/llvm/llvm-project.git'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{_git_target}'])
        x._util_func__subprocess(cwd=_subproj_src, args=['git', 'checkout', 'FETCH_HEAD'])
    x._util_put_pkg_version_desc(_target_pkg_name, x._util_func__subprocess(cwd=_subproj_src, collect_stdout=True, args=['git', 'describe', '--always', '--abbrev=7']))
    x._util_source_apply_patches(_subproj_src, _subproj_src_patches)
def _build_step_00():
    _tblgen_dir = (Path(_pkg_inst_dir).parent / '.NATIVE').absolute().as_posix()
    _tblgen_req = ((_target_platform == 'win-msvc') and (_cross_build_enabled))

    _cmake_search_dir = ';'.join(_extra_search_dir)
    args = [BUILD_CMD, *_extra_args_build,
        '-S',   (Path(_subproj_src) / 'llvm'),
        '-D',  'LLVM_BUILD_LLVM_DYLIB:BOOL=0',
        '-D',  'CMAKE_BUILD_TYPE=RelWithDebInfo',
        '-D', f'CMAKE_PREFIX_PATH={_cmake_search_dir}',
        '-D', f'CMAKE_FIND_ROOT_PATH={_extra_sysroot};{_cmake_search_dir}',
        '-D',  'LLVM_ENABLE_PROJECTS=clang;clang-tools-extra;lldb',
        '-D',  'CLANG_PLUGIN_SUPPORT:BOOL=0',
        '-D',  'LLVM_APPEND_VC_REV:BOOL=0',
        '-D',  'LLVM_ENABLE_BINDINGS:BOOL=0',
        '-D',  'LLVM_INCLUDE_BENCHMARKS:BOOL=0',
        '-D',  'LLVM_INCLUDE_EXAMPLES:BOOL=0',
        '-D',  'LLVM_INCLUDE_TESTS:BOOL=0',
        '-D',  'LLVM_INCLUDE_DOCS:BOOL=0',
        '-D',  'LLVM_INCLUDE_UTILS:BOOL=0',
        '-D',  'LLVM_ENABLE_ZLIB=FORCE_ON',
        '-D',  'LLVM_ENABLE_ZSTD=OFF',
        '-D',  'LLDB_ENABLE_SWIG:BOOL=0',
        '-D',  'LLDB_ENABLE_LIBEDIT:BOOL=0',
        '-D',  'LLDB_ENABLE_CURSES:BOOL=0',
        '-D',  'LLDB_ENABLE_LUA:BOOL=0',
        '-D',  'LLDB_ENABLE_PYTHON:BOOL=0',
        '-D',  'LLDB_ENABLE_LIBXML2:BOOL=0',
        '-D',  'LLDB_ENABLE_FBSDVMCORE:BOOL=0',
        '-D',  'LLVM_TARGETS_TO_BUILD=AArch64;ARM;RISCV;WebAssembly;X86',
        '-D',  'LLDB_USE_SYSTEM_DEBUGSERVER:BOOL=1',
        '-D', f'LLVM_NATIVE_TOOL_DIR={(Path(_tblgen_dir) / "bin").absolute().as_posix()}',
    ]

    if _tblgen_req:
        shutil.rmtree(_tblgen_dir, ignore_errors=True); \
            os.makedirs(_tblgen_dir, exist_ok=True)

        _tblgen_build_args = [*args]
        _tblgen_build_args_bdir_idx = 0
        _tblgen_build_args_zlib_idx = 0
        for i, entry in enumerate(_tblgen_build_args):
            if entry == '-B':
                _tblgen_build_args_bdir_idx = i + 1
            if entry.startswith('LLVM_ENABLE_ZLIB'):
                _tblgen_build_args_zlib_idx = i
        _tblgen_build_args[_tblgen_build_args_bdir_idx] = _tblgen_dir
        _tblgen_build_args[_tblgen_build_args_zlib_idx] = 'LLVM_ENABLE_ZLIB=OFF'

        _tblgen_build_env = _win32_msvc_env_native
        _tblgen_build_env['CFLAGS']   = '/utf-8'
        _tblgen_build_env['CXXFLAGS'] = _tblgen_build_env['CFLAGS']
        x._util_func__subprocess(env=_tblgen_build_env, args=_tblgen_build_args)

        _tblgen_build_targets = ['llvm-tblgen', 'clang-tblgen', 'lldb-tblgen', 'clang-tidy-confusable-chars-gen']
        _tblgen_build_args = f"{BUILD_CMD} --build {_tblgen_dir} -j {x.CPU_COUNT} --target {';'.join(_tblgen_build_targets)}"
        x._util_func__subprocess(env=_tblgen_build_env, args=shlex.split(_tblgen_build_args))


    LLVM_ARCH = {
        'amd64': 'X86',
        'arm64': 'AArch64',
        'armv7': 'ARM',
    }[_target_arch]
    args.extend([
        '-D', f'LLVM_TARGET_ARCH={LLVM_ARCH}',
        '-D', f'CMAKE_C_HOST_COMPILER={_host_cc}',
        '-D', f'CMAKE_CXX_HOST_COMPILER={_host_cxx}',
    ])
    if _target_platform == 'macosx':
        args.extend([
            '-D', f'LLVM_HOST_TRIPLE={_target_arch}-apple-darwin',
        ])
    if _target_platform == 'linux' and _cross_build_enabled:
        args.extend([
            '-D', f'LLVM_HOST_TRIPLE={_cross_target_triple}',
        ])
    if _target_platform == 'win-mingw':
        args.extend([
            '-D', f'LLVM_HOST_TRIPLE={_cross_target_triple}',
        ])
    if _target_platform == 'win-msvc':
        args.extend([
            '-D',  'CMAKE_SYSTEM_NAME=Windows',
            '-D',  'CMAKE_CROSSCOMPILING:BOOL=TRUE',
            '-D', f'LLVM_HOST_TRIPLE={_cross_target_triple}',
        ])

    x._util_func__subprocess(env=BUILD_ENV, args=args)
def _build_step_01():
    _build_targets = ['clangd', 'llvm-symbolizer', 'lldb', 'lldb-dap', 'lldb-instr']
    if _target_platform == 'linux':
        _build_targets.append('lldbIntelFeatures')
    if _target_platform != 'macosx':
        _build_targets.append('lldb-server')

    args = f"{BUILD_CMD} --build {_pkg_buld_dir} -j {x.CPU_COUNT} --target {';'.join(_build_targets)}"
    x._util_func__subprocess(env=BUILD_ENV, args=shlex.split(args))
def _build_step_02():
    _install_targets = {
        (Path(_pkg_buld_dir) / 'tools').absolute().as_posix(): [
            'llvm-symbolizer',
        ],
        (Path(_pkg_buld_dir) / 'tools' / 'lldb' / 'tools').absolute().as_posix(): [
            'lldb',
            'lldb-argdumper',
            'lldb-dap',
            'lldb-instr',
        ],
        (Path(_pkg_buld_dir) / 'tools' / 'lldb').absolute().as_posix(): [
            'liblldb',
        ],
        (Path(_pkg_buld_dir) / 'tools' / 'clang').absolute().as_posix(): [
            'clangd',
            'clang-resource-headers',
        ],
    }
    if _target_platform == 'linux':
        _install_targets[(Path(_pkg_buld_dir) / 'tools' / 'lldb' / 'tools').absolute().as_posix()].extend([
            'lldbIntelFeatures',
        ])
    if _target_platform != 'macosx':
        _install_targets[(Path(_pkg_buld_dir) / 'tools' / 'lldb' / 'tools').absolute().as_posix()].extend([
            'lldb-server',
        ])

    for _dir, _targets in _install_targets.items():
        for _target in _targets:
            x._util_func__subprocess(env=BUILD_ENV, args=[
                BUILD_CMD, '--install', _dir, '--component', _target,
            ])
    if _target_platform == 'macosx':
        _src = '/Applications/Xcode.app/Contents/SharedFrameworks/LLDB.framework/Versions/A/Resources/debugserver'
        (Path(_pkg_inst_dir) / 'bin' / 'lldb-server').symlink_to(_src, target_is_directory=False)
