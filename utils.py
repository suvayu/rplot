# coding=utf-8
"""Utilities"""

def _import_args(namespace, d = {}):
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


## histogram utilities
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

    def thn2array(hist, err=False, asym=False, pair=False, shaped=False):
        """Convert ROOT histograms to numpy.array

           hist -- histogram to convert
           err  -- include bin errors
           asym -- Asymmetric errors
           pair -- pair bin errors with bin content, by default errors
                   are put in a similarly shaped array in res[1]
         shaped -- return an array with appropriate dimensions, 1-D
                   array is returned normally
        """
        if shaped:
            xbins = hist.GetNbinsX()
            ybins = hist.GetNbinsY()
            zbins = hist.GetNbinsZ()
            # add overflow, underflow bins
            if ybins == 1: shape = [xbins + 2]
            elif zbins == 1: shape = [xbins + 2, ybins + 2]
            else: shape = [xbins + 2, ybins + 2, zbins + 2]
        else:
            shape = [len(hist)]
        if err: shape.append(3 if asym else 2)
        val = np.array([thnbincontent(hist, i, err=err, asym=asym)
                        for i in xrange(len(hist))]).reshape(*shape)
        if pair: return val
        else: return val.transpose()

    def thnbins(hist, edges=False, width=False, pair=False):
        """Return histogram bin centre or edges"""
        val = np.array([thnbincentre(hist, i, edges, width)
                        for i in xrange(len(hist))])
        if pair: return val
        else: return val.transpose()

    def thnprint(hist, err=False, asym=False, pair=False, shaped=True):
        """Print ROOT histograms of any dimention"""
        val = thn2array(hist, err=err, asym=asym, pair=pair, shaped=shaped)
        print('Hist: {}, dim: {}'.format(hist.GetName(), len(np.shape(val))))
        hist.Print()
        print(np.flipud(val)) # flip y axis, FIXME: check what happens for 3D

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
    for b in xrange(hist.GetXaxis().GetNbins()):
        content = hist.GetBinContent(b)
        # FIXME: shouldn't work, comparing floats
        if content != 0.: hist.SetBinContent(b, content+offset)
    return hist
