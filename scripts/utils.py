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


PROJ_ROOT = (Path(__file__).parent / '..').absolute().as_posix()
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
PKG_VER_DESC = os.getenv('DEPS_VER', '')
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
    cwd: Union[str, None] = None, env: Union[dict[str, str], None] = None, shell=False, collect_stdout=False,
) -> str:
    print_stderr(f'>>>> subprocess cmdline: {args}')
    proc = sp.run(
        args=args, cwd=cwd, env=env, check=True, shell=shell,
        stdout=(sp.PIPE if collect_stdout else None), text=(True if collect_stdout else None),
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

def _util_func__exec_python(args: list[str]):
    _util_func__subprocess([(Path(sys.executable)).absolute().as_posix(), *args])
def _util_func__pip_install(packages: list[str]):
    args = ['-m', 'pip', 'install', '--upgrade']
    if not ON_GITHUB_CI:
        args.extend(['--trusted-host', 'repo.huaweicloud.com'])
        args.extend(['-i', 'https://repo.huaweicloud.com/repository/pypi/simple'])
    args.extend(packages)
    _util_func__exec_python(args)

def _util_put_pkg_version_desc(ver: str):
    if not PKG_VER_DESC:
        return
    Path(PKG_VER_DESC).write_text(ver, encoding='utf-8')
def _util_get_pkg_version_desc() -> str:
    if not PKG_VER_DESC:
        return ''
    return Path(PKG_VER_DESC).read_text(encoding='utf-8').strip()

def _util_append_ci_env(f: io.TextIOWrapper, k, v):
    print_stderr(f'{k}: {v}'); f.write(f'{k}={v}\n')

def _util_source_apply_patches(cwd: str, patches_dir: str):
    if not (Path(patches_dir)).exists():
        return
    _util_func__subprocess(cwd=cwd, args=['git', 'reset', '--hard', 'HEAD'])
    _util_func__subprocess(cwd=cwd, args=['git', 'clean', '-d', '-f', '-q'])
    for it in Path(patches_dir).iterdir():
        if not it.is_file():
            continue
        _util_func__subprocess(cwd=cwd, args=[
            'git', 'apply', '--verbose', '--ignore-space-change', '--ignore-whitespace', it.absolute().as_posix(),
        ])

def _util_get_cross_toolchain_dir():
    env = 'CROSS_TOOLCHAIN_ROOT'
    if dir := os.getenv(env):
        return dir
    raise RuntimeError(f'missing required env: `{env}`')

def _util_load_json_from_file(filepath: str) -> dict:
    return json.loads(Path(filepath).read_text())
