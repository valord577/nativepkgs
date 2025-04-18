#!/usr/bin/env python3

# fmt: off

import os
import shutil
import sys


_env: dict = {}
_ctx: dict = {
    'PKG_INST_STRIP': '',
    'CMAKE_CMD': 'cmake',
    'PKG_3RD_DEPS_SHARED': [],
    'PKG_3RD_DEPS_STATIC': [],
    'PKG_CONFIG_PATH': [],
    'BUILD_ENV': os.environ.copy(),
    'SHELL_REQ': False,
    'CMAKE_SEARCH_PATH': [],
}

def module_init(env: dict) -> list:
    global _env; _env = env
    return [
        _platform_check,
        _source_dl_3rd_deps,
        _source_download,
        _source_apply_patches,
        _build_step_msvc,
        _build_step_unix,
        _build_step_00,
        _build_step_01,
        _build_step_02,
    ]



def _platform_check():
    if not (_env['PKG_PLATFORM'] in ['macosx', 'linux', 'win-mingw', 'win-msvc']):
        _env['FUNC_EXIT'](f'unsupported PKG_PLATFORM: {_env["PKG_PLATFORM"]}')  # exited
def _source_dl_3rd_deps():
    if not _env.get('PLATFORM_APPLE', False):
        _env['FUNC_PKGC'](_ctx, _env, 'zlib-ng', '860e4cf', 'static')
def _source_download():
    _git_target = 'refs/tags/llvmorg-20.1.3'
    if not os.path.exists(os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], '.git'))):
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'init'])
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'remote', 'add', 'x', 'https://github.com/llvm/llvm-project.git'])
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'fetch', '-q', '--no-tags', '--prune', '--no-recurse-submodules', '--depth=1', 'x', f'+{_git_target}'])
        _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'checkout', 'FETCH_HEAD'])
    if file_ver := os.getenv('DEPS_VER', ''):
        with open(file_ver, 'w') as f:
            f.write(f'v{_git_target.split("-")[-1]}')
def _source_apply_patches():
    if not os.path.exists(_env['SUBPROJ_SRC_PATCHES']):
        return
    _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'reset', '--hard', 'HEAD'])
    _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'], args=[shutil.which('git'), 'clean', '-d', '-f', '-q'])
    with os.scandir(_env['SUBPROJ_SRC_PATCHES']) as it:
        entries = sorted(it, key=lambda e: e.name)
        for entry in entries:
            if not entry.is_file():
                continue
            _env['FUNC_PROC'](cwd=_env['SUBPROJ_SRC'],
                args=[shutil.which('git'), 'apply', '--verbose', '--ignore-space-change', '--ignore-whitespace', entry.path])



def _build_step_msvc():
    if _env['PKG_PLATFORM'] != 'win-msvc':
        return
    _ctx['BUILD_ENV'] = _env['WIN32_MSVC_ENV_TARGET']
    _ctx['BUILD_ENV']['CFLAGS']   = '/utf-8'
    _ctx['BUILD_ENV']['CXXFLAGS'] = _ctx['BUILD_ENV']['CFLAGS']
    _ctx['SHELL_REQ'] = True

    if _env['LIB_RELEASE'] == '0':
        _env['FUNC_EXIT'](f'unsupported LIB_RELEASE: {_env["LIB_RELEASE"]}')  # exited
    if _env['LIB_RELEASE'] == '1':
        _env['EXTRA_CMAKE'].extend(['-D', 'CMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded'])
def _build_step_unix():
    if _env['PKG_PLATFORM'] == 'win-msvc':
        return
    _env['FUNC_PYPI'](['pip', 'ninja'])
    if not os.getenv('VIRTUAL_ENV'):
        _binary_dirpath = os.path.abspath(os.path.join(sys.prefix, 'bin'))
        _ctx['BUILD_ENV']['PATH'] = f"{_binary_dirpath}{os.pathsep}{os.getenv('PATH', '')}"
    _env['EXTRA_CMAKE'].extend(['-G', 'Ninja'])
