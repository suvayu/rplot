#!/usr/bin/env python3
# coding=utf-8

# argument parsing
from argparse import ArgumentParser

optparser = ArgumentParser(description=__doc__)
optparser.add_argument('filenames', nargs='+', help='ROOT files')
options = optparser.parse_args()

from fixes import ROOT
from ROOT import gROOT, gDirectory

import cmd
import shlex
from rdir import Rdir, savepwd
from utils import is_dir, root_str, NoExitArgParse
from textwrap import dedent


class empty(cmd.Cmd):
    def emptyline(self):
        pass

    def do_EOF(self, line):
        """Exit on EOF (C-d)"""
        return True


class rshell(cmd.Cmd):
    """Shell-like navigation commands for ROOT files"""

    ls_parser = NoExitArgParse(description='List objects in directory/file',
                               epilog='See also: pathspec', add_help=False)
    ls_parser.add_argument('-l', action='store_true', dest='showtype',
                           help='Long form listing, include object type and '
                           'size (compressed in parantheses).')
    ls_parser.add_argument('paths', nargs='*', help='Object names.')

    pwd = gROOT
    prompt = '{}> '.format(pwd.GetName())

    objs = {}

    @classmethod
    def _bytes2kb(cls, Bytes):
        unit = 1
        while Bytes >= 1024:
            Bytes /= 1024.0
            unit += 1
        if unit == 1:
            return Bytes
        elif unit == 2:
            unit = 'KB'
        elif unit == 3:
            unit = 'MB'
        elif unit == 4:
            unit = 'GB'
        return '{:.1f}{}'.format(Bytes, unit)

    def add_files(self, files):
        self.rdir_helper = Rdir(files)

    def completion_helper(self, text, line, begidx, endidx, comp_type=None):
        if line.rfind(':') > 0:
            pathstr = line.split()[-1]
        else:
            pathstr = text
        self.comp_f = [f.GetName() + ':' for f in self.rdir_helper.files]
        if self.pwd == gROOT and pathstr.find(':') < 0:
            completions = self.comp_f
        else:
            path = os.path.dirname(pathstr)
            completions = self.rdir_helper.ls_names(path, comp_type)
            # NB: Strip trailing slash, and get path without filename.
            # This is necessary since Cmd for some reason splits at
            # the colon separator.
            path = path.rstrip('/').split(':')[-1]
            if path or text.rfind('/') == 0:
                completions = ['/'.join((path, i)) for i in completions]
            completions += self.comp_f
        if not text:
            return completions
        else:
            return filter(lambda i: str.startswith(i, text), completions)

    def precmd(self, line):
        return cmd.Cmd.precmd(self, line)

    def postcmd(self, stop, line):
        self.oldpwd = self.pwd.GetDirectory('')
        self.pwd = gDirectory.GetDirectory('')
        dirn = self.pwd.GetName()
        if len(dirn) > 20:
            dirn = '{}..{}'.format(dirn[0:9], dirn[-9:])
        self.prompt = '{}> '.format(dirn)
        return cmd.Cmd.postcmd(self, stop, line)

    def get_ls_fmt(self, showtype=False, indent=''):
        if showtype:
            return indent + '{cls:<20}{fs:>8}({us:>8}) {nm}{m}'
        else:
            return indent + '{nm}{m}'

    def print_key(self, key, fmt):
        name = key.GetName()
        if isinstance(key, ROOT.TKey):
            cname = key.GetClassName()
            fsize = self._bytes2kb(key.GetNbytes())
            usize = self._bytes2kb(key.GetObjlen())
        else:                   # NB: special case, a TFile
            cname = key.ClassName()
        cls = ROOT.TClass.GetClass(cname)
        if cls.InheritsFrom(ROOT.TFile.Class()):
            res = fmt.format(cls=cname, nm=name, m=':', fs='-', us='-')
        elif cls.InheritsFrom(ROOT.TDirectoryFile.Class()):
            res = fmt.format(cls=cname, nm=name, m='/', fs=fsize, us=usize)
        else:
            res = fmt.format(cls=cname, nm=name, m='', fs=fsize, us=usize)
        print(res)

    def ls_objs(self, keys, showtype=False, indent=''):
        # handle invalid keys
        if keys:
            valid = reduce(lambda i, j: i and j, keys)
        else:
            valid = False
        if valid:
            fmt = self.get_ls_fmt(showtype, indent)
            for key in keys:
                self.print_key(key, fmt)
        else:
            raise ValueError('{}: cannot access {}: No such object')

    def print_memobjs(self, objs):
        """Print memory objects"""
        for name, obj in objs.iteritems():
            print '{}:\n  {}'.format(name, root_str(obj))

    def do_lsmem(self, args):
        """List objects read in memory"""
        if args:
            tokens = shlex.split(args)
            try:
                tmp = dict([(tok, self.objs[tok]) for tok in tokens])
            except KeyError:
                from fnmatch import fnmatchcase
                tmp = {}
                for tok in tokens:
                    tmp.update(dict([(key, self.objs[key]) for key in self.objs
                                     if fnmatchcase(key, tok)]))
            self.print_memobjs(tmp)
        else:
            self.print_memobjs(self.objs)

    def complete_lsmem(self, text, line, begidx, endidx):
        return filter(lambda key: key.startswith(text), self.objs)

    def help_ls(self):
        self.ls_parser.print_help()

    def do_ls(self, args=''):
        """List contents of a directory/file"""
        opts = self.ls_parser.parse_args(args.split())
        if opts.paths:          # w/ args
            for path in opts.paths:
                isdir = self.rdir_helper.get_dir(path)
                indent = ''
                if isdir:
                    if not isinstance(isdir, ROOT.TFile):
                        # convert to TKey when TDirectoryFile
                        dirname = isdir.GetName()
                        with savepwd():
                            isdir.cd('..')
                            # read the latest cycle
                            isdir = filter(lambda k: k.GetName() == dirname,
                                           gDirectory.GetListOfKeys())[0]
                    self.print_key(isdir, self.get_ls_fmt(opts.showtype))
                    indent = ' '
                keys = self.rdir_helper.ls(path)
                try:
                    self.ls_objs(keys, opts.showtype, indent)
                except ValueError as err:
                    print(str(err).format('ls', path))
        else:                     # no args
            if gROOT == self.pwd:
                # can't access files trivially when in root
                for f in gROOT.GetListOfFiles():
                    self.print_key(f, self.get_ls_fmt(opts.showtype))
            else:               # in a file
                try:
                    self.ls_objs(self.rdir_helper.ls(), opts.showtype)
                except ValueError as err:
                    print(str(err).format('ls', ''))
                    print('Warning: this shouldn\'t happen, something went '
                          'terribly wrong!')

    def complete_ls(self, text, line, begidx, endidx):
        return self.completion_helper(text, line, begidx, endidx)

    def do_pwd(self, args=None):
        """Print the name of the current working directory"""
        thisdir = self.pwd.GetDirectory('')
        pwdname = thisdir.GetName()
        while not (isinstance(thisdir, ROOT.TFile) or self.pwd == gROOT):
            thisdir = thisdir.GetDirectory('../')
            if isinstance(thisdir, ROOT.TFile):
                break
            pwdname = '/'.join((thisdir.GetName(), pwdname))
        if isinstance(self.pwd, ROOT.TFile):
            print('{}:'.format(pwdname))
        elif self.pwd == gROOT:
            print(pwdname)
        else:
            print('{}:/{}'.format(thisdir.GetName(), pwdname))

    def do_cd(self, args=''):
        """Change directory to specified directory.  See also: pathspec."""
        if args.strip() == '-':
            success = self.oldpwd.cd()
        else:
            success = self.pwd.cd(args)
        if not success:
            print('cd: {}: No such file or directory'.format(args))
        else:
            if not args.strip():
                gROOT.cd()

    def complete_cd(self, text, line, begidx, endidx):
        return self.completion_helper(text, line, begidx, endidx,
                                      ROOT.TDirectoryFile)

    def save_obj(self, args):
        """Read objects into shell"""
        self.objs.update(args)

    def help_read(self):
        msg = '''\
        Syntax: read <objname> [as <newobjname>]

        If <objname> is a directory, all objects in that directory are
        read in to memory.  In this case, if `as <newobjname>\' is present,
        objects are stored in a list of that name.  <objname> can also be a
        globbing pattern or a regular expression, `as <newobjname>\'
        semantics are similar to directory.

        Note: Since `as\' is a keyword, an object named `as\' cannot be read
        simply.  Use a regex for that: e.g. a[s].'''
        print(dedent(msg))

    def do_read(self, args):
        """Read objects into memory."""
        if args:
            tokens = shlex.split(args)
            path = tokens[0]
            if 'as' in tokens:  # destination var specified or not
                # or 3 == len(tokens)
                try:
                    assert(tokens[1] == 'as')
                    try:
                        newobj = tokens[2]
                    except IndexError:
                        newobj = None
                        # raise ValueError('Missing destination variable')
                except AssertionError:
                    print 'Unknown command token: {}'.format(tokens[1])
                    print 'Will do regular read'
            else:
                newobj = None

            # find and read objects
            objs = self.rdir_helper.read(path, metainfo=True)
            if not objs:        # nothing found, try glob
                pattern = path.rsplit('/', 1)
                if len(pattern) > 1:
                    path, pattern = pattern[:-1], pattern[-1]
                else:
                    path, pattern = None, pattern[0]
                from fnmatch import fnmatchcase
                match = lambda name: fnmatchcase(name, pattern)
                notdir = lambda key: not is_dir(key) and match(key.GetName())
                objs = self.rdir_helper.read(path, robj_p=notdir, metainfo=True)
            if not objs:        # nothing found, try regex
                import re
                match = re.compile(pattern).match
                notdir = lambda key: not is_dir(key) and match(key.GetName())
                objs = self.rdir_helper.read(path, robj_p=notdir, metainfo=True)

            # save read objects
            if newobj:
                if len(objs) > 1:
                    objs = {newobj: objs}
                else:
                    objs = {newobj: objs[0]}  # only one element
            else:
                objs = [(obj.GetName(), obj) for obj in objs]
            self.save_obj(objs)
        else:
            print('Nothing to read!')

    def complete_read(self, text, line, begidx, endidx):
        return self.completion_helper(text, line, begidx, endidx)

    def do_python(self, args=None):
        """Start an interactive Python console"""
        import code
        import readline
        import rlcompleter
        # save, switch, and restore history files
        readline.write_history_file(__histfile__)
        readline.clear_history()  # remove rplotsh history from Python
        if os.path.exists(__pyhistfile__):
            readline.read_history_file(__pyhistfile__)

        # save and restore old completer
        rplotsh_completer = readline.get_completer()
        readline.set_completer(rlcompleter.Completer(self.objs).complete)
        readline.parse_and_bind("tab: complete")
        shell = code.InteractiveConsole(self.objs)
        shell.interact()
        readline.set_completer(rplotsh_completer)

        readline.write_history_file(__pyhistfile__)
        if os.path.exists(__histfile__):
            readline.read_history_file(__histfile__)

    def help_pathspec(self):
        msg = '''\
        Paths inside the current file can be specified using the normal syntax:
        - full path: /dir1/dir2
        - relative path: ../dir1

        Paths in other root files have to be preceded by the file name and a
        colon:
        - file path: myfile.root:/dir1/dir2

        See also: TDirectoryFile::cd(..) in ROOT docs, `help pathspec\'.'''
        print(dedent(msg))


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
    __pyhistfile__ = '{}.py'.format(__histfile__)

    if os.path.exists(__histfile__):
        readline.read_history_file(__histfile__)

    atexit.register(readline.write_history_file, __histfile__)
    del atexit, readline

    # command loop
    try:
        rplotsh_inst = rplotsh()
        rplotsh_inst.add_files(options.filenames)
        rplotsh_inst.cmdloop()
    except KeyboardInterrupt:
        rplotsh_inst.postloop()
        sys.exit(1)
