#!/usr/bin/env python3

# fmt: off

import datetime as dt
import importlib.util
import os
import platform
import pprint
import shutil
import subprocess as sp
import sys
from typing import NoReturn


# set when only building one module
_unique_module: str = ''



PROJ_ROOT = os.path.abspath(os.path.dirname(__file__))
# ----------------------------
# optimize
#  - 0 DEBUG
#  - 1 RELEASE (default)
# ----------------------------
LIB_RELEASE = '0' if os.getenv('LIB_RELEASE', '') == '0' else '1'
# ----------------------------
# static or shared
# ----------------------------
PKG_TYPE = 'shared' if os.getenv('PKG_TYPE', '') == 'shared' else 'static'
# ----------------------------
# ci runtime
# ----------------------------
ON_GITLAB_CI = os.getenv('GITLAB_CI', '')      == 'true'
ON_GITHUB_CI = os.getenv('GITHUB_ACTIONS', '') == 'true'

class _ctx:
    def __init__(self, module: str):
        self.module = module
        self.script = self._lazy_import()
        self.native_plat = platform.system().lower()
        self.native_arch = platform.machine().lower()
        self.target_plat = ''
        self.target_arch = ''
        self.target_libc = ''
        self.env_passthrough = {}
        self.extra_cmake: list[str] = []
        self.extra_meson: list[str] = []
        self.cross_build_enabled = False
        self.cross_target_triple = ''
        self.cross_pkgconfig_bin = ''

        self.ccache = ''
        if ccache := shutil.which('ccache'):
            self.ccache = ccache
        if self.ccache:
            self.extra_cmake.extend(['-D', 'CMAKE_C_COMPILER_LAUNCHER=ccache'])
            self.extra_cmake.extend(['-D', 'CMAKE_CXX_COMPILER_LAUNCHER=ccache'])

        if sys.platform == 'linux':
            self.nproc = len(os.sched_getaffinity(0))
        else:
            _nproc = os.cpu_count()
            self.nproc = _nproc if _nproc else 0

        self.s3_bucket = ''
        self.s3_client = None
        if ON_GITHUB_CI:
            _util_func__pip_install(['boto3==1.23.10'])
            import boto3
            self.s3_bucket = os.getenv('S3_R2_STORAGE_BUCKET', '')
            self.s3_client = boto3.client(
                service_name = 's3',
                region_name  = os.getenv('S3_R2_STORAGE_REGION', 'auto'),
                endpoint_url = f'https://{os.getenv("S3_R2_ACCOUNT_ID", "")}.r2.cloudflarestorage.com',
                aws_access_key_id = os.getenv('S3_R2_ACCESS_KEY', ''),
                aws_secret_access_key = os.getenv('S3_R2_SECRET_KEY', ''),
            )


    def _lazy_import(self):
        name = self.module
        path = os.path.abspath(os.path.join(PROJ_ROOT, 'scripts', f'{name}.py'))
        spec = importlib.util.spec_from_file_location('', path)
        if not spec:
            show_errmsg(f'missing module[{name}]: "failed @importlib.util.spec_from_file_location"')
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # type: ignore
        except FileNotFoundError:
            show_errmsg(f'missing module[{name}]: "no such file [{path}]"')
        if not hasattr(module, 'module_init'):
            show_errmsg(f'missing module[{name}]: "no attr [module_init]"')
        return module

    def getenv(self) -> dict:
        env = {
            **self.env_passthrough,
            **{
                'PROJ_ROOT': PROJ_ROOT,

                'LIB_RELEASE': LIB_RELEASE,
                'PARALLEL_JOBS': str(self.nproc),

                'FUNC_PROC': _util_func__subprocess,
                'FUNC_PYPI': _util_func__pip_install,
                'FUNC_PKGC': _util_func__dl_pkgc,
                'FUNC_EXIT': show_errmsg,

                'PKG_NAME': self.module,
                'PKG_TYPE': PKG_TYPE,
                'PKG_PLATFORM': self.target_plat,
                'PKG_ARCH': self.target_arch,
                'PKG_LIBC': self.target_libc,
                'PKG_ARCH_LIBC': self.target_arch,

                'EXTRA_CMAKE': self.extra_cmake,
                'EXTRA_MESON': self.extra_meson,

                'CROSS_PKGCONFIG_BIN': self.cross_pkgconfig_bin,
                'CROSS_BUILD_ENABLED': self.cross_build_enabled,
                'CROSS_TARGET_TRIPLE': self.cross_target_triple,
            },
        }
        if env['PKG_LIBC']:
            env['PKG_ARCH_LIBC'] = f"{env['PKG_ARCH']}-{env['PKG_LIBC']}"
        env['PKG_BULD_DIR'] = os.path.abspath(os.path.join(PROJ_ROOT, 'tmp', env['PKG_NAME'], env['PKG_PLATFORM'], env['PKG_ARCH_LIBC']))
        env['PKG_INST_DIR'] = os.path.abspath(os.path.join(PROJ_ROOT, 'out', env['PKG_NAME'], env['PKG_PLATFORM'], env['PKG_ARCH_LIBC']))
        if ON_GITLAB_CI or ON_GITHUB_CI:
            env['PKG_INST_DIR'] = os.getenv('INST_DIR') or env['PKG_INST_DIR']

        if not _unique_module:
            env['SUBPROJ_SRC'] = os.path.abspath(os.path.join(PROJ_ROOT, '.deps', env['PKG_NAME']))
            env['SUBPROJ_SRC_PATCHES'] = os.path.abspath(os.path.join(PROJ_ROOT, 'patches', env['PKG_NAME']))
        return env


