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
hour		= config.hour

# but we need to get the day before
today		= date(year,month, day)
today		-= timedelta(1)

year		= today.year
month		= today.month
day			= today.day
ym	 		= "%s%02d" % (year, month)

ftp_site 	= "trmmopen.gsfc.nasa.gov"
path	 	= "pub/merged/3B42RT/"
force		= 0
verbose		= 0
	
file_00 = "3B42RT.%04d%02d%02d00.7.bin.gz"%(year, month, day)
file_03 = "3B42RT.%04d%02d%02d03.7.bin.gz"%(year, month, day)
file_06 = "3B42RT.%04d%02d%02d06.7.bin.gz"%(year, month, day)
file_09 = "3B42RT.%04d%02d%02d09.7.bin.gz"%(year, month, day)
file_12 = "3B42RT.%04d%02d%02d12.7.bin.gz"%(year, month, day)
file_15 = "3B42RT.%04d%02d%02d15.7.bin.gz"%(year, month, day)
file_18 = "3B42RT.%04d%02d%02d18.7.bin.gz"%(year, month, day)
file_21 = "3B42RT.%04d%02d%02d21.7.bin.gz"%(year, month, day)
		
trmm_files = [file_00, file_03, file_06, file_09, file_12, file_15, file_18, file_21]

# Set file vars
delete_files 		= os.path.join(config.data_dir,"trmm", "trmm_24*")
output_file 		= os.path.join(config.data_dir,"trmm", "trmm_24_%s_4326.tif" % ym)
#color_file 			= os.path.join(".", "rainfall_colors.txt")
color_file 			= os.path.join(".", "rain.txt")
rgb_output_file 	= os.path.join(config.data_dir,"trmm", "trmm_24_%s_4326_rgb.tif"% ym)

def get_latest_trmm_file():
	#now 	= datetime.today()

	hour	= 6	#int((now.hour-1)/3 )*3
	
	filename 	= "3B42RT.%04d%02d%02d%02d.7.bin.gz"%(year, month, day, hour)
	print filename
	
	local_filename = os.path.join(config.data_dir,"trmm", filename)
	if not os.path.exists( local_filename ):
		ftp = FTP(ftp_site)
		ftp.login()               					# user anonymous, passwd anonymous@
		ftp.cwd("pub/merged/3B42RT/")
		file = open(local_filename, 'wb')
		ftp.retrbinary("RETR " + filename, file.write)
		file.close()
		ftp.quit()
	
	return filename
	
# ===============================================================
# Get All TRMM files from that day
#			
def get_daily_trmm_files():
	print("Checking "+ftp_site+" for latest file...")
	ftp = FTP(ftp_site)

	ftp.login()               					# user anonymous, passwd anonymous@
	ftp.cwd("pub/merged/3B42RT/")

	for f in trmm_files:
		local_filename = os.path.join(config.data_dir, "trmm", f)
		if not os.path.exists(local_filename):
			print "Downloading it...", f
			file = open(local_filename, 'wb')
			try:
				ftp.retrbinary("RETR " + f, file.write)
				file.close()
			except:
				print "FTP Error", sys.exc_info()[0]
				os.remove(local_filename)
				sys.exit(1)
	ftp.quit()

