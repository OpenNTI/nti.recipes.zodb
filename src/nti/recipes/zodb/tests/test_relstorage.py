#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"
import textwrap
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

    def setUp(self):
        self.buildout = setup_buildout_environment()

    def test_parse(self):
        buildout = self.buildout
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
                    contains_string('cache-local-mb 300'))

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('cache-servers cache'))

    def test_parse_no_environment(self):
        # No verification, just sees if it runs
        buildout = self.buildout

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
                    contains_string('cache-local-mb 300'))

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('cache-servers cache'))

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    contains_string('name zzzUsers'))

    def test_parse_no_secondary_cache(self):
        # No verification, just sees if it runs

        buildout = self.buildout

        Databases(buildout, 'relstorages',
                  {'storages': 'Users Users_1 Sessions',
                   'sql_user': 'user',
                   'sql_passwd': 'passwd',
                   'sql_host': 'host',
                   'enable-persistent-cache': 'true'})

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    is_not(contains_string('cache-servers')))

    def test_parse_no_secondary_cache_legacy(self):
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
    maxDiff = None

    def test_parse_sqlite(self):
        buildout = self.buildout

        buildout['relstorages_sessions_storage_opts'] = {
            'sql_adapter_extra_args': textwrap.dedent(
                """
                driver gevent sqlite
                <pragmas>
                    synchronous off
                </pragmas>
                """
            )
        }
        Databases(buildout, 'relstorages', {
            'storages': 'Users Sessions',
            'sql_adapter': 'sqlite3',
            'write-zodbconvert': 'true',
        })


        expected = textwrap.dedent("""\
            <zodb Users>
                pool-size 60
                database-name Users
                cache-size 100000
                <zlibstorage Users>
                <relstorage Users>
                    blob-dir /data/Users.blobs
                    shared-blob-dir true
                    cache-prefix Users

                    commit-lock-timeout 60
                    cache-local-mb 300
                    cache-local-dir /caches/data_cache/Users.cache

                    name Users
                    keep-history false
                    pack-gc false
                    <sqlite3>
                        data-dir /data/relstorages_users_storage/

                    </sqlite3>
                </relstorage>
            </zlibstorage>
            </zodb>
        """).strip()
        self.assertEqual(
            buildout['relstorages_users_storage']['client_zcml'],
            expected)

        expected = """\
            <zodb Sessions>
                pool-size 60
                database-name Sessions
                cache-size 100000
                <zlibstorage Sessions>
                <relstorage Sessions>
                    blob-dir /data/Sessions.blobs
                    shared-blob-dir true
                    cache-prefix Sessions

                    commit-lock-timeout 60
                    cache-local-mb 300
                    cache-local-dir /caches/data_cache/Sessions.cache

                    name Sessions
                    keep-history false
                    pack-gc true
                    <sqlite3>
                        data-dir /data/relstorages_sessions_storage/
                        driver gevent sqlite
                        <pragmas>
                           synchronous off
                        </pragmas>
                    </sqlite3>
                </relstorage>
            </zlibstorage>
            </zodb>
        """
        self.assertEqual(
            [x.strip() for x in
             buildout['relstorages_sessions_storage']['client_zcml'].splitlines() if x.strip()],
            [x.strip() for x in expected.splitlines() if x.strip()])

        assert_that(buildout['zodb_conf']['input'],
                    contains_string('data-dir /data/relstorages_sessions_storage/'))

        assert_that(buildout['sessions_to_relstorage_conf']['input'],
                    contains_string('data-dir /data/relstorages_sessions_storage/'))
