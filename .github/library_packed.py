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

import os


_inst_dir = os.getenv('INST_DIR') or ''
_pkg_zipname = os.getenv('PKG_ZIPNAME') or ''

x._util_dopack_zip_with_softlinks(Path(_inst_dir), _pkg_zipname)
