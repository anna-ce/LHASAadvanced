import os, shutil
import config

from boto.s3.connection import S3Connection
from boto.s3.key import Key

#
# Move products to persistent storage (AWS S3 or Local Dir)
#
def CopyToS3( s3_bucket, s3_folder, file_list, force, verbose ):
	
	if config.USING_AWS_S3_FOR_STORAGE:
		aws_access_key 			= os.environ.get('AWS_ACCESSKEYID')
		aws_secret_access_key 	= os.environ.get('AWS_SECRETACCESSKEY')
	
		conn 		= S3Connection(aws_access_key, aws_secret_access_key)
	
		if verbose:
			print "CopyToS3", s3_bucket, s3_folder, file_list
		
		mybucket 	= conn.get_bucket(s3_bucket)
		k 			= Key(mybucket)

		for f in file_list:
			fname	= os.path.basename(f)
			k.key 	= os.path.join(s3_folder, fname)
	
			# Check if it already exists
			possible_key = mybucket.get_key(k.key)
			#if verbose:
			#	print "Possible key", possible_key, k.key
		
			if force or not possible_key:
				if verbose:
					print "storing to s3:", mybucket, k.key
	
				k.set_contents_from_filename(f)
				mybucket.set_acl('public-read', k.key )
				
	if config.USING_LOCAL_DIR_FOR_STORAGE:
		dest_dir = os.path.join(config.LOCAL_DIR_STORAGE, s3_bucket, s3_folder)
		if( not os.path.exists(dest_dir)):
			if verbose:
				print "Making dest dir", dest_dir
			os.makedirs(dest_dir)			
			
		for f in file_list:
			fname	= os.path.basename(f)
			
			dest_file_name = os.path.join(dest_dir, fname)
			if verbose:
				print "Copying ", f, " to ", dest_file_name
	
			shutil.copy(f, dest_file_name)