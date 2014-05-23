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
ymd 		= config.ymd

#year 		= 2013
#month		= 10
#day		= 1

protocol	= "ftp://"
ftp_site 	= "ftp.nsstc.org"
path		= "outgoing/molthan/%d%02d%02d06/grib1"%(year,month, day)
force		= 0
verbose		= 0

def execute(cmd):
	if(verbose):
		print cmd
	os.system(cmd)
	
def process_wrf_d01_file():
	filename = get_wrf_file("d01", 24)
	process_wrf_file("d01", filename)
	
def process_wrf_d02_file():
	filename =  get_wrf_file("d02", 24)
	process_wrf_file("d02", filename)
	
def process_wrf_d03_file():
	filename =  get_wrf_file("d03", 24)
	process_wrf_file("d03", filename)

#
# Grab the 24hr forecast file that contains the 24hr accumulation
#
def get_wrf_file( dx, fcst ):
	yy 			= year - 2000
	hr			= 0
	download 	= "%02d%02d%02d0600_arw_%s.grb1f%02d%04d"%(yy,month,day,dx,fcst,hr)
		
	local_filename = os.path.join(config.data_dir, "wrf", ymd, download)
	if os.path.exists(local_filename):
		if verbose:
			print "Download file exists:", local_filename
		return local_filename
	else:
		if verbose:
			print "Downloading %s to %s" %( protocol+ftp_site+path+"/"+download, local_filename)
		
		file = open(local_filename+".gz", 'wb')
	
		ftp.retrbinary("RETR " + download+".gz", file.write)
		file.close()
		
		# decompress it
		cmd = "gzip -d "+local_filename+".gz"
		if verbose:
			print cmd
		err = os.system(cmd)
		if err:
			print err
			sys.exit(err)
		
		return local_filename
		
