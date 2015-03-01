# coding=utf-8
"""A global filesystem-like hierarchy of ROOT objects in PyROOT

"""

import os.path


class pathspec(object):
    """Path specification as expected by ROOT.

    Paths inside the current file can be specified in the usual way:
    - full path: /dir1/dir2
    - relative path: ../dir1

    Paths in other root files have to be preceded by the file name and
    a colon:
    - file path: myfile.root:/dir1/dir2

    See: TDirectoryFile::cd(..) in ROOT docs

    Useful information is provided as properties.

    Example:
    >>> ps = pathspec('foo.root:/path/to/obj/bar')
    >>> if ps.relative:
    ...     obj = rfile.Get(ps.rpath)
    ... else:
    ...     rfile = TFile.Open(ps.rfile, 'read')
    ...     obj = rfile.Get(ps.rpath)

    Pathname parsing rules:

    - Colons in file names are not allowed, since it is used to split
      the path into file path, and root object path.  Probably using
      some kind of an URL library can improve this.

    - When colons are being used, no other assumption is made about
      the ROOT file other than the above mentioned
      limitation. However, when only file paths are given (w/o the
      trailing colon), it is assumed to be path to a ROOT file if the
      path ends in `.root', path to a ROOT object inside a ROOT file
      otherwise.

    """

    # declare properties for pydoc
    path, rfile, rpath = None, None, None
    relative, norfile, norpath = None, None, None
    rfile_basename, rfile_dirname, rfile_split = None, None, None
    rpath_basename, rpath_dirname, rpath_split = None, None, None

    def __init__(self, path):
        self.path = path
        if path.find(':') < 0:
            if path.find('.root') < 0:
                self.rfile = ''
                self.rpath = path
            else:
                self.rfile = path
                self.rpath = ''
        else:
            self.rfile, self.rpath = path.split(':', 1)
        self.rpath = self.rpath.rstrip('/')
        self.norfile = not self.rfile
        self.norpath = not self.rpath
        self.relative = self.rpath.find('../') == 0 or \
                        self.rpath.find('/') > 0
        if self.rfile and self.relative:
            raise ValueError('Relative path not allowed with file specifier')

        # utilities
        self.rfile_dirname = os.path.dirname(self.rfile)
        self.rfile_basename = os.path.basename(self.rfile)
        self.rfile_split = os.path.split(self.rfile)
        self.rpath_split = os.path.split(self.rpath)
        self.rpath_basename = os.path.basename(self.rpath)
        self.rpath_dirname = os.path.dirname(self.rpath)

    def __str__(self):
        return self.path


from fixes import ROOT
from ROOT import gROOT, gDirectory
from utils import is_type


class savepwd(object):
    """Save present working directory and restore when done."""

    def __init__(self):
        self.pwd = gDirectory.GetDirectory('')

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        pass

    def __del__(self):
        self.pwd.cd()


class Rdir(object):
    """Global filesystem like directory hierarchy for a ROOT session."""

    files = []

    def __init__(self, files):
        with savepwd():
            self.files = []
            for f in files:
                if isinstance(f, str):
                    self.files.append(ROOT.TFile.Open(f, 'read'))
                else:
                    raise TypeError('Expected string, {} found'.format(type(f)))

    def get_dir(self, path=None):
        """Return directory from path.

        Doesn't check for non-directory.  It's the caller's
        responsibility.

        """
        if not path:
            return gDirectory.GetDirectory('')
        else:
            path = pathspec(path)
            with savepwd():
                if path.rfile:  # need to change to correct file first
                    if path.rfile not in [f.GetName() for f in self.files]:
                        # opening a file changes dir to the new file
                        self.files += [ROOT.TFile.Open(path.rfile, 'read')]
                    else:
                        gROOT.cd('{}:'.format(path.rfile))
                return gDirectory.GetDirectory(path.rpath)

    def ls(self, path=None, robj_t=None, robj_p=None):
        """Return list of key(s) in path.

        If path is a directory, returns a list of keys in the
        directory.  If it is a non-directory, returns the key for the
        object.

        The returned list can be filtered with object type, or a
        custom filter function.  Object type can be any ROOT Class
        that uses the ClassDef macro in it's declaration.  The custom
        filter function can be any function that can filter using the
        object key.  When these two filtering methods are combined, it
        is equivalent to boolean AND.

        path   -- path specification string (see pathspec for format)
        robj_t -- ROOT object type
        robj_p -- custom filter function that takes ROOT.TKey

        """
        rdir = self.get_dir(path)
        if not rdir:
            path = pathspec(path)
            # try again from one level up
            rdir = self.get_dir('{}:{}'.format(path.rfile, path.rpath_dirname))
            # FIXME: should be: while not rdir: keep trying
            keys = [rdir.GetKey(path.rpath_basename)]
        else:
            keys = rdir.GetListOfKeys()
        if robj_t:
            keys = filter(lambda key: is_type(key, robj_t), keys)
        if robj_p:
            keys = filter(robj_p, keys)
        return filter(None, keys)

    def ls_names(self, path=None, robj_t=None, robj_p=None):
        """Return list of key(s) names in path.

        For documentation on arguments, see Rdir.ls(..)

        """
        return [k.GetName() for k in self.ls(path, robj_t, robj_p)]

    def read(self, path=None, robj_t=None, robj_p=None, metainfo=False):
        """Return list of object(s) in path.

        When metainfo is True, source filename is added as a property
        (obj.file).  For documentation on other arguments, see
        Rdir.ls(..)

        """
        objs = []
        for k in self.ls(path, robj_t, robj_p):
            objs.append(k.ReadObj())
            if metainfo:
                setattr(objs[-1], 'file', k.GetFile().GetName())
        return objs
