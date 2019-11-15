=========
 Changes
=========

1.0.0a2 (2019-11-15)
====================

- RelStorage: The value of ``sql_adapter_extra_args`` is validated to
  be syntactically correct.

- RelStorage: Support providing a PostgreSQL DSN

- All storages: Change the default to use zlibstorage only to
  decompress existing records, not to compress new records. Set the
  ``compress`` option (in this recipe or the ``environment`` recipe)
  to ``compress`` to turn compression on. Set it to ``decompress`` to
  explicitly request only decompression, and set it to ``none`` to
  explicitly disable all compression and decompression. In the future,
  expect the default to change to ``none``. See `issue 9 <https://github.com/NextThought/nti.recipes.zodb/issues/9>`_.

- ZEO: Instead of using ``${buildout:directory}/var/`` and
  ``${buildout:directory}/var/log`` directly, refer
  to ``${deployment:run-directory}`` and ``${deployment:log-directory}``.

- All storages: Make previously hard-coded values configurable. This
  includes ``pool-size`` (``pool_size``), ``commit-lock-timeout``
  (``commit_lock_timeout_``) and ``cache-size`` (``cache_size``).
  These values can be set in the recipe, in the ``_opts`` section, or
  in the ``_opts`` section for a particular storage.

- RelStorage PostgreSQL: Automatically use a correct DSN based on the
  configured host, port, dbname and password if no ``dsn`` setting is
  specified. Previously it was complex to specify a DSN using
  configurable values.

- RelStorage: Make ``shared_blob_dir``, ``cache_local_mb`` and
  ``pack_gc`` be configurable at the storage level instead of just the
  recipe part level.

1.0.0a1 (2019-11-14)
====================

- Fix relstorage recipe on Python 3. See `issue 8
  <https://github.com/NextThought/nti.recipes.zodb/issues/8>`_.

- For RelStorage, if the ``sql_adapter`` is set to ``sqlite3``, then
  derive a path to the data directory automatically. This can be set
  at the main part level, the part_opts level, or the
  part_storage_opts level. Also automatically set ``shared-blob-dir``
  to true.

- For RelStorage, avoid writing out the deprecated
  ``cache-local-dir-count`` option.
