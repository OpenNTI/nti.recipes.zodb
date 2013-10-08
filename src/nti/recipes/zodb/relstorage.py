#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A meta-recipe to create multiple
relstorage connections in a Dataserver buildout.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

class Databases(object):

	def __init__(self, buildout, name, options ):
		# The initial use case has the same SQL
		# database, SQL user, cache servers,
		# etc, for all connections. The recipe
		# can easily be extended to allow separate values
		# in the future

		# by default, relstorage assumes a shared blob
		# directory. However, our most common use case here
		# is not to share. While using either wrong setting
		# in an environment is dangerous and can lead to data loss,
		# it's slightly worse to assume shared when its not
		if 'shared-blob-dir' not in options:
			options['shared-blob-dir'] = b'false' # options must be strings
		shared_blob_dir = options['shared-blob-dir']
		# Order matters
		buildout.parse("""
		[base_storage]
		name = BASE
		data_dir = ${deployment:data-directory}
		blob_dir = ${:data_dir}/${:name}.blobs
		shared-blob-dir = %s
		cache_module_name = memcache
		cache_servers = ${environment:cache_servers}
		commit_lock_timeout = 30
		cache_local_mb = 200
		poll_interval = 50
		sql_db = ${:name}
		sql_user = ${environment:sql_user}
		sql_passwd = ${environment:sql_passwd}
		sql_host = ${environment:sql_host}
		client_zcml =
				<zodb ${:name}>
					pool-size 2
					database-name ${:name}
					cache-size 75000
					<zlibstorage>
						<relstorage ${:name}>
							blob-dir ${:blob_dir}
							shared-blob-dir ${:shared-blob-dir}
							cache-prefix ${:name}
							cache-servers ${:cache_servers}
							cache-module-name ${:cache_module_name}
							commit-lock-timeout ${:commit_lock_timeout}
							cache-local-mb ${:cache_local_mb}
							poll-interval ${:poll_interval}

							keep-history false
							pack-gc false
							<mysql>
								db ${:sql_db}
								user ${:sql_user}
								passwd ${:sql_passwd}
								host ${:sql_host}
							</mysql>
						</relstorage>
					</zlibstorage>
				</zodb>""" % (shared_blob_dir,) )

		storages = options['storages'].split()
		blob_paths = []
		zeo_uris = []
		zcml_names = []

		for storage in storages:
			part_name = storage.lower() + '_storage'
			buildout.parse("""
			[%s]
			<= base_storage
			name = %s
			""" % ( part_name, storage ) )

			blob_paths.append( "${%s:blob_dir}" % part_name )
			zcml_names.append( "${%s:client_zcml}" % part_name )
			zeo_uris.append( "zconfig://${zodb_conf:output}#%s" % storage.lower() )

		buildout.parse("""
		[blob_dirs]
		recipe = z3c.recipe.mkdir
		mode = 0700
		paths =
			%s
		""" % '\n\t\t\t'.join( blob_paths ) )

		buildout.parse("""
		[zodb_conf]
		recipe = collective.recipe.template
		output = ${deployment:etc-directory}/zodb_conf.xml
		input = inline:
				%%import zc.zlibstorage
				%%import relstorage

				%s
		""" % '\n\t\t\t\t'.join( zcml_names ) )
		# Indents must match or we get parsing errors, hence
		# the tabs

		buildout.parse("""
		[zodb_uri_conf]
		recipe = collective.recipe.template
		output = ${deployment:etc-directory}/zeo_uris.ini
		input = inline:
			  [ZODB]
			  uris = %s
		""" % ' '.join( zeo_uris ) )

	def install(self):
		return ()

	def update(self):
		pass
