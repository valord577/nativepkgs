# fmt: off

import sys
sys.dont_write_bytecode = True

import io
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)


from pathlib import Path
from typing import NoReturn

PROJ_ROOT = (Path(__file__).absolute().resolve().parents[0]).as_posix()

def logv(str: object):
    print(f'--- {str}', file=sys.stderr)
def logi(str: object):
    print(f'[I] {str}', file=sys.stderr)
def logw(str: object):
    print(f'[W] {str}', file=sys.stderr)
def loge(str: object) -> NoReturn:
    print(f'[E] {str}', file=sys.stderr); sys.exit(1)

def loge_usage() -> NoReturn:
    loge(f'Usage: [python3] {PROJ_ROOT}/build_v2.py --help')

if __name__ == "__main__": loge_usage()
# ----------------------------

import http.client
import inspect
import json
import stat
import subprocess as sp
import os
import platform
import shutil
import urllib.request

from typing import Literal, cast, overload


# ----------------------------
ENVIRON = os.environ.copy()
ON_GITLAB_CI = (ENVIRON.get('GITLAB_CI') or '')      == 'true'
ON_GITHUB_CI = (ENVIRON.get('GITHUB_ACTIONS') or '') == 'true'
ON_CODE_EDIT = (not ON_GITLAB_CI) and (not ON_GITHUB_CI)
# ----------------------------
BUILD_DEFAULT_FEATURES = {
    'PKG_TYPE': 'static',
}
def feature(key: str) -> str:
    v = ENVIRON.get(key)
    if not v:
        return BUILD_DEFAULT_FEATURES[key]
    if key == 'PKG_TYPE':
        if v not in ['static', 'shared']:
            return BUILD_DEFAULT_FEATURES[key]
        return v
    else:
        return v
def feature_build_shared() -> str:
    return '1' if feature('PKG_TYPE') == 'shared' else '0'
# ----------------------------
def gha_append_env(env: "dict[str, str]"):
    if not ON_GITHUB_CI:
        return
    with open(feature('GITHUB_ENV'), 'a') as f:
        for k, v in env.items():
            logv(f'append github action env: {k}={v}')
            _ = f.write(f'{k}={v}\n')

def append_pkgconf_search_path(env: "dict[str, str]", dir: "Path"):
    new = dir.absolute().as_posix()
    if old := env.get('PKG_CONFIG_PATH'):
        new = (new + os.pathsep + old)
    env['PKG_CONFIG_PATH'] = new
# ----------------------------
NATIVE_PLAT = {
    'linux':   'linux',
    'darwin':  'macosx',
    'windows': 'windows',
}[platform.system().lower()]
NATIVE_ARCH = {
    'amd64':   'amd64',
    'x86_64':  'amd64',
    'arm64':   'arm64',
    'aarch64': 'arm64',
}[platform.machine().lower()]

fext = ('.exe' if NATIVE_PLAT == 'windows' else '')
# ----------------------------
def detect_cpu_count() -> int:
    if NATIVE_PLAT == 'linux':
        return len(os.sched_getaffinity(0))
    return os.cpu_count() or 2
# ----------------------------
def detect_libc_runtime() -> str:
    if NATIVE_PLAT != 'linux':
        return ''


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
# ----------------------------
def current_func_name() -> str:
    return inspect.stack()[1][3]
# ----------------------------
def get_cross_toolchain_dir(target_plat: str) -> str:
    env = 'CROSS_TOOLCHAIN_ROOT'
    if dir := ENVIRON.get(env):
        return dir

    base = Path('/opt/toolchain')
    if base_env := ENVIRON.get('CROSS_TOOLCHAIN_BASE'):
        base = Path(base_env)
    dir = {
        'linux':     base / 'linux310-gcc7',
        'win-mingw': base / 'llvm-mingw',
        'android':   base / 'ndk-r27d-slim',
    }[target_plat]
    if dir.exists() and dir.is_dir():
        return dir.absolute().as_posix()
    loge(f'missing required env: `{env}`')
# ----------------------------
@overload
def run_as_subprocess(args: "str | list[str]",
    cwd: "str | Path | None" = None, env: "dict[str, str] | None" = None, shell: bool = False,
    *,
    stdout: "int | None" = None,
) -> None: ...
@overload
def run_as_subprocess(args: "str | list[str]",
    cwd: "str | Path | None" = None, env: "dict[str, str] | None" = None, shell: bool = False,
    *,
    collect_stdout: Literal[True],
) -> str: ...
def run_as_subprocess(args: "str | list[str]",
    cwd: "str | Path | None" = None, env: "dict[str, str] | None" = None, shell: bool = False,
    collect_stdout: bool = False, stdout: "int | None" = None,
) -> "str | None":
    logi(f'subprocess cmdline: {args}')
    if collect_stdout:
        stdout = sp.PIPE
    if not env:
        env = ENVIRON
    proc = sp.run(args=args, cwd=cwd, env=env, check=True, shell=shell, stdout=stdout, text=True,)
    return proc.stdout if collect_stdout else None