def process_latest_trmm_region(dx, dt):
	region 				= config.regions[dx]
	bbox				= region['bbox']
	tzoom               = region['tiles-zoom']
    
	#color_file 			= os.path.join(".", "rainfall_colors.txt")
	color_file 			= os.path.join(".", "rain.txt")
	output_file 		= os.path.join(config.data_dir,"trmm",dx,"trmm_3B42RT_%s_4326.tif" % dt)
	subset_file 		= os.path.join(config.data_dir,"trmm",dx,"trmm_3B42RT_%s_%s_subset_4326.tif" % (dt,dx))
	subset_rgb_file 	= os.path.join(config.data_dir,"trmm",dx,"trmm_3B42RT_%s_%s_subset_4326_rgb.tif" % (dt,dx))
	resampled_file 		= os.path.join(config.data_dir,"trmm",dx,"trmm_3B42RT_%s_%s_subset_4326_1km.tif" % (dt,dx))
	resampled_rgb_file 	= os.path.join(config.data_dir,"trmm",dx,"trmm_3B42RT_%s_%s_subset_4326_1km_rgb.tif" % (dt,dx))
	
	mbtiles_dir			= os.path.join(config.data_dir,"mbtiles", "trmm_3B42RT_%s_%s" % (dx, dt))
	mbtiles_fname 		= mbtiles_dir + ".mbtiles"

	# subset it to our BBOX
	# use ullr
	if force or not os.path.exists(subset_file):
		lonlats	= "" + str(bbox[0]) + " " + str(bbox[3]) + " " + str(bbox[2]) + " " + str(bbox[1])	
		cmd 	= "gdal_translate -q -projwin " + lonlats +" "+ output_file+ " " + subset_file
		if verbose:
			print cmd
		os.system(cmd)
	
	# color it using colormap
	#cmd = "gdaldem color-relief -q -alpha "+ subset_file+ " " + color_file + " " + subset_rgb_file
	#print cmd
	#os.system(cmd)

	# resample it at 1km and reproject for mbtiles
	if force or not os.path.exists(resampled_file):
		cmd = "gdalwarp -overwrite -q -tr 0.008999 0.008999 -r cubicspline -co COMPRESS=LZW -cblend 5 " + subset_file + " " + resampled_file
		if verbose:
			print cmd
		os.system(cmd)

	# color it using colormap
	if force or not os.path.exists(resampled_rgb_file):
		cmd = "gdaldem color-relief -q -alpha " + resampled_file + " " + color_file + " " + resampled_rgb_file
		if verbose:
			print cmd
		os.system(cmd)	

	# mbtiles
	# https://github.com/developmentseed/gdal2mb	
	if force or not os.path.exists(mbtiles_dir):
		cmd = "./gdal2tiles.py -z "+tzoom+" --s_srs=EPSG:4326 " + resampled_rgb_file  + " " + mbtiles_dir
		if verbose:
			print cmd
		os.system(cmd)

	if force or not os.path.exists(mbtiles_fname):
		# generate metadata.json
		metafile = os.path.join(mbtiles_dir, "metadata.json")
		json = "{\n"
		json += "  \"name\": \"TRMM 24hr Precipitation - "+ dt + "\",\n"
		json += "  \"description\": \"TRMM\",\n"
		json += "  \"version\": 1\n"
		json += "}"
		f = open(metafile, "w")
		f.write(json)
		f.close()
			
		cmd = "./mb-util " + mbtiles_dir  + " " + mbtiles_fname
		if verbose:
			print cmd
		os.system(cmd)

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
	
def process_latest_trmm_d02_file(dt):
	process_latest_trmm_region("d02", dt)

def process_latest_trmm_d03_file(dt):
	process_latest_trmm_region("d03", dt)
	
