#!/usr/bin/env python3

# fmt: off

import sys
from pathlib import Path

sys.dont_write_bytecode = True

_this_file = (Path(__file__).absolute().resolve())
sys.path.append(
    (_this_file.parents[0]).as_posix()
); import x_utils as x
# ----------------------------


def _format_size(_path: Path) -> str:
    _size = _path.stat().st_size
    _human_size = _size
    _unit_index = 0 if _human_size < 1024 else 1
    while _human_size >= 1024 * 1024:
        _unit_index += 1
        _human_size //= 1024

    if _unit_index == 0:
        _human = f'{_human_size:4d}'
    else:
        _precision = 0 if (_human_size // 1024) >= 10 else 1
        _human = f'{(_human_size / 1024.0):3.{_precision}f}{"BKMGT"[_unit_index]}'
    return f'{_size:13d} (≈ {_human})'

basepath = Path(sys.argv[1])
depth = 0
if len(sys.argv) > 2:
    depth = int(sys.argv[2])

# Path('...'), depth, prefixes, connector, is_symlink, is_dir
_stack: "list[tuple[Path, int, list[str], str, bool, bool]]" = [
    (basepath, -1, [], '', basepath.is_symlink(), basepath.is_dir())
]

while _stack:
    _path, _depth, _prefixes, _connector, _is_symlink, _is_dir = _stack.pop()

    _name_with_symlink = _path.name
    if _depth == -1:
        _name_with_symlink = _path.as_posix()
    if _is_symlink:
        _name_with_symlink = f'{_name_with_symlink} -> {_path.readlink().as_posix()}'
    _line = f'[{_format_size(_path)}]   {_name_with_symlink}'

    _child_prefixes: "list[str]" = []
    if _depth == -1:
        x.logv(f"{_line}")
    else:
        _child_prefixes = _prefixes + ['    ' if _connector.startswith('└') else '│   ']
        x.logv(f"{''.join(_prefixes)}{_connector}{_line}")

    if (not _is_dir) or (depth > 0 and _depth + 1 >= depth):
        continue

    entries_d: "list[Path]" = []
    entries_f: "list[Path]" = []
    for it in _path.iterdir():
        if it.is_dir():
            entries_d.append(it)
        else:
            entries_f.append(it)
    entries_d_sorted = sorted(entries_d, key=lambda p: p.name)
    entries_f_sorted = sorted(entries_f, key=lambda p: p.name)
    for i, entry in enumerate(reversed(entries_d_sorted + entries_f_sorted)):
        _is_last = (i == 0)
        _stack.append((
            entry,
            _depth + 1,
            _child_prefixes,
            ('└── ' if _is_last else '├── '),
            entry.is_symlink(),
            entry.is_dir(),
        ))
