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
def get_build_env(
    win32_msvc_env: "dict[str, str] | None" = None
) -> "dict[str, str]":
    env = x.ENVIRON
    if ctx.args.target_plat == 'win-msvc':
        if not win32_msvc_env:
            win32_msvc_env = ctx.args.win32_msvc_env_target
        env.update(win32_msvc_env)
        env['CFLAGS'] = '/utf-8'
        env['CXXFLAGS'] = env['CFLAGS']
    return env
# ----------------------------
extra_search_dir: "list[str]" = []
# ----------------------------
def _3rd_included():
    from build_v2 import DependencySpec

    _3rd_deps: list[DependencySpec] = []
    if ctx.args.target_plat not in {'macosx', 'iphoneos', 'iphonesimulator'}:
        _3rd_deps.extend([
            {
                'name': 'zlib-ng',
                'type': 'static',
                'vers': '1273109',
                'args': '',
            },
        ])

    for dep in _3rd_deps:
        dep_path = ctx.include_3rd_dependencies(dep)
        extra_search_dir.append(dep_path.as_posix())
def _fetch_source():
    ctx.fetch_source_from_git('refs/heads/main', 'https://github.com/llvm/llvm-project.git')
def _build_step_0():
    _tblgen_dir = (Path(x.PROJ_ROOT) / 'tmp' / 'llvm.NATIVE')
    _tblgen_req = ((ctx.args.target_plat == 'win-msvc') and (ctx.args.target_arch != x.NATIVE_ARCH))

    _cmake_search_dir = ';'.join(extra_search_dir)
    args = [
        'cmake', *(ctx.args.extra_cmake),
        '-S',   ctx.subproj_src_dir('llvm').as_posix(),
        '-D',  'LLVM_BUILD_LLVM_DYLIB:BOOL=0',
        '-D',  'CMAKE_BUILD_TYPE=Release',
        '-D', f'CMAKE_PREFIX_PATH={_cmake_search_dir}',
        '-D', f'CMAKE_FIND_ROOT_PATH={_cmake_search_dir}',
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
        '-D',  'LLVM_TARGETS_TO_BUILD=AArch64;ARM;RISCV;WebAssembly;X86',
        '-D',  'LLDB_USE_SYSTEM_DEBUGSERVER:BOOL=1',
        '-D', f'LLVM_NATIVE_TOOL_DIR={(_tblgen_dir / "bin").as_posix()}',
    ]
    if ctx.args.target_plat != 'win-msvc':
        x.runpy_pip(['ninja'])
        args.extend(['-G', 'Ninja'])

    if _tblgen_req and (not _tblgen_dir.exists()):
        _tblgen_build_args: list[str] = []
        _tblgen_build_args.append(args[0])

        i = 1; c = len(args)
        while i < c:
            arg = args[i]; i += 1
            if arg == '-B':
                _tblgen_build_args.extend(['-B', _tblgen_dir.as_posix()])
                i += 1; continue
            if (i-1) % 2 == 1:
                continue
            if arg.startswith('CMAKE_C_COMPILER_TARGET'):
                continue
            if arg.startswith('CMAKE_CXX_COMPILER_TARGET'):
                continue
            if arg.startswith('LLVM_ENABLE_ZLIB'):
                arg = 'LLVM_ENABLE_ZLIB=OFF'
            _tblgen_build_args.extend([args[i-2], arg])
        x.run_as_subprocess(env=get_build_env(ctx.args.win32_msvc_env_native), args=_tblgen_build_args)

        _tblgen_build_targets = ['llvm-tblgen', 'clang-tblgen', 'lldb-tblgen', 'clang-tidy-confusable-chars-gen']
        x.run_as_subprocess(env=get_build_env(ctx.args.win32_msvc_env_native),
            args=['cmake', '--build', _tblgen_dir.as_posix(), '-j', f'{x.detect_cpu_count()}', '--target', ';'.join(_tblgen_build_targets)])

    LLVM_ARCH = {
        'amd64': 'X86',
        'arm64': 'AArch64',
        'armv7': 'ARM',
    }[ctx.args.target_arch]
    args.extend(['-D', f'LLVM_TARGET_ARCH={LLVM_ARCH}'])

    if ctx.args.target_plat != 'win-msvc':
        args.extend([
            '-D', f'CMAKE_C_HOST_COMPILER="clang"',
            '-D', f'CMAKE_CXX_HOST_COMPILER="clang++"',
        ])
    else:
        if ctx.args.target_arch != x.NATIVE_ARCH:
            args.extend([
                '-D',  'CMAKE_SYSTEM_NAME=Windows',
                '-D',  'CMAKE_CROSSCOMPILING:BOOL=TRUE',
            ])
        args.extend([
            '-D', f'CMAKE_C_HOST_COMPILER="clang-cl.exe"',
            '-D', f'CMAKE_CXX_HOST_COMPILER="clang-cl.exe"',
        ])

    if ctx.args.llvm_triple:
        args.extend(['-D', f'LLVM_HOST_TRIPLE={ctx.args.llvm_triple}'])

    x.run_as_subprocess(env=get_build_env(), args=args)