def _self_func__tree(basepath: str, depth: int = 0):
    # name, path, depth, is_last, is_symlink, is_dir
    _stack = [(basepath, basepath, -1, '-1', os.path.islink(basepath), os.path.isdir(basepath))]
    while _stack:
        _name, _path, _depth, _is_last, _is_symlink, _is_dir = _entry = _stack.pop()
        if _depth == -1:
            print(_name, file=sys.stderr)
        else:
            print(f"{'│   ' * _depth}{'└── ' if _is_last == '1' else '├── '}{_name}{f' -> {os.readlink(_path)}' if _is_symlink else ''}", file=sys.stderr)

        if (not _is_dir) or (depth > 0 and _depth + 1 >= depth):
            continue
        with os.scandir(_path) as it:
            entries = sorted(it, key=lambda e: e.name)
            entries_dir_first = [ d for d in entries if d.is_dir() ]
            entries_dir_first.extend([ f for f in entries if not f.is_dir() ])
            for i, entry in enumerate(reversed(entries_dir_first)):
                _stack.append(
                    (
                        entry.name,
                        entry.path,
                        _depth + 1,
                        '1' if i == 0 else '0',
                        entry.is_symlink(),
                        entry.is_dir(follow_symlinks=False),
                    )
                )
def _util_func__dl_pkgc(_ctx: dict, _env: dict[str, str],
    pkg_name: str, pkg_version: str, pkg_type: str, pkg_extra='',
):
    _3rd_deps_dir = os.path.abspath(os.path.join(PROJ_ROOT, f".lib.{_env['PKG_PLATFORM']}.{_env['PKG_ARCH_LIBC']}"))
    _this_lib_dir = os.path.abspath(os.path.join(_3rd_deps_dir, pkg_name))
    os.makedirs(_3rd_deps_dir, exist_ok=True)
    if False:
        pass
    elif ON_GITLAB_CI:
        pass
    elif ON_GITHUB_CI:
        pass
    else:
        try:
            os.remove(_this_lib_dir)
        except:
            pass
        _src = os.path.abspath(os.path.join(PROJ_ROOT, 'out', pkg_name, _env['PKG_PLATFORM'], _env['PKG_ARCH_LIBC']))
        os.symlink(_src, _this_lib_dir, target_is_directory=True)

    _ctx['PKG_CONFIG_PATH'].append(os.path.abspath(os.path.join(_this_lib_dir, 'lib', 'pkgconfig')))
    if pkg_type == 'shared':
        _ctx['PKG_3RD_DEPS_SHARED'].append(_this_lib_dir)
    if pkg_type == 'static':
        _ctx['PKG_3RD_DEPS_STATIC'].append(_this_lib_dir)
