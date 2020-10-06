#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
__docformat__ = "restructuredtext en"

import unittest

from nti.recipes.zodb.zeo import Databases
from . import default_buildout

class TestDatabases(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.buildout = default_buildout()

    def test_parse(self):
        # No verification, just sees if it runs
        buildout = self.buildout

        Databases(buildout, 'zeo',
                  {'storages': 'Users Users_1 Sessions',
                   'pack-gc': 'true'})

        expected = """\
<zodb Users_1>
  cache-size 100000
  database-name Users_1
  pool-size 60
  <zlibstorage>
      <zeoclient>
        blob-dir /data/Users_1.blobs
        name Users_1
        server /var/zeosocket
        shared-blob-dir true
        storage 2
      </zeoclient>
    compress false
  </zlibstorage>
</zodb>"""
        self.assertEqual(
            buildout['users_1_client']['client_zcml'],
            expected)

        expected = """\
%import zc.zlibstorage
<zeo>
  address /var/zeosocket
</zeo>
<serverzlibstorage 1>
    <filestorage 1>
      blob-dir /data/Users.blobs
      pack-gc true
      path /data/Users.fs
    </filestorage>
  compress false
</serverzlibstorage>
<serverzlibstorage 2>
    <filestorage 2>
      blob-dir /data/Users_1.blobs
      pack-gc true
      path /data/Users_1.fs
    </filestorage>
  compress false
</serverzlibstorage>
<serverzlibstorage 3>
    <filestorage 3>
      blob-dir /data/Sessions.blobs
      pack-gc true
      path /data/Sessions.fs
    </filestorage>
  compress false
</serverzlibstorage>
<eventlog>
    <logfile>
      format %(asctime)s %(message)s
      level DEBUG
      path /var/log/zeo.log
    </logfile>
</eventlog>"""
        self.assertEqual(
            buildout['base_zeo']['zeo.conf'],
            expected
        )

    def test_parse_no_compress(self):
        # No verification, just sees if it runs
        buildout = self.buildout

        Databases(buildout, 'zeo', {
            'storages': 'Users Users_1 Sessions',
            'pack-gc': 'true',
            'compress': 'none',
        })
        expected = """\
<zodb Users_1>
  cache-size 100000
  database-name Users_1
  pool-size 60
  <zeoclient>
    blob-dir /data/Users_1.blobs
    name Users_1
    server /var/zeosocket
    shared-blob-dir true
    storage 2
  </zeoclient>
</zodb>"""

        self.assertEqual(
            buildout['users_1_client']['client_zcml'],
            expected)

        expected = """\
<zeo>
  address /var/zeosocket
</zeo>
<filestorage 1>
  blob-dir /data/Users.blobs
  pack-gc true
  path /data/Users.fs
</filestorage>
<filestorage 2>
  blob-dir /data/Users_1.blobs
  pack-gc true
  path /data/Users_1.fs
</filestorage>
<filestorage 3>
  blob-dir /data/Sessions.blobs
  pack-gc true
  path /data/Sessions.fs
</filestorage>
<eventlog>
    <logfile>
      format %(asctime)s %(message)s
      level DEBUG
      path /var/log/zeo.log
    </logfile>
</eventlog>"""

        self.assertEqual(
            buildout['base_zeo']['zeo.conf'],
            expected
        )

    def test_parse_override_defaults_in_opts(self):
        buildout = self.buildout
        buildout['zeo_opts'] = {
            'pool_size': '2'
        }

        Databases(buildout, 'zeo', {
            'storages': 'Users_1',
            'pack-gc': 'true',
            'compress': 'none',
        })

        expected = """\
<zodb Users_1>
  cache-size 100000
  database-name Users_1
  pool-size 2
  <zeoclient>
    blob-dir /data/Users_1.blobs
    name Users_1
    server /var/zeosocket
    shared-blob-dir true
    storage 1
  </zeoclient>
</zodb>"""

        self.assertEqual(
            buildout['users_1_client']['client_zcml'],
            expected)

    def test_parse_override_defaults_in_recipe(self):
        buildout = self.buildout

        Databases(buildout, 'zeo', {
            'storages': 'Users_1',
            'pack-gc': 'true',
            'compress': 'none',
            'pool_size': '2'
        })

        expected = """\
<zodb Users_1>
  cache-size 100000
  database-name Users_1
  pool-size 2
  <zeoclient>
    blob-dir /data/Users_1.blobs
    name Users_1
    server /var/zeosocket
    shared-blob-dir true
    storage 1
  </zeoclient>
</zodb>"""

        self.assertEqual(
            buildout['users_1_client']['client_zcml'],
            expected)


    def test_parse_pool_timeout_in_recipe(self):
        buildout = self.buildout

        Databases(buildout, 'zeo', {
            'storages': 'Users_1',
            'pack-gc': 'true',
            'compress': 'none',
            'pool_size': '2',
            'pool_timeout': '60',
        })

        expected = """\
<zodb Users_1>
  cache-size 100000
  database-name Users_1
  pool-size 2
  pool-timeout 60
  <zeoclient>
    blob-dir /data/Users_1.blobs
    name Users_1
    server /var/zeosocket
    shared-blob-dir true
    storage 1
  </zeoclient>
</zodb>"""

        self.assertEqual(
            buildout['users_1_client']['client_zcml'],
            expected)
