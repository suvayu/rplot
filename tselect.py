# coding=utf-8
"""Selection interface for TTrees"""

from __future__ import print_function

from fixes import ROOT


def redirect2hist(pair):
    """Scan and add expression, selection pair for redirects to histogram"""
    import uuid
    if pair[0].find('>>') < 0:
        return ('{}>>hist_{}'.format(pair[0], uuid.uuid4()), pair[1])
    else:
        return pair


def parse_hist_name(expr):
    """Return parsed histogram name"""
    start, stop = expr.find('>', 2)+2, expr.find('(')
    if expr[start] == '+':      # in case continue filling an existing hist
        start += 1
    if stop > 0:      # has binning info
        return expr[start:stop]
    else:
        return expr[start:]


# TTree selector
class Tselect(object):
    def __init__(self, tree):
        """Initialise TTree selector with tree"""
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


class Tsplice(object):
    """Implements splices for ROOT trees.

       This is not real splicing, it emulates the behaviour by
       maintaining an internal list of entry lists (e.g. TEventList,
       TEntryList, and TEntryListArray).

       >>> mysplice = Tsplice(tree)
       >>> spliced_tree1 = mysplice.make_splice(name1, 'foo<42')
       >>> spliced_tree2 = mysplice.make_splice(name2, 'bar>42')
       >>> spliced_tree1 = mysplice.get_splice(name1)

       The underlying tree and the entry lists can be accessed like this
       >>> mysplice.tree          # underlying tree
       >>> mysplice.elists[name]  # entry lists are stored in a dictionary

       There is also an advanced layered mode (off by default).  This
       is useful when you want to `build up' selections by applying
       them subsequently on top of one another.  To enable this mode,
       you can pass the `layered' flag during initialisation.  If you
       want to switch after the fact, you can set the layered property
       to True.  Make sure to clean up the entry list if this is done.
       Otherwise it is easy to loose track of which entry list was
       created with what selection.

    """

    elists = {}

    def __init__(self, tree, layered=False):
        """When layered is True, do not reset before creating new splices"""
        self.tree = tree
        self.layered = layered
        self.elists['all'] = tree.GetEntryList()
        self.current = self.elists['all']

    def reset(self):
        """Reset last splice to all entries"""
        self.tree.SetEntryList(self.elists['all'])
        self.current = self.elists['all']
        return self.tree

    def set_splice(self, elist):
        """Set entry list as splice"""
        if isinstance(elist, ROOT.TEventList):
            self.tree.SetEventList(elist)
        else:
            self.tree.SetEntryList(elist)
        self.current = elist
        return self.tree

    def make_splice(self, name, selection, listtype='entrylist', append=False):
        """Create and return a spliced tree as per selection.

           name      -- name of the splice

           selection -- selection used to create the splice, maybe a
                        selection string or a TCut object.

           listtype  -- type of splice to create, supported types are
                        TEventList, TEntryList, and TEntryListArray,
                        selected by: '', 'entrylist', and
                        'tentrylistarray', respectively.

           append    -- if append is true, continue filling any existing
                        splice.

           NOTE: when in layered mode, self.reset() is called before
           creating a new slice.

        """
        import uuid
        if not name:
            name = 'elist_'.format(uuid.uuid4())
        assert(name.find('>') < 0)  # forbid redirection in name
        if not append and name in self.elists:
            print('Tsplice: existing entry list will be overwritten!')
        assert(selection)
        listtype = listtype.lower()
        # empty for TEventList
        assert(listtype in ['', 'entrylist', 'entrylistarray'])

        if not self.layered:
            self.reset()
        if append:
            if self.layered and self.current != self.elists['all']:
                print('Tsplice is in layered mode, last splice was not `all\','
                      ' make sure this is what you want')
            self.tree.Draw('>>+{}'.format(name), selection, listtype)
        else:
            self.tree.Draw('>>{}'.format(name), selection, listtype)
        # should I also keep the selection?
        self.elists[name] = ROOT.gDirectory.Get(name)
        self.current = self.elists[name]
        return self.set_splice(self.elists[name])

    def get_splice(self, name):
        """Apply and return a splice created earlier.

           See make_splice(..) to look at how to make splices.

        """
        try:
            self.set_splice(self.elists[name])  # set_splice fixes current
        except KeyError:
            print('unknown entry list:', name)
        return self.tree
