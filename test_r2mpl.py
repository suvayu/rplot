#!/usr/bin/env python

import unittest
from fixes import ROOT
from r2mpl import th12errorbar, th12hist
import numpy as np


def setUpModule():
    ROOT.gROOT.SetBatch(True)
    ROOT.gErrorIgnoreLevel = ROOT.kWarning


class test_r2mpl(unittest.TestCase):
    def setUp(self):
        self.nbins = 20
        self.hist = ROOT.TH1F('hist', '', self.nbins, -3, 3)
        self.hist.FillRandom('gaus', 1000)

    def tearDown(self):
        del self.hist

    def test_th12errorbar(self):
        x, y, yerr = th12errorbar(self.hist, yerr=True)
        self.assertEqual(np.shape(x), (self.nbins,))
        self.assertEqual(np.shape(y), (self.nbins,))
        self.assertEqual(np.shape(yerr), (2, self.nbins))

    def test_th12hist(self):
        c, b = th12hist(self.hist, edges=True)
        self.assertEqual(np.shape(c), (self.nbins,))
        self.assertEqual(np.shape(b), (self.nbins+1,))
