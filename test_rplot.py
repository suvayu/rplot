import unittest
import os
from fixes import ROOT
from ROOT import TH1F, TF1
from rplot import arrange, Rplot
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
        self.items = [[0, i] for i in range(16)]

    def test_arrange(self):
        rearranged = arrange(self.items, 8)
        self.assertEqual(len(rearranged), 2)
        self.assertEqual(len(rearranged[0]), len(rearranged[1]))

    def test_reverse(self):
        rearranged = arrange(self.items, 8)
        for l in rearranged:
            l.reverse()
        items_r = arrange(self.items, 8, reverse=True)
        self.assertListEqual(rearranged, items_r)

    def test_predicate(self):
        items_p = arrange(self.items, 8, predicate=lambda l: l.append(99))
        nplots = len(items_p)
        ref = [99 for j in range(nplots)]
        for i in range(nplots):
            self.assertListEqual([l[-1] for l in items_p], ref)


class test_Rplot(unittest.TestCase):
    """Test overlaying with transparency, and stacking"""

    @classmethod
    def setUpClass(self):
        self.hists1 = [TH1F('hist{}'.format(i), '', 100, -10, 10)
                       for i in range(16)]
        fns = [TF1('fn{}'.format(i), 'TMath::Gaus(x, {}, 1)'.format(i-8),
                   -10, 10) for i in range(len(self.hists1))]
        fill_hists(self.hists1, fns)
        del fns

        self.hists2 = [TH1F('hist{}'.format(s), '', 100, -10, 10)
                       for s in ascii_lowercase[0:6]]
        fns = [TF1('fn{}'.format(i),
                   '{}*TMath::Gaus(x, 0, {})'.format(1./(i+1), i-3), -10, 10)
               for i in range(len(self.hists2))]
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
        from ROOT import TFrame
        plotter = Rplot(2, 2, 1200, 800)
        plotter.draw_hist(self.plots, 'hist')
        plotter.canvas.Update()
        for i, plot in enumerate(self.plots):
            pad = plotter.canvas.cd(i+1)
            primitives = [pl for pl in pad.GetListOfPrimitives()
                          if not isinstance(pl, TFrame)]
            self.assertEqual(len(plot), len(primitives))

    def test_stack(self):
        from ROOT import TFrame
        # splicing overwrites ROOT objects in memory
        plots = self.plots[2:]
        plotter = Rplot(2, 1, 1200, 400)
        plotter.stack = True
        plotter.draw_hist(plots, 'hist')
        plotter.canvas.Update()
        for i, plot in enumerate(plots):
            pad = plotter.canvas.cd(i+1)
            primitives = [pl for pl in pad.GetListOfPrimitives()
                          if not isinstance(pl, TFrame)]
            self.assertEqual(len(plot), len(primitives))
            ref_counts = []
            for j, pl in enumerate(plot):
                count = pl.GetEntries()
                if j > 0:
                    count += ref_counts[-1]
                ref_counts.append(count)
            ref_counts.reverse()
            self.assertListEqual(ref_counts, [pl.GetEntries()
                                              for pl in primitives])