#
# Process most recent TRMM file
#
def	process_latest_trmm_file( filename ):
	arr             = filename.split('.')
	dt	            =  arr[1]
	region 			= config.regions['global']
	tzoom           = region['tiles-zoom']
	local_filename 	= os.path.join(config.data_dir, "trmm", filename)
    
	if verbose:
		print "processing:", local_filename
	
	farr 			= filename.split('.')
	baseName		= "%s_%s" % (farr[0], farr[1])
	
	trmm_file 	= TRMM3B42RTFile(local_filename)
	precip 		= trmm_file.precip()

	print 'TRMM precip max:', precip.max()
	print 'TRMM precip min:', precip.min()
	print 'TRMM precip mean:', precip.mean()
	print 'TRMM precip std-dev:', precip.std()
		
	nrows 	= precip.shape[0]
	ncols 	= precip.shape[1]	 

	y 		= 60	
	x 		= -180		
	res 	= 0.25

	# Set file vars
	delete_files 		= os.path.join(config.data_dir,"trmm", "trmm_3B42RT_*")

	output_file 		= os.path.join(config.data_dir,"trmm","trmm_3B42RT_%s_4326.tif" % dt)
	blended_file 		= os.path.join(config.data_dir,"trmm","trmm_3B42RT_%s_4326_blended.tif" % dt)
	blended_rgb_file	= os.path.join(config.data_dir,"trmm","trmm_3B42RT_%s_4326_blended_rgb.tif" % dt)
	mbtiles_dir 		= os.path.join(config.data_dir,"mbtiles","trmm_3B42RT_%s" % dt)
	mbtiles_fname 		= mbtiles_dir + ".mbtiles"

	if force:
		cmd 	= "rm " + delete_files
		if verbose:
			print cmd
		os.system(cmd)

	if force or not os.path.exists(output_file):
		# Create gtif
		driver = gdal.GetDriverByName("GTiff")
		dst_ds = driver.Create(output_file, ncols, nrows, 1, gdal.GDT_Float32 )

		# top left x, w-e pixel resolution, rotation, top left y, rotation, n-s pixel resolution
		dst_ds.SetGeoTransform( [ x, res, 0, y, 0, -res ] )
  
		# set the reference info 
		srs = osr.SpatialReference()
		srs.SetWellKnownGeogCS("WGS84")
		dst_ds.SetProjection( srs.ExportToWkt() )

		# write the band
		band = dst_ds.GetRasterBand(1)
		band.SetNoDataValue(-31999)
		band.WriteArray(precip)
		dst_ds = None
	
	# blend it
	if force or not os.path.exists(blended_file):
		cmd = "gdalwarp -overwrite -q -r cubicspline -co COMPRESS=LZW -cblend 5 " + output_file + " " + blended_file
		if verbose:
			print cmd
		os.system(cmd)

	# color it using colormap
	if force or not os.path.exists(blended_rgb_file):
		cmd = "gdaldem color-relief -q -alpha " + blended_file + " " + color_file + " " + blended_rgb_file
		if verbose:
			print cmd
		os.system(cmd)

	return
	# Create mbtiles
	if force or not os.path.exists(mbtiles_fname):			
		cmd = "./gdal2tiles.py -z "+ tzoom + " " + blended_rgb_file  + " " + mbtiles_dir
		if verbose:
			print cmd
		os.system(cmd)

		# generate metadata.json
		metafile = os.path.join(mbtiles_dir, "metadata.json")
		json = "{\n"
		json += "  \"name\": \"TRMM 24hr Precipitation - "+ ym + "\",\n"
		json += "  \"description\": \"TRMM\",\n"
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
			
	process_latest_trmm_d02_file(dt)
	process_latest_trmm_d03_file(dt)

#
# Generate the global 24hr Rainfall Accumulation File
#
def generate_24h_accumulation():		
	
	for f in trmm_files:
		local_filename = os.path.join(config.data_dir, "trmm", f)

		trmm_file 	= TRMM3B42RTFile(local_filename)
		precip 		= trmm_file.precip()

		#print f
		#print 'TRMM precip max:', precip.max()
		#print 'TRMM precip min:', precip.min()
		#print 'TRMM precip mean:', precip.mean()
		#print 'TRMM precip std-dev:', precip.std()

		if f == file_00:
			data = precip
		else:
			data += precip
		
	print "data:", data.min(), data.mean(), data.max(), data.std()
	
	nrows 	= precip.shape[0]
	ncols 	= precip.shape[1]	 

	y 		= 60	
	x 		= -180		
	res 	= 0.25

	if force:
		cmd 	= "rm " + delete_files
		if verbose:
			print cmd
		os.system(cmd)

	if verbose:
		print "Creating:", output_file
	
	driver = gdal.GetDriverByName("GTiff")
	dst_ds = driver.Create(output_file, ncols, nrows, 1, gdal.GDT_Float32 )

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
	
	# color it using colormap for testing
	cmd = "gdaldem color-relief -q -alpha "+output_file+" " + color_file + " " + rgb_output_file
	if verbose:
		print cmd
	os.system(cmd)
	
