# coding=utf-8
"""Utilities"""


def is_type(key, rtype):
    """Is key the ROOT type `rtype''?"""
    from ROOT import TClass
    return TClass.GetClass(key.GetClassName()).InheritsFrom(rtype.Class())


def is_dir(key):
    """Is it a directory key?"""
    from ROOT import TDirectoryFile
    return is_type(key, TDirectoryFile)


def root_str(objs):
    """String representation for ROOT objects"""
    fmt = '{cls}({nm})'
    try:
        res = [fmt.format(cls=obj.ClassName(), nm=obj.GetName())
               for obj in objs]
        res = '[{}]'.format(', '.join(res))
    except:
        res = fmt.format(cls=objs.ClassName(), nm=objs.GetName())
    return res


class Rtmpfile(object):
    # NOTE: This is to ignore the security warning from os.tmpnam.
    # There is no risk since I `recreate' the TFile.
    from warnings import filterwarnings
    filterwarnings(action='ignore', category=RuntimeWarning,
                   message='tmpnam is a potential security risk.*')

    def __init__(self, keep=False):
        """Do not remove temporary file if `keep' is `True'"""
        self.keep = keep
        from os import tmpnam
        from time import strftime, localtime
        from ROOT import TFile
        self.rfile = TFile.Open('{}-{}.root'.format(
            tmpnam(), strftime('%y-%m-%d-%H%M%S%Z', localtime())), 'recreate')

    def __del__(self):
        from os import remove
        self.rfile.Close()
        if not self.keep:
            remove(self.rfile.GetName())

    def __enter__(self):
        """Return the ROOT file when used with `with'"""
        return self.rfile

    def __exit__(self, exc_type, exc_value, traceback):
        """Return True, in case an exception is raised, ignored otherwise."""
        return True


# RooFit utilities
def dst_iter(dst):
    """RooAbsData iterator: generator to iterate over a RooDataSet"""
    argset = dst.get()
    for i in range(dst.numEntries()):
        dst.get(i)
        yield argset


# histogram utilities
def th1fill(hist, dim=1):
    """Return a TH1.Fill wrapper for use with map(..)."""
    if 1 == dim:
        fill = lambda i: hist.Fill(i)
    elif 2 == dim:
        fill = lambda i, j: hist.Fill(i, j)
    elif 3 == dim:
        fill = lambda i, j, k: hist.Fill(i, j, k)
    else:
        fill = None
    return fill


def th1clonereset(hist, name):
    """Clone and reset ROOT histogram"""
    res = hist.Clone(name)
    res.Reset('icesm')
    res.Sumw2()
    return res


def thnbincontent(hist, x, y=0, z=0, err=False, asym=False):
    """Get histogram bin content.

       hist -- histogram
       x    -- bin x coordinates
       y    -- bin y coordinates (only for 2D)
       z    -- bin z coordinates (only for 3D)
       err  -- also return error
       asym -- return asymmetric error

    """
    dim = hist.GetDimension()
    if dim == 1:
        xyz = [x]
    elif dim == 2:
        xyz = [x, y]
    else:
        xyz = [x, y, z]
    content = hist.GetBinContent(*xyz)
    if err and asym:
        return (content, hist.GetBinErrorUp(*xyz), hist.GetBinErrorLow(*xyz))
    elif err:
        return (content, hist.GetBinError(*xyz))
    else:
        return content


def taxisbincentre(axis, i, edges=False, width=False):
    """Get histogram bin centre (X-axis).

       axis  -- axis instance
       i     -- bin number
       edges -- also return bin low edges
       width -- also return bin width
    """
    if edges and width:
        return (axis.GetBinCenter(i), axis.GetBinLowEdge(i),
                axis.GetBinWidth(i))
    elif edges:
        return (axis.GetBinCenter(i), axis.GetBinLowEdge(i))
    elif width:
        return (axis.GetBinCenter(i), axis.GetBinWidth(i))
    else:
        return axis.GetBinCenter(i)


def thnbincentre(hist, i, edges=False, width=False):
    """Get histogram bin centre (X, Y, Z).

       hist  -- histogram
       i     -- bin number
       edges -- also return bin low edges
       width -- also return bin width
    """
    dim = hist.GetDimension()
    axes = []
    if dim == 1:
        axes.append(hist.GetXaxis())
    elif dim == 2:
        axes.append(hist.GetYaxis())
    else:
        axes.append(hist.GetZaxis())
    res = map(lambda ax: taxisbincentre(ax, i, edges, width), axes)
    return res[0] if len(res) == 1 else res