def runpy(args: "list[str]", cwd: "str | Path | None" = None):
    run_as_subprocess(args=[(Path(sys.executable)).absolute().as_posix(), *args], cwd=cwd)
def runpy_pip(pkgs: "list[str]"):
    args = ['-m', 'pip', 'install', '--upgrade']
    if not ON_GITHUB_CI:
        args.extend(['--trusted-host', 'repo.huaweicloud.com'])
        args.extend(['-i', 'https://repo.huaweicloud.com/repository/pypi/simple'])
    args.extend(['pip', *pkgs])
    runpy(args=args)
# ----------------------------
def unzip_with_softlink(zipfile: Path, extract_dir: "str | None" = None, is_msys64: bool = False):
    if not extract_dir:
        extract_dir = zipfile.parent.as_posix()
    cmd = ['unzip', '-o', zipfile.as_posix(), '-d', extract_dir]
    if (NATIVE_PLAT == 'windows') and (is_msys64):
        cmd = ['C:/msys64/usr/bin/bash.exe', '-c', ' '.join(cmd)]
    run_as_subprocess(args=cmd)
# ----------------------------
RCLONE_EXEC = (Path(PROJ_ROOT) / '.github' / f'rclone{fext}')
if ON_GITHUB_CI and (not RCLONE_EXEC.exists()):
    plat = {
        'linux':   'linux',
        'macosx':  'osx',
        'windows': 'windows',
    }[NATIVE_PLAT]
    arch = NATIVE_ARCH

    _rclone_dir = RCLONE_EXEC.parent

    download_link = f'https://downloads.rclone.org/rclone-current-{plat}-{arch}.zip'
    rclone_zipfile = (_rclone_dir / 'rclone.zip')
    logv(f'downloading rclone from "{download_link}" > "{rclone_zipfile.as_posix()}"')
    with cast(http.client.HTTPResponse,
        urllib.request.urlopen(
            urllib.request.Request(download_link)
        )
    ) as resp:
        if resp.status != 200:
            loge(f"respcode: {resp.status}, respbody: ->\n{resp.read().decode(errors='ignore')}")
        with rclone_zipfile.open('wb') as dst:
            shutil.copyfileobj(resp, dst)
    run_as_subprocess(args=['unzip', '-j', rclone_zipfile.as_posix(), f'*/rclone{fext}', '-d', _rclone_dir.as_posix()])

    rclone_conf_content = f'''\
[r2]
type = s3
provider = Cloudflare
access_key_id = {feature("S3_R2_ACCESS_KEY")}
secret_access_key = {feature("S3_R2_SECRET_KEY")}
region = {feature("S3_R2_STORAGE_REGION")}
endpoint = https://{feature("S3_R2_ACCOUNT_ID")}.r2.cloudflarestorage.com
no_check_bucket = true
no_head = true
'''
    _ = (_rclone_dir / 'rclone.conf').write_text(rclone_conf_content)
# ----------------------------
def win32_msvc_detect() -> "tuple[Path, Path]":
    if NATIVE_PLAT != 'windows':
        loge(f'only works on windows, host os: {NATIVE_PLAT}')

    msvc_search_path: "list[Path]" = []
    if _userdef := ENVIRON.get('MSVC_INSTALL_DIR'):
        msvc_search_path.append(Path(_userdef))
    else:
        # auto search vs install dir
        msvc_install_dir = [
            'C:/Program Files/Microsoft Visual Studio',
            'C:/Program Files (x86)/Microsoft Visual Studio',
        ]
        valid_products = {'BuildTools', 'Community', 'Professional', 'Enterprise'}
        for dir in msvc_install_dir:
            for product in Path(dir).glob('*/*'):
                if (not product.is_dir()) or (product.name not in valid_products):
                    continue
                year = int(product.parents[0].name)
                if year < 2019:
                    continue
                msvc_search_path.append(product)

    msvc_dir: "Path | None" = None; msvc_devshell: "Path | None" = None
    for dir in msvc_search_path:
        if (not dir.exists()) or (not dir.is_dir()):
            continue
        dll = (dir / 'Common7' / 'Tools' / 'Microsoft.VisualStudio.DevShell.dll')
        if dll.exists() and dll.is_file():
            msvc_dir = dir; msvc_devshell = dll; break
    if (not msvc_dir) or (not msvc_devshell):
        loge(f'failed to search msvc environment')
    logv(f'load msvc devshell: "{msvc_devshell.as_posix()}"')
    return (msvc_dir, msvc_devshell)

