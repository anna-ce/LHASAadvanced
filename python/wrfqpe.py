#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Requirements:
#	gdal, numpy pytrmm...
#
# Access and Process MSFC WRF QPE
#
import numpy, os, sys, inspect
from osgeo import osr, gdal
from ftplib import FTP
from datetime import date
import warnings
from gzip import GzipFile
import pygrib
import pyproj
import argparse

# Site configuration
import config

year		= config.year
month		= config.month
day			= config.day
ym	 		= "%s%02d" % (year, month)

#year 		= 2013
#month		= 10
#day		= 1

ftp_site 	= "ftp.nsstc.org"
path		= "outgoing/molthan/%d%02d%02d06/grib1"%(year,month, day)
force		= 0
verbose		= 0

def process_wrf_d01_file():
	filename = get_wrf_file("d01", 24)
	process_wrf_file("d01", filename)
	
def process_wrf_d02_file():
	filename =  get_wrf_file("d02", 24)
	process_wrf_file("d02", filename)
	
def process_wrf_d03_file():
	filename =  get_wrf_file("d03", 24)
	process_wrf_file("d03", filename)

def get_wrf_file( dx, fcst ):
	yy 			= year - 2000
	hr			= 0
	download 	= "%02d%02d%02d0600_arw_%s.grb1f%02d%04d"%(yy,month,day,dx,fcst,hr)
		
	local_filename = os.path.join(config.data_dir, "wrf", download)
	if os.path.exists(local_filename):
		return local_filename
	else:
		print "Downloading to...", local_filename
		file = open(local_filename+".gz", 'wb')
	
		ftp.retrbinary("RETR " + download+".gz", file.write)
		ftp.quit()
		file.close()
		
		# decompress it
		cmd = "gzip -d "+local_filename+".gz"
		print cmd
		err = os.system(cmd)
		if err:
			print err
			sys.exit(err)
		
		return local_filename
		
def process_wrf_file(dx, file_name):
	print "Processing:"+file_name+" for "+ dx

	grbs 	    = pygrib.open(file_name)
	
	grba		= grbs.select(name='Total Precipitation')
	grb			= grba[0]
	data 		= grb['values']
	lats, lons 	= grb.latlons()
	
	region		= config.regions[dx]
	tzoom       = region['tiles-zoom']
	grbstr 	    = "%s" % grb	
	arr 	    = grbstr.split(':')
	id 		    = arr[0]
	
	#print grb
	#print 'shape/min/max data %s %6.2f %6.2f'%(str(data.shape),data.min(),data.max())
	#print str('min/max of %d lats on %s grid %4.2f %4.2f' % (grb['Nj'], grb['typeOfGrid'],lats.min(),lats.max()))
	#print str('min/max of %d lons on %s grid %4.2f %4.2f' % (grb['Ni'], grb['typeOfGrid'],lons.min(),lons.max()))
	#grbs.close()
	
	# Set file vars
	delete_files 		= os.path.join(config.data_dir,"wrf", "wrf_precip_out_*")
	output_file 		= os.path.join(config.data_dir,"wrf","wrf_precip_out_"+dx+"_lambert.tif")
	rgb_output_file 	= os.path.join(config.data_dir,"wrf","wrf_precip_out_"+dx+"lambert_rgb.tif")
	
	reproj_file 		= os.path.join(config.data_dir,"wrf","wrf_precip_out_"+dx+"4326.tif")
	reproj_rgb_file 	= os.path.join(config.data_dir,"wrf","wrf_precip_out_"+dx+"4326_rgb.tif")
	
	color_file 			= os.path.join(config.data_dir,"wrf_colors.txt")
	resampled_file 		= os.path.join(config.data_dir,"wrf","wrf_precip_out_"+dx+"4326_1km.tif")
	resampled_rgb_file 	= os.path.join(config.data_dir,"wrf","wrf_precip_out_"+dx+"4326_1km_rgb.tif")
	
	mbtiles_dir			= os.path.join(config.data_dir,"mbtiles", "wrf_precip_%s_%s%02d00" % (dx, ym, day))
	mbtiles_fname 		= mbtiles_dir+".mbtiles"
	
	cmd = "rm "+delete_files
	if verbose:
		print cmd
	os.system(cmd)
	
	# generate lambert conformant conic
	if force or not os.path.exists(output_file):			
		cmd = "gdal_translate -q -b %s %s %s" %(id, file_name, output_file)
		if verbose:
			print cmd
		os.system(cmd)
	
	# reproject to 4326
	if force or not os.path.exists(reproj_file):			
		cmd = "gdalwarp -q -t_srs EPSG:4326 " + output_file + " " + reproj_file
		if verbose:
			print cmd
		os.system(cmd)

	# color it using colormap
	#cmd = "gdaldem color-relief -q -alpha "+reproj_file+" " + color_file + " " + reproj_rgb_file
	#print cmd
	#os.system(cmd)
			
	# resample it at 1km
	if force or not os.path.exists(resampled_file):			
		cmd = "gdalwarp -q -tr 0.008999 0.008999 -r cubic " + reproj_file + " " + resampled_file
		if verbose:
			print cmd
		os.system(cmd)
	
	# color it
	if force or not os.path.exists(resampled_rgb_file):			
		cmd = "gdaldem color-relief -q -alpha " + resampled_file + " " + color_file + " " + resampled_rgb_file
		print cmd
		os.system(cmd)
	
	# mbtiles
	
	if force or not os.path.exists(mbtiles_fname):			
		cmd = "./gdal2tiles.py -z "+tzoom+" --s_srs=EPSG:4326 " + resampled_rgb_file  + " " + mbtiles_dir
		if verbose:
			print cmd
		os.system(cmd)

		# generate metadata.json
		metafile = os.path.join(mbtiles_dir, "metadata.json")
		json = "{\n"
		json += "  \"name\": \"Precipitation Forecast - "+ ym + "\",\n"
		json += "  \"description\": \"WRF Forecast - "+ os.path.basename(file_name)+"\",\n"
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
	print "Copy to S3 "+ mbtiles_fname
	region		= config.regions[dx]
	bucketName 	= region['bucket']
		
	cmd = "./aws-copy.py --bucket "+bucketName+ " --file " + mbtiles_fname
	if verbose:
		cmd += " --verbose "
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
	apg_input.add_argument("-f", "--force", action='store_true', help="HydroSHEDS forces new water image to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	options = parser.parse_args()

	force		= options.force
	verbose		= options.verbose
	
	print("Checking "+ ftp_site + " for latest file...")
	ftp = FTP(ftp_site)

	ftp.login()               					# user anonymous, passwd anonymous@
	print("cwd to "+path)
	ftp.cwd(path)
	
	#process_wrf_wrf_d01_file
	#process_wrf_d02_file()
	process_wrf_d03_file()
	
	
