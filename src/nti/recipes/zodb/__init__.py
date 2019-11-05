#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
See `relstorage.py` and `zeo.py`.
"""

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from textwrap import dedent

class MetaRecipe(object):
    # Contains the base methods that are required of a recipe,
    # but which meta-recipes (recipes that write other config sections)
    # don't actually need.

    def install(self):
        return () # pragma: no cover

    def update(self):
        "Does nothing."


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
        self._dirs_to_create_refs.add((part, setting))

    def add_database(self, part, setting):
        # Adds the ZCML at part:setting to zodb_conf.xml
        self._zodb_refs.add((part, setting))

    def _derive_related_part_name(self, name):
        return '%s_%s' % (self.my_name, name)

    @staticmethod
    def __refs_to_lines(refs, indent=4):
        return ('\n' + ' ' * indent).join(
            '${%s:%s}' % ref
            for ref in refs
        )

    def _parse(self, text, **kwargs):
        __traceback_info__ = text, kwargs
        return self.buildout.parse(dedent(text) % kwargs)

    def _normalized_storage_names(self):
        return [x.lower() for x in self.my_options['storages'].split()]

    def buildout_add_mkdirs(self):
        name = self._derive_related_part_name('mkdirs')
        paths = self.__refs_to_lines(self._dirs_to_create_refs)
        self._parse("""
        [%(part_name)s]
        recipe = z3c.recipe.mkdir
        mode = 0700
        paths =
            %(paths)s
        """, part_name=name, paths=paths)

    def buildout_add_zodb_conf(self):
        zcml_names = self.__refs_to_lines(self._zodb_refs, indent=8)
        self._parse("""
        [zodb_conf]
        recipe = collective.recipe.template
        output = ${deployment:etc-directory}/zodb_conf.xml
        input = inline:
                %%import zc.zlibstorage
                %%import relstorage

                %(zcml_names)s
        """, zcml_names=zcml_names)

    def buildout_add_zeo_uris(self):
        uris = [
            "zconfig://${zodb_conf:output}#%s" % name
            for name in self._normalized_storage_names()
        ]

        self._parse("""
        [zodb_uri_conf]
        recipe = collective.recipe.template
        output = ${deployment:etc-directory}/zeo_uris.ini
        input = inline:
              [ZODB]
              uris = %(uris)s
        """, uris=' '.join(uris))
