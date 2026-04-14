#!/usr/bin/env python3

# fmt: off

import sys
sys.dont_write_bytecode = True

import utils as x
# ----------------------------

from pathlib import Path


basepath = Path(sys.argv[1])
depth = 0
if len(sys.argv) > 2:
    depth = int(sys.argv[2])

# Path('...'), depth, prefixes, connector, is_symlink, is_dir
_stack = [(basepath, -1, [], '', basepath.is_symlink(), basepath.is_dir())]

while _stack:
    _path, _depth, _prefixes, _connector, _is_symlink, _is_dir = _stack.pop()

    _name_with_symlink = _path.name
    if _depth == -1:
        _name_with_symlink = _path.as_posix()
    if _is_symlink:
        _name_with_symlink = f'{_name_with_symlink} -> {_path.readlink().as_posix()}'

    _child_prefixes: list[str] = []
    if _depth == -1:
        x.print_stderr(f"{_name_with_symlink}")
    else:
        _child_prefixes = _prefixes + ['    ' if _connector.startswith('└') else '│   ']
        x.print_stderr(f"{''.join(_prefixes)}{_connector}{_name_with_symlink}")

    if (not _is_dir) or (depth > 0 and _depth + 1 >= depth):
        continue

    entries_d: list[Path] = []
    entries_f: list[Path] = []
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
