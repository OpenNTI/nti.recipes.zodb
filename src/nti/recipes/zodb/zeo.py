#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A meta recipe to create configuration for ZEO clients and servers
supporting multiple storages.

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from . import MultiStorageRecipe
from . import deployment
from . import serverzlibstorage
from . import filestorage
from . import ZodbClientPart
from . import zodb

from ._model import hyphenated
from ._model import Part
from ._model import Ref
from ._model import ZConfigSection
from ._model import renamed

logger = __import__('logging').getLogger(__name__)



class BaseStoragePart(Part):
    name = 'BASE'
    number = 0
    data_dir = deployment.data
    blob_dir = Ref('data_dir') / Ref('name') + '.blobs'
    data_file = Ref('data_dir') / Ref('name') + '.fs'
    pack_gc = hyphenated(False)
    server_zcml = None

# client and storage have to be separate to avoid a dep loop

class BaseClientPart(ZodbClientPart):
    client_zcml = None

class zeoclient(ZConfigSection):
    def __init__(self, **kwargs):
        ZConfigSection.__init__(self, 'zeoclient', None, **kwargs)

class zeo(ZConfigSection):
    def __init__(self, address):
        ZConfigSection.__init__(
            self, 'zeo', None,
            address=address
        )

class eventlog(ZConfigSection):
    def __init__(self):
        logfile = ZConfigSection(
            'logfile', None,
            path=Ref('logFile'),
            format="%(asctime)s %(message)s",
            level="DEBUG",
        )
        ZConfigSection.__init__(
            self,
            'eventlog', None, logfile
        )

class BaseZeoPart(Part):
    name = None
    recipe = 'zc.zodbrecipes:server'
    clientPipe = Ref('deployment', 'run-directory') / 'zeosocket'
    logFile = Ref('deployment', 'log-directory') / 'zeo.log'
    zeoConf = renamed('zeo.conf')
    deployment = 'deployment'

class Databases(MultiStorageRecipe):
    import_relstorage = ''

    def __init__(self, buildout, name, options):
        MultiStorageRecipe.__init__(self, buildout, name, options)
        storages = options['storages'].split()
        zeo_name = options.get('name', name)

        # Order matters
        base_storage_part = BaseStoragePart(
            self._derive_related_part_name('base_storage'),
            server_zcml=self.zlibstorage_wrapper(
                filestorage(
                    Ref('number'),
                    path=Ref('data_file'),
                    blob_dir=Ref("blob_dir"),
                    pack_gc=Ref("pack-gc").hyphenate()
                ),
                serverzlibstorage
            )
        )
        self._parse(base_storage_part)

        base_client_part = BaseClientPart(
            self._derive_related_part_name('base_client'),
            extends=(base_storage_part,),
            storage_num=1,
            client_zcml=zodb(
                Ref('name'),
                self.zlibstorage_wrapper(
                    zeoclient(
                        server=BaseZeoPart.clientPipe,
                        shared_blob_dir=hyphenated(True),
                        blob_dir=hyphenated(self.ref('blob_dir')),
                        storage=self.ref('storage_num'),
                        name=self.ref('name'),
                    )
                )
            )
        )
        base_client_part.buildout_lookup = self.make_buildout_lookup([base_storage_part, options])

        self._parse(base_client_part)
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
            storage_part_extends = [
                base_storage_part,
                self.my_options_base_name,
                buildout.get(name + '_opts'),
                buildout.get(storage_part_name + '_opts'),
            ]
            storage_part = Part(
                storage_part_name,
                extends=storage_part_extends,
                name=storage,
                number=i,
                pack_gc=hyphenated(options.get('pack-gc', False))
            )
            self._parse(storage_part)

            client_part_name = storage.lower() + '_client'
            client_part_extends = [
                storage_part,
                base_client_part,
                # We have to put these in the list again so they get
                # the desired (high) precedence.
                self.my_options_base_name,
                buildout.get(name + '_opts'),
                buildout.get(storage_part_name + '_opts'),
                buildout.get(client_part_name + '_opts'),
            ]
            client_part = Part(
                client_part_name,
                extends=client_part_extends,
                name=storage,
                storage_num=i,
            )
            client_parts.append(client_part)

            self.create_directory(storage_part.name, 'blob_dir')
            self.add_database(client_part.name, 'client_zcml')

            server_zcml_names.append(storage_part['server_zcml'].ref())
            zodb_file_uris.append(base_file_uri % {'part': client_part.name})

        base_zeo_part = BaseZeoPart(
            'base_zeo',
            name=zeo_name,
            zeoConf=[
                self.zlibstorage_import(),
                zeo(self.ref('clientPipe')),
            ] + server_zcml_names + [
                eventlog(),
            ],
        )

        self._parse(base_zeo_part)

        for client in client_parts:
            # We'd like for users to be able to override
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
            self._parse(client)

        self.buildout_add_zodb_conf()
        self.buildout_add_zeo_uris()

        self._parse(Part(
            'zodb_direct_file_uris_conf',
            recipe='collective.recipe.template',
            output=deployment.etc / 'zodb_file_uris.ini',
            input=[
                'inline:',
                '[ZODB]',
                'uris = %s' % ' '.join(zodb_file_uris)
            ]
        ))

        self.buildout_add_mkdirs()
