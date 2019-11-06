#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A meta-recipe to create multiple
relstorage connections in a Dataserver buildout.

"""

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from ._model import Part
from ._model import ZConfigSection
from ._model import ZConfigSnippet
from ._model import Ref
from ._model import hyphenated

from . import MultiStorageRecipe
from . import filestorage
from . import zlibstorage
from . import zodb
from . import ZodbClientPart

logger = __import__('logging').getLogger(__name__)

def _option_true(value):
    return value and value.lower() in ('1', 'yes', 'on', 'true')

class relstorage(ZConfigSection):
    blob_cache_size = Ref('blob-cache-size').hyphenate()
    blob_dir = Ref("blob_dir").hyphenate()
    cache_local_dir = Ref('cache-local-dir').hyphenate()
    cache_local_mb = Ref('cache-local-mb').hyphenate()
    cache_prefix = Ref('name').hyphenate()
    commit_lock_timeout = Ref('commit_lock_timeout').hyphenate()
    keep_history = hyphenated(False)
    name = Ref('relstorage-name-prefix') + Ref('name')
    pack_gc = Ref('pack-gc').hyphenate()
    shared_blob_dir = Ref('shared-blob-dir').hyphenate()

    def __init__(self, memcache_config):
        ZConfigSection.__init__(
            self, 'relstorage', Ref('name'),
            ZConfigSection(
                Ref('sql_adapter'), None,
                APPEND=Ref('sql_adapter_args')
            ),
            APPEND=memcache_config,
        )

class BaseStoragePart(ZodbClientPart):
    blob_cache_size = hyphenated(None)
    blob_dir = Ref('data_dir') / Ref('name') + '.blobs'
    blob_dump_dir = Ref('data_dir') / 'relstorage_dump' / Ref('dump_name') / 'blobs'
    cache_local_dir = hyphenated(None)
    cache_local_mb = hyphenated(None)

    commit_lock_timeout = 60
    data_dir = Ref('deployment', 'data-directory')
    dump_dir = Ref('data_dir') / 'relstorage_dump' / Ref('dump_name')
    dump_name = Ref('name')
    filestorage_name = 'NONE'
    name = 'BASE'
    pack_gc = hyphenated(False)
    relstorage_name_prefix = hyphenated(None)
    shared_blob_dir = hyphenated(False)

    sql_db = Ref('name')
    sql_adapter_args = ZConfigSnippet(
        db=Ref('sql_db'),
        user=Ref('sql_user'),
        passwd=Ref('sql_passwd'),
        host=Ref('sql_host'),
        APPEND=Ref('sql_adapter_extra_args')
    )
    sql_adapter_extra_args = None

class Databases(MultiStorageRecipe):

    def __init__(self, buildout, name, options):
        MultiStorageRecipe.__init__(self, buildout, name, options)
        # Get the 'environment' block from buildout if it exists. This is for
        # combatibility with existing buildouts.
        environment = buildout.get('environment', {})
        relstorage_name_prefix = options.get('relstorage-name-prefix', '')

        # The initial use case has the same SQL database, SQL user,
        # cache servers, etc, for all connections. Using _opts sections
        # either for the this element or for an individual storage in this element
        # can override it.
        sql_user = options.get('sql_user') or environment.get('sql_user')
        sql_passwd = options.get('sql_passwd') or environment.get('sql_passwd')
        sql_host = options.get('sql_host') or environment.get('sql_host')
        sql_adapter = options.get('sql_adapter') or 'mysql'

        # by default, relstorage assumes a shared blob
        # directory. However, our most common use case here
        # is not to share. While using either wrong setting
        # in an environment is dangerous and can lead to data loss,
        # it's slightly worse to assume shared when its not
        if 'shared-blob-dir' not in options:
            options['shared-blob-dir'] = 'false'
        shared_blob_dir = options['shared-blob-dir']

        cache_local_dir = ''
        if _option_true(options.get('enable-persistent-cache', 'true')):
            # Do not store this 'cache-local-dir' in the relstorage options.
            # We'll intermittently have buildout issues when writing this
            # to the installed.cfg while looking up the storage refs. We
            # avoid taking any user-defined values since it might be
            # confusing to have one (count limited) directory for all storages.
            cache_local_dir = '${deployment:cache-directory}/data_cache/${:name}.cache'
        cache_local_mb = options.get('cache-local-mb', '300')

        blob_cache_size = options.get('blob-cache-size', '')
        pack_gc = options.get('pack-gc', 'false')

        # Utilizing the built in memcache capabilites is not
        # beneficial in all cases. In fact it rarely is. It's
        # semi-deprecated in RelStorage 3. If the recipe option
        # 'cache_servers' is empty or not defined, the relstorage
        # config options 'cache_module_name' and 'cache_module_name'
        # will be omitted from the generated config.
        cache_servers = options.get('cache_servers') or environment.get('cache_servers', '')
        if cache_servers.strip():
            extra_base_kwargs = {
                'cache_module_name': 'memcache',
                'cache_servers': cache_servers.strip()
            }
            remote_cache_config = ZConfigSnippet(**{
                k.replace('_', '-'): v
                for k, v
                in extra_base_kwargs.items()
            })
        else:
            extra_base_kwargs = {}
            remote_cache_config = ZConfigSnippet()

        # Connections have a pointer to a new RelStorage object, and when a connection
        # is closed, this new storage is never actually closed or cleaned up, because
        # the connection might be reused. Instead, connections rely on
        # reference counting/GC to clean up the relstorage object and its resources
        # (The DB will clean up active connections in the pool, but only when it itself
        # is closed). This could be a problem in cases of cycles.

        # Order matters
        base_storage_name = name + '_base_storage'

        base_storage_part = BaseStoragePart(
            base_storage_name,
            sql_user=sql_user,
            sql_passwd=sql_passwd,
            sql_host=sql_host,
            sql_adapter=sql_adapter,
            storage_zcml=zlibstorage(
                self.ref('name'),
                relstorage(remote_cache_config)
            ),
            client_zcml=zodb(self.ref('name'), self.ref('storage_zcml')),
            filestorage_zcml=zlibstorage(
                self.ref('filestorage_name'),
                filestorage(self.ref('filestorage_name'))
            ),
            shared_blob_dir=shared_blob_dir,
            relstorage_name_prefix=relstorage_name_prefix,
            cache_local_dir=cache_local_dir,
            cache_local_mb=cache_local_mb,
            blob_cache_size=blob_cache_size,
            pack_gc=pack_gc,
            **extra_base_kwargs
        )
        if not blob_cache_size:
            del base_storage_part['blob-cache-size']
            del base_storage_part['storage_zcml'].storage['blob-cache-size']


        __traceback_info__ = base_storage_part
        self._parse(base_storage_part)
        storages = options['storages'].split()

        for storage in storages:
            part_name = name + '_' + storage.lower() + '_storage'
            # Note that while it would be nice to automatically extend
            # from this section, that leads to a recursive invocation
            # of this recipe, which obviously fails (with weird errors
            # about "part already exists"). So we use _opts for everything,
            # in precedence order
            other_bases_list = [base_storage_name]
            if name + '_opts' in buildout:
                other_bases_list.append(name + '_opts')
            if part_name + '_opts' in buildout:
                other_bases_list.append(part_name + '_opts')
            part = Part(
                part_name,
                extends=other_bases_list,
                name=storage,
            )

            part = part.with_settings(**self.__adapter_settings(part))
            self._parse(part)

            self.create_directory(part_name, 'blob_dir')
            self.create_directory(part_name, 'cache-local-dir')
            self.add_database(part_name, 'client_zcml')

            if _option_true(options.get('write-zodbconvert', 'false')):
                self.__create_zodbconvert_parts(part)

        self.buildout_add_mkdirs(name='blob_dirs')
        self.buildout_add_zodb_conf()
        self.buildout_add_zeo_uris()

    def __get_in_order(self, option_name, options_order):
        for options in options_order:
            if option_name in options:
                return options[option_name]
        return None # pragma: no cover

    def __adapter_settings(self, part):
        if self.__get_in_order('sql_adapter',
                               [self.my_options] + [self.buildout[p]
                                                    for p in part.extends]) == 'sqlite3':
            # sqlite resides on a single machine. No need to duplicate
            # blobs both in the DB and in the blob cache. This reduces parallel
            # commit, but it's not really parallel anyway.
            # Note that we DO NOT add the data-dir to the list of directories to create.
            # Uninstalling this part should not remove that directory, which is
            # what would happen if we added it.
            settings = {
                'shared-blob-dir': True,
                'sql_adapter_args': ZConfigSnippet(**{
                    'data-dir': part.uses_my_name(self.ref('data_dir') / '%s'),
                    'APPEND': self.ref('sql_adapter_extra_args'),
                })
            }
        else:
            settings = {}
        return settings

    def __create_zodbconvert_parts(self, part):
        # ZODB convert to and from files

        normalized_storage_name = part['name'].lower()

        src_part_name = 'zodbconvert_' + part.name + '_src'
        dest_part_name = 'zodbconvert_' + part.name + '_destination'
        self.create_directory(src_part_name, 'dump_dir')
        self.create_directory(dest_part_name, 'blob_dump_dir')

        to_relstorage_part_name = normalized_storage_name + '_to_relstorage_conf'
        from_relstorage_part_name = normalized_storage_name + '_from_relstorage_conf'

        src_part = Part(
            src_part_name,
            extends=part.extends,
            name='source',
            filestorage_name='destination',
            dump_name=normalized_storage_name,
            sql_db=part['name'],
        )
        src_part = src_part.with_settings(**self.__adapter_settings(part))
        self._parse(src_part)

        dest_part = src_part.named(dest_part_name).with_settings(
            name='destination',
            filestorage_name='source',
        )
        self._parse(dest_part)

        choices = {
            to_relstorage_part_name: dest_part_name,
            from_relstorage_part_name: src_part_name
        }
        to_relstorage_part = Part(
            to_relstorage_part_name,
            recipe='collective.recipe.template',
            output=Part.uses_name('${deployment:etc-directory}/relstorage/%s.xml'),
            input=[
                'inline:',
                '%import zc.zlibstorage',
                '%import relstorage',
                self.choice_ref(choices, 'storage_zcml'),
                self.choice_ref(choices, 'filestorage_zcml'),
            ],
        )
        self._parse(to_relstorage_part)

        from_relstorage_part = to_relstorage_part.named(from_relstorage_part_name)
        self._parse(from_relstorage_part)
