#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Requirements:
#	gdal, numpy pytrmm...
#
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
from osgeo.gdalconst import GA_Update

# Site configuration
import config

protocol	= "ftp://"
ftp_site 	= "hrsl.arsusda.gov"
path		= "pub/jbolten/FAS/L03"
force		= 1
verbose		= 1

color_file 			= os.path.join("cluts", "smos.txt")

def execute(cmd):
	if(verbose):
		print cmd
	os.system(cmd)

def process_d02_file(fname):
	process_regional_file("d02",fname)
	
def process_d03_file(fname):
	process_regional_file("d03",fname)

def process_smos_region_subset(global_file, bbox, subset_file, clut_file, rgb_subset_file):
	if force or not os.path.exists(subset_file):
		cmd = "gdalwarp -overwrite -q -co COMPRESS=LZW -te %f %f %f %f %s %s" % (bbox[0], bbox[1], bbox[2], bbox[3], global_file, subset_file)
		execute(cmd)
		
	if force or not os.path.exists(rgb_subset_file):
		cmd = "gdaldem color-relief -q -alpha -of GTiff %s %s %s" % ( subset_file, clut_file, rgb_subset_file)
		execute(cmd)

def process_smos_region_upsample(pixelsize, bbox, subset_file, resampled_file, rgb_resampled_file, clut_file):
	if force or not os.path.exists(resampled_file):
		cmd = "gdalwarp -overwrite -q -tr %f %f -te %f %f %f %f -co COMPRESS=LZW %s %s" % (pixelsize,pixelsize,bbox[0], bbox[1], bbox[2], bbox[3], subset_file, resampled_file)
		execute(cmd)

	if force or not os.path.exists(rgb_resampled_file):
		cmd = "gdaldem color-relief -q -alpha -of GTiff %s %s %s" % ( resampled_file, clut_file, rgb_resampled_file)
		execute(cmd)

def process_smos_region_thumbnail(rgb_subset_file, thn_width, thn_height, static_file,  thumbnail_file):
	tmp_file = thumbnail_file + ".tmp.tif"
	if force or not os.path.exists(thumbnail_file):
		cmd="gdalwarp -overwrite -q -multi -ts %d %d -r cubicspline -co COMPRESS=LZW %s %s" % (thn_width, thn_height, rgb_subset_file, tmp_file )
		execute(cmd)
		cmd = "composite -quiet -blend 60 %s %s %s" % ( tmp_file, static_file, thumbnail_file)
		execute(cmd)
		execute("rm "+tmp_file)

def process_smos_region_topojson(dx, ymd, subset_file, supersampled_file, supersampled_rgb_file, pixelsize, bbox, shp_file, geojson_file, topojson_file, topojson_gz_file):
	# we need to resample even higher to improve resolution
	if 1 or force or not os.path.exists(supersampled_file):
		cmd = "gdalwarp -overwrite -tr %f %f -te %f %f %f %f -r cubicspline -co COMPRESS=LZW %s %s"%(pixelsize/10, pixelsize/10, bbox[0], bbox[1], bbox[2], bbox[3], subset_file, supersampled_file)
		execute(cmd)
	
	if 1 or force or not os.path.exists(supersampled_rgb_file):
		cmd = "gdaldem color-relief -q -alpha -of GTiff %s %s %s" % ( supersampled_file, color_file, supersampled_rgb_file)
		execute(cmd)
	
	if force or not os.path.exists(shp_file):
		cmd = "gdal_contour -q -a sm -fl 0.4 -fl 0.6 -fl 0.8 %s %s" % ( supersampled_file, shp_file )
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

def process_smos_region_to_s3( dx, ymd, thumbnail_file, topojson_gz_file):

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

def process_smos_region_cleanup(dx, ymd):
	if not verbose:			# probably debugging, so do not dispose of artifacts
		delete_files = [
		]
		#cmd = "rm "+ " ".join(delete_files)
		#execute(cmd)
		
		#print "Removed files"
		
