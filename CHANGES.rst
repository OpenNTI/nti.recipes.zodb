=========
 Changes
=========

1.0.0a2 (unreleased)
====================

- Nothing changed yet.


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
