==================
 nti.recipes.zodb
==================

Opinionated recipes for creating RelStorage and ZEO configurations, especially
tailored for multi-databases.

.. image:: https://travis-ci.org/NextThought/nti.recipes.zodb.svg?branch=master
    :target: https://travis-ci.org/NextThought/nti.recipes.zodb

.. image:: https://coveralls.io/repos/github/NextThought/nti.recipes.zodb/badge.svg?branch=master
   :target: https://coveralls.io/github/NextThought/nti.recipes.zodb?branch=master

Limitations
===========

A single buildout can use *either* one RelStorage recipe *or* one ZEO
recipe. It can never have both, or more than one of each. This is
because both recipes write to the same configuration files

Dependencies
============

The recipes defined here use `collective.recipe.template`_ to output
configuration files, and `z3c.recipe.mkdir`_ to create implicitly
defined directories. `zc.zodbrecipes`_ is used to create the ZEO
server. You shouldn't need to install these manually as buildout will
take care of making them available when needed.

.. _collective.recipe.template: https://pypi.org/project/collective.recipe.template/
.. _z3c.recipe.mkdir: https://pypi.org/project/z3c.recipe.mkdir/
.. _zc.zodbrecipes: https://pypi.org/project/zc.zodbrecipes/

Directories and Files
=====================

The recipes defined here use the directory structure and variables
defined by `zc.recipe.deployment`_. There should be a buildout part
called ``deployment`` that uses this recipe. Alternatively (and
especially useful when composing a buildout from multiple
configurations), you can define a ``deployment`` part that lists these
directories manually. You'll also need to include the username that
should own created files and directories:

.. code:: ini

   [deployment]
   bin-directory = ${buildout:bin-directory}
   cache-directory = ${:run-directory}/caches
   crontab-directory = ${:root-directory}/etc/cron.d
   data-directory = ${:root-directory}/data
   etc-directory = ${:root-directory}/etc
   log-directory = ${:root-directory}/var/log
   logrotate-directory = ${:root-directory}/etc/logrotate.d
   rc-directory = ${:root-directory}/bin/rc
   root-directory = ${buildout:root-directory}
   run-directory = ${:root-directory}/var

The deployment recipe takes care of creating the needed directories,
but here we'll just do so manually. We'll define a common
configuration snippet that we'll include in future examples::

    >>> write(sample_buildout, 'deployment.cfg',
    ... """
    ... [deployment]
    ... root-directory = ${buildout:directory}
    ... data-directory = ${:root-directory}/data
    ... etc-directory = ${:root-directory}/etc
    ... log-directory = ${:root-directory}/var/log
    ... run-directory = ${:root-directory}/var
    ... rc-directory = ${:root-directory}/bin/rc
    ... cache-directory = ${:run-directory}/caches
    ... logrotate-directory = ${:root-directory}/etc/logrotate.d
    ... crontab-directory = ${:root-directory}/etc/cron.d
    ... user = user
    ...
    ... [directories]
    ... recipe = z3c.recipe.mkdir
    ... create-intermediate = true
    ... mode = 0700
    ... paths =
    ...    ${deployment:etc-directory}
    ...    ${deployment:run-directory}
    ...    ${deployment:cache-directory}
    ...    ${deployment:data-directory}
    ...    ${deployment:log-directory}
    ...    ${deployment:rc-directory}
    ...    ${deployment:logrotate-directory}
    ...    ${deployment:crontab-directory}
    ... """)

Both recipes create two files in the ``etc-directory``.

zodb_conf.xml
    This file is meant to be read with
    ``ZODB.config.databaseFromFile`` or ``databaseFromURL``. If you
    specify more than one storage, they will be listed in the order
    provided, creating a multi-database, with the first listed storage
    as the "root" database.

zeo_uris.ini
    This file provides the same database configuration as
    ``zodb_conf.xml`` (indeed, it references that file), but in a form
    of a single URL string that can be read using zodburi_. This can
    be convient for passing in the form of a string.

