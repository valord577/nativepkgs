#!/usr/bin/env python3

# fmt: off

import os
import platform
import shutil
import stat
import sys
import urllib.request


_rclone_ver = 'v1.70.3'
_rclone_dir = os.path.abspath(os.path.dirname(__file__))

def _print(msg: str):
    print(msg, file=sys.stderr)


if __name__ == "__main__":
    plat = platform.system().lower()
    if plat == 'darwin':
        plat = 'osx'
    if not (plat in ['linux', 'windows', 'osx']):
        _print(f'unsupported plat: {plat}')
        sys.exit(1)

    arch = platform.machine().lower()
    if plat == 'linux':
        if arch == 'aarch64': arch = 'arm64'
        if arch == 'x86_64':  arch = 'amd64'
    if not (arch in ['amd64', 'arm64']):
        _print(f'unsupported arch: {arch}')
        sys.exit(1)


    prifix = f'rclone-{_rclone_ver}-{plat}-{arch}'
    url = f'https://github.com/rclone/rclone/releases/download/{_rclone_ver}/{prifix}.zip'
    _print(f'downloading rclone from "{url}"')

    rclone_zippath = os.path.abspath(os.path.join(_rclone_dir, 'rclone.zip'))
    with urllib.request.urlopen(url) as resp:
        if resp.getcode() != 200:
            _print(f"respcode: {resp.getcode()}, respbody: ->\n{resp.read().decode()}")
            sys.exit(1)
        with open(rclone_zippath, 'wb') as f:
            while True:
                data = resp.read(8 * 1024)
                if not data:
                    break
                f.write(data)

    rclone_unzip_prefix = os.path.abspath(os.path.join(_rclone_dir, prifix))
    rclone_exename = 'rclone' if plat != 'windows' else 'rclone.exe'
    rclone_exepath = os.path.abspath(os.path.join(rclone_unzip_prefix, rclone_exename))
    shutil.unpack_archive(rclone_zippath, extract_dir=_rclone_dir)
    os.chmod(rclone_exepath, stat.S_IRWXU)
    shutil.move(src=rclone_exepath, dst=_rclone_dir)
    shutil.rmtree(rclone_unzip_prefix, ignore_errors=True)


    rclone_conf_dst = os.path.abspath(os.path.join(_rclone_dir, 'rclone.conf'))
    rclone_conf_src = os.path.abspath(os.path.join(_rclone_dir, 'rclone.conf.tmpl'))
    with open(rclone_conf_src, 'r') as src:
        with open(rclone_conf_dst, 'w') as dst:
            while line := src.readline():
                line = line.replace('@S3_R2_ACCOUNT_ID@', os.getenv('S3_R2_ACCOUNT_ID', '<mask>'))
                line = line.replace('@S3_R2_ACCESS_KEY@', os.getenv('S3_R2_ACCESS_KEY', '<mask>'))
                line = line.replace('@S3_R2_SECRET_KEY@', os.getenv('S3_R2_SECRET_KEY', '<mask>'))
                line = line.replace('@S3_R2_STORAGE_REGION@', os.getenv('S3_R2_STORAGE_REGION', 'auto'))
                dst.write(line)
