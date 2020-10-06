import os
from setuptools import setup, find_packages


entry_points = {
    "zc.buildout" : [
        'relstorage = nti.recipes.zodb.relstorage:Databases',
        'zeo = nti.recipes.zodb.zeo:Databases'
    ],
}

TESTS_REQUIRE = [
    'PyHamcrest',
    'collective.recipe.template',
    'z3c.recipe.mkdir',
    'zope.testing',
    'zope.testrunner',
    'zdaemon',
]

def read_file(*path):
    base_dir = os.path.dirname(__file__)
    file_path = (base_dir, ) + tuple(path)
    with open(os.path.join(*file_path)) as f:
        result = f.read()
    return result

setup(
    name='nti.recipes.zodb',
    version='1.1.0',
    author='Jason Madden',
    author_email='open-source@nextthought.com',
    description="zc.buildout recipes for RelStorage and ZEO",
    long_description=read_file('README.rst'),
    license='Proprietary',
    keywords='buildout relstorage ZEO',
    url="https://github.com/NextThought/nti.recipes.zodb",
    project_urls={
        'Bug Tracker': 'https://github.com/NextThought/nti.recipes.zodb/issues',
        'Source Code': 'https://github.com/NextThought/nti.recipes.zodb/',
        #'Documentation': 'https://ntirecipeszodb.readthedocs.io',
    },
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
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Testing',
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
        'zc.zodbrecipes',
        'ZConfig', # zc.zodbrecipes also depends on this
    ],
    extras_require={
        'test': TESTS_REQUIRE
    },
    entry_points=entry_points
)
