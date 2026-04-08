#!/usr/bin/env python3

# fmt: off

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.append(
    (Path(__file__).parent / '..').absolute().as_posix()
)
from scripts import utils as x
# ----------------------------

import glob
import os
import platform
import shutil
import stat
import urllib.request


_rclone_ver = 'current'
_rclone_dir = (Path(x.PROJ_ROOT) / '.github').absolute().as_posix()

plat = platform.system().lower()
if plat == 'darwin':
    plat = 'osx'
if not (plat in ['linux', 'windows', 'osx']):
    raise RuntimeError(f'unsupported plat: {plat}')
fext = ('.exe' if plat == 'windows' else '')

arch = platform.machine().lower()
if plat == 'linux':
    if arch == 'aarch64': arch = 'arm64'
    if arch == 'x86_64':  arch = 'amd64'
if not (arch in ['amd64', 'arm64']):
    raise RuntimeError(f'unsupported arch: {arch}')


download_link = f'https://downloads.rclone.org/rclone-current-{plat}-{arch}.zip'
x.print_stderr(f'downloading rclone from "{download_link}"')

rclone_zipfile = (Path(_rclone_dir) / 'rclone.zip').absolute().as_posix()
with urllib.request.urlopen(download_link) as resp:
    if resp.getcode() != 200:
        raise ConnectionError(f"respcode: {resp.getcode()}, respbody: ->\n{resp.read().decode(errors='ignore')}")
    with open(rclone_zipfile, 'wb') as f:
        shutil.copyfileobj(resp, f)


shutil.unpack_archive(rclone_zipfile, extract_dir=_rclone_dir)
rclone_exec = glob.glob(f'{_rclone_dir}/rclone-v*-{plat}-{arch}/rclone{fext}')[0]
os.chmod(rclone_exec, stat.S_IRWXU); shutil.move(src=rclone_exec, dst=_rclone_dir)


rclone_conf_src = (Path(_rclone_dir) / 'rclone.conf.tmpl')
rclone_conf_content = rclone_conf_src.read_text()
rclone_conf_content = rclone_conf_content.replace('@S3_R2_ACCOUNT_ID@', os.getenv('S3_R2_ACCOUNT_ID', '<mask>'))
rclone_conf_content = rclone_conf_content.replace('@S3_R2_ACCESS_KEY@', os.getenv('S3_R2_ACCESS_KEY', '<mask>'))
rclone_conf_content = rclone_conf_content.replace('@S3_R2_SECRET_KEY@', os.getenv('S3_R2_SECRET_KEY', '<mask>'))
rclone_conf_content = rclone_conf_content.replace('@S3_R2_STORAGE_REGION@', os.getenv('S3_R2_STORAGE_REGION', 'auto'))

rclone_conf_dst = (Path(_rclone_dir) / 'rclone.conf')
rclone_conf_dst.write_text(rclone_conf_content)
