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

from .. import _model as model

# pylint:disable=protected-access

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

    def test_lookup_correct_order(self):
        # Later items take precedence.
        first = model.Part('first', key='a string')
        second = model.Part('second', key=42)
        # wrapped in a const
        val = second['key']
        assert_that(val.const, is_(42))
        part = model.Part('part', extends=(first, second))
        part_val = part['key']
        assert_that(part_val.const, is_(42))

    def test_get_default(self):
        part = model.Part('part')
        self.assertIs(part.get('no-key', self), self)


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


class TestConst(unittest.TestCase):

    def test_str(self):
        self.assertEqual(str(model._Const(self)), str(self))