def _util_func__subprocess(args: list[str],
    cwd: str | None = None, env: dict[str, str] | None = None,
):
    print(f'>>>> subprocess cmdline: {args}', file=sys.stderr)
    proc = sp.run(args=args, cwd=cwd, env=env)
    if proc.returncode != 0:
        print(f'>>>> subprocess exitcode: {proc.returncode}', file=sys.stderr)
        sys.exit(proc.returncode)
def _util_func__pip_install(packages: list[str]):
    args = [sys.executable, '-m', 'pip', 'install', '--upgrade']
    if not ON_GITHUB_CI:
        args.extend(['-i', 'https://mirrors.bfsu.edu.cn/pypi/web/simple'])
    args.extend(packages)
    _util_func__subprocess(args)



def _setctx_linux(
    ctx: _ctx, _native: bool, _tuple: tuple[str, ...],
):
    if ctx.native_plat != 'linux':
        show_errmsg(f'unsupported host os: {ctx.native_plat}')
    ctx.env_passthrough['PLATFORM_LINUX'] = True

    def _get_linux_libc_type() -> str:
        import mmap

        _libc_type = ''
        with open(sys.executable, 'rb') as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
                if -1 != m.find(b'GLIBC_'):
                    _libc_type = 'gnu'
                if -1 != m.find(b'musl-'):
                    _libc_type = 'musl'
        return _libc_type

    if _native:
        if False:
            pass
        elif ctx.native_arch == 'aarch64':
            ctx.target_arch = 'arm64'
        elif ctx.native_arch == 'x86_64':
            ctx.target_arch = 'amd64'
        else:
            show_errmsg(f'unsupported native arch: {ctx.native_arch}')

        ctx.target_libc = _get_linux_libc_type()
        if not ctx.target_libc:
            show_errmsg(f'unknown native libc type')

        if ctx.ccache:
            for cc  in ['cc',  'clang',   'gcc']:
                if _cc  := shutil.which(cc):
                    ctx.env_passthrough['CC']  = f'{ctx.ccache} {_cc}'
                    break
            for cxx in ['c++', 'clang++', 'g++']:
                if _cxx := shutil.which(cxx):
                    ctx.env_passthrough['CXX'] = f'{ctx.ccache} {_cxx}'
                    break
    else:
        CROSS_TOOLCHAIN_ROOT = os.getenv('CROSS_TOOLCHAIN_ROOT')
        if not CROSS_TOOLCHAIN_ROOT:
            show_errmsg('missing required env: `CROSS_TOOLCHAIN_ROOT`')

        ctx.cross_build_enabled = True
        ctx.target_arch = _tuple[2]
        ctx.target_libc = _tuple[3]
        if ctx.target_arch == 'arm64':
            ctx.cross_target_triple = f'aarch64-unknown-linux-{ctx.target_libc}'
        if ctx.target_arch == 'amd64':
            ctx.cross_target_triple = f'x86_64-pc-linux-{ctx.target_libc}'
        if ctx.target_arch == 'armv7':
            ctx.cross_target_triple = f'arm-unknown-linux-{ctx.target_libc}'
        ctx.env_passthrough['SYSROOT'] = sysroot = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, ctx.cross_target_triple))

        ctx.env_passthrough['CROSS_LDFLAGS'] = f'-fuse-ld=lld --sysroot={sysroot}'
        ctx.env_passthrough['CROSS_FLAGS'] = f'--target={ctx.cross_target_triple} --gcc-toolchain={sysroot}/usr --sysroot={sysroot}'
        if ctx.target_arch == 'armv7':
            ctx.env_passthrough['CROSS_FLAGS'] += ' -march=armv7-a -mfpu=neon-vfpv4'
        ctx.env_passthrough['HOSTCC']  = shutil.which('clang')
        ctx.env_passthrough['HOSTCXX'] = shutil.which('clang++')
        ctx.env_passthrough['HOSTCPP'] = shutil.which('clang-cpp')
        ctx.env_passthrough['CC']  = f"{ctx.ccache} {ctx.env_passthrough['HOSTCC']}  {ctx.env_passthrough['CROSS_FLAGS']}"
        ctx.env_passthrough['CXX'] = f"{ctx.ccache} {ctx.env_passthrough['HOSTCXX']} {ctx.env_passthrough['CROSS_FLAGS']}"
        ctx.env_passthrough['CPP'] = f"{ctx.env_passthrough['HOSTCPP']} {ctx.env_passthrough['CROSS_FLAGS']}"

        ctx.env_passthrough['LD'] = shutil.which('ld.lld')
        ctx.env_passthrough['NM'] = shutil.which('llvm-nm')
        ctx.env_passthrough['AR'] = shutil.which('llvm-ar')
        ctx.env_passthrough['AS'] = shutil.which('llvm-as')
        ctx.env_passthrough['RANLIB']  = shutil.which('llvm-ranlib')
        ctx.env_passthrough['STRIP']   = shutil.which('llvm-strip')
        ctx.env_passthrough['READELF'] = shutil.which('llvm-readelf')

        # cmake toolchain file
        CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE = os.getenv('CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE')
        if not CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE:
            CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'toolchain-cmake-template'))
        CROSS_TOOLCHAIN_FILE_CMAKE = f'{CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE}.{ctx.cross_target_triple}'
        ctx.extra_cmake.extend(["-D", f"CMAKE_TOOLCHAIN_FILE={CROSS_TOOLCHAIN_FILE_CMAKE}"])
        # meson toolchain file
        CROSS_TOOLCHAIN_FILE_PREFIX_MESON = os.getenv('CROSS_TOOLCHAIN_FILE_PREFIX_MESON')
        if not CROSS_TOOLCHAIN_FILE_PREFIX_MESON:
            CROSS_TOOLCHAIN_FILE_PREFIX_MESON = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'toolchain-meson-template'))
        CROSS_TOOLCHAIN_FILE_MESON = f'{CROSS_TOOLCHAIN_FILE_PREFIX_MESON}.{ctx.cross_target_triple}'
        ctx.extra_meson.extend(["--cross-file", CROSS_TOOLCHAIN_FILE_MESON])
        # pkgconf bin
        CROSS_TOOLCHAIN_PKGCONF_PREFIX = os.getenv('CROSS_TOOLCHAIN_PKGCONF_PREFIX')
        if not CROSS_TOOLCHAIN_PKGCONF_PREFIX:
            CROSS_TOOLCHAIN_PKGCONF_PREFIX = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'pkgconf-wrapper'))
        ctx.cross_pkgconfig_bin = f'{CROSS_TOOLCHAIN_PKGCONF_PREFIX}.{ctx.cross_target_triple}'
