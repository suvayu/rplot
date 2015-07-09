"""Provides fixes and workarounds for many ROOT eccentricities.

It also adds methods to ROOT classes so that they support standard
Python API for common tasks (e.g. iteration), language constructs
(e.g. `if .. in ..:'), etc.

To use these fixes/features, one should import ROOT from this module
before doing anything.

  >>> from fixes import ROOT

@author Suvayu Ali
@email Suvayu dot Ali at cern dot ch
@date 2014-09-05 Fri

"""


import ROOT


# General helpers
def set_attribute(clss, attr, value):
    """For all cls in clss, set cls.attr to value.

    If value is a string, treat it is as an existing cls attribute and
    remap its value to attr (cls.attr = cls.value ).

    """
    def _setter(cls, attr, value):
        if isinstance(value, str):
            value = getattr(cls, value)
        setattr(cls, attr, value)
    try:
        for cls in clss:
            _setter(cls, attr, value)
    except TypeError:
        _setter(clss, attr, value)


def set_ownership(methods):
    """Tell Python caller owns returned object, set `clsmethod._creates'."""
    set_attribute(methods, '_creates', True)


def py_next(iterator):
    el = iterator.cpp_next()        # call C++ version of cls.next()
    if el:
        return el
    else:
        raise StopIteration


_creators = [
    ROOT.TObject.Clone,
    ROOT.TFile.Open,
    ROOT.RooAbsReal.clone,
    ROOT.RooAbsData.correlationMatrix,
    ROOT.RooAbsData.covarianceMatrix,
    ROOT.RooAbsData.reduce,
    ROOT.RooDataSet.binnedClone
]

# add create* and plot* methods to _creators
for typ in (ROOT.RooAbsReal, ROOT.RooAbsData):
    matches = [attr for attr in vars(typ)
               if attr.find('create') == 0 or attr.find('plot') == 0]
    _creators.extend(map(lambda attr: getattr(typ, attr), matches))
# cleanup temporary vars
del matches, attr

set_ownership(_creators)


_root_containers = [
    ROOT.TCollection
]

_roofit_containers = [
    ROOT.RooAbsCollection,
    ROOT.RooLinkedList
]

# `if <item> in <container>:' construct
set_attribute(_root_containers, '__contains__', 'FindObject')
set_attribute(_roofit_containers, '__contains__', 'find')

# # key access: obj[name]
# set_attribute(_root_containers, '__getitem__', 'FindObject')
# set_attribute(_roofit_containers, '__getitem__', 'find')

# iteration for all RooFit containers
set_attribute(_roofit_containers, '__iter__', 'fwdIterator')
set_attribute(ROOT.RooFIter, 'cpp_next', 'next')  # save C++ verion of next
set_attribute(ROOT.RooFIter, 'next', py_next)    # reassign python version
set_attribute(ROOT.RooFIter, '__next__', 'next')  # python 3 compatibility
del py_next


# standalone iterator for RooAbsData FIXME: integrate into python properly
def dst_iter(dst):
    """Generator function to iterate over entries in a RooDataSet"""
    argset = dst.get()
    for i in xrange(dst.numEntries()):
        dst.get(i)
        yield argset
