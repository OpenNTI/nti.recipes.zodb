# -*- coding: utf-8 -*-

import os

import zc.buildout.buildout
import zc.buildout.testing

class NoDefaultBuildout(zc.buildout.testing.Buildout):
    # The testing buildout doesn't provide a way to
    # ignore local defaults, which makes it system dependent, which
    # is clearly wrong
    def __init__(self):
        # pylint:disable=super-init-not-called,non-parent-init-called
        zc.buildout.buildout.Buildout.__init__(
            self,
            '',
            [('buildout', 'directory', os.getcwd())],
            user_defaults=False)

    def __delitem__(self, key):
        raise NotImplementedError('__delitem__')
