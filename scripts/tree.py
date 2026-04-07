#!/usr/bin/env python3

# fmt: off

import utils as x


import os
import sys


basepath = sys.argv[1]
depth = 0
if len(sys.argv) > 2:
    depth = int(sys.argv[2])

# name, path, depth, is_last, is_symlink, is_dir
_stack = [(basepath, basepath, -1, '-1', os.path.islink(basepath), os.path.isdir(basepath))]
while _stack:
    _name, _path, _depth, _is_last, _is_symlink, _is_dir = _entry = _stack.pop()
    if _depth == -1:
        x.print_stderr(f"{_name}{f' -> {os.readlink(_path)}' if _is_symlink else ''}")
    else:
        x.print_stderr(f"{'│   ' * _depth}{'└── ' if _is_last == '1' else '├── '}{_name}{f' -> {os.readlink(_path)}' if _is_symlink else ''}")

    if (not _is_dir) or (depth > 0 and _depth + 1 >= depth):
        continue
    with os.scandir(_path) as it:
        entries = sorted(it, key=lambda e: e.name)
        entries_dir_first = []
        entries_dir_first.extend([ d for d in entries if     d.is_dir() ])
        entries_dir_first.extend([ f for f in entries if not f.is_dir() ])
        for i, entry in enumerate(reversed(entries_dir_first)):
            _stack.append(
                (
                    entry.name,
                    entry.path,
                    _depth + 1,
                    '1' if i == 0 else '0',
                    entry.is_symlink(),
                    entry.is_dir(follow_symlinks=False),
                )
            )
