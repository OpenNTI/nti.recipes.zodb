#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
__docformat__ = "restructuredtext en"

import unittest

from nti.recipes.zodb.zeo import Databases
from . import NoDefaultBuildout

class TestDatabases(unittest.TestCase):
    maxDiff = None
    def test_parse(self):
        # No verification, just sees if it runs
        buildout = NoDefaultBuildout()
        buildout['deployment'] = {
            'etc-directory': '/etc',
            'data-directory': '/data',
            'run-directory': '/var',
            'log-directory': '/var/log',
        }

        Databases(buildout, 'zeo',
                  {'storages': 'Users Users_1 Sessions',
                   'pack-gc': 'true'})

        expected = """\
<zodb users_1_client>
  cache-size 100000
  database-name users_1_client
  pool-size 60
  <zlibstorage>
      <zeoclient>
        blob-dir /data/users_1_client.blobs
        name users_1_client
        server /var/zeosocket
        shared-blob-dir true
        storage 1
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
        buildout = NoDefaultBuildout()
        buildout['deployment'] = {
            'etc-directory': '/etc',
            'data-directory': '/data',
            'run-directory': '/var',
            'log-directory': '/var/log',
        }

        Databases(buildout, 'zeo', {
            'storages': 'Users Users_1 Sessions',
            'pack-gc': 'true',
            'compress': 'none',
        })
        expected = """\
<zodb users_1_client>
  cache-size 100000
  database-name users_1_client
  pool-size 60
  <zeoclient>
    blob-dir /data/users_1_client.blobs
    name users_1_client
    server /var/zeosocket
    shared-blob-dir true
    storage 1
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
