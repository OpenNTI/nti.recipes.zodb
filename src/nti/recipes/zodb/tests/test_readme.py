#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import doctest
import os
import unittest

from zope.testing import renormalizing
import zc.buildout.testing

def test_suite():
    # If these get passed to the child buildout,
    # they result in unwanted warnings which mess up
    # doctests. They've already been read, no harm in
    # removing them.
    os.environ.pop('PYTHONWARNINGS', None)
    os.environ.pop('PYTHONDEVMODE', None)
    root = this_dir = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(root, 'setup.py')):
        prev, root = root, os.path.dirname(root)
        if root == prev: # pragma: no cover
            # Let's avoid infinite loops at root
            raise AssertionError('could not find my setup.py')

    optionflags = (
        doctest.NORMALIZE_WHITESPACE
        | doctest.ELLIPSIS
        | doctest.IGNORE_EXCEPTION_DETAIL
    )

    index_rst = os.path.join(root, 'README.rst')
    # Can't pass absolute paths to DocFileSuite, needs to be
    # module relative
    index_rst = os.path.relpath(index_rst, this_dir)

    return unittest.TestSuite((
        unittest.defaultTestLoader.loadTestsFromName(__name__),
        doctest.DocFileSuite(
            index_rst,
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            optionflags=optionflags,
            checker=renormalizing.RENormalizing([
                zc.buildout.testing.normalize_path,
                zc.buildout.testing.normalize_endings,
                zc.buildout.testing.normalize_script,
                zc.buildout.testing.normalize_egg_py,
                zc.buildout.testing.not_found,
            ]),
        )
    ))
