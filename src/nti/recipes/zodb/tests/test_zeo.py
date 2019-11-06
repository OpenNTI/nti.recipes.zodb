#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
__docformat__ = "restructuredtext en"

import unittest

from hamcrest import assert_that
from hamcrest import contains_string

from nti.recipes.zodb.zeo import Databases
from . import NoDefaultBuildout

class TestDatabases(unittest.TestCase):

    def test_parse(self):
        # No verification, just sees if it runs

        buildout = NoDefaultBuildout()
        buildout['deployment'] = {
            'etc-directory': '/etc',
            'data-directory': '/data'
        }

        Databases(buildout, 'zeo', {'storages': 'Users Users_1 Sessions',
                                    'pack-gc': 'true'})

        #buildout.print_options()

        assert_that(buildout['users_1_storage']['server_zcml'],
                    contains_string('pack-gc true'))

        for i in range(1, 4):
            assert_that(buildout['base_zeo']['zeo.conf'], contains_string('<filestorage %d>' % i))
