#!/usr/bin/python
# coding=utf-8
"""Plotting interface for ROOT objects"""

import sys, os
from uuid import uuid4

from fixes import ROOT
from ROOT import gROOT, gSystem, gDirectory, gPad, gStyle

# colours
from ROOT import (kBlack, kWhite, kGray, kViolet, kMagenta, kPink,
                  kRed, kOrange, kYellow, kSpring, kGreen, kTeal,
                  kCyan, kAzure, kBlue)

# markers
from ROOT import (kDot, kPlus, kStar, kCircle, kMultiply,
                  kFullDotSmall, kFullDotMedium, kFullDotLarge,
                  kFullCircle, kFullSquare, kFullTriangleUp,
                  kFullTriangleDown, kOpenCircle, kOpenSquare,
                  kOpenTriangleUp, kOpenTriangleDown)


# helpers
def get_screen_size():
    """Get screen size (linux only)"""
    import subprocess
    xrandr = subprocess.Popen(('xrandr', '-q'), stdout = subprocess.PIPE)
    displays = subprocess.check_output(('grep', '\*'), stdin = xrandr.stdout)
    displays = displays.splitlines()
    displays = [display.split()[0] for display in displays]
    displays = [display.split('x') for display in displays]
    displays = [(int(dim[0]), int(dim[1])) for dim in displays]
    xres = min(displays[0][0], displays[1][0])
    yres = min(displays[0][1], displays[1][1])
    return (xres - 50, yres - 50)

def get_optimal_size(xgrid, ygrid, width=None, height=None, aspect=4.0/3):
    """Calculate canvas size from grid"""
    _width = lambda h: int(float(h/ygrid) * aspect * xgrid)
    _height = lambda w: int(float(w/xgrid) * (1/aspect) * ygrid)
    if not (width or height):
        width, height = get_screen_size()
        if xgrid > ygrid:       # wide
            height = _height(width)
        elif ygrid > xgrid:     # tall
            width = _width(height)
        else:                   # square (xgrid == ygrid)
            width = height
    elif not width and height:  # get width
        width = _width(height)
    elif not height and width:  # get height
        height = _height(width)
    return (width, height)

def isplottable(plottable):
    plottable_t = (ROOT.TAttLine, ROOT.TAttFill, ROOT.TAttMarker,
                   ROOT.TAttText, ROOT.TAttBBox2D, ROOT.TAttImage)
    return isinstance(plottable, plottable_t)

def arrange(plottables, sep, reverse = False, predicate = None):
    """Rearrange plottables in nested structure understood by Rplot.

    plottables -- flat iterable with plottables
    sep        -- number of consecutive plottables
                  that consitute one plot (pad)
    reverse    -- reverse plottable order
    predicate  -- apply predicate on each plot
                  (list of plottables on one pad)
    """
    tmp = []
    for i in xrange(0, len(plottables), sep):
        l = plottables[i:i+sep]
        if reverse: l.reverse()
        if predicate: predicate(l)
        tmp.append(l)
    return tmp

def partition(l, n):
    ll = len(l)
    reslen = ll/n + ll % n # no of partitions + 1 (if remainder)
    return [l[i*n : i*n+n] for i in xrange(reslen)]


