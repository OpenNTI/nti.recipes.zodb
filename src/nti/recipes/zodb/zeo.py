#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A meta recipe to create configuration for ZEO clients and servers
supporting multiple storages.

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from . import MetaRecipe

logger = __import__('logging').getLogger(__name__)


_base_storage = """
[base_storage]
name = BASE
number = 0
data_dir = ${deployment:data-directory}
blob_dir = ${:data_dir}/${:name}.blobs
data_file = ${:data_dir}/${:name}.fs
pack-gc = false
server_zcml =
        <serverzlibstorage ${:number}>
            <filestorage ${:number}>
                path ${:data_file}
                blob-dir ${:blob_dir}
                pack-gc ${:pack-gc}
            </filestorage>
        </serverzlibstorage>

"""
# client and storage have to be separate to avoid a dep loop
_base_client = """
[base_client]
<= base_storage
pool_size = 7
cache-size = 75000
name = BASE
client_zcml =
        <zodb ${:name}>
            pool-size ${:pool_size}
            database-name ${:name}
            cache-size ${:cache-size}
            <zlibstorage>
                <zeoclient>
                    server ${base_zeo:clientPipe}
                    shared-blob-dir True
                    blob-dir ${:blob_dir}
                    storage 1
                    name ${:name}
                </zeoclient>
            </zlibstorage>
        </zodb>
"""

_zeo = """
[base_zeo]
name = %s
recipe = zc.zodbrecipes:server
clientPipe = ${buildout:directory}/var/zeosocket
logFile = ${buildout:directory}/var/log/zeo.log
zeo.conf =
        %%import zc.zlibstorage
        <zeo>
            address ${:clientPipe}
        </zeo>

        %s

        <eventlog>
            <logfile>
                path ${:logFile}
                format %%(asctime)s %%(message)s
                level DEBUG
            </logfile>
        </eventlog>
deployment = deployment
"""

class Databases(MetaRecipe):

    def __init__(self, buildout, name, options):
        storages = options['storages'].split()
        zeo_name = options.get('name', 'Dataserver')

        # Order matters
        buildout.parse(_base_storage)


        blob_paths = []
        zeo_uris = []
        client_zcml_names = []
        server_zcml_names = []
        zodb_file_uris = []
        client_parts = []

        base_file_uri = ("zlibfile://${%(part)s:data_file}"
                         "?database_name=${%(part)s:name}"
                         "&blobstorage_dir=${%(part)s:blob_dir}")

        # To add a new database, define
        # a storage and client section and fill in the details.
        # Ref the storage section from the paths in zeo_dirs
        # and the appropriate ZCML in the zeo and zodb_conf sections

        for i, storage in enumerate(storages):
            # storages begin at 1
            i = i + 1
            storage_part_name = storage.lower() + '_storage'
            buildout.parse("""
            [%s]
            <= base_storage
            name = %s
            number = %d
            pack-gc = %s
            """ % (storage_part_name, storage, i, options.get('pack-gc', 'false')))

            client_part_name = storage.lower() + '_client'
            client_parts.append(("""
            [%s]
            <= %s
               base_client
            name = %s
            """ % (client_part_name, storage_part_name, storage),
                                 client_part_name))


            blob_paths.append("${%s:blob_dir}" % storage_part_name)
            client_zcml_names.append("${%s:client_zcml}" % client_part_name)
            server_zcml_names.append("${%s:server_zcml}" % storage_part_name)

            zeo_uris.append("zconfig://${zodb_conf:output}#%s" % storage.lower())

            zodb_file_uris.append(base_file_uri % {'part': client_part_name})

        # Indents must match or we get parsing errors, hence
        # the tabs
        buildout.parse(_zeo % (zeo_name, '\n        '.join(server_zcml_names)))
        buildout.parse(_base_client)
        for client, _part_name in client_parts:
            # We'd like for users to be able to overdide
            # our settings in their default.cfg, like they can
            # with normal sections. This is a problem for a few reasons.
            # First, buildout won't .parse() input if the section already
            # exists, which it will if it was in the defaults.
            # We can delete it, but then we hit the second problem:
            # the values are interpolated already by buildout when it is parsed,
            # so changing them later doesn't change the ZCML string.
            # If we want this to work, we have to do something more sophisticated
            # (an easy thing would be to allow them to be set on this part,
            # and force them to all be the same for all storages)
            # For now, make it cause the parse error if attempted so
            # people don't expect it to work.

            buildout.parse(client)

        buildout.parse("""
        [zodb_conf]
        recipe = collective.recipe.template
        output = ${deployment:etc-directory}/zodb_conf.xml
        input = inline:
                %%import zc.zlibstorage
                %%import relstorage

                %s
        """ % '\n                '.join(client_zcml_names))

        buildout.parse("""
        [zodb_uri_conf]
        recipe = collective.recipe.template
        output = ${deployment:etc-directory}/zeo_uris.ini
        input = inline:
              [ZODB]
              uris = %s
        """ % ' '.join(zeo_uris))

        buildout.parse("""
        [zodb_direct_file_uris_conf]
        recipe = collective.recipe.template
        output = ${deployment:etc-directory}/zodb_file_uris.ini
        input = inline:
              [ZODB]
              uris = %s
        """ % ' '.join(zodb_file_uris))

        buildout.parse("""
        [zeo_dirs]
        recipe = z3c.recipe.mkdir
        paths =
            %s
        mode = 0700
        """ % '\n            '.join(blob_paths))
