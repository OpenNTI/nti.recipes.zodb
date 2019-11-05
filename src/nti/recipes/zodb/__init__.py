#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
See `relstorage.py` and `zeo.py`.
"""

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

class MetaRecipe(object):
    # Contains the base methods that are required of a recipe,
    # but which meta-recipes (recipes that write other config sections)
    # don't actually need.

    def install(self):
        return () # pragma: no cover

    def update(self):
        "Does nothing."