.. _zc.recipe.deployment: https://pypi.org/project/zc.recipe.deployment/_
.. _zodburi: https://pypi.org/project/zodburi/


Recipe Options
==============

Both recipes defined here accept some common options.

storages
    Required. A whitespace delimited list of storage names. Each of these will be
    added to the generated configuration files for a client to use (and
    for ZEO, for the server to serve).

    This can only be defined directly in the recipe part.
compress
   If "decompress" (the default) each storage will be wrapped in a
   `zc.zlibstorage`_ that only compress existing records. If set to
   "compress" new records will also be compressed.

   Set to "none" to disable the wrapper entirely.

   This can be set in the recipe part. If it's not defined there, a
   value defined in the ``environment`` part will be used before
   falling back to the default.

.. _zc.zlibstorage: https://pypi.org/project/zc.zlibstorage/

Storage and Database Options
============================

Some options are available to configure the ZODB database. These are
used by both recipes and may be defined at a per-database level (see
each recipe for an explanation of how). The defaults are built-in, but
setting a value in the recipe part will provide a new default for all
storages. Additionally, for backwards compatibility and composing
buildout configurations, if there is a part named ``<part>_opts_``,
where ``<part>`` is the name of the recipe part, options defined there
will override options defined in the recipe part, but will bee
overridden by options defined for an individual storage.

These two configurations both set the same ZODB cache size.

.. code:: ini

   [zeo]
   recipe = nti.recipes.zodb:zeo
   storages = users
   cache_size = 50

.. code:: ini

   [zeo]
   recipe = nti.recipes.zodb:zeo
   storages = users

   [zeo_opts]
   cache_size = 50


cache_size
   Controls the ZODB per-connection object cache. Setting this to a large-enough
   value to contain your application's working set can be very important, especially
   in read-heavy workloads. Setting it too large can waste memory.
pool_size
    Controls the number of ZODB connections kept in the ZODB pool. It
    is very important to set this large enough to accomodate the
    number of concurrent activities (requests) your application will
    handle. Each connection in the pool holds resources like its cache
    and in the case of RelStorage RDBMS sockets and possibly memcache
    sockets. Setting it too large can waste memory and file-descriptors.

    Normally, opening a DB and closing the connection will create a
    connection (if needed), then return it to the pool (if the pool is
    not full). However, in the case of multi-databases, when an object
    from a secondary database needs to be loaded, the active
    connection will request a connection to that database, and when
    the active connection is closed, that secondary connection is also
    closed *but not returned to the pool*. Instead, the active
    (primary) connection keeps a reference to it that it will use in
    the future. This has the effect of driving all secondary pools
    based on the efficiency of the primary pool. Thus, the pool-size
    for everything except the primary database is essentially
    meaningless (if the application always begins by opening that
    primary database), but that pool size controls everything.

    Calling DB.connectionDebugInfo() can show improperly sized pools:
    connections in the pool have 'opened' of None, while those in use
    have a timestamp and the length of time it's been open.

RelStorage
==========

The ``relstorage`` recipe creates configurations to connect to a
MySQL, PostgreSQL, or SQLite3 RelStorage database *in history-free
mode*. (Oracle is not supported.)

There are a number of different ways to configure storages. If you
have multiple storages residing on a common database server, and you
also have other databases on that server (SQLAlchemy, etc), you might
be interested in using a shared ``environment`` section to contain
the server location and account credentials.

.. note:: Do not store plain passwords in buildout configuration
          files. Use something like `nti.recipes.passwords
          <https://pypi.org/project/nti.recipes.passwords/>`_ to store
          them encrypted instead.

