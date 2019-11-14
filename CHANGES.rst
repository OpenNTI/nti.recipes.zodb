=========
 Changes
=========

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