def win32_msvc_dump_env(msvc_dir: Path, msvc_devshell: Path, target_arch: str) -> "dict[str, str]":
    if NATIVE_PLAT != 'windows':
        loge(f'only works on windows, host os: {NATIVE_PLAT}')

    msvc_env_json = (Path(PROJ_ROOT) / 'tmp' / f'.msvc_env_{target_arch}.json'); \
        msvc_env_json.parent.mkdir(parents=True, exist_ok=True)

    # Only supports access to the VS DevShell from PowerShell
    #  - https://learn.microsoft.com/visualstudio/ide/reference/command-prompt-powershell#developer-powershell
    vs_devshell_arg = f'-host_arch={NATIVE_ARCH} -arch={target_arch}'

    pwsh_script_blk  = f'Import-Module "{msvc_devshell}"; '
    pwsh_script_blk += f'Enter-VsDevShell -VsInstallPath "{msvc_dir}" -SkipAutomaticLocation -DevCmdArguments "{vs_devshell_arg}"; '
    pwsh_script_blk += f'Get-ChildItem Env: | Select-Object -Property Name,Value | ConvertTo-Json -Depth 1  1>{msvc_env_json.as_posix()}; '
    run_as_subprocess(['pwsh',
        '-WorkingDirectory', PROJ_ROOT,
        '-NonInteractive',
        '-NoProfileLoadTime',
        '-ExecutionPolicy', 'Bypass',
        '-Command', pwsh_script_blk
    ])

    msvc_env: dict[str, str] = {}
    for kv in cast("list[dict[str, str]]", json.loads(msvc_env_json.read_text())):
        msvc_env[kv['Name']] = kv['Value']
    return msvc_env
# ----------------------------
def apple_crossfiles_generate(
    target_plat: str, target_arch: str, apple_arch: str, sdk: str, deployment_name: str, deployment_vers: str,
) -> "tuple[Path, Path]":
    if NATIVE_PLAT != 'macosx':
        loge(f'only works on macosx, host os: {NATIVE_PLAT}')

    pkgconf_wrapper = (Path(PROJ_ROOT) / 'tmp' / f'.apple_pkgconf_wrapper.{target_plat}-{target_arch}'); \
        pkgconf_wrapper.parent.mkdir(parents=True, exist_ok=True)
    pkgconf_wrapper_content = '''\
#!/usr/bin/env sh
set -e

PKG_CONFIG_LIBDIR="${PKG_CONFIG_LIBDIR}:@SYSROOT@/usr/lib"
export PKG_CONFIG_LIBDIR

if command -v pkgconf >/dev/null 2>&1 ; then
  exec pkgconf "$@"
else
  exec pkg-config "$@"
fi
'''
    pkgconf_wrapper_content = pkgconf_wrapper_content.replace('@SYSROOT@', sdk)
    if not pkgconf_wrapper.exists():
        _ = pkgconf_wrapper.write_text(pkgconf_wrapper_content)
        pkgconf_wrapper.chmod(stat.S_IRWXU)


    _meson_subsystem = {
        'macosx':          'macos',
        'iphoneos':        'ios',
        'iphonesimulator': 'ios-simulator',
    }[target_plat]

    _meson_arch = {
        'amd64': 'x86_64',
        'arm64': 'aarch64',
    }[target_arch]

    meson_crossfile = (pkgconf_wrapper.parent / f'.apple_meson_crossfile.{target_plat}-{target_arch}'); \
    meson_crossfile_content = f'''\
[constants]
prefix = ''
ccache = []
ccflags = ['-arch', '{apple_arch}', '-isysroot', '{sdk}', '-m{deployment_name}-version-min={deployment_vers}']

[host_machine]
system = 'darwin'
kernel = 'xnu'
subsystem = '{_meson_subsystem}'
cpu_family = '{_meson_arch}'
cpu = '{_meson_arch}'
endian = 'little'

[properties]
needs_exe_wrapper = true

[binaries]
c   = ccache + [prefix / 'clang']   + ccflags
cpp = ccache + [prefix / 'clang++'] + ccflags
ar = prefix / 'ar'
as = prefix / 'as'
nm = prefix / 'nm'
objcopy = prefix / 'objcopy'
strip   = prefix / 'strip'
ranlib  = prefix / 'ranlib'
pkg-config = '@DIRNAME@/{pkgconf_wrapper.name}'
cmake = 'cmake'
'''
    if not meson_crossfile.exists():
        _ = meson_crossfile.write_text(meson_crossfile_content)

    return (pkgconf_wrapper, meson_crossfile)
# ----------------------------