def process_regional_file(dx, fname):
	region 		= config.regions[dx]
	bbox		= region['bbox']
	tzoom   	= region['tiles-zoom']
	pixelsize   = region['pixelsize']
	thn_width   = region['thn_width']
	thn_height  = region['thn_height']
    
	basename	= os.path.basename(fname)
	arr			= basename.split('.')
	ymd			= arr[0]
	
	if verbose:
		print "process region:", dx, basename, ymd

	file_dir	 			= os.path.join(config.data_dir,"smos", dx, ymd)
	
	if not os.path.exists(file_dir):
		os.mkdir(file_dir)
		
	subset_file 			= os.path.join(config.data_dir,"smos", dx, ymd, "sm_%s_%s.tif" % (dx,ymd))
	thumbnail_file 			= os.path.join(config.data_dir,"smos", dx, ymd, "sm_%s_%s.thn.png" % (dx,ymd))
	static_file 			= os.path.join(config.data_dir,"smos", dx, "%s_static.tiff" % (dx))
	rgb_subset_file			= os.path.join(config.data_dir,"smos", dx, ymd, "sm_%s_%s_rgb.tif" % (dx,ymd))
	resampled_file 			= os.path.join(config.data_dir,"smos", dx, ymd, "sm_%s_%s_1km.tif" % (dx,ymd))
	rgb_resampled_file 		= os.path.join(config.data_dir,"smos", dx, ymd, "sm_%s_%s_1km_rgb.tif" % (dx,ymd))
	supersampled_file	 	= os.path.join(config.data_dir,"smos", dx, ymd, "sm_%s_%s_100m.tif" % (dx,ymd))
	supersampled_rgb_file 	= os.path.join(config.data_dir,"smos", dx, ymd, "sm_%s_%s_100m_rgb.tif" % (dx,ymd))
	shp_file 				= os.path.join(config.data_dir,"smos", dx, ymd, "sm_%s_%s_1km.shp" % (dx,ymd))
	geojson_file 			= os.path.join(config.data_dir,"smos", dx, ymd, "sm_%s_%s_1km.geojson" % (dx,ymd))
	topojson_file			= os.path.join(config.data_dir,"smos", dx, ymd, "sm_%s_%s.topojson" % (dx,ymd))
	topojson_gz_file		= os.path.join(config.data_dir,"smos", dx, ymd, "sm_%s_%s.topojson.gz" % (dx,ymd))
	
	process_smos_region_subset(fname, bbox, subset_file, color_file, rgb_subset_file)
	process_smos_region_upsample(pixelsize, bbox, subset_file, resampled_file, rgb_resampled_file, color_file)
	process_smos_region_thumbnail( rgb_subset_file, thn_width, thn_height, static_file,  thumbnail_file)
	process_smos_region_topojson( dx, ymd, subset_file, supersampled_file, supersampled_rgb_file, pixelsize, bbox, shp_file, geojson_file, topojson_file, topojson_gz_file )
	
	#process_smos_region_to_s3( dx, ymd, thumbnail_file, topojson_gz_file)
	process_smos_region_cleanup(dx, ymd)

	
