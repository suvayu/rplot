#!/usr/bin/env python

import unittest
import os
from fixes import ROOT
from ROOT import TH1F, TF1
from rplot import arrange, Rplot
from utils import file_hash
from string import ascii_lowercase

__pngfile__ = '/tmp/test.png'


def setUpModule():
    ROOT.gROOT.SetBatch(True)
    ROOT.gErrorIgnoreLevel = ROOT.kWarning


def tearDownModule():
    if os.path.exists(__pngfile__):
        os.remove(__pngfile__)


# utilities
def fill_hists(hists, fns):
    """Fill histograms using given functions"""
    for i, hist in enumerate(hists):
        hist.FillRandom(fns[i].GetName(), 1000)
        hist.SetXTitle('Foo[bar]')
        hist.SetYTitle('Events')


class test_arrange(unittest.TestCase):
    def setUp(self):
        self.items = [[0, i] for i in xrange(16)]

    def test_arrange(self):
        rearranged = arrange(self.items, 8)
        self.assertEqual(len(rearranged), 2)
        self.assertEqual(len(rearranged[0]), len(rearranged[1]))

    def test_reverse(self):
        rearranged = arrange(self.items, 8)
        map(lambda l: l.reverse(), rearranged)
        items_r = arrange(self.items, 8, reverse=True)
        map(self.assertListEqual, rearranged, items_r)

    def test_predicate(self):
        items_p = arrange(self.items, 8, predicate=lambda l: l.append(99))
        ref = [99 for j in xrange(8)]
        for i in xrange(2):
            self.assertListEqual([items_p[i][j][-1] for j in xrange(8)], ref)


class test_Rplot(unittest.TestCase):
    """Test overlaying with transparency, and stacking"""

    @classmethod
    def setUpClass(self):
        self.hists1 = [TH1F('hist{}'.format(i), '', 100, -10, 10)
                       for i in xrange(16)]
        fns = [TF1('fn{}'.format(i), 'TMath::Gaus(x, {}, 1)'.format(i-8),
                   -10, 10) for i in xrange(len(self.hists1))]
        fill_hists(self.hists1, fns)
        del fns

        self.hists2 = [TH1F('hist{}'.format(s), '', 100, -10, 10)
                       for s in ascii_lowercase[0:6]]
        fns = [TF1('fn{}'.format(i),
                   '{}*TMath::Gaus(x, 0, {})'.format(1./(i+1), i-3), -10, 10)
               for i in xrange(len(self.hists2))]
        fill_hists(self.hists2, fns)
        del fns

        self.plots = [
            [h for i, h in enumerate(self.hists1) if i % 2 == 0],
            [h for i, h in enumerate(self.hists1) if i % 2 == 1],
            [h for i, h in enumerate(self.hists2) if i % 2 == 0],
            [h for i, h in enumerate(self.hists2) if i % 2 == 1],
        ]

    @classmethod
    def tearDownClass(self):
        del self.plots

    def test_overlay(self):
        plotter = Rplot(2, 2, 1200, 800)
        plotter.draw_hist(self.plots, 'hist')
        plotter.canvas.Update()
        plotter.canvas.Print(__pngfile__)
        self.assertEqual('25c6ff7ed5422880e47a0c50b0d6e044',
                         file_hash(__pngfile__))

    def test_stack(self):
        # splicing overwrites ROOT objects in memory
        plots = [self.plots[2], self.plots[3]]
        plotter = Rplot(2, 1, 1200, 400)
        plotter.stack = True
        plotter.draw_hist(plots, 'hist')
        plotter.canvas.Update()
        plotter.canvas.Print(__pngfile__)
        self.assertEqual('df05887dc179fc0097d0f01dfd9f23a8',
                         file_hash(__pngfile__))
