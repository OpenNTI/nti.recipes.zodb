#!/usr/bin/env python
from setuptools import setup, find_packages
import codecs

VERSION = '0.0.0'

entry_points = {
	"zc.buildout" : [
		'databases = nti.recipes.relstorage.meta.Databases'
	],
}

setup(
    name = 'nti.recipes.relstorage',
    version = VERSION,
    author = 'Jason Madden',
    author_email = 'open-source@nextthought.com',
    description = "zc.buildout recipes for RelStorage",
    long_description = codecs.open('README.rst', encoding='utf-8').read(),
    license = 'APACHE 2.0',
    keywords = 'buildout relstorage',
    #url = 'https://github.com/NextThought/nti.nose_traceback_info',
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
		'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.3',
        'Topic :: Software Development :: Testing'
		'Framework :: Buildout',
        ],
	packages=find_packages('src'),
	package_dir={'': 'src'},
	namespace_packages=['nti', 'nti.recipes'],
	install_requires=[
		'zc.buildout'
	],
	entry_points=entry_points
)