#
# Subset 24hr Rainfall Accumulation and resample for specific region
#
def process_trmm_region( dx ):
	region 	= config.regions[dx]
	bbox	= region['bbox']
	tzoom   = region['tiles-zoom']
    
	if verbose:
		print "process_trmm_region:", dx

	resampled_file 		= os.path.join(config.data_dir,"trmm", dx, "trmm_24_%s_%s_4326_1km.tif" % (dx,ym))
	subset_file 		= os.path.join(config.data_dir,"trmm", dx, "trmm_24_%s_%s_subset_4326.tif" % (dx,ym))
	subset_rgb_file 	= os.path.join(config.data_dir,"trmm", dx, "trmm_24_%s_%s_subset_4326_rgb.tif" % (dx,ym))
	mbtiles_dir			= os.path.join(config.data_dir,"mbtiles", "trmm_24_%s_%s%02d00" % (dx, ym, day))
	mbtiles_fname 		= mbtiles_dir +".mbtiles"
	
	# resample it at 1km for that bbox
	if force or not os.path.exists(subset_file):
		lonlats	= "%f %f %f %f" % ( bbox[0], bbox[1], bbox[2], bbox[3])
		
		cmd = "gdalwarp -overwrite -q -tr 0.008999 0.008999 -r cubicspline -co COMPRESS=LZW -cblend 5 -te %s %s %s" % (lonlats, output_file, subset_file)
		if verbose:
			print cmd
		os.system(cmd)

	# subset it to our BBOX  projwin ulx uly lrx lry
	#if force or not os.path.exists(subset_file):
	#	lonlats	= "" + str(bbox[0]) + " " + str(bbox[3]) + " " + str(bbox[2]) + " " + str(bbox[1])
	#	cmd 	= "gdal_translate -q -projwin " + lonlats +" "+ resampled_file + " " + subset_file
	#	if verbose:
	#		print cmd
	#	os.system(cmd)

	# color it using colormap
	#cmd = "gdaldem color-relief -q -alpha "+ subset_file+ " " + color_file + " " + subset_rgb_file
	#print cmd
	#os.system(cmd)

		
	# color it using colormap
	if force or not os.path.exists(subset_rgb_file):
		cmd = "gdaldem color-relief -q -alpha " + subset_file + " " + color_file + " " + subset_rgb_file
		if verbose:
			print cmd
		os.system(cmd)
		
	if force or not os.path.exists(mbtiles_fname):			
		cmd = "./gdal2tiles.py -z " + tzoom + " " + subset_rgb_file  + " " + mbtiles_dir
		if verbose:
			print cmd
		os.system(cmd)

		# generate metadata.json
		metafile = os.path.join(mbtiles_dir, "metadata.json")
		json = "{\n"
		json += "  \"name\": \"TRMM 24hr Accumulation - "+ ym + "\",\n"
		json += "  \"description\": \"TRMM\",\n"
		json += "  \"version\": 1\n"
		json += "}"
		f = open(metafile, "w")
		f.write(json)
		f.close()

		cmd = "./mb-util " + mbtiles_dir  + " " + mbtiles_fname
		if verbose:
			print cmd
		os.system(cmd)

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
		
def process_trmm_d02_file():
	process_trmm_region("d02")

def process_trmm_d03_file():
	process_trmm_region("d03")
		
# ===============================================================
# Process All TRMM files from that day to get 24hr accumulation
#
def	process_trmm_files():
	print "process_trmm_files..."
	
	generate_24h_accumulation()
	process_trmm_d02_file()
	process_trmm_d03_file()

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


	get_daily_trmm_files()
	process_trmm_files()
	
	latest_file = get_latest_trmm_file()
	process_latest_trmm_file( latest_file)
	
	#process_trmm_file("3B42RT.2013093021.7.bin.gz")