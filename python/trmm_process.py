#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Requirements:
#	gdal, numpy pytrmm...
#
import numpy, sys, os, inspect, math
from osgeo import osr, gdal
from ftplib import FTP
from datetime import date, datetime, timedelta

from pytrmm import TRMM3B42RTFile

# Site configuration
import config
import argparse

year		= config.year
month		= config.month
day			= config.day
#hour		= config.hour

# but we need to get the 24hr rainfall accumulation of the day before
#today		= date(year,month, day)
#today		-= timedelta(1)

#year		= today.year
#month		= today.month
#day		= today.day
#ym	 		= "%s%02d" % (year, month)
#ymd	 	= "%s%02d%02d" % (year, month, day)

ymd = config.ymd

ftp_site 	= "trmmopen.gsfc.nasa.gov"
path	 	= "pub/merged/3B42RT/"
force		= 0
verbose		= 0

#	
# Files for a whole day
#
	
file_00 = "3B42RT.%04d%02d%02d00.7.bin.gz"%(year, month, day)
file_03 = "3B42RT.%04d%02d%02d03.7.bin.gz"%(year, month, day)
file_06 = "3B42RT.%04d%02d%02d06.7.bin.gz"%(year, month, day)
file_09 = "3B42RT.%04d%02d%02d09.7.bin.gz"%(year, month, day)
file_12 = "3B42RT.%04d%02d%02d12.7.bin.gz"%(year, month, day)
file_15 = "3B42RT.%04d%02d%02d15.7.bin.gz"%(year, month, day)
file_18 = "3B42RT.%04d%02d%02d18.7.bin.gz"%(year, month, day)
file_21 = "3B42RT.%04d%02d%02d21.7.bin.gz"%(year, month, day)
	
trmm_files = [file_00, file_03, file_06, file_09, file_12, file_15, file_18, file_21]

# testing with specific files
#
#trmm_files = [
#	"3B42RT.2013120421.7.bin.gz",
#	"3B42RT.2013120500.7.bin.gz",
#	"3B42RT.2013120503.7.bin.gz",
#	"3B42RT.2013120506.7.bin.gz",
#	"3B42RT.2013120509.7.bin.gz",
#	"3B42RT.2013120512.7.bin.gz",
#	"3B42RT.2013120515.7.bin.gz",
#	"3B42RT.2013120518.7.bin.gz"
#]

# required directories
trmm_3B42RT_dir		=  os.path.join(config.data_dir,"trmm","3B42RT", ymd)
trmm_d02_dir		=  os.path.join(config.data_dir,"trmm","d02", ymd)
trmm_d03_dir		=  os.path.join(config.data_dir,"trmm","d03", ymd)
trmm_dir			=  os.path.join(config.data_dir,"trmm", ymd)

# Set file vars
delete_files 		= os.path.join(trmm_dir, "TMP*")
output_file_360		= os.path.join(trmm_dir, "TMP_trmm_24_%s_360.tif" % ymd)
output_file_180		= os.path.join(trmm_dir, "trmm_24_%s_180.tif" % ymd)
output_file_180_1	= os.path.join(trmm_dir, "TMP_trmm_24_%s_180_1.tif" % ymd)
output_file_180_2	= os.path.join(trmm_dir, "TMP_trmm_24_%s_180_2.tif" % ymd)
rgb_output_file 	= os.path.join(trmm_dir, "trmm_24_%s_rgb.tif"% ymd)

color_file 			= os.path.join("cluts", "green-blue-gr.txt")

def execute(cmd):
	if(verbose):
		print cmd
	os.system(cmd)
	
# ===============================================================
# Get All TRMM files from that day
#			
def get_daily_trmm_files():
	if verbose:
		print("Checking "+ftp_site+" for latest file...")
		
	try:
		ftp = FTP(ftp_site)
		
		ftp.login()               					# user anonymous, passwd anonymous@
		ftp.cwd("pub/merged/3B42RT/")
		
	except:
		print "FTP login Error", sys.exc_info()[0]
		ftp.close()
		sys.exit(1)

	for f in trmm_files:
		local_filename = os.path.join(trmm_3B42RT_dir, f)
		if not os.path.exists(local_filename):
			if verbose:
				print "Downloading it...", f
			file = open(local_filename, 'wb')
			try:
				ftp.retrbinary("RETR " + f, file.write)
				file.close()
			except:
				print "FTP Error", sys.exc_info()[0]
				os.remove(local_filename)
				ftp.close();
				sys.exit(1)

	ftp.close()