def process_file(fname, output_file):
	print "process_file", fname
	grbs 	= pygrib.open(fname)
	#region	= config.regions[dx]	
	
	#grbs.seek(0)
 	#for grb in grbs:
  	#  print grb 
  	#  print "Name:", grb.shortName
  	#  print "typeOfLevel:", grb.typeOfLevel

	grbs.seek(0)
	grbmsg = grbs.read(1)

	#grba		= grbs.select(name='1')
	#grb			= grba[0]
	#data 		= grb['values']
	#lats, lons 	= grb.latlons()
	
	print "grbmsg:", grbmsg[0]
	grb			= grbmsg[0]
	#data 		= grb['values']
	#lats, lons 	= grb.latlons()
	
	grbstr 	    = "%s" % grb	
	arr 	    = grbstr.split(':')
	id 		    = arr[0]
	
	print "id:", id
	print "grb:", grb
	#print "data", data
	#print "lat/lons", lats, lons
	#print lats.shape, lats.min(), lats.max(), lons.shape, lons.min(), lons.max()
	
	grbs.close()

	#output_file 		= fname+"_4326.tiff"
	output_rgb_file 	= fname+".rgb.tiff"
	
	#reproj_file		= fname+"_4326.tif"
	reproj_rgb_file	= fname+".rgb.tif"
	color_file 		= os.path.join("cluts", "smos.txt")
	
	#if force or not os.path.exists(output_file):			
	#	cmd = "gdal_translate -q -ot Byte -scale 0 1 0 255 -b %s %s %s" %(id, fname, output_file)
	#	execute(cmd)
	
	if force or not os.path.exists(output_file):			
		cmd = "gdal_translate -q -b %s %s %s" %(id, fname, output_file)
		execute(cmd)

	# we need to fix the projection
	# top left x, w-e pixel resolution, rotation, top left y, rotation, n-s pixel resolution
	y		= 90.0
	x		= -180.0
	res 	= 0.25
	
	dst_ds = gdal.Open( output_file, GA_Update )
	dst_ds.SetGeoTransform( [ x, res, 0, y, 0, -res ] )
  
	# set the reference info 
	srs = osr.SpatialReference()
	srs.SetWellKnownGeogCS("WGS84")
	dst_ds.SetProjection( srs.ExportToWkt() )
	dst_ds 	= None

	# reproject to 4326
	#if force or not os.path.exists(reproj_file):			
	#	cmd = "gdalwarp -q -t_srs EPSG:4326 " + output_file + " " + reproj_file
	#	execute(cmd)
		
	# color it using colormap
	if force or not os.path.exists(reproj_rgb_file):			
		cmd = "gdaldem color-relief -q -alpha "+output_file+" " + color_file + " " + output_rgb_file
		execute(cmd)
	
def checkdirs():
		
	# required directories
	smos_d03_dir		=  os.path.join(config.data_dir,"smos","d02")
	smos_d02_dir		=  os.path.join(config.data_dir,"smos","d03")
	smos_dir			=  os.path.join(config.data_dir,"smos")

	if not os.path.exists(smos_dir):
	    os.makedirs(smos_dir)

	if not os.path.exists(smos_d02_dir):
	    os.makedirs(smos_d02_dir)

	if not os.path.exists(smos_d03_dir):
	    os.makedirs(smos_d03_dir)

#
# ======================================================================
#
if __name__ == '__main__':
	
	parser 		= argparse.ArgumentParser(description='WRF Processing')
	apg_input 	= parser.add_argument_group('Input')

	apg_input.add_argument("-f", "--force", action='store_true', help="forces new product to be generated")
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
	filenames = []
	
	def getsmos(name):
		#print name
		if name.find(".as2.grib") > 0:
			filenames.append(name)
		
	ftp.retrlines('NLST', getsmos )

	download = filenames[len(filenames)-1]
	print "latest is: ", download
	
	#ftp.quit()

	#filename 			= "20140820_20140822/20140820_20140822.smp.grib"
	#outfile_name		= "20140820_20140822/20140820_20140822.smp.tif"
	
	folder = download.split(".")[0]
	local_folder 		= os.path.join(config.data_dir, "smos", folder)
	if not os.path.exists(local_folder):
		os.makedirs(local_folder)
	
	local_filename 		= os.path.join(local_folder, download)
	
	if not os.path.exists(local_filename):
		print "Downloading ", local_filename
		file = open(local_filename, 'wb')
		ftp.retrbinary("RETR " + download, file.write)
	else:
		print "Found", local_filename
		
	ftp.close()	
	output_filename 	= os.path.join(local_folder, download.replace(".grib",".tif"))
	
	process_file(local_filename, output_filename)
	process_d03_file(output_filename)
