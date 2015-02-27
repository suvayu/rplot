"""ROOT to Matplotlib"""


def th12errorbar(hist, yerr=True, xerr=False, asym=True):
    """Convert 1D histogram to array appropriate for Axes.errorbar"""
    assert (hist.GetDimension() == 1)
    from utils import thnbins, thn2array
    xwerr = thnbins(hist, width=xerr)
    ywerr = thn2array(hist, err=yerr, asym=asym)
    res = []
    if xerr:
        res += [xwerr[0], xwerr[1]/2.0]
    else:
        res.append(xwerr)
    if yerr:
        res.insert(1, ywerr[0])
        res.insert(2, ywerr[1:])
    else:
        res.insert(1, ywerr)
    return res


def th12hist(hist, edges=True):
    """Convert 1D histogram to array.

       FIXME: This needs to be converted to a `dataset' that can be
       converted to Axes.hist

    """
    assert (hist.GetDimension() == 1)
    from utils import thnbins, thn2array
    return (thn2array(hist), thnbins(hist, edges=edges, overflow=True)[1][1:])
