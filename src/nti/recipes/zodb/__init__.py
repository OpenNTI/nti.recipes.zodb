#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
See `relstorage.py` and `zeo.py`.
"""

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division


from ._model import ZConfigSection
from ._model import Ref
from ._model import ChoiceRef
from ._model import Part
from ._model import hyphenated

class MetaRecipe(object):
    # Contains the base methods that are required of a recipe,
    # but which meta-recipes (recipes that write other config sections)
    # don't actually need.

    def install(self):
        return () # pragma: no cover

    def update(self):
        "Does nothing."

class filestorage(ZConfigSection):

    path = Ref('dump_dir') / 'data.fs'
    blob_dir = Ref('blob_dump_dir').hyphenate()

    def __init__(self, _name=None, **kwargs):
        ZConfigSection.__init__(self, 'filestorage', _name, **kwargs)

class zlibstorage(ZConfigSection):

    def __init__(self, _name, storage):
        self.storage = storage
        ZConfigSection.__init__(self, self.__class__.__name__,
                                _name, storage)

class zodb(ZConfigSection):
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
    pool_size = hyphenated(60)
    database_name = Ref('name').hyphenate()
    cache_size = Ref('cache-size').hyphenate()

    def __init__(self, _name, storage):
        ZConfigSection.__init__(self, 'zodb', _name, APPEND=storage)

class deployment(object):
    data = Ref('deployment', 'data-directory')
    etc = Ref('deployment', 'etc-directory')

class ZodbClientPart(Part):
    cache_size = hyphenated(100000)
    name = 'BASE'

class MultiStorageRecipe(MetaRecipe):
    # Base recipe for deriving multiple storages
    # from a single call to this recipe.
    # All of our work is done during __init__.

    # References to hardcoded paths such as /etc/
    # come from the standard ``deployment`` section

    # This expands into multiple buildout parts; each part whose
    # description begins with ``$PART_`` is prefixed with the name
    # of this part.
    #
    # * ``$PART_mkdirs`` creates any needed directories.
    # * ``zodb_conf`` creates ``/etc/zodb_conf.xml``
    # * ``zodb_uri_conf`` creates ``/etc/zeo_uris.ini``,
    #   a configparser formatted file with ZODB uris for each
    #   configured database. This is the same information as ``zodb_conf.xml``,
    #   in a different format.

    def __init__(self, buildout, my_name, my_options):
        self.buildout = buildout
        self.my_name = my_name
        self.my_options = my_options
        # Any directories that need to be created
        # should be a setting in one of the created parts. They are
        # addressed here as (part, setting) pairs, and added to a part
        # that uses the z3c.recipe.mkdir recipe to create them.
        self._dirs_to_create_refs = set()
        # Likewise, but referring to settings that define a <zodb>
        # element as a string.
        self._zodb_refs = set()

    def create_directory(self, part, setting):
        self._dirs_to_create_refs.add(Ref(part, setting))

    def add_database(self, part, setting):
        # Adds the ZCML at part:setting to zodb_conf.xml
        self._zodb_refs.add(Ref(part, setting))

    def ref(self, part, setting=None):
        """
        Return a substitution reference: ${part:setting}.

        If called with only one argument, it is the setting and the part
        is the current part: ${:setting}
        """
        if setting is None:
            setting = part
            part = ''
        return Ref(part, setting)

    def choice_ref(self, section_map, setting):
        return ChoiceRef(section_map, setting)

    def _derive_related_part_name(self, name):
        return '%s_%s' % (self.my_name, name)

    @staticmethod
    def __refs_to_lines(refs):
        return [
            str(ref)
            for ref in refs
        ]

    def _parse(self, part):
        __traceback_info__ = part
        return self.buildout.parse(str(part))

    def _normalized_storage_names(self):
        return [x.lower() for x in self.my_options['storages'].split()]

    def buildout_add_mkdirs(self, name=None):
        # For historical reasons (compatibility with existing deployments)
        # allow picking a name for this section instead of automatically choosing.
        part = Part(
            name or self._derive_related_part_name('mkdirs'),
            recipe='z3c.recipe.mkdir',
            mode='0700',
            paths=self.__refs_to_lines(self._dirs_to_create_refs))
        self._parse(part)

    def buildout_add_zodb_conf(self):
        zcml_names = self.__refs_to_lines(self._zodb_refs)
        part = Part(
            'zodb_conf',
            recipe='collective.recipe.template',
            output=deployment.etc / 'zodb_conf.xml',
            input=[
                'inline:',
                '%import zc.zlibstorage',
                '%import relstorage',
            ] + zcml_names
        )
        self._parse(part)

    def buildout_add_zeo_uris(self):
        uris = ' '.join(
            "zconfig://${zodb_conf:output}#%s" % name
            for name in self._normalized_storage_names()
        )
        part = Part(
            'zodb_uri_conf',
            recipe='collective.recipe.template',
            output=deployment.etc / 'zeo_uris.ini',
            input=[
                'inline:',
                '[ZODB]',
                'uris = ' + uris
            ],
        )
        self._parse(part)
