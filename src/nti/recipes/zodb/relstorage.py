#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A meta-recipe to create multiple
relstorage connections in a Dataserver buildout.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

import textwrap


logger = __import__('logging').getLogger(__name__)

class Databases(object):

    def __init__(self, buildout, name, options):
        # Get the 'environment' block from buildout if it exists. This is for
        # combatibility with existing buildouts.
        environment = buildout.get('environment', {})
        relstorage_name_prefix = options.get('relstorage-name-prefix', '')

        # The initial use case has the same SQL
        # database, SQL user, cache servers,
        # etc, for all connections. The recipe
        # can easily be extended to allow separate values
        # in the future
        sql_user = options.get('sql_user') or environment.get('sql_user')
        sql_passwd = options.get('sql_passwd') or environment.get('sql_passwd')
        sql_host = options.get('sql_host') or environment.get('sql_host')

        # by default, relstorage assumes a shared blob
        # directory. However, our most common use case here
        # is not to share. While using either wrong setting
        # in an environment is dangerous and can lead to data loss,
        # it's slightly worse to assume shared when its not
        if 'shared-blob-dir' not in options:
            options['shared-blob-dir'] = b'false' # options must be strings
        shared_blob_dir = options['shared-blob-dir']

        cache_local_dir = ''
        if options.get('enable-persistent-cache', '').lower() == 'true':
            # Do not store this 'cache-local-dir' in the relstorage options.
            # We'll intermittently have buildout issues when writing this
            # to the installed.cfg while looking up the storage refs. We
            # avoid taking any user-defined values since it might be
            # confusing to have one (count limited) directory for all storages.
            cache_local_dir = b'${deployment:cache-directory}/data_cache/${:name}.cache'
        cache_local_mb = options.get('cache-local-mb', '300')
        cache_local_dir_count = options.get('cache-local-dir-count', '20')
        blob_cache_size = options.get('blob-cache-size', '')
        pack_gc = options.get('pack-gc', 'false')

        # Poll interval is extremely critical. If the memcache instance
        # is unreliable or subject to going away, it seems that the poll
        # interval still applies; this means that a storage could be
        # up to that far out of date without knowing it.  In environments
        # with a fairly high write rate, this is a crucial mistake
        # (we still have some fairly high write rates in our chat code)
        # which leads to conflict errors. Fortunately, DB load seems not
        # to be an issue, so we can poll to our heart's content and
        # set this to 0...although this may eat up mysql connections?
        # UPDATE: 7.1.2016 Remove poll-interval to use default specified
        # by relstorage (see https://github.com/zodb/relstorage/issues/87).

        # Utilizing the built in memcache capabilites is not beneficial in all
        # cases. If the recipe option 'cache_servers' is empty or not defined,
        # the relstorage config options 'cache_module_name' and
        # 'cache_module_name' will be omitted from the generated config.
        cache_servers = options.get('cache_servers') or environment.get('cache_servers', '')
        cache_config = '\n        '.join(textwrap.dedent("""
            cache_module_name = memcache
            cache_servers = %s
            """ % (cache_servers.strip(),)).splitlines())
        remote_cache_config = '\n                            '.join(textwrap.dedent("""
            cache-servers ${:cache_servers}
            cache-module-name ${:cache_module_name}
            """).splitlines())

        if not cache_servers.strip():
            cache_config = ''
            remote_cache_config = ''

        # Also crucial is the pool-size. Each connection has resources
        # like a memcache connection, a MySQL connection, and its
        # in-memory cache. Normally, opening a DB and closing the
        # connection will create a connection (if needed), then return
        # it to the pool. However, in the case of multi-databases,
        # when an object from a secondary database needs to be loaded,
        # the active connection will request a connection to that
        # database, and when the active connection is closed, that
        # secondary connection is also closed: BUT NOT RETURNED TO THE
        # POOL. Instead, the active (primary) connection keeps a
        # reference to it that it will use in the future. This has the
        # effect of driving all secondary pools based on the
        # efficiency of the primary pool. Thus, the pool-size for
        # everything except the primary database is essentially
        # meaningless (if the application always begins by opening
        # that primary database), but that pool size controls everything.

        # If we're doing XHR-polling, it's not unusual for one gunicorn/gevent
        # worker to have 30 or 40 polling requests active on it an any
        # one time. Each of those consumes a connection; if our pool size
        # is smaller than the number of active requests, we can wind
        # up thrashing on connections, rapidly opening and closing them.
        # (Because closing the main connection causes it to be repushed on the pool,
        # which triggers the pool to shrink in size if need be). Calling
        # DB.connectionDebugInfo() can show this: connections in the pool
        # have 'opened' of None, while those in use have a timestamp and the length
        # of time it's been open.

        # Connections have a pointer to a new RelStorage object, and when a connection
        # is closed, this new storage is never actually closed or cleaned up, because
        # the connection might be reused. Instead, connections rely on
        # reference counting/GC to clean up the relstorage object and its resources
        # (The DB will clean up active connections in the pool, but only when it itself
        # is closed). This could be a problem in cases of cycles.

        # Order matters
        base_storage_name = name + '_base_storage'
        buildout.parse("""
        [%s]
        name = BASE
        data_dir = ${deployment:data-directory}
        blob_dir = ${:data_dir}/${:name}.blobs
        dump_name = ${:name}
        dump_dir = ${:data_dir}/relstorage_dump/${:dump_name}
        blob_dump_dir = ${:data_dir}/relstorage_dump/${:dump_name}/blobs
        filestorage_name = NONE
        shared-blob-dir = %s
        relstorage-name-prefix = %s
        %s
        commit_lock_timeout = 60
        cache-size = 100000
        cache-local-dir = %s
        cache-local-mb = %s
        cache-local-dir-count = %s
        blob-cache-size = %s
        pack-gc = %s
        sql_db = ${:name}
        sql_user = %s
        sql_passwd = %s
        sql_host = %s
        sql_adapter = mysql
        sql_adapter_args =
                 db ${:sql_db}
                 user ${:sql_user}
                 passwd ${:sql_passwd}
                 host ${:sql_host}
                 ${:sql_adapter_extra_args}
        sql_adapter_extra_args =
        storage_zcml =
                    <zlibstorage ${:name}>
                        <relstorage ${:name}>
                            blob-dir ${:blob_dir}
                            shared-blob-dir ${:shared-blob-dir}
                            cache-prefix ${:name}
                            %s
                            commit-lock-timeout ${:commit_lock_timeout}
                            cache-local-mb ${:cache-local-mb}
                            cache-local-dir ${:cache-local-dir}
                            cache-local-dir-count ${:cache-local-dir-count}
                            blob-cache-size ${:blob-cache-size}
                            name ${:relstorage-name-prefix}${:name}
                            keep-history false
                            pack-gc ${:pack-gc}
                            <${:sql_adapter}>
                                ${:sql_adapter_args}
                            </${:sql_adapter}>
                        </relstorage>
                    </zlibstorage>
        client_zcml =
                <zodb ${:name}>
                    pool-size 60
                    database-name ${:name}
                    cache-size ${:cache-size}
                    ${:storage_zcml}
                </zodb>
        filestorage_zcml =
                <zlibstorage ${:filestorage_name}>
                    <filestorage ${:filestorage_name}>
                        path ${:dump_dir}/data.fs
                        blob-dir ${:blob_dump_dir}
                    </filestorage>
                </zlibstorage>
        """ % (base_storage_name, shared_blob_dir, relstorage_name_prefix, cache_config,
               cache_local_dir, cache_local_mb, cache_local_dir_count,
               blob_cache_size, pack_gc, sql_user, sql_passwd, sql_host, remote_cache_config))
        storages = options['storages'].split()
        blob_paths = []
        zeo_uris = []
        zcml_names = []
        for storage in storages:
            part_name = name + '_' + storage.lower() + '_storage'
            # Note that while it would be nice to automatically extend
            # from this section, that leads to a recursive invocation
            # of this recipe, which obviously fails (with weird errors
            # about "part already exists"). So we use _opts for everything,
            # in precedence order
            other_bases = [base_storage_name]
            if name + '_opts' in buildout:
                other_bases.append(name + '_opts')
            if part_name + '_opts' in buildout:
                other_bases.append(part_name + '_opts')
            other_bases = '\n                '.join(other_bases)
            part_template = """
            [%s]
            <=
                %s
            name = %s
            """
            part = part_template % (part_name, other_bases, storage)
            buildout.parse(part)

            blob_paths.append("${%s:blob_dir}" % part_name)
            blob_paths.append("${%s:cache-local-dir}" % part_name)

            zcml_names.append("${%s:client_zcml}" % part_name)
            zeo_uris.append("zconfig://${zodb_conf:output}#%s" % storage.lower())

            # ZODB convert to and from files
            src_part_name = 'zodbconvert_' + part_name + '_src'
            dest_part_name = 'zodbconvert_' + part_name + '_destination'
            blob_paths.append("${%s:dump_dir}" % src_part_name)
            blob_paths.append("${%s:blob_dump_dir}" % dest_part_name)

            to_relstorage_part_name = storage.lower() + '_to_relstorage_conf'
            from_relstorage_part_name = storage.lower() + '_from_relstorage_conf'

            zodb_convert_part_template = """
            [%s]
            <=
                %s
            name = %s
            filestorage_name = %s
            dump_name = %s
            sql_db = %s
            """
            src_part = zodb_convert_part_template % (src_part_name,
                                                     other_bases,
                                                     'source', 'destination',
                                                     storage.lower(),
                                                     storage)
            buildout.parse(src_part)

            dest_part = zodb_convert_part_template % (dest_part_name,
                                                      other_bases,
                                                      'destination', 'source',
                                                      storage.lower(),
                                                      storage)
            buildout.parse(dest_part)
            convert_template = """
            [%s]
            recipe = collective.recipe.template
            output = ${deployment:etc-directory}/relstorage/%s.xml
            input = inline:
                %%import zc.zlibstorage
                %%import relstorage

                ${%s:storage_zcml}
                ${%s:filestorage_zcml}
            """
            buildout.parse(convert_template % (to_relstorage_part_name,
                                               to_relstorage_part_name,
                                               dest_part_name,
                                               dest_part_name))
            buildout.parse(convert_template % (from_relstorage_part_name,
                                               from_relstorage_part_name,
                                               src_part_name,
                                               src_part_name))
        buildout.parse("""
        [blob_dirs]
        recipe = z3c.recipe.mkdir
        mode = 0700
        paths =
            %s
        """ % '\n            '.join(blob_paths))

        buildout.parse("""
        [zodb_conf]
        recipe = collective.recipe.template
        output = ${deployment:etc-directory}/zodb_conf.xml
        input = inline:
                %%import zc.zlibstorage
                %%import relstorage

                %s
        """ % '\n                '.join(zcml_names))
        # Indents must match or we get parsing errors, hence
        # the tabs

        buildout.parse("""
        [zodb_uri_conf]
        recipe = collective.recipe.template
        output = ${deployment:etc-directory}/zeo_uris.ini
        input = inline:
              [ZODB]
              uris = %s
        """ % ' '.join(zeo_uris))

    def install(self):
        return ()

    def update(self):
        pass
