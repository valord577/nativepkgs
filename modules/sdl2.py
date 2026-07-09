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
    ctx.fetch_source_from_git('refs/heads/release-2.32.x', 'https://github.com/libsdl-org/SDL.git')
def _build_step_0():
    x.run_as_subprocess(env=get_build_env(), args=[
        'cmake', *(ctx.args.extra_cmake),
        '-S',   ctx.subproj_src_dir().as_posix(),
        '-D', f'BUILD_SHARED_LIBS:BOOL={x.feature_build_shared()}',
        '-D', f'SDL_STATIC:BOOL={x.feature_build_static()}',
        '-D', f'SDL_SHARED:BOOL={x.feature_build_shared()}',
        '-D',  'CMAKE_BUILD_TYPE=Release',
        '-D',  'SDL_CCACHE:BOOL=0',
        '-D',  'SDL_TEST:BOOL=0',
        '-D',  'SDL_LIBC:BOOL=1',
        '-D',  'SDL2_DISABLE_SDL2MAIN:BOOL=1',
    ])
def _build_step_1():
    x.run_as_subprocess(env=get_build_env(), args=['cmake', '--build', ctx.args.pkg_buld_dir, '-j', f'{x.detect_cpu_count()}'])
def _build_step_2():
    x.run_as_subprocess(env=get_build_env(), args=['cmake', '--install', ctx.args.pkg_buld_dir, '--strip'])
