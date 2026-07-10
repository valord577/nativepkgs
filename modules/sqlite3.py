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
        _fetch_source,
        _build_step_0,
    ]
# ----------------------------
def get_build_env() -> "dict[str, str]":
    env = x.ENVIRON
    if ctx.args.target_plat == 'win-msvc':
        env.update(ctx.args.win32_msvc_env_target)
        env['CFLAGS'] = '/utf-8'
        env['CXXFLAGS'] = env['CFLAGS']
    return env
# ----------------------------
archive_prefix = 'sqlite-amalgamation-3530300'
# ----------------------------
def _fetch_source():
    ctx.fetch_source_from_http(version='v3.53.3',
        url=f'https://sqlite.org/2026/{archive_prefix}.zip',
        archive_format='zip',
        archive_prefix=f'{archive_prefix}/',
        extracted_file=['sqlite3.c', 'sqlite3.h'],
    )
def _build_step_0():
    import shutil

    args = ctx.args.cc + ctx.args.ldflags + [
        '-DHAVE_FDATASYNC=1',
        '-DSQLITE_DQS=0',
        '-DSQLITE_THREADSAFE=1',
        '-DSQLITE_DEFAULT_AUTOMATIC_INDEX=1',
        '-DSQLITE_DEFAULT_AUTOVACUUM=0',
        '-DSQLITE_DEFAULT_FOREIGN_KEYS=0',
        '-DSQLITE_DEFAULT_MMAP_SIZE=0',
        '-DSQLITE_DEFAULT_MEMSTATUS=0',
        '-DSQLITE_DEFAULT_SYNCHRONOUS=3',
        '-DSQLITE_DEFAULT_WAL_SYNCHRONOUS=3',
        '-DSQLITE_JSON_MAX_DEPTH=64',
        '-DSQLITE_LIKE_DOESNT_MATCH_BLOBS',
        '-DSQLITE_TEMP_STORE=3',
        '-DSQLITE_MAX_EXPR_DEPTH=0',
        '-DSQLITE_OMIT_AUTORESET',
        '-DSQLITE_OMIT_AUTOINIT',
        '-DSQLITE_OMIT_DECLTYPE',
        '-DSQLITE_OMIT_DEPRECATED',
        '-DSQLITE_OMIT_LOAD_EXTENSION',
        '-DSQLITE_OMIT_PROGRESS_CALLBACK',
        '-DSQLITE_OMIT_SHARED_CACHE',
        '-DSQLITE_OMIT_UTF16',
        '-DSQLITE_STRICT_SUBTYPE=1',
    ] + [
        '-std=c11', '-fPIC', '-Wall', '-Wextra',
        '-shared', '-v', '-O3', '-DNDEBUG',
        '-ffunction-sections', '-fdata-sections',
        '-Wl,--icf=safe', '-pthread',
    ]

    output = (Path(ctx.args.pkg_inst_dir))
    if ctx.args.target_plat in {'linux', 'android'}:
        output = (output / 'lib' / 'libsqlite3.so'); \
            output.parent.mkdir(parents=True, exist_ok=True)
        args.extend([
            '-Wl,--gc-sections', '-Wl,-rpath,$ORIGIN', '-Wl,--build-id',
            '-o', output.as_posix(), f'-Wl,--soname={output.name}', '-lm',
        ])
    elif ctx.args.target_plat == 'win-mingw':
        pass
    else: # apple platform
        output = (output / 'lib' / 'libsqlite3.dylib'); \
            output.parent.mkdir(parents=True, exist_ok=True)
        args.extend([
            '-Wl,--gc-sections', '-Wl,--build-id',
            '-o', output.as_posix(), '-install_name', output.name,
        ])
    args.extend([
        f'-I{ctx.subproj_src_dir(archive_prefix).as_posix()}',
        ctx.subproj_src_dir(archive_prefix, 'sqlite3.c').as_posix(),
    ])
    x.run_as_subprocess(env=get_build_env(), args=args)


    src_dst_mapping: list[dict[Path, Path]] = [
        {
            (ctx.subproj_src_dir(archive_prefix, 'sqlite3.h')):
                (Path(ctx.args.pkg_inst_dir) / 'include' / 'sqlite3.h'),
        },
    ]
    for map in src_dst_mapping:
        for src, dst in map.items():
            if src.is_file():
                dst.unlink(missing_ok=True)
                dst.parent.mkdir(parents=True, exist_ok=True)
                _ = shutil.copy2(src, dst)
            if src.is_dir():
                shutil.rmtree(dst, ignore_errors=True)
                _ = src.rename(dst)

    _pkgconf_content = '''\
prefix=${pcfiledir}/../..
includedir=${prefix}/include
libdir=${prefix}/lib

Name: SQLite
Description: SQL database engine
Version: @PKGCONFIG_VERSION@
Requires:
Cflags: -I${includedir}
Libs: -L${libdir} -lsqlite3
'''
    _pkgconf_content = _pkgconf_content.replace('@PKGCONFIG_VERSION@', ctx.subproj_src_ver())

    _pkgconf = (Path(ctx.args.pkg_inst_dir) / 'lib' / 'pkgconfig' / 'sqlite3.pc'); \
        _pkgconf.parent.mkdir(parents=True, exist_ok=True)
    _ = _pkgconf.write_text(_pkgconf_content)
