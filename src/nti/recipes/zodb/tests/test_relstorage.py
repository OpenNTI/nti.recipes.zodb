#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"


import unittest

from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import contains_string

from nti.recipes.zodb.relstorage import Databases

from . import NoDefaultBuildout

def setup_buildout_environment():
    buildout = NoDefaultBuildout()
    buildout['deployment'] = {
        'etc-directory': '/etc',
        'data-directory': '/data',
        'cache-directory': '/caches'
    }
    buildout['relstorages_opts'] = {
        'sql_user': 'BAZ',
        'pack-gc': 'true'
    }
    buildout['relstorages_users_storage_opts'] = {
        'sql_user': 'FOO',
        'pack-gc': 'false'
    }
    return buildout

class TestDatabases(unittest.TestCase):

    def test_parse(self):
        buildout = setup_buildout_environment()
        buildout['environment'] = {
            'sql_user': 'user',
            'sql_passwd': 'passwd',
            'sql_host': 'host',
            'cache_servers': 'cache'
        }

        Databases(buildout, 'relstorages',
                  {'storages': 'Users Users_1 Sessions',
                   'enable-persistent-cache': 'true'})

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('shared-blob-dir false'))

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('FOO'))

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('pack-gc false'))

        assert_that(buildout['relstorages_users_1_storage']['client_zcml'],
                    contains_string('BAZ'))
        assert_that(buildout['relstorages_users_1_storage']['client_zcml'],
                    contains_string('pack-gc true'))

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('cache-local-dir /caches/data_cache/Users.cache'))

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('cache-local-dir-count 20'))

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('cache-local-mb 300'))

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('cache-servers cache'))

class TestDatabasesNoEnvironment(unittest.TestCase):

    def test_parse(self):
        # No verification, just sees if it runs

        buildout = setup_buildout_environment()

        Databases(buildout, 'relstorages',
                  {'storages': 'Users Users_1 Sessions',
                   'sql_user': 'user',
                   'sql_passwd': 'passwd',
                   'sql_host': 'host',
                   'relstorage-name-prefix': 'zzz',
                   'cache_servers': 'cache',
                   'enable-persistent-cache': 'true'})

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('shared-blob-dir false'))

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('FOO'))

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('pack-gc false'))

        assert_that(buildout['relstorages_users_1_storage']['client_zcml'],
                    contains_string('BAZ'))
        assert_that(buildout['relstorages_users_1_storage']['client_zcml'],
                    contains_string('pack-gc true'))

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('cache-local-dir /caches/data_cache/Users.cache'))

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('cache-local-dir-count 20'))

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('cache-local-mb 300'))

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('cache-servers cache'))

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('name zzzUsers'))

class TestDatabasesNoSecondaryCache(unittest.TestCase):

    def test_parse(self):
        # No verification, just sees if it runs

        buildout = setup_buildout_environment()

        Databases(buildout, 'relstorages',
                  {'storages': 'Users Users_1 Sessions',
                   'sql_user': 'user',
                   'sql_passwd': 'passwd',
                   'sql_host': 'host',
                   'enable-persistent-cache': 'true'})

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    is_not(contains_string('cache-servers')))

class TestDatabasesNoSecondaryCacheLegacy(unittest.TestCase):

    def test_parse(self):
        # No verification, just sees if it runs

        buildout = setup_buildout_environment()
        buildout['environment'] = {
            'sql_user': 'user',
            'sql_passwd': 'passwd',
            'sql_host': 'host'
        }

        Databases(buildout, 'relstorages',
                  {'storages': 'Users Users_1 Sessions',
                   'enable-persistent-cache': 'true'})

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    is_not(contains_string('cache-servers')))