def process_wrf_file(dx, file_name):
	if verbose:
		print "Processing:"+file_name+" for "+ dx

	grbs 	    = pygrib.open(file_name)
	
	grba		= grbs.select(name='Total Precipitation')
	grb			= grba[0]
	data 		= grb['values']
	lats, lons 	= grb.latlons()
	
	print "grb:", grb
	
	region		= config.regions[dx]	
	pxsize		= region['pixelsize']
	tzoom       = region['tiles-zoom']
	bbox		= region['bbox']
	thn_width   = region['thn_width']
	thn_height  = region['thn_height']
	bucketName 	= region['bucket']
	
	grbstr 	    = "%s" % grb	
	arr 	    = grbstr.split(':')
	id 		    = arr[0]
	
	#print grb
	#print 'shape/min/max data %s %6.2f %6.2f'%(str(data.shape),data.min(),data.max())
	#print str('min/max of %d lats on %s grid %4.2f %4.2f' % (grb['Nj'], grb['typeOfGrid'],lats.min(),lats.max()))
	#print str('min/max of %d lons on %s grid %4.2f %4.2f' % (grb['Ni'], grb['typeOfGrid'],lons.min(),lons.max()))
	grbs.close()
	
	# Set file vars
	output_file 		= os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_"+dx+"_"+ymd+"_lambert.tif")
	rgb_output_file 	= os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_"+dx+"_"+ymd+"_lambert_rgb.tif")
	
	reproj_file 		= os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_"+dx+"_"+ymd+"_4326.tif")
	reproj_rgb_file 	= os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_"+dx+"_"+ymd+"_4326_rgb.tif")
	
	color_file 			= os.path.join("cluts", "green-blue-gr.txt")
	
	resampled_file 		= os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_"+dx+"_"+ymd+"_4326_1km.tif")
	resampled_rgb_file 	= os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_"+dx+"_"+ymd+"_4326_1km_rgb.tif")
		
	shp_file 			= os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_"+dx+"_"+ymd+"_4326_1km.shp")
	geojson_file 		= os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_"+dx+"_"+ymd+"_4326_1km.geojson")
	topojson_file		= os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_"+dx+"_"+ymd+".topojson")
	topojson_gz_file	= os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_"+dx+"_"+ymd+".topojson.gz")
	thumbnail_file 		= os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_%s_%s.thn.png" % (dx,ymd))
	
	static_file 		= os.path.join(config.data_dir,"wrf", dx, "%s_static.tiff" % (dx))

	
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
		cmd = "gdalwarp -q -tr %f %f -te %f %f %f %f -r cubicspline %s %s" % (pxsize,pxsize,bbox[0], bbox[1], bbox[2], bbox[3],reproj_file,resampled_file)
		if verbose:
			print cmd
		os.system(cmd)
	
	# color it
	if force or not os.path.exists(resampled_rgb_file):			
		cmd = "gdaldem color-relief -q -alpha " + resampled_file + " " + color_file + " " + resampled_rgb_file
		if verbose:
			print cmd
		os.system(cmd)
	
	if force or not os.path.exists(shp_file):
		cmd = "gdal_contour -q -a forecast -fl 2 -fl 3 -fl 5 -fl 13 -fl 21 -fl 34 -fl 55 -fl 89 -fl 144 %s %s" % ( resampled_file, shp_file )
		execute(cmd)
	
	if force or not os.path.exists(geojson_file):
		cmd = "ogr2ogr -f geoJSON %s %s" %( geojson_file, shp_file) 
		execute(cmd)
	
	if force or not os.path.exists(topojson_file):
		forecast 	= "precip_forecast_%s_%s" % (dx, ymd)
		cmd 		= "topojson --simplify-proportion 0.5  --bbox -p forecast -o %s -- %s=%s" % (topojson_file, forecast, geojson_file ) 
		execute(cmd)
	
	if force or not os.path.exists(topojson_gz_file):
		if( force ):
			execute("rm -f "+topojson_file)
			
		cmd = "gzip %s" % (topojson_file)
		execute(cmd)
	
	tmp_file = thumbnail_file + ".tmp.tif"
	if force or not os.path.exists(thumbnail_file):
		cmd="gdalwarp -overwrite -q -multi -ts %d %d -r cubicspline -co COMPRESS=LZW %s %s" % (thn_width, thn_height, resampled_rgb_file, tmp_file )
		execute(cmd)
		cmd = "composite -blend 60 %s %s %s" % ( tmp_file, static_file, thumbnail_file)
		execute(cmd)
		execute("rm "+tmp_file)
		
	cmd = "./aws-copy.py --bucket " + bucketName + " --folder " + ymd + " --file " + topojson_gz_file
	if verbose:
		cmd += " --verbose"
	execute(cmd)

	cmd = "./aws-copy.py --bucket " + bucketName + " --folder " + ymd + " --file " + thumbnail_file
	if verbose:
		cmd += " --verbose"
	execute(cmd)
	
	delete_files = [
		os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_%s_%s_4326.tif" % (dx,ymd)),
		os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_%s_%s_4326_1km.dbf" % (dx,ymd)),
		os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_%s_%s_4326_1km.prj" % (dx,ymd)),
		os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_%s_%s_4326_1km.shp" % (dx,ymd)),
		os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_%s_%s_4326_1km.shx" % (dx,ymd)),
		os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_%s_%s_4326_1km.geojson" % (dx,ymd)),
		#os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_%s_%s.topojson" % (dx,ymd)),
		os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_%s_%s_4326_1km_rgb.tif" % (dx,ymd)),
		os.path.join(config.data_dir,"wrf", dx, ymd, "wrf_24_%s_%s_lambert.tif" % (dx,ymd))
	]
	
	if not verbose:		# probably debugging, so do not dispose of artifacts
		cmd = "rm "+ " ".join(delete_files)
		execute(cmd)
	
	
def checkdirs():
		
	# required directories
	wrf_d03_dir		=  os.path.join(config.data_dir,"wrf","d02", ymd)
	wrf_d02_dir		=  os.path.join(config.data_dir,"wrf","d03", ymd)
	wrf_dir			=  os.path.join(config.data_dir,"wrf", ymd)

	if not os.path.exists(wrf_dir):
	    os.makedirs(wrf_dir)

	if not os.path.exists(wrf_d02_dir):
	    os.makedirs(wrf_d02_dir)

	if not os.path.exists(wrf_d03_dir):
	    os.makedirs(wrf_d03_dir)
		
	
#
# ======================================================================
#
if __name__ == '__main__':
	version_num = int(gdal.VersionInfo('VERSION_NUM'))
	if version_num < 1800: # because of GetGeoTransform(can_return_null)
		print('ERROR: Python bindings of GDAL 1.8.0 or later required')
		sys.exit(1)
	
	parser 		= argparse.ArgumentParser(description='WRF Processing')
	apg_input 	= parser.add_argument_group('Input')

	apg_input.add_argument("-f", "--force", action='store_true', help="HydroSHEDS forces new water image to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	options = parser.parse_args()

	force		= options.force
	verbose		= options.verbose
	
	checkdirs()
	
	if verbose:
		print("Checking "+ ftp_site + " for latest file...")

	ftp = FTP(ftp_site)

	ftp.login()               					# user anonymous, passwd anonymous@
	if verbose:
		print("cwd to "+path)
	ftp.cwd(path)
	
	#process_wrf_d02_file()
	process_wrf_d03_file()
	ftp.quit()
	
	