#
# Generate the global 24hr Rainfall Accumulation File
#
def generate_24h_accumulation():		
	
	index = 0
	for f in trmm_files:
		local_filename = os.path.join(trmm_3B42RT_dir, f)

		if verbose:
			print local_filename
			
		trmm_file 	= TRMM3B42RTFile(local_filename)
		precip 		= trmm_file.precip()

		#print f
		#print 'TRMM precip max:', precip.max()
		#print 'TRMM precip min:', precip.min()
		#print 'TRMM precip mean:', precip.mean()
		#print 'TRMM precip std-dev:', precip.std()

		if index == 0:
			data = precip*3			
			index = 1
		else:
			data += precip*3
		
	nrows 	= precip.shape[0]
	ncols 	= precip.shape[1]	 

	y		= 60
	x		= 0
	
	res 	= 0.25

	if force:
		cmd = "rm " + delete_files
		execute(cmd)

	if verbose:
		print "Creating:", output_file_360
	
	driver = gdal.GetDriverByName("GTiff")
	dst_ds = driver.Create(output_file_360, ncols, nrows, 1, gdal.GDT_Float32 )

	# top left x, w-e pixel resolution, rotation, top left y, rotation, n-s pixel resolution
	dst_ds.SetGeoTransform( [ x, res, 0, y, 0, -res ] )
  
	# set the reference info 
	srs = osr.SpatialReference()
	srs.SetWellKnownGeogCS("WGS84")
	dst_ds.SetProjection( srs.ExportToWkt() )

	# write the band
	band = dst_ds.GetRasterBand(1)
	band.SetNoDataValue(-31999)
	band.WriteArray(data)
	dst_ds = None
	
	#
	# TRMM data is projected 0-360.
	# Let's split tthe two halves and switch them around to get -180-180
	#
	cmd = "gdal_translate -q -srcwin 0 0 720 480 -a_ullr 0 60 180 -60 %s %s" %(output_file_360, output_file_180_1)
	execute(cmd)
	
	cmd = "gdal_translate -q -srcwin 720 0 720 480 -a_ullr -180 60 0 -60 %s %s" %( output_file_360, output_file_180_2)
	execute(cmd)
	
	cmd = "gdal_merge.py -q -o %s %s %s" % ( output_file_180, output_file_180_1, output_file_180_2 )
	execute(cmd)

	#
	# colorize results for validation
	#
	cmd = "gdaldem color-relief -q -alpha -of GTiff %s %s %s" % ( output_file_180, color_file, rgb_output_file)
	execute(cmd)
	
	
def process_trmm_region_subset(global_file, bbox, subset_file, clut_file, rgb_subset_file):
	if force or not os.path.exists(subset_file):
		cmd = "gdalwarp -overwrite -q -co COMPRESS=LZW -te %f %f %f %f %s %s" % (bbox[0], bbox[1], bbox[2], bbox[3], global_file, subset_file)
		execute(cmd)
		
	if force or not os.path.exists(rgb_subset_file):
		cmd = "gdaldem color-relief -q -alpha -of GTiff %s %s %s" % ( subset_file, clut_file, rgb_subset_file)
		execute(cmd)
	
def process_trmm_region_upsample(pixelsize, bbox, global_file, resampled_file):
	if force or not os.path.exists(resampled_file):
		cmd = "gdalwarp -overwrite -q -tr %f %f -te %f %f %f %f -co COMPRESS=LZW %s %s" % (pixelsize,pixelsize,bbox[0], bbox[1], bbox[2], bbox[3], global_file, resampled_file)
		execute(cmd)
	
def process_trmm_region_thumbnail(rgb_subset_file, thn_width, thn_height, static_file,  thumbnail_file):
	tmp_file = thumbnail_file + ".tmp.tif"
	if force or not os.path.exists(thumbnail_file):
		cmd="gdalwarp -overwrite -q -multi -ts %d %d -r cubicspline -co COMPRESS=LZW %s %s" % (thn_width, thn_height, rgb_subset_file, tmp_file )
		execute(cmd)
		cmd = "composite -blend 60 %s %s %s" % ( tmp_file, static_file, thumbnail_file)
		execute(cmd)
		execute("rm "+tmp_file)
	
def process_trmm_region_topojson(dx, ymd, subset_file, supersampled_file, supersampled_rgb_file, pixelsize, bbox, shp_file, geojson_file, topojson_file, topojson_gz_file):
	# we need to resample even higher to improve resolution
	if force or not os.path.exists(supersampled_file):
		cmd = "gdalwarp -overwrite -q -tr %f %f -te %f %f %f %f -r cubicspline -co COMPRESS=LZW %s %s"%(pixelsize/10, pixelsize/10, bbox[0], bbox[1], bbox[2], bbox[3], subset_file, supersampled_file)
		execute(cmd)
	
	#if force or not os.path.exists(supersampled_rgb_file):
	#	cmd = "gdaldem color-relief -q -alpha -of GTiff %s %s %s" % ( supersampled_file, color_file, supersampled_rgb_file)
	#	execute(cmd)
	
	if force or not os.path.exists(shp_file):
		cmd = "gdal_contour -q -a precip -fl 2 -fl 3 -fl 5 -fl 13 -fl 21 -fl 34 -fl 55 -fl 89 -fl 144 %s %s" % ( supersampled_file, shp_file )
		execute(cmd)
	
	if force or not os.path.exists(geojson_file):
		cmd = "ogr2ogr -f geoJSON %s %s" %( geojson_file, shp_file) 
		execute(cmd)
	
	if force or not os.path.exists(topojson_file):
		precip = "daily_precip_%s_%s" % (dx,ymd)
		cmd = "topojson --simplify-proportion 0.5  --bbox -p precip -o %s -- %s=%s" % (topojson_file, precip, geojson_file ) 
		execute(cmd)
	
	if force or not os.path.exists(topojson_gz_file):
		if( force ):
			execute("rm -f "+topojson_file)
			
		cmd = "gzip %s" % (topojson_file)
		execute(cmd)
	
