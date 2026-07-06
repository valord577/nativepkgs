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
# ----------------------------
def dozip_with_softlink(filepath: Path, zipname: "str | None" = None):
    if not zipname:
        zipname = filepath.name

    shell = 'sh'
    wkdir = filepath.parent.absolute().as_posix()
    if (NATIVE_PLAT == 'windows'):
        shell = 'C:/msys64/usr/bin/bash.exe'
        wkdir = f'$(cygpath -u "{wkdir}")'
    cmdline = f'zip -ry {zipname}.zip {filepath.name}'
    run_as_subprocess(args=[shell, '-c', f'cd {wkdir}; {cmdline}'])
def unzip_with_softlink(zipfile: Path, extract_dir: "str | None" = None, is_msys64: bool = False):
    if not extract_dir:
        extract_dir = zipfile.parent.as_posix()
    cmd = ['unzip', '-o', zipfile.as_posix(), '-d', extract_dir]
    if (NATIVE_PLAT == 'windows') and (is_msys64):
        cmd = ['C:/msys64/usr/bin/bash.exe', '-c', ' '.join(cmd)]
    run_as_subprocess(args=cmd)
# ----------------------------
RCLONE_EXEC = (Path(PROJ_ROOT) / '.github' / 'rclone')
if ON_GITHUB_CI and (not RCLONE_EXEC.exists()):
    plat = {
        'linux':   'linux',
        'macosx':  'osx',
        'windows': 'windows',
    }[NATIVE_PLAT]
    fext = ('.exe' if plat == 'windows' else '')
    arch = NATIVE_ARCH

    _rclone_dir = RCLONE_EXEC.parent

    download_link = f'https://downloads.rclone.org/rclone-current-{plat}-{arch}.zip'
    rclone_zipfile = (_rclone_dir / 'rclone.zip')
    logv(f'downloading rclone from "{download_link}" > "${rclone_zipfile.as_posix()}"')
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
