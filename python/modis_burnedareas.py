#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Requirements:
#	gdal, numpy pytrmm...
#
# Access and Process MODIS Burned Areas
#
import numpy, sys, os, inspect
from osgeo import osr, gdal
from ftplib import FTP
from datetime import date
import warnings
from gzip import GzipFile

# Site configuration
import config
import argparse

year		= config.year
month		= config.month
day			= config.day
ymd	 		= config.ymd


ftp_site 	= "ba1.geog.umd.edu"
path		= "Collection51/TIFF/Win04/%s"%(year)		# Central America
user		= 'user'
password	= 'burnt_data'
force		= 0
verbose		= 0

def get_latest_mcd45_file():
	print("Checking "+ ftp_site + " for latest file...")
	ftp = FTP(ftp_site)
	
	ftp.login(user, password)               					# user anonymous, passwd anonymous@
	print("cwd to "+path)
	ftp.cwd(path)
	filenames 	= []
	ftp.retrlines('NLST', filenames.append )
	download 	= filenames[len(filenames)-1]	# last one in list
	download  	= download[:len(download)-3]	# remove .gz
	
	print "latest is: ", download	
	
	# remove the .gz extension
	local_filename = os.path.join(config.data_dir, "modis_fires", download)
	if os.path.exists(local_filename):
		print "already downloaded..."
		ftp.close()
		return local_filename
	else:
		if verbose:
			print "Downloading ", download+".gz", " to:", local_filename+".gz"
		file = open(local_filename+".gz", 'wb')
		try:
			ftp.retrbinary("RETR " + download+".gz", file.write)
			file.close()
			ftp.quit()
			
			# decompress it
			cmd = "gunzip -d "+local_filename+".gz" 
			if verbose:
				print cmd
			err = os.system(cmd)
			print "gunzip err", err
			if err != 0:
				raise Exception("gunzip error")
			ftp.close()
			return local_filename
		except:
			print "Error", sys.exc_info()[0]
			os.remove(local_filename+".gz")
			ftp.close()
			sys.exit(1)
			
def process_mcd45_file(dx, file_name):
	if verbose:
		print "Processing:"+file_name
		
	region 	= config.regions[dx]
	bbox	= region['bbox']
	tzoom   = region['tiles-zoom']
	
	# Set file vars
	output_file 		= os.path.join(config.data_dir,"modis_fires", dx, "mcd45_%s_out.tif" % ymd)
	rgb_output_file 	= os.path.join(config.data_dir,"modis_fires", dx, "mcd45_%s_out_rgb.tif" % ymd)
	subset_file 		= os.path.join(config.data_dir,"modis_fires", dx, "mcd45_%s_subset.tif" % ymd)
	subset_rgb_file 	= os.path.join(config.data_dir,"modis_fires", dx, "mcd45_%s_subset_rgb.tif" % ymd)
	color_file 			= os.path.join("cluts","mcd45_colors.txt")
	resampled_file 		= os.path.join(config.data_dir,"modis_fires", dx, "mcd45_%s_resampled.tif" % ymd)
	resampled_rgb_file 	= os.path.join(config.data_dir,"modis_fires", dx, "mcd45_%s_resampled_rgb.tif" % ymd)
	
	mbtiles_dir			= os.path.join(config.data_dir,"mbtiles", "mcd45_%s_%s" % (dx, ymd))
	mbtiles_fname 		= mbtiles_dir +".mbtiles"

	# for now
	cmd = "cp "+ file_name + " " + output_file 
	if verbose:
		print cmd
	os.system(cmd)
	
	# color it using colormap
	#if force or not os.path.exists(rgb_output_file):
	#	cmd = "gdaldem color-relief -alpha "+output_file+" " + color_file + " " + rgb_output_file
	#	if verbose:
	#		print cmd
	#	os.system(cmd)
	
	
	# subset it to our BBOX
	# use ullr
	if force or not os.path.exists(subset_file):
		lonlats	= "" + str(bbox[0]) + " " + str(bbox[3]) + " " + str(bbox[2]) + " " + str(bbox[1])
		cmd 	= "gdal_translate -projwin " + lonlats +" "+ output_file+ " " + subset_file
		if verbose:
			print cmd
		os.system(cmd)

	# color it using colormap
	#if force or not os.path.exists(subset_rgb_file):
	#	cmd = "gdaldem color-relief -alpha "+ subset_file+ " " + color_file + " " + subset_rgb_file
	#	if verbose:
	#		print cmd
	#	os.system(cmd)

	# resample it at 1km
	if force or not os.path.exists(resampled_file):
		cmd = "gdalwarp -tr 0.008999 0.008999 -r near " + subset_file + " " + resampled_file
		if verbose:
			print cmd
		os.system(cmd)

	# color it using colormap
	if force or not os.path.exists(resampled_rgb_file):
		cmd = "gdaldem color-relief -alpha " + resampled_file + " " + color_file + " " + resampled_rgb_file
		if verbose:
			print cmd
		os.system(cmd)
		
	# Create mbtiles
	if force or not os.path.exists(mbtiles_fname):			
		cmd = "./gdal2tiles.py -z "+ tzoom + " " + resampled_rgb_file  + " " + mbtiles_dir
		if verbose:
			print cmd
		os.system(cmd)

		# generate metadata.json
		metafile = os.path.join(mbtiles_dir, "metadata.json")
		json = "{\n"
		json += "  \"name\": \"MODIS Fire Product - "+ ym + "\",\n"
		json += "  \"description\": \"MODIS UMD \",\n"
		json += "  \"version\": 1\n"
		json += "}"
		f = open(metafile, "w")
		f.write(json)
		f.close()

		cmd = "./mb-util " + mbtiles_dir  + " " + mbtiles_fname
		if verbose:
			print cmd
		os.system(cmd)

	# copy mbtiles to S2
	bucketName 	= region['bucket']
	# copy mbtiles to S3
	bucketName = region['bucket']
	cmd = "./aws-copy.py --bucket "+bucketName+ " --file " + mbtiles_fname
	if verbose:
		cmd += " --verbose"
		print cmd
	os.system(cmd)
	cmd = "rm -rf "+ mbtiles_dir
	if verbose:
		print cmd
		os.system(cmd)
#
# ======================================================================
#
if __name__ == '__main__':
	version_num = int(gdal.VersionInfo('VERSION_NUM'))
	if version_num < 1800: # because of GetGeoTransform(can_return_null)
		print('ERROR: Python bindings of GDAL 1.8.0 or later required')
		sys.exit(1)
	
	parser 		= argparse.ArgumentParser(description='MODIS Processing')
	apg_input 	= parser.add_argument_group('Input')
	apg_input.add_argument("-f", "--force", action='store_true', help="forces new product to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose
	
	# region d02 and d03 share the same MODIS product
	
	latest_file = get_latest_mcd45_file()
	process_mcd45_file( 'd02', latest_file)
	process_mcd45_file( 'd03', latest_file)
