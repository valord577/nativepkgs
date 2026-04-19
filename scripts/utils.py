#!/usr/bin/env python3

# fmt: off

import importlib.util
import io
import json
import subprocess as sp
import os
import platform
import sys

from pathlib import Path
from typing import Union


PROJ_ROOT = (Path(__file__).absolute().resolve().parents[1]).as_posix()
# ----------------------------
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
# ----------------------------
# ci runtime
# ----------------------------
ON_GITLAB_CI = os.getenv('GITLAB_CI', '')      == 'true'
ON_GITHUB_CI = os.getenv('GITHUB_ACTIONS', '') == 'true'
ON_CODE_EDIT = (not ON_GITLAB_CI) and (not ON_GITHUB_CI) \
    and (os.getenv('CLANGD_CODE_COMPLETION', '0') == '1')
# ----------------------------
RCLONE_EXEC = (Path(PROJ_ROOT) / '.github' / 'rclone')
# ----------------------------
S3_R2_ACCOUNT_ID = os.getenv('S3_R2_ACCOUNT_ID', '<mask>')
S3_R2_ACCESS_KEY = os.getenv('S3_R2_ACCESS_KEY', '<mask>')
S3_R2_SECRET_KEY = os.getenv('S3_R2_SECRET_KEY', '<mask>')
S3_R2_STORAGE_REGION = os.getenv('S3_R2_STORAGE_REGION', 'auto')
S3_R2_STORAGE_BUCKET = os.getenv('S3_R2_STORAGE_BUCKET', '<mask>')
# ----------------------------
CPU_COUNT = os.cpu_count() or 2
if sys.platform == 'linux':
    CPU_COUNT = len(os.sched_getaffinity(0))
# ----------------------------
NATIVE_PLAT = platform.system().lower()
if NATIVE_PLAT not in ['linux', 'darwin', 'windows']:
    raise NotImplementedError(f'unsupported native platform: {NATIVE_PLAT}')
NATIVE_ARCH = platform.machine().lower()
if NATIVE_ARCH == 'x86_64':  NATIVE_ARCH = 'amd64'
if NATIVE_ARCH == 'aarch64': NATIVE_ARCH = 'arm64'
# ----------------------------
# >>>> utils functions >>>>
# ----------------------------
def print_stderr(str):
    print(str, file=sys.stderr)
def _util_func__subprocess(args: Union[str, list[str]],
    cwd: Union[str, None] = None, env: Union[dict[str, str], None] = None, shell=False,
    collect_stdout=False, stdout = None,
) -> str:
    print_stderr(f'>>>> subprocess cmdline: {args}')
    proc = sp.run(
        args=args, cwd=cwd, env=env, check=True, shell=shell,
        stdout=(sp.PIPE if collect_stdout else stdout), text=(True if collect_stdout else None),
    )
    return proc.stdout if collect_stdout else ''
def _util_load_module(name: str, attrs: Union[list[str], None] = None):
    module = importlib.import_module(name)
    for attr in (attrs or []):
        getattr(module, attr)
    return module
def _util_load_pyfile(file: str, attrs: Union[list[str], None] = None):
    spec = importlib.util.spec_from_file_location('', file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for attr in (attrs or []):
        getattr(module, attr)
    return module

def _util_func__exec_python(args: list[str], cwd: Union[str, None] = None):
    _util_func__subprocess(args=[(Path(sys.executable)).absolute().as_posix(), *args], cwd=cwd)
def _util_func__pip_install(packages: list[str]):
    args = ['-m', 'pip', 'install', '--upgrade']
    if not ON_GITHUB_CI:
        args.extend(['--trusted-host', 'repo.huaweicloud.com'])
        args.extend(['-i', 'https://repo.huaweicloud.com/repository/pypi/simple'])
    args.extend(['pip', *packages])
    _util_func__exec_python(args=args)

def _util_put_pkg_version_desc(pkg_name: str, ver: str):
    (Path(PROJ_ROOT) / '.deps' / f'{pkg_name}.ver') \
        .write_text(ver, encoding='utf-8')
def _util_get_pkg_version_desc(pkg_name: str) -> str:
    return (Path(PROJ_ROOT) / '.deps' / f'{pkg_name}.ver') \
        .read_text(encoding='utf-8').strip()

def _util_append_ci_env(f: io.TextIOWrapper, k, v):
    print_stderr(f'{k}: {v}'); f.write(f'{k}={v}\n')
def _util_append_env_pkgconf_path(env: dict[str, str], dir: Path):
    old_pkgconf_path = env.get('PKG_CONFIG_PATH', '')
    new_pkgconf_path = (dir).absolute().as_posix()
    env['PKG_CONFIG_PATH'] = new_pkgconf_path + os.pathsep + old_pkgconf_path

def _util_source_cleanup(cwd: str):
    _util_func__subprocess(cwd=cwd, args=['git', 'reset', '--hard', 'HEAD'])
    _util_func__subprocess(cwd=cwd, args=['git', 'clean', '-d', '-f', '-q'])
def _util_source_apply_patches(cwd: str, patches_dir: str):
    if not (Path(patches_dir)).exists():
        return
    _util_source_cleanup(cwd)

    patches: list[Path] = []
    for it in Path(patches_dir).iterdir():
        if not it.is_file():
            continue
        patches.append(it)
    patches_sorted = sorted(patches, key=lambda p: p.name)
    for it in patches_sorted:
        _util_func__subprocess(cwd=cwd, args=[
            'git', 'apply', '--verbose', '--ignore-space-change', '--ignore-whitespace', it.absolute().as_posix(),
        ])
def _util_source_sync_submodules(submodules: list[dict[str, str]]):
    for _submodule in submodules:
        repo = _submodule['repo']; path = _submodule['path']; cwd  = _submodule['cwd']; url  = _submodule['url']
        _util_func__subprocess(cwd=cwd, args=['git', 'config', '--local', f'submodule.{repo}.url', url])
        _util_func__subprocess(cwd=cwd, args=['git', 'submodule', 'sync', '--', path])
        _util_func__subprocess(cwd=cwd, args=['git', 'submodule', 'update', '--init', '--depth=1', '--single-branch', '-f', '--', path])

def _util_get_cross_toolchain_dir():
    env = 'CROSS_TOOLCHAIN_ROOT'
    if dir := os.getenv(env):
        return dir
    raise RuntimeError(f'missing required env: `{env}`')

def _util_load_json_from_file(filepath: str) -> dict:
    return json.loads(Path(filepath).read_text())
