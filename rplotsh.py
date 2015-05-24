#!/usr/bin/env python3
# coding=utf-8

# argument parsing
from argparse import ArgumentParser

optparser = ArgumentParser(description=__doc__)
optparser.add_argument('filenames', nargs='+', help='ROOT files')
options = optparser.parse_args()

from rshell import rshell, empty


class rplotsh(rshell, empty):
    """Interactive plotting interface for ROOT files"""

    def postloop(self):
        print


if __name__ == '__main__':
    # history file for interactive use
    import atexit
    import readline
    import os
    import sys

    # history variables
    __histfile__ = '.rplotsh'

    if os.path.exists(__histfile__):
        readline.read_history_file(__histfile__)

    atexit.register(readline.write_history_file, __histfile__)
    del atexit, readline

    # command loop
    try:
        rplotsh_inst = rplotsh()
        rplotsh_inst.add_files(options.filenames)
        rplotsh_inst.set_histfile(__histfile__)
        rplotsh_inst.cmdloop()
    except KeyboardInterrupt:
        rplotsh_inst.postloop()
        sys.exit(1)
