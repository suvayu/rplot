import unittest
import os
import numpy as np
from fixes import ROOT
from tselect import Tsplice, Tselect, redirect2hist, parse_hist_name


def setUpModule():
    rfile = ROOT.TFile.Open('/tmp/testtree.root', 'recreate')
    tree = ROOT.TTree('testtree', '')
    foo = np.array([0], dtype=np.float32)
    tree.Branch("foo", foo, "foo/F")
    bar = np.array([0], dtype=np.double)
    tree.Branch("bar", bar, "bar/D")
    baz = np.array([0], dtype=np.int32)
    tree.Branch("baz", baz, "baz/I")
    sz = np.array([0], dtype=np.int32)
    tree.Branch("sz", sz, "sz/I")
    data = np.array([1., 2., 3., 4., 5.], dtype=np.float32)
    tree.Branch("data", data, "data[sz]/F")
    for i in xrange(1000):
        foo[0] = np.random.lognormal(mean=np.pi)
        bar[0] = np.random.normal(loc=0)
        baz[0] = np.random.binomial(100, 0.3)
        data += i
        sz[0] = 3 + i % 3
        tree.Fill()
    tree.Write()
    rfile.Close()


def tearDownModule():
    if os.path.exists('/tmp/testtree.root'):
        os.remove('/tmp/testtree.root')


def nplotted(tree, plot, selection=''):
    tree.Draw(plot, selection, 'goff')
    return tree.GetSelectedRows()


class test_Tsplice(unittest.TestCase):
    def setUp(self):
        self.rfile = ROOT.TFile.Open('/tmp/testtree.root')
        self.tree = self.rfile.Get('testtree')
        self.nentries = self.tree.GetEntries()
        # total no of elements in data
        self.ndata = nplotted(self.tree, 'data')
        self.splice = Tsplice(self.tree)

    def tearDown(self):
        self.rfile.Close()

    def test_reset(self):
        self.splice.make_splice('sz_gt_5', ROOT.TCut('sz>5'))  # zero
        self.assertEqual(nplotted(self.splice.reset(), 'sz'), self.nentries)

    def test_make_splice(self):
        self.splice.reset()
        cut = ROOT.TCut('foo>10')
        nexpected = nplotted(self.splice.reset(), 'foo', cut)
        tree = self.splice.make_splice('foo_gt_10', cut)
        self.assertEqual(nexpected, nplotted(tree, 'foo'))

        cut = ROOT.TCut('bar<0')
        nexpected = nplotted(self.splice.reset(), 'bar', cut)
        tree = self.splice.make_splice('nve_bar', cut)
        self.assertEqual(nexpected, nplotted(tree, 'bar'))

    def test_set_splice(self):
        self.splice.reset()
        cut = ROOT.TCut('bar>0')
        self.splice.make_splice('pve_bar', cut)
        nexpected = nplotted(self.splice.reset(), 'bar', cut)
        tree = self.splice.set_splice(self.splice.elists['pve_bar'])
        self.assertEqual(nexpected, nplotted(tree, 'bar'))

    def test_get_splice(self):
        self.splice.reset()
        cut = ROOT.TCut('sz==4')
        self.splice.make_splice('sz_eq_4', cut)
        nexpected = nplotted(self.splice.reset(), 'sz', cut)
        tree = self.splice.get_splice('sz_eq_4')
        self.assertEqual(nexpected, nplotted(tree, 'sz'))

    def test_elistarray_splice(self):
        self.splice.reset()
        # entries with 5 elements in data are guaranteed to pass, for
        # other entries, it passes when the passing element is < size,
        # which happens 3/5 times (when it is b/w 0-2), it is always
        # found for size = 5.  Therefore, it is found for at least 4/5
        # entries.
        cut = ROOT.TCut('(data[]%5)>3')
        tree = self.splice.make_splice('data_mod_5', cut,
                                       listtype='entrylistarray')
        expected = nplotted(tree, 'data')
        # print self.ndata, self.nentries, expected, 4*self.nentries/5
        self.assertLess(expected, self.ndata)
        self.assertLess(expected, self.nentries)
        self.assertGreater(expected, 4*self.nentries/5)

    def test_append(self):
        self.splice.reset()
        cut = ROOT.TCut('bar<0')
        self.splice.make_splice('bar', cut)
        cut = ROOT.TCut('bar>=0')
        # this generates a warning, but adds no entries
        self.splice.make_splice('bar', cut, append=True)
        self.splice.reset()
        # this works, and should add the rest of the entries
        tree = self.splice.make_splice('bar', cut, append=True)
        self.assertEqual(self.nentries, nplotted(tree, 'bar'))


class test_helpers(unittest.TestCase):
    def setUp(self):
        self.expr_noredir = ('foo', 'bar')
        self.expr_redir = ('foo>>hist', 'bar')
        self.expr_app = ('foo>>+hist', 'bar')

    def test_redirect2hist(self):
        expr = redirect2hist(self.expr_noredir)
        self.assertGreater(expr[0].find('>'), 0)
        self.assertNotEqual(expr, self.expr_noredir)

    def test_parse_hist_name(self):
        name = parse_hist_name(self.expr_redir[0])
        self.assertEqual(name, 'hist')
        name = parse_hist_name(self.expr_app[0])
        self.assertEqual(name, 'hist')


class test_Tselect(unittest.TestCase):
    def setUp(self):
        self.rfile = ROOT.TFile.Open('/tmp/testtree.root')
        self.tree = self.rfile.Get('testtree')
        self.nentries = self.tree.GetEntries()
        # total no of elements in data
        self.ndata = nplotted(self.tree, 'data')
        self.selector = Tselect(self.tree)

    def test_exprs(self):
        expr = ('foo>>hist', 'sz>4')
        self.selector.exprs = expr
        self.assertNotEqual(np.shape(expr), self.selector.shape)

    def test_fill_hist(self):
        self.selector.exprs = [
            ('foo>>hist1', 'sz>4'),
            ('data>>hist2', 'sz>4')
        ]
        hs = self.selector.fill_hists()
        self.assertAlmostEqual(hs[0].GetEntries(), self.nentries/3., delta=1)
        self.assertAlmostEqual(hs[1].GetEntries(), 5*self.nentries/3., delta=2)