def _setctx_apple(
    ctx: _ctx, _native: bool, _tuple: tuple[str, ...],
):
    pass
def _setctx_win32_mingw(
    ctx: _ctx, _native: bool, _tuple: tuple[str, ...],
):
    if ctx.native_plat != 'linux':
        show_errmsg(f'unsupported host os: {ctx.native_plat}')
    ctx.env_passthrough['PLATFORM_WIN32'] = True

    CROSS_TOOLCHAIN_ROOT = os.getenv('CROSS_TOOLCHAIN_ROOT')
    if not CROSS_TOOLCHAIN_ROOT:
        show_errmsg('missing required env: `CROSS_TOOLCHAIN_ROOT`')

    ctx.cross_build_enabled = True
    ctx.target_arch = _tuple[1]
    if ctx.target_arch == 'arm64':
        ctx.cross_target_triple = f'aarch64-w64-mingw32'
    if ctx.target_arch == 'amd64':
        ctx.cross_target_triple = f'x86_64-w64-mingw32'
    _target_arch = ctx.cross_target_triple[:-len('-w64-mingw32')]
    ctx.env_passthrough['SYSROOT'] = sysroot = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, ctx.cross_target_triple))

    ctx.env_passthrough['HOSTCC']  = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'bin', 'clang'))
    ctx.env_passthrough['HOSTCXX'] = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'bin', 'clang++'))
    ctx.env_passthrough['HOSTCPP'] = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'bin', 'clang-cpp'))
    ctx.env_passthrough['CC']  = f"{ctx.ccache} {os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'bin', f'{ctx.cross_target_triple}-clang'))}"
    ctx.env_passthrough['CXX'] = f"{ctx.ccache} {os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'bin', f'{ctx.cross_target_triple}-clang++'))}"
    ctx.env_passthrough['WINDRES'] = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'bin', f'{ctx.cross_target_triple}-windres'))

    ctx.env_passthrough['LD'] = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'bin', f'{ctx.cross_target_triple}-ld'))
    ctx.env_passthrough['NM'] = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'bin', f'{ctx.cross_target_triple}-nm'))
    ctx.env_passthrough['AR'] = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'bin', f'{ctx.cross_target_triple}-ar'))
    ctx.env_passthrough['AS'] = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'bin', f'{ctx.cross_target_triple}-as'))
    ctx.env_passthrough['RANLIB'] = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'bin', f'{ctx.cross_target_triple}-ranlib'))
    ctx.env_passthrough['STRIP']  = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'bin', f'{ctx.cross_target_triple}-strip'))


    # cmake toolchain file
    CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE = os.getenv('CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE')
    if not CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE:
        CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'toolchain-cmake-template'))
    CROSS_TOOLCHAIN_FILE_CMAKE = f'{CROSS_TOOLCHAIN_FILE_PREFIX_CMAKE}.{_target_arch}'
    ctx.extra_cmake.extend(["-D", f"CMAKE_TOOLCHAIN_FILE={CROSS_TOOLCHAIN_FILE_CMAKE}"])
    # meson toolchain file
    CROSS_TOOLCHAIN_FILE_PREFIX_MESON = os.getenv('CROSS_TOOLCHAIN_FILE_PREFIX_MESON')
    if not CROSS_TOOLCHAIN_FILE_PREFIX_MESON:
        CROSS_TOOLCHAIN_FILE_PREFIX_MESON = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'toolchain-meson-template'))
    CROSS_TOOLCHAIN_FILE_MESON = f'{CROSS_TOOLCHAIN_FILE_PREFIX_MESON}.{_target_arch}'
    ctx.extra_meson.extend(["--cross-file", CROSS_TOOLCHAIN_FILE_MESON])
    # pkgconf bin
    CROSS_TOOLCHAIN_PKGCONF_PREFIX = os.getenv('CROSS_TOOLCHAIN_PKGCONF_PREFIX')
    if not CROSS_TOOLCHAIN_PKGCONF_PREFIX:
        CROSS_TOOLCHAIN_PKGCONF_PREFIX = os.path.abspath(os.path.join(CROSS_TOOLCHAIN_ROOT, 'pkgconf-wrapper'))
    ctx.cross_pkgconfig_bin = f'{CROSS_TOOLCHAIN_PKGCONF_PREFIX}.{_target_arch}'