def _build_step_00():
    _extra_args_cmake: list[str] = _env['EXTRA_CMAKE']

    if _env['PKG_TYPE'] == 'static':
        _extra_args_cmake.extend(['-D', 'LLVM_BUILD_LLVM_DYLIB:BOOL=0'])
    if _env['PKG_TYPE'] == 'shared':
        _env['FUNC_EXIT'](f'unsupported pkg type: {_env["PKG_TYPE"]}')  # exited
        _extra_args_cmake.extend(['-D', 'LLVM_BUILD_LLVM_DYLIB:BOOL=1'])

    if _env['LIB_RELEASE'] == '0':
        _extra_args_cmake.extend(['-D', 'CMAKE_BUILD_TYPE=Debug'])
    if _env['LIB_RELEASE'] == '1':
        _ctx['PKG_INST_STRIP'] = '--strip'
        _extra_args_cmake.extend(['-D', 'CMAKE_BUILD_TYPE=Release'])


    _tblgen_dir = os.path.abspath(os.path.join(os.path.dirname(_env['PKG_INST_DIR']), '.NATIVE'))
    _tblgen_req = ((_env['PKG_PLATFORM'] == 'win-msvc') and (_env['CROSS_BUILD_ENABLED']))

    args = [
        _ctx['CMAKE_CMD'],
        '-S',  os.path.abspath(os.path.join(_env['SUBPROJ_SRC'], 'llvm')),
        '-D', f'CMAKE_PREFIX_PATH={";".join(_ctx["CMAKE_SEARCH_PATH"])}',
        '-D', f'CMAKE_FIND_ROOT_PATH={_env["SYSROOT"]};{";".join(_ctx["CMAKE_SEARCH_PATH"])}',
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
        '-D', f'LLVM_NATIVE_TOOL_DIR={os.path.abspath(os.path.join(_tblgen_dir, "bin"))}',
    ]
    args.extend(_extra_args_cmake)

    if _tblgen_req:
        shutil.rmtree(_tblgen_dir, ignore_errors=True); \
            os.makedirs(_tblgen_dir, exist_ok=True)

        _tblgen_build_args = []; _tblgen_build_args.extend(args)
        _tblgen_build_args_bdir_idx = 0
        _tblgen_build_args_zlib_idx = 0
        for i, entry in enumerate(_tblgen_build_args):
            if entry == '-B':
                _tblgen_build_args_bdir_idx = i + 1
            if entry.startswith('LLVM_ENABLE_ZLIB'):
                _tblgen_build_args_zlib_idx = i
        _tblgen_build_args[_tblgen_build_args_bdir_idx] = _tblgen_dir
        _tblgen_build_args[_tblgen_build_args_zlib_idx] = 'LLVM_ENABLE_ZLIB=OFF'

        _tblgen_build_env = _env['WIN32_MSVC_ENV_NATIVE']
        _tblgen_build_env['CFLAGS']   = '/utf-8'
        _tblgen_build_env['CXXFLAGS'] = _tblgen_build_env['CFLAGS']
        _env['FUNC_PROC'](env=_tblgen_build_env, args=_tblgen_build_args, shell=_ctx['SHELL_REQ'])

        _tblgen_build_targets = ['llvm-tblgen', 'clang-tblgen', 'lldb-tblgen', 'clang-tidy-confusable-chars-gen']
        _tblgen_build_args = [_ctx['CMAKE_CMD'], '--build', _tblgen_dir, '-j', _env['PARALLEL_JOBS'], '--target', ';'.join(_tblgen_build_targets)]
        _env['FUNC_PROC'](env=_tblgen_build_env, args=_tblgen_build_args, shell=_ctx['SHELL_REQ'])


    LLVM_ARCH = ''
    if _env['PKG_ARCH'] == 'amd64': LLVM_ARCH = 'X86'
    if _env['PKG_ARCH'] == 'arm64': LLVM_ARCH = 'AArch64'
    if _env['PKG_ARCH'] == 'armv7': LLVM_ARCH = 'ARM'
    if _env['PKG_PLATFORM'] == 'macosx':
        args.extend([
            '-D', f'LLVM_HOST_TRIPLE={_env["PKG_ARCH"]}-apple-darwin',
            '-D', f'LLVM_TARGET_ARCH={LLVM_ARCH}',
            '-D', f'CMAKE_C_HOST_COMPILER={_env["HOSTCC"]}',
            '-D', f'CMAKE_CXX_HOST_COMPILER={_env["HOSTCXX"]}',
        ])
    if (_env['PKG_PLATFORM'] == 'linux') and (_env['CROSS_BUILD_ENABLED']):
        args.extend([
            '-D', f'LLVM_HOST_TRIPLE={_env["CROSS_TARGET_TRIPLE"]}',
            '-D', f'LLVM_TARGET_ARCH={LLVM_ARCH}',
            '-D', f'CMAKE_C_HOST_COMPILER={_env["HOSTCC"]}',
            '-D', f'CMAKE_CXX_HOST_COMPILER={_env["HOSTCXX"]}',
        ])
    if _env['PKG_PLATFORM'] == 'win-mingw':
        _triple = ''
        if _env['PKG_ARCH'] == 'amd64': _triple = 'x86_64-w64-windows-gnu'
        if _env['PKG_ARCH'] == 'arm64': _triple = 'aarch64--w64-windows-gnu'
        args.extend([
            '-D', f'LLVM_HOST_TRIPLE={_triple}',
            '-D', f'LLVM_TARGET_ARCH={LLVM_ARCH}',
            '-D', f'CMAKE_C_HOST_COMPILER={_env["HOSTCC"]}',
            '-D', f'CMAKE_CXX_HOST_COMPILER={_env["HOSTCXX"]}',
        ])
    if _env['PKG_PLATFORM'] == 'win-msvc':
        args.extend([
            '-D',  'CMAKE_SYSTEM_NAME=Windows',
            '-D',  'CMAKE_CROSSCOMPILING:BOOL=TRUE',
            '-D', f'LLVM_HOST_TRIPLE={_env["CROSS_TARGET_TRIPLE"]}',
            '-D', f'LLVM_TARGET_ARCH={LLVM_ARCH}',
            '-D', f'CMAKE_C_HOST_COMPILER={_env["HOSTCC"]}',
            '-D', f'CMAKE_CXX_HOST_COMPILER={_env["HOSTCXX"]}',
        ])

    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args, shell=_ctx['SHELL_REQ'])
