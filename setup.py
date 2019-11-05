import codecs
from setuptools import setup, find_packages

VERSION = '0.0.0'

entry_points = {
    "zc.buildout" : [
        'relstorage = nti.recipes.zodb.relstorage:Databases',
        'zeo = nti.recipes.zodb.zeo:Databases'
    ],
}

TESTS_REQUIRE = [
    'PyHamcrest',
    'zope.testrunner',
]

setup(
    name='nti.recipes.zodb',
    version=VERSION,
    author='Jason Madden',
    author_email='open-source@nextthought.com',
    description="zc.buildout recipes for RelStorage and ZEO",
    long_description=codecs.open('README.rst', encoding='utf-8').read(),
    license='Proprietary',
    keywords='buildout relstorage ZEO',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Testing'
        'Framework :: Buildout',
    ],
    packages=find_packages('src'),
    package_dir={'': 'src'},
    tests_require=TESTS_REQUIRE,
    namespace_packages=['nti', 'nti.recipes'],
    install_requires=[
        'setuptools',
        'zc.buildout',
        'zc.recipe.deployment',
        'zc.zodbrecipes'
    ],
    extras_require={
        'test': TESTS_REQUIRE
    },
    entry_points=entry_points
)
