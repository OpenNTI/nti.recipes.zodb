#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A meta-recipe to create multiple
relstorage connections in a Dataserver buildout.

"""

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import io

import ZConfig.schemaless

from ._model import Part
from ._model import ZConfigSection
from ._model import ZConfigSnippet
from ._model import Ref as SubstVar
from ._model import RelativeRef as LocalSubstVar
from ._model import hyphenated
from ._model import Default

from . import MultiStorageRecipe
from . import filestorage
from . import zodb
from . import ZodbClientPart

logger = __import__('logging').getLogger(__name__)
NativeStringIO = io.BytesIO if bytes is str else io.StringIO

def _option_true(value):
    return value and value.lower() in ('1', 'yes', 'on', 'true')

class relstorage(ZConfigSection):
    blob_cache_size = LocalSubstVar('blob-cache-size').hyphenate()
    blob_dir = LocalSubstVar("blob_dir").hyphenate()
    cache_local_dir = LocalSubstVar('cache-local-dir').hyphenate()
    cache_local_mb = LocalSubstVar('cache-local-mb').hyphenate()
    cache_prefix = LocalSubstVar('name').hyphenate()
    commit_lock_timeout = LocalSubstVar('commit_lock_timeout').hyphenate()
    keep_history = hyphenated(False)
    name = LocalSubstVar('relstorage-name-prefix') + LocalSubstVar('name')
    pack_gc = LocalSubstVar('pack-gc').hyphenate()
    shared_blob_dir = LocalSubstVar('shared-blob-dir').hyphenate()

    def __init__(self, memcache_config):
        ZConfigSection.__init__(
            self, 'relstorage', LocalSubstVar('name'),
            # One section, <$adapter>
            ZConfigSection(
                LocalSubstVar('sql_adapter'), None,
                APPEND=LocalSubstVar('sql_adapter_args')
            ),
            APPEND=memcache_config,
        )

class BaseStoragePart(ZodbClientPart):
    blob_cache_size = Default(None).hyphenate()
    blob_dir = LocalSubstVar('data_dir') / LocalSubstVar('name') + '.blobs'
    blob_dump_dir = (
        LocalSubstVar('data_dir')
        / 'relstorage_dump'
        / LocalSubstVar('dump_name')
        / 'blobs'
    )
    cache_local_dir = hyphenated(None)
    cache_local_mb = Default(300).hyphenate()

    commit_lock_timeout = Default(60)
    data_dir = SubstVar('deployment', 'data-directory')
    dump_dir = LocalSubstVar('data_dir') / 'relstorage_dump' / LocalSubstVar('dump_name')
    dump_name = LocalSubstVar('name')
    filestorage_name = 'NONE'
    name = 'BASE'
    pack_gc = Default(False).hyphenate()
    relstorage_name_prefix = hyphenated(None)
    # Prior to RelStorage 3, by default, relstorage assumes a shared blob
    # directory. However, our most common use case here
    # is not to share. While using either wrong setting
    # in an environment is dangerous and can lead to data loss,
    # it's slightly worse to assume shared when its not
    shared_blob_dir = Default(False).hyphenate()

    sql_db = LocalSubstVar('name')
    sql_adapter_args = ZConfigSnippet(
        db=LocalSubstVar('sql_db'),
        user=LocalSubstVar('sql_user'),
        passwd=LocalSubstVar('sql_passwd'),
        host=LocalSubstVar('sql_host'),
        APPEND=LocalSubstVar('sql_adapter_extra_args')
    )
    sql_adapter_extra_args = None


def _ZConfig_write_to(config, writer, part):
    writer.begin_line("# This comment preserves whitespace")
    indent = writer.current_indent * 2 + '  '
    for line in config.__str__(indent).splitlines():
        writer.begin_line(line)

ZConfig.schemaless.Section.write_to = _ZConfig_write_to

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


        cache_local_dir = ''
        if _option_true(options.get('enable-persistent-cache', 'true')):
            # Do not store this 'cache-local-dir' in the relstorage options.
            # We'll intermittently have buildout issues when writing this
            # to the installed.cfg while looking up the storage refs. We
            # avoid taking any user-defined values since it might be
            # confusing to have one (count limited) directory for all storages.
            cache_local_dir = '${deployment:cache-directory}/data_cache/${:name}.cache'

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

        relstorage_zcml = self.zlibstorage_wrapper(relstorage(remote_cache_config))
        filestorage_zcml = self.zlibstorage_wrapper(filestorage(self.ref('filestorage_name')))
        blob_cache_size = options.get('blob-cache-size', '')
        # Order matters
        base_storage_name = name + '_base_storage'

        base_storage_part = BaseStoragePart(
            base_storage_name,
            sql_user=sql_user,
            sql_passwd=sql_passwd,
            sql_host=sql_host,
            sql_adapter=sql_adapter,
            storage_zcml=relstorage_zcml,
            client_zcml=zodb(self.ref('name'), self.ref('storage_zcml')),
            filestorage_zcml=filestorage_zcml,
            relstorage_name_prefix=relstorage_name_prefix,
            cache_local_dir=cache_local_dir,
            blob_cache_size=blob_cache_size,
            **extra_base_kwargs
        )

        # TODO: Let this be configured for each storage.
        if not blob_cache_size:
            del base_storage_part['blob-cache-size']
            zcml = base_storage_part['storage_zcml']
            if hasattr(zcml, 'storage'):
                zcml = zcml.storage # unwrap zlibstorage
            del zcml['blob-cache-size']

        # TODO: This is for pool_timeout; it supports
        # configuring in _opts_base and _opts, but not per-storage.
        # Well, technically that's not true: per-storage is supported, but
        # there must be a a value in opts_base or _opts first.
        # We only document the shared values though.
        base_storage_part.buildout_lookup = self.make_buildout_lookup((
            name + '_opts_base',
            name + '_opts',
            extra_base_kwargs,
        ))

        self._parse(base_storage_part)
        storages = options['storages'].split()

        for storage in storages:
            part_name = name + '_' + storage.lower() + '_storage'
            # Note that while it would be nice to automatically extend
            # from this section, that leads to a recursive invocation
            # of this recipe, which obviously fails (with weird errors
            # about "part already exists"). So we use _opts for everything,
            # in precedence order
            other_bases_list = [
                base_storage_part,
                buildout.get(name + '_opts_base'),
                buildout.get(name + '_opts'),
                buildout.get(part_name + '_opts')
            ]
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

    def _resolve(self, part, obj):
        if isinstance(obj, SubstVar):
            if not obj.part: # Relative.
                return self._resolve(part, part.get(obj.setting))
            # buildout values are already fully resolved
            return self.buildout[obj.part][obj.setting] # pragma: no cover
        return obj


    def __clear_top_level_inherited_adapter_settings(self, sql_adapter_args):
        for k in BaseStoragePart.sql_adapter_args.keys():
            sql_adapter_args.pop(k, None)

    def _adapter_settings_for_sqlite3(self, part, sql_adapter_args):
        # sqlite resides on a single machine. No need to duplicate
        # blobs both in the DB and in the blob cache. This reduces parallel
        # commit, but it's not really parallel anyway.
        # Note that we DO NOT add the data-dir to the list of directories to create.
        # Uninstalling this part should not remove that directory, which is
        # what would happen if we added it.

        # Top-level settings which we got by default have to go; there are none.
        self.__clear_top_level_inherited_adapter_settings(sql_adapter_args)
        sql_adapter_args.addValue('data-dir', str(part['data_dir']) + '/' + part.name)
        return {
            'shared-blob-dir': True
        }

    def _adapter_settings_for_postgresql(self, part, sql_adapter_args):
        # If no DSN is specified in the sql_adapter_args then we compute one.
        if 'dsn' in sql_adapter_args:
            return {}
        # Hoist everything present by default into the dsn. Resolve them now so that we don't
        # put in empty fields and can use defaults.
        def resolve(obj):
            return self._resolve(part, obj)
        dsn = ' '
        for dsn_key, setting_key in (
                ('dbname', 'db'),
                ('user', 'user',),
                ('password', 'passwd'),
                ('host', 'host')
        ):
            setting = sql_adapter_args.pop(setting_key)[0]
            setting = resolve(setting)
            if setting:
                dsn += "%s='%s' " % (dsn_key, setting)
        dsn = dsn.strip()

        self.__clear_top_level_inherited_adapter_settings(sql_adapter_args)

        if 'sql_port' in sql_adapter_args:
            # Note no quotes
            dsn += ' port=%s' % (resolve(sql_adapter_args['sql_port'][0]))
            sql_adapter_args.pop('sql_port')

        sql_adapter_args.addValue('dsn', dsn)
        # No special settings to return, everything is in the mutated sql_adapter_args
        return {}

    def _adapter_settings_for_mysql(self, part, sql_adapter_args):
        # Our default is set up for MySQL
        return {}

    def __adapter_settings(self, part):
        # sql adapter args could be dict-like if its our default template,
        # or it could be a string if it's specified by the user to replace our default
        # template.
        sql_adapter_args = part['sql_adapter_args']
        if isinstance(sql_adapter_args, str):
            sql_adapter_args = ZConfig.schemaless.loadConfigFile(NativeStringIO(sql_adapter_args))
        else:
            sql_adapter_args = ZConfig.schemaless.Section(data={
                k: [v] for k, v in sql_adapter_args.items()
            })

        # Inline the sql_adapter_extra_args here so we can verify them as valid
        # and so the db-specific functions get an entire view
        extra_args = part['sql_adapter_extra_args']
        if hasattr(extra_args, 'const'):
            extra_args = extra_args.const
        if extra_args:
            config = ZConfig.schemaless.loadConfigFile(NativeStringIO(str(extra_args)))
            for k, v in config.items():
                sql_adapter_args[k] = v
            sql_adapter_args.sections.extend(config.sections)

        adapter_name = str(part.get('sql_adapter'))
        settings = getattr(self, '_adapter_settings_for_' + adapter_name)(part, sql_adapter_args)

        settings['sql_adapter_args'] = sql_adapter_args
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
                self.zlibstorage_import(),
                '%import relstorage',
                self.choice_ref(choices, 'storage_zcml'),
                self.choice_ref(choices, 'filestorage_zcml'),
            ],
        )
        self._parse(to_relstorage_part)

        from_relstorage_part = to_relstorage_part.named(from_relstorage_part_name)
        self._parse(from_relstorage_part)