def _build_step_01():
    _build_targets = ['clangd', 'llvm-symbolizer', 'lldb', 'lldb-dap', 'lldb-instr']
    if _env.get('PLATFORM_LINUX', False):
        _build_targets.append('lldbIntelFeatures')
    if not _env.get('PLATFORM_APPLE', False):
        _build_targets.append('lldb-server')

    args = [_ctx['CMAKE_CMD'], '--build', _env['PKG_BULD_DIR'], '-j', _env['PARALLEL_JOBS'], '--target', ';'.join(_build_targets)]
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args, shell=_ctx['SHELL_REQ'])
def _build_step_02():
    args = [_ctx['CMAKE_CMD'], '--install', '<?>', '--component', '<?>']
    if _ctx['PKG_INST_STRIP']:
        args.append( _ctx['PKG_INST_STRIP'])

    args[2] = os.path.abspath(os.path.join(_env['PKG_BULD_DIR'], 'tools')); args[4] = 'llvm-symbolizer'
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args, shell=_ctx['SHELL_REQ'])

    args[2] = os.path.abspath(os.path.join(_env['PKG_BULD_DIR'], 'tools', 'lldb', 'tools')); args[4] = 'lldb'
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args, shell=_ctx['SHELL_REQ'])
    args[2] = os.path.abspath(os.path.join(_env['PKG_BULD_DIR'], 'tools', 'lldb', 'tools')); args[4] = 'lldb-argdumper'
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args, shell=_ctx['SHELL_REQ'])
    args[2] = os.path.abspath(os.path.join(_env['PKG_BULD_DIR'], 'tools', 'lldb', 'tools')); args[4] = 'lldb-dap'
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args, shell=_ctx['SHELL_REQ'])
    args[2] = os.path.abspath(os.path.join(_env['PKG_BULD_DIR'], 'tools', 'lldb', 'tools')); args[4] = 'lldb-instr'
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args, shell=_ctx['SHELL_REQ'])

    args[2] = os.path.abspath(os.path.join(_env['PKG_BULD_DIR'], 'tools', 'lldb')); args[4] = 'liblldb'
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args, shell=_ctx['SHELL_REQ'])
    args[2] = os.path.abspath(os.path.join(_env['PKG_BULD_DIR'], 'tools', 'clang')); args[4] = 'clangd'
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args, shell=_ctx['SHELL_REQ'])
    args[2] = os.path.abspath(os.path.join(_env['PKG_BULD_DIR'], 'tools', 'clang')); args[4] = 'clang-resource-headers'
    _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args, shell=_ctx['SHELL_REQ'])

    if _env.get('PLATFORM_LINUX', False):
        args[2] = os.path.abspath(os.path.join(_env['PKG_BULD_DIR'], 'tools', 'lldb', 'tools')); args[4] = 'lldbIntelFeatures'
        _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args, shell=_ctx['SHELL_REQ'])
    if _env.get('PLATFORM_APPLE', False):
        _src = '/Applications/Xcode.app/Contents/SharedFrameworks/LLDB.framework/Versions/A/Resources/debugserver'
        _dst = os.path.abspath(os.path.join(_env['PKG_INST_DIR'], 'bin', 'lldb-server'))
        os.symlink(_src, _dst, target_is_directory=False)
    else:
        args[2] = os.path.abspath(os.path.join(_env['PKG_BULD_DIR'], 'tools', 'lldb', 'tools')); args[4] = 'lldb-server'
        _env['FUNC_PROC'](env=_ctx['BUILD_ENV'], args=args, shell=_ctx['SHELL_REQ'])
