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


def default_buildout(default_sections=None, **extra_options):
    # You CANNOT make a change to a section after it's constructed
    # here and expect sections that later extend it to see the change. The original
    # raw data is cached in a few places.
    extra_options = extra_options or {}
    buildout = NoDefaultBuildout()
    sections = dict(
        deployment={
            'etc-directory': '/etc',
            'data-directory': '/data',
            'cache-directory': '/caches',
            'run-directory': '/var',
            'log-directory': '/var/log',
        },
        **(default_sections or {})
    )
    for k in sections:
        sections[k].update(extra_options.get(k, {}))
        buildout[k] = sections[k]
    return buildout
