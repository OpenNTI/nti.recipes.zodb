#!/usr/bin/env python
from setuptools import setup, find_packages
import codecs

VERSION = '0.0.0'

entry_points = {
	"zc.buildout" : [
		'relstorage = nti.recipes.zodb.relstorage:Databases',
		'zeo = nti.recipes.zodb.zeo:Databases'
	],
}

setup(
	name = 'nti.recipes.zodb',
	version = VERSION,
	author = 'Jason Madden',
	author_email = 'open-source@nextthought.com',
	description = "zc.buildout recipes for RelStorage and ZEO",
	long_description = codecs.open('README.rst', encoding='utf-8').read(),
	license = 'Proprietary',
	keywords = 'buildout relstorage ZEO',
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
		'setuptools',
		'zc.buildout',
		'zc.recipe.deployment',
		'zc.zodbrecipes'
	],
	entry_points=entry_points
)
