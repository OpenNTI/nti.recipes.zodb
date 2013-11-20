#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A meta-recipe to create multiple
relstorage connections in a Dataserver buildout.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# StringIO does BAD things with unicode literals
# prior to 2.7.3
import sys
if sys.version_info < (2,7,3):
	raise ImportError("Need at least python 2.7.3")


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
		base_storage_name = name + '_base_storage'
		buildout.parse("""
		[%s]
		name = BASE
		data_dir = ${deployment:data-directory}
		blob_dir = ${:data_dir}/${:name}.blobs
		dump_name = ${:name}
		dump_dir = ${:data_dir}/relstorage_dump/${:dump_name}
		blob_dump_dir = ${:data_dir}/relstorage_dump/${:dump_name}/blobs
		filestorage_name = NONE
		shared-blob-dir = %s
		cache_module_name = memcache
		cache_servers = ${environment:cache_servers}
		commit_lock_timeout = 30
		cache_local_mb = 200
		poll_interval = 50
		pack-gc = false
		sql_db = ${:name}
		sql_user = ${environment:sql_user}
		sql_passwd = ${environment:sql_passwd}
		sql_host = ${environment:sql_host}
		sql_adapter = mysql
		sql_adapter_args =
				 db ${:sql_db}
				 user ${:sql_user}
				 passwd ${:sql_passwd}
				 host ${:sql_host}
				 ${:sql_adapter_extra_args}
		sql_adapter_extra_args =
		storage_zcml =
					<zlibstorage ${:name}>
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
							pack-gc ${:pack-gc}
							<${:sql_adapter}>
								${:sql_adapter_args}
							</${:sql_adapter}>
						</relstorage>
					</zlibstorage>
		client_zcml =
				<zodb ${:name}>
					pool-size 2
					database-name ${:name}
					cache-size 75000
					${:storage_zcml}
				</zodb>
		filestorage_zcml =
				<zlibstorage ${:filestorage_name}>
					<filestorage ${:filestorage_name}>
						path ${:dump_dir}/data.fs
						blob-dir ${:blob_dump_dir}
					</filestorage>
				</zlibstorage>
		""" % (base_storage_name, shared_blob_dir) )

		storages = options['storages'].split()
		blob_paths = []
		zeo_uris = []
		zcml_names = []

		for storage in storages:
			part_name = name + '_' + storage.lower() + '_storage'
			# Note that while it would be nice to automatically extend
			# from this section, that leads to a recursive invocation
			# of this recipe, which obviously fails (with weird errors
			# about "part already exists"). So we use _opts for everything,
			# in precedence order
			other_bases = [base_storage_name]
			if name + '_opts' in buildout:
				other_bases.append( name + '_opts' )
			if part_name + '_opts' in buildout:
				other_bases.append( part_name + '_opts' )
			other_bases = '\n\t\t\t\t'.join( other_bases )
			part_template = """
			[%s]
			<=
				%s
			name = %s
			"""
			part = part_template % ( part_name, other_bases, storage )
			buildout.parse(part)

			blob_paths.append( "${%s:blob_dir}" % part_name )

			zcml_names.append( "${%s:client_zcml}" % part_name )
			zeo_uris.append( "zconfig://${zodb_conf:output}#%s" % storage.lower() )

			# ZODB convert to and from files
			src_part_name = 'zodbconvert_' + part_name + '_src'
			dest_part_name = 'zodbconvert_' + part_name + '_destination'
			blob_paths.append( "${%s:dump_dir}" % src_part_name )
			blob_paths.append( "${%s:blob_dump_dir}" % dest_part_name )

			to_relstorage_part_name = storage.lower() + '_to_relstorage_conf'
			from_relstorage_part_name = storage.lower() + '_from_relstorage_conf'

			zodb_convert_part_template = """
			[%s]
			<=
				%s
			name = %s
			filestorage_name = %s
			dump_name = %s
			"""
			src_part = zodb_convert_part_template % ( src_part_name,
													  other_bases,
													  'source', 'destination',
													  storage.lower())
			buildout.parse(src_part)

			dest_part = zodb_convert_part_template % ( dest_part_name,
													   other_bases,
													   'destination', 'source',
													   storage.lower())
			buildout.parse(dest_part)
			convert_template = """
			[%s]
			recipe = collective.recipe.template
			output = ${deployment:etc-directory}/relstorage/%s.xml
			input = inline:
				%%import zc.zlibstorage
				%%import relstorage

				${%s:storage_zcml}
				${%s:filestorage_zcml}
			"""
			buildout.parse( convert_template % (to_relstorage_part_name,
												to_relstorage_part_name,
												dest_part_name,
												dest_part_name ))
			buildout.parse( convert_template % (from_relstorage_part_name,
												from_relstorage_part_name,
												src_part_name,
												src_part_name ))

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
