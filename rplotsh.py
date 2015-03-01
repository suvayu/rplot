#!/usr/bin/env python
# coding=utf-8

# argument parsing
from argparse import ArgumentParser

optparser = ArgumentParser(description=__doc__)
optparser.add_argument('filenames', nargs='+', help='ROOT files')
options = optparser.parse_args()


from fixes import ROOT
from ROOT import gROOT, gSystem, gDirectory, gPad, gStyle
# colours
from ROOT import (kBlack, kWhite, kGray, kViolet, kMagenta, kPink,
                  kRed, kOrange, kYellow, kSpring, kGreen, kTeal,
                  kCyan, kAzure, kBlue)
# markers
from ROOT import (kDot, kPlus, kStar, kCircle, kMultiply,
                  kFullDotSmall, kFullDotMedium, kFullDotLarge,
                  kFullCircle, kFullSquare, kFullTriangleUp,
                  kFullTriangleDown, kOpenCircle, kOpenSquare,
                  kOpenTriangleUp, kOpenTriangleDown)

import cmd
from rdir import Rdir
from utils import is_dir


class empty(cmd.Cmd):
    def emptyline(self):
        pass


class rshell(cmd.Cmd):
    """Shell-like navigation commands for ROOT files"""

    ls_parser = ArgumentParser()
    ls_parser.add_argument('-l', action='store_true', dest='showtype')
    ls_parser.add_argument('paths', nargs='*')

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
        self.comp_f = map(lambda i: i.GetName() + ':', self.rdir_helper.files)
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
            print(fmt.format(cls=cname, nm=name, m=':',
                             fs='-', us='-'))
        elif cls.InheritsFrom(ROOT.TDirectoryFile.Class()):
            print(fmt.format(cls=cname, nm=name, m='/',
                             fs=fsize, us=usize))
        else:
            print(fmt.format(cls=cname, nm=name, m='',
                             fs=fsize, us=usize))

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

    def do_lsmem(self, args):
        """List objects read into memory"""
        def print_objs(objs):
            for name, obj in objs.iteritems():
                print '{:<30}  <-  {:<}'.format(name, obj)
        if args:
            import shlex
            tokens = shlex.split(args)
            tmp = dict([(tok, self.objs[tok]) for tok in tokens])
            if not tmp:
                tmp = dict([(tok, self.objs[tok]) for tok in tokens])
            print_objs(tmp)
        else:
            print_objs(self.objs)

    def complete_lsmem(self, text, line, begidx, endidx):
        return filter(lambda key: key.startswith(text), self.objs)

    def do_ls(self, args=''):
        """List contents of a directory/file. (see `pathspec')"""
        opts = self.ls_parser.parse_args(args.split())
        if opts.paths:          # w/ args
            for path in opts.paths:
                isdir = self.rdir_helper.get_dir(path)
                indent = ''
                if isdir:
                    if not isinstance(isdir, ROOT.TFile):
                        # convert to TKey when TDirectoryFile
                        dirname = isdir.GetName()
                        isdir.cd('..')
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
                    print('Warning: this shouldn\'t happen, something went terribly wrong!')

    def complete_ls(self, text, line, begidx, endidx):
        return self.completion_helper(text, line, begidx, endidx)

    def do_pwd(self, args=None):
        """Print the name of current working directory"""
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
        """Change directory to specified directory. (see `pathspec')"""
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

    def do_read(self, args):
        """Read objects into memory."""
        if args:
            import shlex
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
                objs = map(lambda obj: (obj.GetName(), obj), objs)
            self.save_obj(objs)
        else:
            print('Nothing to read!')

    def complete_read(self, text, line, begidx, endidx):
        return self.completion_helper(text, line, begidx, endidx)

    def help_read(self):
        print('Syntax: read <objname> [as <newobjname>]')
        print
        print('If <objname> is a directory, all objects in that')
        print('directory are read in to memory.  In this case,')
        print('if `as <newobjname>\' is present, objects are stored')
        print('in a list of that name.  <objname> can also be a')
        print('globbing pattern or a regular expression, `as ')
        print('<newobjname>\' semantics are similar to directory.')
        print
        print('Note: Since `as\' is a keyword, an object named as cannot')
        print('be read simply.  Use a regex for that: e.g. a[s].')

    def do_python(self, args=None):
        """Start an interactive Python console"""
        import code
        import readline
        import rlcompleter
        myobjs = self.objs
        ROOT_globals = dict([(k, v) for k, v in globals().iteritems()
                             if k.startswith('g') or k.startswith('k')])
        myobjs.update(ROOT_globals)
        # myobjs.update({'ls': self.do_ls, 'cd': self.do_cd, 'read' : self.do_read})
        readline.set_completer(rlcompleter.Completer(myobjs).complete)
        readline.parse_and_bind("tab: complete")
        shell = code.InteractiveConsole(myobjs)
        shell.interact()

    def help_pathspec(self):
        msg = "Paths inside the current file can be specified using the\n"
        msg += "normal syntax:\n"
        msg += "- full path: /dir1/dir2\n"
        msg += "- relative path: ../dir1\n\n"

        msg += "Paths in other root files have to be preceded by the file\n"
        msg += "name and a colon:\n"
        msg += "- file path: myfile.root:/dir1/dir2\n\n"

        msg += "See: TDirectoryFile::cd(..) in ROOT and rdir.pathspec docs"
        print(msg)


class rplotsh(rshell, empty):
    """Interactive plotting interface for ROOT files"""

    def do_EOF(self, line):
        """Exit rplot shell"""
        return True

    def postloop(self):
        print


if __name__ == '__main__':
    # history file for interactive use
    import atexit
    import readline
    import os
    import sys
    history_path = '.rplotsh'

    def save_history(history_path=history_path):
        import readline
        readline.write_history_file(history_path)

    if os.path.exists(history_path):
        readline.read_history_file(history_path)

    atexit.register(save_history)
    del atexit, readline, save_history, history_path

    # command loop
    try:
        rplotsh_inst = rplotsh()
        rplotsh_inst.add_files(options.filenames)
        rplotsh_inst.cmdloop()
    except KeyboardInterrupt:
        rplotsh_inst.postloop()
        sys.exit(1)