def process_trmm_region_to_s3( dx, ymd, thumbnail_file, topojson_gz_file):
	# copy mbtiles to S3
	region 		= config.regions[dx]
	bucketName 	= region['bucket']
	folder		= ymd
	 
	cmd = "./aws-copy.py --bucket " + bucketName + " --folder " + ymd + " --file " + topojson_gz_file
	if verbose:
		cmd += " --verbose"
	print cmd
	execute(cmd)

	cmd = "./aws-copy.py --bucket " + bucketName + " --folder " + ymd + " --file " + thumbnail_file
	if verbose:
		cmd += " --verbose"
	print cmd
	execute(cmd)
	
def process_trmm_region_cleanup(dx, ymd):
	if not verbose:			# probably debugging, so do not dispose of artifacts
		delete_files = [
			os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s_1km.dbf" % (dx,ymd)),
			os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s_1km.geojson" % (dx,ymd)),
			os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s_1km.prj" % (dx,ymd)),
			os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s_1km.shp" % (dx,ymd)),
			os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s_1km.shx" % (dx,ymd)),
			#os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s_1km.tif" % (dx,ymd)),
			os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s.topojson" % (dx,ymd)),
			os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s_100m.*" % (dx,ymd)),

			os.path.join(config.data_dir,"trmm", ymd, "TMP_trmm_24_%s*" % (ymd)),
		]
		cmd = "rm "+ " ".join(delete_files)
		execute(cmd)
		
		print "Removed files"
	
# ===========================
# Subset 24hr Rainfall Accumulation and resample for specific region
#
def process_trmm_region( dx ):
	region 		= config.regions[dx]
	bbox		= region['bbox']
	tzoom   	= region['tiles-zoom']
	pixelsize   = region['pixelsize']
	thn_width   = region['thn_width']
	thn_height  = region['thn_height']
    
	if verbose:
		print "process_trmm_region:", dx

	subset_file 			= os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s.tif" % (dx,ymd))
	thumbnail_file 			= os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s.thn.png" % (dx,ymd))
	static_file 			= os.path.join(config.data_dir,"trmm", dx, "%s_static.tiff" % (dx))
	rgb_subset_file			= os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s_rgb.tif" % (dx,ymd))
	resampled_file 			= os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s_1km.tif" % (dx,ymd))
	supersampled_file	 	= os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s_100m.tif" % (dx,ymd))
	supersampled_rgb_file 	= os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s_100m_rgb.tif" % (dx,ymd))
	shp_file 				= os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s_1km.shp" % (dx,ymd))
	geojson_file 			= os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s_1km.geojson" % (dx,ymd))
	topojson_file			= os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s.topojson" % (dx,ymd))
	topojson_gz_file		= os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s.topojson.gz" % (dx,ymd))
	
	process_trmm_region_subset(output_file_180, bbox, subset_file, color_file, rgb_subset_file)
	process_trmm_region_upsample(pixelsize, bbox, output_file_180, resampled_file)
	process_trmm_region_thumbnail( rgb_subset_file, thn_width, thn_height, static_file,  thumbnail_file)
	process_trmm_region_topojson( dx, ymd, subset_file, supersampled_file, supersampled_rgb_file, pixelsize, bbox, shp_file, geojson_file, topojson_file, topojson_gz_file )
	
	process_trmm_region_to_s3( dx, ymd, thumbnail_file, topojson_gz_file)

	process_trmm_region_cleanup(dx, ymd)
		
# ===========================
# Process Region 2
#
def process_trmm_d02_file():
	process_trmm_region("d02")

# ============================
# Process Region 1
#
def process_trmm_d03_file():
	process_trmm_region("d03")
		
# ===============================================================
# Process All TRMM files from that day to get 24hr accumulation
#
def	process_trmm_files():
	if verbose:
		print "process_trmm_files..."
	
	generate_24h_accumulation()
	#process_trmm_d02_file()
	process_trmm_d03_file()
	
# ======================================================================
# Make sure directories exist
#
def checkdirs():
		
	if not os.path.exists(trmm_3B42RT_dir):
	    os.makedirs(trmm_3B42RT_dir)

	if not os.path.exists(trmm_d02_dir):
	    os.makedirs(trmm_d02_dir)

	if not os.path.exists(trmm_d03_dir):
	    os.makedirs(trmm_d03_dir)
		
	if not os.path.exists(trmm_dir):
	    os.makedirs(trmm_dir)
		
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
	apg_input.add_argument("-f", "--force", action='store_true', help="HydroSHEDS forces new water image to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose

	checkdirs()
	
	get_daily_trmm_files()
	process_trmm_files()
	print "Done."