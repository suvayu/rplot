# coding=utf-8
"""Plotting interface TTree branches"""

from fixes import ROOT


def redirect2hist(pair):
    """Scan and add expression, selection pair for redirects to histogram"""
    import uuid
    if pair[0].find('>>') < 0:
        return ('{}>>hist{}'.format(pair[0], uuid.uuid4()), pair[1])
    else:
        return pair


def parse_hist_name(expr):
    """Return parsed histogram name"""
    start, stop = expr.find('>', 2)+2, expr.find('(')
    if stop > 0:      # has binning info
        return expr[start:stop]
    else:
        return expr[start:]


# TTree plotter
class Tplot(object):
    def __init__(self, tree):
        """Initialise TTree plotter with tree"""
        assert(tree)
        self.tree = tree

    @property
    def exprs(self):
        """List of (expression, selection) pairs"""
        return self._exprs

    @exprs.setter
    def exprs(self, exprs):
        import numpy as np
        self.shape = np.shape(exprs)
        if 1 == len(self.shape):
            exprs = [exprs]
            self.shape = np.shape(exprs)
        # ensure shape == (N, 2)
        assert(2 == len(self.shape))
        assert(2 == self.shape[1])
        self._exprs = map(redirect2hist, exprs)

    @exprs.deleter
    def exprs(self):
        del self.shape
        del self._exprs

    def fill_hists(self, opts=''):
        """Iterate over expressions and fill histograms"""
        def _get_hist(expr):
            if not expr[0]:
                return None
            self.tree.Draw(expr[0], expr[1], '{} goff'.format(opts))
            return ROOT.gROOT.FindObject(parse_hist_name(expr[0]))
        self.hists = map(_get_hist, self._exprs)
        return self.hists

empty_expr = ('', '')
