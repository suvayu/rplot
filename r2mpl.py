"""ROOT to Matplotlib"""

def th12errorbar(hist, yerr=True, xerr=False, asym=True):
    """Convert 1D histogram to array appropriate for Axes.errorbar"""
    from .utils import thnbins, thn2array
    assert (hist.GetDimension() == 1)
    xwerr = thnbins(hist, width=xerr)
    ywerr = thn2array(hist, err=yerr, asym=asym)
    res = []
    if xerr: res += [xwerr[0], xwerr[1]/2.0]
    else: res.append(xwerr)
    if yerr:
        res.insert(1, ywerr[0])
        res.insert(2, ywerr[1:])
    else: res.insert(1, ywerr)
    return res