By default, the name of the database is the same as the storage name.

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... extends = deployment.cfg
    ... parts = directories relstorage
    ...
    ... [environment]
    ... sql_user = the_user
    ... sql_host = the_server
    ... sql_passwd = the_passwd
    ...
    ... [relstorage]
    ... recipe = nti.recipes.zodb:relstorage
    ... storages = users sessions
    ... compress = none
    ... """)

    >>> print_(system(buildout), end='')
    Installing...
    Installing relstorage.
    >>> ls(sample_buildout, 'etc')
    d  cron.d
    d  logrotate.d
    -  zeo_uris.ini
    -  zodb_conf.xml
    >>> cat(sample_buildout, 'etc', 'zodb_conf.xml')
    %import relstorage
    <zodb users>
      cache-size 100000
      database-name users
      pool-size 60
      <relstorage users>
        <mysql>
          # This comment preserves whitespace
              db users
              host the_server
              passwd the_passwd
              user the_user
        </mysql>
      blob-dir /sample-buildout/data/users.blobs
      cache-local-dir /sample-buildout/var/caches/data_cache/users.cache
      cache-local-mb 300
      cache-prefix users
      commit-lock-timeout 60
      keep-history false
      name users
      pack-gc false
      shared-blob-dir false
    </relstorage>
    </zodb>
    <zodb sessions>
      cache-size 100000
      database-name sessions
      pool-size 60
      <relstorage sessions>
        <mysql>
          # This comment preserves whitespace
              db sessions
              host the_server
              passwd the_passwd
              user the_user
        </mysql>
      blob-dir /sample-buildout/data/sessions.blobs
      cache-local-dir /sample-buildout/var/caches/data_cache/sessions.cache
      cache-local-mb 300
      cache-prefix sessions
      commit-lock-timeout 60
      keep-history false
      name sessions
      pack-gc false
      shared-blob-dir false
    </relstorage>
    </zodb>

Much can be configured at both the recipe level and in a section named
for the storage (prefixed with the name of the recipe, unlike in the
zeo recipe, and suffixed with '_storage_opts'), but a few settings can
only be configured on the recipe or environment part.

enable-persistent-cache
    Defaults to true.
cache-servers
   Deprecated. A list of memcache servers to use. Can be configured at the recipe
   or environment level.
blob-cache-size
   Defaults to no size cap.

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... extends = deployment.cfg
    ... parts = directories relstorage
    ...
    ... [environment]
    ... sql_user = the_user
    ... sql_host = the_server
    ... sql_passwd = the_passwd
    ...
    ... [relstorage]
    ... recipe = nti.recipes.zodb:relstorage
    ... storages = users sessions
    ... compress = none
    ... pack_gc = true
    ... commit_lock_timeout = 10
    ...
    ... [relstorage_users_storage_opts]
    ... cache_size = 42
    ... cache_local_mb = 2
    ... sql_user = custom_user
    ... """)

    >>> print_(system(buildout), end='')
    Uninstalling relstorage...
    Installing relstorage.
    >>> ls(sample_buildout, 'etc')
    d  cron.d
    d  logrotate.d
    -  zeo_uris.ini
    -  zodb_conf.xml
    >>> cat(sample_buildout, 'etc', 'zodb_conf.xml')
    %import relstorage
    <zodb users>
      cache-size 42
      database-name users
      pool-size 60
      <relstorage users>
        <mysql>
          # This comment preserves whitespace
              db users
              host the_server
              passwd the_passwd
              user custom_user
        </mysql>
      blob-dir /sample-buildout/data/users.blobs
      cache-local-dir /sample-buildout/var/caches/data_cache/users.cache
      cache-local-mb 2
      cache-prefix users
      commit-lock-timeout 10
      keep-history false
      name users
      pack-gc true
      shared-blob-dir false
    </relstorage>
    </zodb>
    <zodb sessions>
      cache-size 100000
      database-name sessions
      pool-size 60
      <relstorage sessions>
        <mysql>
          # This comment preserves whitespace
              db sessions
              host the_server
              passwd the_passwd
              user the_user
        </mysql>
      blob-dir /sample-buildout/data/sessions.blobs
      cache-local-dir /sample-buildout/var/caches/data_cache/sessions.cache
      cache-local-mb 300
      cache-prefix sessions
      commit-lock-timeout 10
      keep-history false
      name sessions
      pack-gc true
      shared-blob-dir false
    </relstorage>
    </zodb>