# Numpy based utilities
try:
    import numpy as np

    def thn2array(hist, err=False, asym=False, pair=False, shaped=False,
                  overflow=False):
        """Convert ROOT histograms to numpy.array

           hist -- histogram to convert
           err  -- include bin errors
           asym -- Asymmetric errors
           pair -- pair bin errors with bin content, by default errors
                   are put in a similarly shaped array in res[1]
         shaped -- return an array with appropriate dimensions, 1-D
                   array is returned normally
       overflow -- include underflow and overflow bins
        """
        if shaped:
            xbins = hist.GetNbinsX()
            ybins = hist.GetNbinsY()
            zbins = hist.GetNbinsZ()
            # add overflow, underflow bins
            overflow *= 2
            if ybins == 1:
                shape = [xbins + overflow]
            elif zbins == 1:
                shape = [xbins + overflow, ybins + overflow]
            else:
                shape = [xbins + overflow, ybins + overflow, zbins + overflow]
        else:
            shape = [len(hist)]
            if not overflow:
                shape[0] -= 2
        if err:
            shape.append(3 if asym else 2)
        hiter = range(len(hist)) if overflow else range(1, len(hist)-1)
        val = np.array([thnbincontent(hist, i, err=err, asym=asym)
                        for i in hiter]).reshape(*shape)
        return val if pair else val.transpose()

    def thnbins(hist, edges=False, width=False, pair=False, overflow=False):
        """Return histogram bin centre or edges"""
        hiter = range(len(hist)) if overflow else range(1, len(hist)-1)
        val = np.array([thnbincentre(hist, i, edges=edges, width=width)
                        for i in hiter])
        return val if pair else val.transpose()

    def thnprint(hist, err=False, asym=False, pair=False, shaped=True):
        """Print ROOT histograms of any dimention"""
        val = thn2array(hist, err=err, asym=asym, pair=pair, shaped=shaped)
        print('Hist: {}, dim: {}'.format(hist.GetName(), len(np.shape(val))))
        hist.Print()
        print(np.flipud(val))  # flip y axis, FIXME: check what happens for 3D

except ImportError:
    import warnings
    # warnings.simplefilter('always')
    msg = 'Could not import numpy.\n'
    msg += 'Unavailable functions: thn2array, thnbins, thnprint.'
    warnings.warn(msg, ImportWarning)

    def thn2array(hist, err, asym, pair, shaped):
        raise NotImplementedError('Not available without numpy')

    def thnbins(hist, edges, width, pair):
        raise NotImplementedError('Not available without numpy')

    def thnprint(hist, err, asym, pair, shaped):
        raise NotImplementedError('Not available without numpy')


def th1offset(hist, offset):
    """Offset non-empty histogram bins"""
    # only offset bins with content
    for b in range(hist.GetXaxis().GetNbins()):
        content = hist.GetBinContent(b)
        # FIXME: shouldn't work, comparing floats
        if content != 0.:
            hist.SetBinContent(b, content+offset)
    return hist


# other utilities
from argparse import (ArgumentParser, ArgumentDefaultsHelpFormatter,
                      RawDescriptionHelpFormatter)


class NoExitArgParse(ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


class RawArgDefaultFormatter(ArgumentDefaultsHelpFormatter,
                             RawDescriptionHelpFormatter):
    pass


def _import_args(namespace, d={}):
    """Import attributes from namespace to local environment.

    namespace -- namespace to import attributes from
    d         -- dictionary that is returned with attributes
                 and values (default: empty dict, leave it
                 this way unless you know what you are doing)

    Usage:
      >>> opts = parser.parse_args(['foo', '-o', 'bar'])
      >>> locals().update(_import_args(opts))

    """
    attrs = vars(namespace)
    for attr in attrs:
        d[attr] = getattr(namespace, attr)
    return d


def file_hash(filename):
    """Calculate MD5 hash of file based on contents"""
    import hashlib
    with open(filename) as myfile:
        contents = myfile.read()
        return hashlib.md5(contents).hexdigest()


def suppress_warnings():
    import warnings
    # NOTE: This is to ignore a warning from the call to
    # TTreeFormula::EvalInstance().  One of the default arguments is a
    # char**.  PyROOT does not provide converters for that, leading to the
    # warning.  As long as this feature is not accessed, ignoring is safe.
    warnings.filterwarnings(action='ignore', category=RuntimeWarning,
                            message='creating converter for unknown type.*')