def _build_step_1():
    _build_targets = ['clangd', 'llvm-symbolizer', 'lldb', 'lldb-dap', 'lldb-instr']
    if ctx.args.target_plat == 'linux':
        _build_targets.append('lldbIntelFeatures')
    if ctx.args.target_plat != 'macosx':
        _build_targets.append('lldb-server')
    x.run_as_subprocess(env=get_build_env(ctx.args.win32_msvc_env_native),
        args=['cmake', '--build', ctx.args.pkg_buld_dir, '-j', f'{x.detect_cpu_count()}', '--target', ';'.join(_build_targets)])
def _build_step_2():
    _targets_mapping: dict[Path, list[str]]
    _install_targets: dict[Path, list[str]] = {
        (Path(ctx.args.pkg_buld_dir) / 'tools'): [
            'llvm-symbolizer',
        ],
        (Path(ctx.args.pkg_buld_dir) / 'tools' / 'lldb' / 'tools'): [
            'lldb',
            'lldb-argdumper',
            'lldb-dap',
            'lldb-instr',
        ],
        (Path(ctx.args.pkg_buld_dir) / 'tools' / 'lldb'): [
            'liblldb',
        ],
        (Path(ctx.args.pkg_buld_dir) / 'tools' / 'clang'): [
            'clangd',
            'clang-resource-headers',
        ],
    }
    if ctx.args.target_plat == 'linux':
        _targets_mapping = {
            (Path(ctx.args.pkg_buld_dir) / 'tools' / 'lldb' / 'tools'): [
                'lldbIntelFeatures',
            ]
        }
        for k, v in _targets_mapping.items():
            _targets = _install_targets.get(k) or []
            _targets.extend(v)
            _install_targets[k] = _targets
    if ctx.args.target_plat != 'macosx':
        _targets_mapping = {
            (Path(ctx.args.pkg_buld_dir) / 'tools' / 'lldb' / 'tools'): [
                'lldb-server',
            ]
        }
        for k, v in _targets_mapping.items():
            _targets = _install_targets.get(k) or []
            _targets.extend(v)
            _install_targets[k] = _targets

    for _dir, _targets in _install_targets.items():
        for _target in _targets:
            x.run_as_subprocess(env=get_build_env(),
                args=['cmake', '--install', _dir.absolute().as_posix(), '--component', _target, '--strip'])
    if ctx.args.target_plat == 'macosx':
        src = '/Applications/Xcode.app/Contents/SharedFrameworks/LLDB.framework/Versions/A/Resources/debugserver'
        (Path(ctx.args.pkg_inst_dir) / 'bin' / 'lldb-server').symlink_to(src, target_is_directory=False)


    if ctx.args.target_plat in {'win-msvc', 'win-mingw'}:
        _libname = {
            'win-msvc':  'liblldb.lib',
            'win-mingw': 'liblldb.dll.a',
        }[ctx.args.target_plat]
        (Path(ctx.args.pkg_inst_dir) / 'lib' / _libname).unlink(missing_ok=True)
