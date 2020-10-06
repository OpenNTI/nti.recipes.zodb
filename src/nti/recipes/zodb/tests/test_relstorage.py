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

from . import default_buildout

def setup_buildout_environment(**extra_options):
    return default_buildout(
        default_sections=dict(
            relstorages_opts={
                'sql_user': 'BAZ',
                'pack-gc': 'true'
            },
            relstorages_users_storage_opts={
                'sql_user': 'FOO',
                'pack-gc': 'false'
            },
        ),
        **extra_options
    )

class TestDatabases(unittest.TestCase):

    def setUp(self):
        self.buildout = setup_buildout_environment()

    def test_parse(self):
        buildout = self.buildout
        buildout['environment'] = {
            'sql_user': 'user',
            'sql_passwd': 'passwd',
            'sql_host': 'host',
            'cache_servers': 'cache',
            'compress': 'true',
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

        Databases(buildout, 'relstorages', {
            'storages': 'Users Users_1 Sessions',
            'sql_user': 'user',
            'sql_passwd': 'passwd',
            'sql_host': 'host',
            'relstorage-name-prefix': 'zzz',
            'cache_servers': 'cache',
            'enable-persistent-cache': 'true',
            'compress': 'none',
            'pool_timeout': '42',
        })

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

        expected = """\
<zodb Users>
  cache-size 100000
  database-name Users
  pool-size 60
  pool-timeout 42
  <relstorage Users>
    <mysql>
      # This comment preserves whitespace
          db Users
          host host
          passwd passwd
          user FOO
    </mysql>
  blob-dir /data/Users.blobs
  cache-local-dir /caches/data_cache/Users.cache
  cache-local-mb 300
  cache-prefix Users
  commit-lock-timeout 60
  keep-history false
  name zzzUsers
  pack-gc false
  shared-blob-dir false
  cache-module-name memcache
  cache-servers cache
</relstorage>
</zodb>"""
        self.assertEqual(
            buildout['relstorages_users_storage']['client_zcml'],
            expected
        )

    def test_parse_no_environment_extra_args(self):
        buildout = self.buildout
        buildout['relstorages_sessions_storage_opts'] = {
            'sql_adapter_extra_args': textwrap.dedent(
                """
                driver gevent mysqldb
                """
            )
        }

        Databases(buildout, 'relstorages',
                  {'storages': 'Sessions',
                   'sql_user': 'user',
                   'sql_passwd': 'passwd',
                   'sql_host': 'host',
                   'relstorage-name-prefix': 'zzz',
                   'cache_servers': 'cache',
                   'enable-persistent-cache': 'true',
                   'compress': 'true'})
        expected = """\
<zodb Sessions>
  cache-size 100000
  database-name Sessions
  pool-size 60
  <zlibstorage Sessions>
    <relstorage Sessions>
        <mysql>
          # This comment preserves whitespace
          db Sessions
          driver gevent mysqldb
          host host
          passwd passwd
          user BAZ
        </mysql>
      blob-dir /data/Sessions.blobs
      cache-local-dir /caches/data_cache/Sessions.cache
      cache-local-mb 300
      cache-prefix Sessions
      commit-lock-timeout 60
      keep-history false
      name zzzSessions
      pack-gc true
      shared-blob-dir false
      cache-module-name memcache
      cache-servers cache
    </relstorage>
</zlibstorage>
</zodb>"""
        self.assertEqual(
            expected,
            buildout['relstorages_sessions_storage']['client_zcml'],
        )

    def test_parse_postgres_with_dsn(self):
        buildout = self.buildout
        buildout['environment'] = {
            'sql_user': 'user',
            'sql_passwd': 'passwd',
            'sql_host': 'host',
        }
        buildout['relstorages_sessions_storage_opts'] = {
            'sql_adapter': 'postgresql',
            'sql_user': '${environment:sql_user}',
            'sql_passwd': '${environment:sql_passwd}',
            'sql_host': '${environment:sql_host}',
            'sql_db': 'sessions',
            'sql_adapter_args': textwrap.dedent(
                """
                dsn dbname=${:sql_db} user=${:sql_user} password=${:sql_passwd} host=${:sql_host}
                """
            ),
        }
        Databases(buildout, 'relstorages', {
            'storages': 'Sessions',
        })

        expected = """\
<zodb Sessions>
  cache-size 100000
  database-name Sessions
  pool-size 60
  <zlibstorage Sessions>
    <relstorage Sessions>
        <postgresql>
          # This comment preserves whitespace
          dsn dbname=sessions user=user password=passwd host=host
        </postgresql>
      blob-dir /data/Sessions.blobs
      cache-local-dir /caches/data_cache/Sessions.cache
      cache-local-mb 300
      cache-prefix Sessions
      commit-lock-timeout 60
      keep-history false
      name Sessions
      pack-gc true
      shared-blob-dir false
    </relstorage>
  compress false
</zlibstorage>
</zodb>"""

        self.assertEqual(
            expected,
            buildout['relstorages_sessions_storage']['client_zcml']
        )

    def test_parse_postgres_auto_dsn(self):
        # If no DSN is provided in sql_adapter_args, then one is created from the parts
        # that are present. Leave out password and host to test skipping those;
        # specify a port to test quoting.
        buildout = self.buildout
        buildout['relstorages_sessions_storage_opts'] = {
            'sql_adapter': 'postgresql',
            'sql_adapter_extra_args': textwrap.dedent("""
                sql_port 5433
            """)
        }
        Databases(buildout, 'relstorages', {
            'storages': 'Sessions',
        })

        expected = """\
<zodb Sessions>
  cache-size 100000
  database-name Sessions
  pool-size 60
  <zlibstorage Sessions>
    <relstorage Sessions>
        <postgresql>
          # This comment preserves whitespace
          dsn dbname='Sessions' user='BAZ' port=5433
        </postgresql>
      blob-dir /data/Sessions.blobs
      cache-local-dir /caches/data_cache/Sessions.cache
      cache-local-mb 300
      cache-prefix Sessions
      commit-lock-timeout 60
      keep-history false
      name Sessions
      pack-gc true
      shared-blob-dir false
    </relstorage>
  compress false
</zlibstorage>
</zodb>"""

        self.assertEqual(
            expected,
            buildout['relstorages_sessions_storage']['client_zcml']
        )



    def test_parse_override_defaults_local(self):
        buildout = self.buildout
        buildout['environment'] = {
            'sql_user': 'user',
            'sql_passwd': 'passwd',
            'sql_host': 'host',
        }
        # If this one isn't present, then
        # the one from the most specific section isn't found at all.
        # That's ok, this is the one that's documented.
        buildout['relstorages_opts']['pool_timeout'] = '64s'
        buildout['relstorages_sessions_storage_opts'] = {
            'pool_size': 13,
            'pool_timeout': 54, # This one is actually found
            'commit_lock_timeout': 42,
        }

        Databases(buildout, 'relstorages', {
            'storages': 'Sessions',
        })

        expected = """\
<zodb Sessions>
  cache-size 100000
  database-name Sessions
  pool-size 13
  pool-timeout 54
  <zlibstorage Sessions>
    <relstorage Sessions>
        <mysql>
          # This comment preserves whitespace
          db Sessions
          host host
          passwd passwd
          user BAZ
        </mysql>
      blob-dir /data/Sessions.blobs
      cache-local-dir /caches/data_cache/Sessions.cache
      cache-local-mb 300
      cache-prefix Sessions
      commit-lock-timeout 42
      keep-history false
      name Sessions
      pack-gc true
      shared-blob-dir false
    </relstorage>
  compress false
</zlibstorage>
</zodb>"""

        self.assertEqual(
            expected,
            buildout['relstorages_sessions_storage']['client_zcml']
        )

    def test_parse_override_defaults_part(self):
        buildout = self.buildout
        buildout['environment'] = {
            'sql_user': 'user',
            'sql_passwd': 'passwd',
            'sql_host': 'host',
        }

        Databases(buildout, 'relstorages', {
            'storages': 'Sessions',
            'pool_size': 13,
            'commit_lock_timeout': 42,
            'cache_size': 345,
        })

        expected = """\
<zodb Sessions>
  cache-size 345
  database-name Sessions
  pool-size 13
  <zlibstorage Sessions>
    <relstorage Sessions>
        <mysql>
          # This comment preserves whitespace
          db Sessions
          host host
          passwd passwd
          user BAZ
        </mysql>
      blob-dir /data/Sessions.blobs
      cache-local-dir /caches/data_cache/Sessions.cache
      cache-local-mb 300
      cache-prefix Sessions
      commit-lock-timeout 42
      keep-history false
      name Sessions
      pack-gc true
      shared-blob-dir false
    </relstorage>
  compress false
</zlibstorage>
</zodb>"""

        self.assertEqual(
            expected,
            buildout['relstorages_sessions_storage']['client_zcml']
        )


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

        Databases(buildout, 'relstorages', {
            'storages': 'Users Users_1 Sessions',
            'enable-persistent-cache': 'true'
        })

        assert_that(buildout['relstorages_users_storage']['client_zcml'],
                    is_not(contains_string('cache-servers')))
    maxDiff = None

    def test_parse_sqlite(self):
        buildout = setup_buildout_environment(relstorages_opts={'sql_adapter': 'sqlite3'})
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
            'write-zodbconvert': 'true',
        })
        self.assertEqual(
            buildout['relstorages_opts']['sql_adapter'],
            'sqlite3')
        self.assertEqual(
            buildout['relstorages_users_storage']['sql_adapter'],
            'sqlite3'
        )
        expected = """\
<zodb Users>
  cache-size 100000
  database-name Users
  pool-size 60
  <zlibstorage Users>
    <relstorage Users>
        <sqlite3>
          # This comment preserves whitespace
          data-dir /data/relstorages_users_storage
        </sqlite3>
      blob-dir /data/Users.blobs
      cache-local-dir /caches/data_cache/Users.cache
      cache-local-mb 300
      cache-prefix Users
      commit-lock-timeout 60
      keep-history false
      name Users
      pack-gc false
      shared-blob-dir true
    </relstorage>
  compress false
</zlibstorage>
</zodb>"""
        self.assertEqual(
            expected,
            buildout['relstorages_users_storage']['client_zcml'],
        )
        expected = """\
<zodb Sessions>
  cache-size 100000
  database-name Sessions
  pool-size 60
  <zlibstorage Sessions>
    <relstorage Sessions>
        <sqlite3>
          # This comment preserves whitespace
          data-dir /data/relstorages_sessions_storage
          driver gevent sqlite

          <pragmas>
            synchronous off
          </pragmas>
        </sqlite3>
      blob-dir /data/Sessions.blobs
      cache-local-dir /caches/data_cache/Sessions.cache
      cache-local-mb 300
      cache-prefix Sessions
      commit-lock-timeout 60
      keep-history false
      name Sessions
      pack-gc true
      shared-blob-dir true
    </relstorage>
  compress false
</zlibstorage>
</zodb>"""

        self.assertEqual(
            buildout['relstorages_sessions_storage']['client_zcml'],
            expected
        )
        self.assertEqual(
            [x.strip() for x in
             buildout['relstorages_sessions_storage']['client_zcml'].splitlines() if x.strip()],
            [x.strip() for x in expected.splitlines() if x.strip()])

        assert_that(buildout['zodb_conf']['input'],
                    contains_string('data-dir /data/relstorages_sessions_storage'))

        assert_that(buildout['sessions_to_relstorage_conf']['input'],
                    contains_string('data-dir /data/relstorages_sessions_storage'))
        assert_that(buildout['sessions_from_relstorage_conf']['input'],
                    contains_string('data-dir /data/relstorages_sessions_storage'))