Configuring The Adapter
-----------------------

By default, a MySQL adapter is assumed. Use the ``sql_adapter``
setting (at the recipe or storage level) to change this.

The ``sql_adapter_extra_args`` may be used to add additional
configuration to the ``<adapter>`` section. This is frequently used to
select a driver.

If you change it to ``postgresql`` a DSN will be constructed based on
the ``sql_*`` settings. You can set ``sql_adapter_args`` to completely
specify the contents of the ``<adapter>`` section (this disables
``sql_adapter_extra_args``).

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... extends = deployment.cfg
    ... parts = directories relstorage
    ...
    ... [environment]
    ... sql_user = the_user
    ... sql_host = the_server
    ... sql_passwd = the_passwd
    ...
    ... [relstorage]
    ... recipe = nti.recipes.zodb:relstorage
    ... storages = users sessions
    ... compress = none
    ... sql_adapter = postgresql
    ... sql_adapter_extra_args =
    ...     driver gevent psycopg2
    ...
    ... [relstorage_users_storage_opts]
    ... sql_adapter = sqlite3
    ... sql_adapter_extra_args =
    ...     driver gevent sqlite3
    ... """)

    >>> print_(system(buildout), end='')
    Uninstalling relstorage...
    Installing relstorage.
    >>> ls(sample_buildout, 'etc')
    d  cron.d
    d  logrotate.d
    -  zeo_uris.ini
    -  zodb_conf.xml
    >>> cat(sample_buildout, 'etc', 'zodb_conf.xml')
    %import relstorage
    <zodb users>
      cache-size 100000
      database-name users
      pool-size 60
      <relstorage users>
        <sqlite3>
          # This comment preserves whitespace
              data-dir /sample-buildout/data/relstorage_users_storage
              driver gevent sqlite3
        </sqlite3>
      blob-dir /sample-buildout/data/users.blobs
      cache-local-dir /sample-buildout/var/caches/data_cache/users.cache
      cache-local-mb 300
      cache-prefix users
      commit-lock-timeout 60
      keep-history false
      name users
      pack-gc false
      shared-blob-dir true
    </relstorage>
    </zodb>
    <zodb sessions>
      cache-size 100000
      database-name sessions
      pool-size 60
      <relstorage sessions>
        <postgresql>
          # This comment preserves whitespace
              driver gevent psycopg2
              dsn dbname='sessions' user='the_user' password='the_passwd' host='the_server'
        </postgresql>
      blob-dir /sample-buildout/data/sessions.blobs
      cache-local-dir /sample-buildout/var/caches/data_cache/sessions.cache
      cache-local-mb 300
      cache-prefix sessions
      commit-lock-timeout 60
      keep-history false
      name sessions
      pack-gc false
      shared-blob-dir false
    </relstorage>
    </zodb>

Other Files
-----------

If the recipe was ``write-zodbconvert`` set to ``true``, then a set of
configuration files for converting to and from RelStorage and
FileStorage using ``zodbconvert`` will be generated.

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... extends = deployment.cfg
    ... parts = directories relstorage
    ...
    ... [environment]
    ... sql_user = the_user
    ... sql_host = the_server
    ... sql_passwd = the_passwd
    ...
    ... [relstorage]
    ... recipe = nti.recipes.zodb:relstorage
    ... storages = users
    ... compress = none
    ... write-zodbconvert = true
    ... """)

    >>> print_(system(buildout), end='')
    Uninstalling relstorage...
    Installing relstorage.
    >>> ls(sample_buildout, 'etc')
    d  cron.d
    d  logrotate.d
    d  relstorage
    -  zeo_uris.ini
    -  zodb_conf.xml
    >>> ls(sample_buildout, 'etc', 'relstorage')
    -  users_from_relstorage_conf.xml
    -  users_to_relstorage_conf.xml

ZEO
===

The ``zeo`` recipe can be used to create configurations for a ZEO
client and ZEO server. It is only intended for personal or test
environments.

.. rubric:: Options

