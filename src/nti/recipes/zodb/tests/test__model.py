# -*- coding: utf-8 -*-
"""
Tests for _model.py.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import operator
import unittest

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_entry

from .. import _model as model

class TestPart(unittest.TestCase):

    def test_failed_lookup_with_str_extends(self):
        part = model.Part('part', extends=('base',))
        with self.assertRaises(KeyError):
            operator.itemgetter('key')(part)

    def test_failed_lookup_with_extends(self):
        base = model.Part('base')
        part = model.Part('part', extends=(base,))
        with self.assertRaises(KeyError):
            operator.itemgetter('key')(part)

class TestZConfigSnippet(unittest.TestCase):

    def test_no_empty_values(self):
        snip = model.ZConfigSnippet(key='')
        assert_that(str(snip), is_(''))

class TestRef(unittest.TestCase):

    def test_rdiv(self):
        ref = model.Ref('part', 'setting')
        val = '/prefix' / ref
        assert_that(str(val), is_('/prefix/${part:setting}'))

        # val is now a compound value. It also handles rdiv,
        # even though it is typically on the RHS simply due to
        # the way it is created
        val2 = '/root' / val
        assert_that(str(val2), is_('/root/prefix/${part:setting}'))