def _setctx_win32_msvc(
    ctx: _ctx, _native: bool, _tuple: tuple[str, ...],
):
    pass


_targets = {
    'linux': {
        'native': True,
        'setctx': _setctx_linux,
        'tuples': [
            ('linux', 'crossbuild', 'amd64', 'gnu'),
            ('linux', 'crossbuild', 'arm64', 'gnu'),
            ('linux', 'crossbuild', 'armv7', 'gnueabihf'),
            ('linux', 'crossbuild', 'amd64', 'musl'),
            ('linux', 'crossbuild', 'arm64', 'musl'),
        ],
    },
    'macosx': {
        'native': True,
        'setctx': _setctx_apple,
        'tuples': [
            ('macosx', 'arm64'),
            ('macosx', 'amd64'),
        ],
    },
    'iphoneos': {
        'native': False,
        'setctx': _setctx_apple,
        'tuples': [
            ('iphoneos', 'arm64'),
        ],
    },
    'iphonesimulator': {
        'native': False,
        'setctx': _setctx_apple,
        'tuples': [
            ('iphonesimulator', 'arm64'),
            ('iphonesimulator', 'amd64'),
        ],
    },
    'win-msvc': {
        'native': True,
        'setctx': _setctx_win32_msvc,
        'tuples': [
            ('win-msvc', 'arm64'),
            ('win-msvc', 'amd64'),
        ],
    },
    'win-mingw': {
        'native': False,
        'setctx': _setctx_win32_mingw,
        'tuples': [
            ('win-mingw', 'arm64'),
            ('win-mingw', 'amd64'),
        ],
    },
}