# ROOT plotter
class Rplot(object):
    """Plotter class for ROOT"""

    fill_colours = (kAzure, kRed, kGray+2, kGreen, kMagenta, kOrange,
                    kCyan-7, kTeal-9)
    line_colours = (kAzure-6, kRed+2, kBlack, kGreen+2, kMagenta+2,
                    kOrange+1, kCyan+1, kTeal-8)

    markers = (kDot, kFullDotSmall, kCircle, kFullTriangleDown,
               kFullTriangleUp, kFullCircle, kPlus, kStar, kMultiply,
               kFullDotMedium, kFullDotLarge, kFullSquare,
               kOpenCircle, kOpenSquare, kOpenTriangleUp,
               kOpenTriangleDown)

    linestyles = {'-':1, '--':2, ':':3, '-.':5}

    grid = (1,1)
    size = (400, 400)
    alpha = 0.05
    plots = []
    canvas = None
    style = True
    stats = False
    stack = False
    shrink2fit = True

    def __init__(self, xgrid=1, ygrid=1, width=None, height=None):
        if gROOT.IsBatch() and not (width and height):
            raise ValueError('Width and height specs are compulsory in batch mode!')
        self.grid = (xgrid, ygrid)
        self.nplots = xgrid * ygrid
        self.size = get_optimal_size(xgrid, ygrid, width, height)

    def prep_canvas(self, name = 'canvas', title = ''):
        self.canvas = ROOT.TCanvas(name, title, *self.size)
        if self.nplots > 1:
            self.canvas.Divide(*self.grid)
        return self.canvas

    def get_stack(self, plots):
        plots_s = [[] for i in xrange(len(plots))]
        for i, plot in enumerate(plots):
            for j, plottable in enumerate(plot):
                plots_s[i].append(plottable.Clone('{}_s'.format(plottable.GetName())))
                if j > 0: plots_s[i][-1].Add(plots_s[i][-2])
            plots_s[i].reverse()
        return plots_s

    def set_style(self, plottable, num):
        if isinstance(plottable, ROOT.TAttFill):
            plottable.SetFillColorAlpha(self.fill_colours[num], 1-num*self.alpha)
        if isinstance(plottable, ROOT.TAttLine):
            plottable.SetLineColor(self.line_colours[num])
        if isinstance(plottable, ROOT.TH1):
            plottable.SetStats(self.stats)
        if isinstance(plottable, ROOT.TAttMarker):
            plottable.SetMarkerSize(0.2)
            plottable.SetMarkerStyle(self.markers[num])
            plottable.SetMarkerColor(self.line_colours[num])

    def get_viewport(self, plot):
        ymin, ymax = 0, 0
        for plottable in plot:
            ymin = min(ymin, plottable.GetMinimum())
            ymax = max(ymax, plottable.GetMaximum())
        if ymin < 0:
            ymin += 0.03*ymin
        if ymax > 0:
            ymax += 0.03*ymax
        return (ymin, ymax)

    def draw_same(self, plot, drawopts):
        if self.shrink2fit:
            yrange = self.get_viewport(plot)
        if isinstance(drawopts, str):
            drawopts = [drawopts] * len(plot)
        if len(plot) != len(drawopts):
            print('# plottables ≠ # options!')
            return
        for i, plottable in enumerate(plot):
            if self.shrink2fit:
                plottable.SetMinimum(yrange[0])
                plottable.SetMaximum(yrange[1])
            opts = drawopts[i]
            if i > 0: opts = '{} same'.format(opts)
            if self.style:
                self.set_style(plottable, i)
            plottable.Draw(opts)

    def draw_hist(self, plots, drawopts):
        if len(plots) % self.nplots == 0:
            if not self.canvas:
                self.prep_canvas()
            if self.stack:
                # necessary, goes out of scope otherwise
                self.plots = self.get_stack(plots)
            else:
                # only for consistency with the above
                self.plots = plots
            if isinstance(drawopts, str):
                drawopts = [drawopts] * len(self.plots)
            if len(self.plots) != len(drawopts):
                print('# plots ≠ # options!')
                return
            for i, plot in enumerate(self.plots):
                if not plot: continue
                self.canvas.cd(i+1)
                if isplottable(plot):
                    if self.style:
                        self.set_style(plot, 0)
                    plot.Draw(drawopts[i])
                else:
                    self.draw_same(plot, drawopts[i])
            return self.canvas
        else:
            print(u'# plots ({}) ≠ # pads ({})!'
                  .format(len(plots), self.nplots))
            return

    def draw_graph(self, *args, **kwargs):
        """Same as draw_hist(..)."""
        self.draw_hist(*args, **kwargs)

    def draw_tree(self, trees, exprs):
        if len(exprs) % len(trees) == 0:
            pass
