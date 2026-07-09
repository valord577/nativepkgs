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
        _build_step_1,
        _build_step_2,
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
def _fetch_source():
    ctx.fetch_source_from_git('refs/tags/1.5.3', 'https://github.com/videolan/dav1d.git')

    x.runpy_pip(['meson', 'ninja'])
def _build_step_0():
    x.run_as_subprocess(env=get_build_env(), args=[
         'meson', 'setup',
        f'--default-library={x.feature("PKG_TYPE")}',
         '-Dbuildtype=release',
         '-Denable_docs=false',
         '-Denable_examples=false',
         '-Denable_seek_stress=false',
         '-Denable_tests=false',
         '-Denable_tools=false',
         *(ctx.args.extra_meson),
         ctx.args.pkg_buld_dir,
         ctx.subproj_src_dir().as_posix(),
    ])
def _build_step_1():
    x.run_as_subprocess(env=get_build_env(), args=['meson', 'compile', '-C', ctx.args.pkg_buld_dir, '-j', f'{x.detect_cpu_count()}'])
def _build_step_2():
    x.run_as_subprocess(env=get_build_env(), args=['meson', 'install', '-C', ctx.args.pkg_buld_dir, '--strip', '--no-rebuild'])