def show_errmsg(errmsg: str) -> NoReturn:
    print(f'[e] {errmsg}', file=sys.stderr)
    sys.exit(1)
def show_help(exitcode = 1) -> NoReturn:
    _native_flag_width = 0
    for k, v in _targets.items():
        if v['native'] and len(k) > _native_flag_width:
            _native_flag_width = len(k) + 1

    _targets_help_str = ''
    for k, v in _targets.items():
        _targets_help_str += f'    {k.ljust(_native_flag_width)}{"(* native)" if v["native"] else ""}\n'
        for tgt in v['tuples']:
            _targets_help_str += f'        {" ".join(tgt[1:])}\n'

    help_str  = f'Usage: {sys.argv[0]} -h|--help\n'
    help_str += f'Usage: {sys.argv[0]} [target] {"" if _unique_module else "-m|--module <module>"}\n\n'
    help_str += f'Target Options:\n{_targets_help_str}\n'
    print(help_str[:-1], file=sys.stderr)
    sys.exit(exitcode)


if __name__ == "__main__":
    if sys.version_info < (3, 6):
        show_errmsg(f'Required Python Interpreter ≥ 3.6')
    if sys.prefix == sys.base_prefix:
        show_errmsg(f'Please run this script in a [virtual environment](https://docs.python.org/3/library/venv.html)')


    argv_tgt: list[str] = []
    argv_mod: str = _unique_module
    argv = sys.argv[1:]; argc = len(argv); i = 0
    while i < argc:
        arg = argv[i]; i += 1
        if False:
            pass
        elif arg.startswith('-h') or arg.startswith('--help'):
            show_help(0)  # exited
        elif arg.startswith('-m') or arg.startswith('--module'):
            if not _unique_module:
                argv_mod = argv[i]
            i += 1
        else:
            argv_tgt.append(arg)
    if not argv_mod:
        show_errmsg(f'Please declare the module to be built')

    argc_tgt = len(argv_tgt)
    ctx = _ctx(module=argv_mod)
    if argc_tgt < 1:
        if False:
            pass
        elif ctx.native_plat == 'linux':
            argc_tgt +=1; argv_tgt.append('linux')
        elif ctx.native_plat == 'darwin':
            argc_tgt +=1; argv_tgt.append('macosx')
        elif ctx.native_plat == 'windows':
            argc_tgt +=1; argv_tgt.append('win-msvc')
        else:
            show_errmsg(f'unsupported native platform: {ctx.native_plat}')

    ctx.target_plat = argv_tgt[0]
    _target = _targets.get(ctx.target_plat)
    if not _target:
        show_errmsg(f'unsupported target platform: {ctx.target_plat}')

    _tuple: tuple[str, ...] | None = None
    if argc_tgt > 1:
        # check target tuple
        _tuple = tuple(argv_tgt)
        if not (_tuple in _target['tuples']):
            show_errmsg(f'unsupported target tuple: {_tuple}')
    _is_native_build = ((argc_tgt == 1) and (_target['native']))
    if (_is_native_build) and (not _tuple):
        show_errmsg(f'unsupported native build: {ctx.target_plat}')
    _target['setctx'](ctx, _is_native_build, _tuple)


    build_env = ctx.getenv()
    if os.getenv('NATIVEPKGS_RUNTIME_VERBOSE', '0') == '1':
        pprint.pp(build_env, indent=2, width=512)

    if build_env['SUBPROJ_SRC']:
        os.makedirs(build_env['SUBPROJ_SRC'], exist_ok=True)
    shutil.rmtree(build_env['PKG_BULD_DIR'], ignore_errors=True); \
        os.makedirs(build_env['PKG_BULD_DIR'], exist_ok=True)
    shutil.rmtree(build_env['PKG_INST_DIR'], ignore_errors=True); \
        os.makedirs(build_env['PKG_INST_DIR'], exist_ok=True)

    build_steps = ctx.script.module_init(build_env)
    for func in build_steps:
        func()
    _self_func__tree(build_env['PKG_INST_DIR'], depth=3)
    print(f'──── Build Done @{dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%S %Z")} ────', file=sys.stderr)