Just like the ``relstorage`` recipe, it requires one or more storages.
Options can be set in the ``zeo`` part to apply to all storages, in a
part named for the storage to configure the server, or in a part named
for the client to configure the client. Note that the client also
inherits configuration options from the server.

pack-gc
   Defaults to false. This can only be set on the recipe part.


    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... extends = deployment.cfg
    ... parts = directories zeo
    ...
    ... [zeo]
    ... recipe = nti.recipes.zodb:zeo
    ... storages = users sessions
    ... compress = none
    ... pack-gc = true
    ...
    ... [users_storage_opts]
    ... pack-gc = true
    ... pool_size = 25
    ...
    ... [sessions_client_opts]
    ... cache-size = 42
    ... """)

And it creates several configuration files::

    >>> print_(system(buildout), end='')
    Uninstalling relstorage...
    Installing zeo.
    >>> ls(sample_buildout, 'etc')
    d  cron.d
    d  logrotate.d
    -  zeo-zdaemon.conf
    -  zeo-zeo.conf
    -  zeo_uris.ini
    -  zodb_conf.xml
    -  zodb_file_uris.ini

.. rubric:: Standard Files

The ``zodb_conf.xml`` and ``zeo_uris.ini`` are created as for RelStorage (the ``zconfig://``
prefixes are missing from the URIs because of a quirk in testing):

    >>> cat(sample_buildout, 'etc', 'zodb_conf.xml')
    <zodb users_client>
      cache-size 100000
      database-name users_client
      pool-size 25
      <zeoclient>
        blob-dir /sample-buildout/data/users_client.blobs
        name users_client
        server /sample-buildout/var/zeosocket
        shared-blob-dir true
        storage 1
      </zeoclient>
    </zodb>
    <zodb sessions_client>
      cache-size 42
      database-name sessions_client
      pool-size 60
      <zeoclient>
        blob-dir /sample-buildout/data/sessions_client.blobs
        name sessions_client
        server /sample-buildout/var/zeosocket
        shared-blob-dir true
        storage 2
      </zeoclient>
    </zodb>
    >>> cat(sample_buildout, 'etc', 'zeo_uris.ini')
    [ZODB]
    uris = /sample-buildout/etc/zodb_conf.xml#users /sample-buildout/etc/zodb_conf.xml#sessions

.. rubric:: zdaemon.conf

This file, prefixed with the name of the buildout part, is the
configuration to use with the ``zdaemon`` command's ``-C`` option in
order to run the ZEO server.

   >>> cat(sample_buildout, 'etc', 'zeo-zdaemon.conf')
   <runner>
     daemon on
     directory /sample-buildout/var
     program /sample-buildout/bin/runzeo -C /sample-buildout/etc/zeo-zeo.conf
     socket-name /sample-buildout/var/zeo-zdaemon.sock
     transcript /sample-buildout/var/log/zeo-zeo.log
     user user
   </runner>
   <BLANKLINE>
   <eventlog>
     <logfile>
       path /sample-buildout/var/log/zeo-zeo.log
     </logfile>
   </eventlog>

.. rubric:: zeo-conf.conf

This is the actual ZEO server configuration, again prefixed with the part name.

    >>> cat(sample_buildout, 'etc', 'zeo-zeo.conf')
    <zeo>
      address /sample-buildout/var/zeosocket
    </zeo>
    <BLANKLINE>
    <filestorage 1>
      blob-dir /sample-buildout/data/users.blobs
      pack-gc true
      path /sample-buildout/data/users.fs
    </filestorage>
    <BLANKLINE>
    <filestorage 2>
      blob-dir /sample-buildout/data/sessions.blobs
      pack-gc true
      path /sample-buildout/data/sessions.fs
    </filestorage>
    <BLANKLINE>
    <eventlog>
      <logfile>
        format %(asctime)s %(message)s
        level DEBUG
        path /sample-buildout/var/log/zeo.log
      </logfile>
    </eventlog>

.. rubric:: zodb_file_uris.ini

Intentionally undocumented. Expert use only.
