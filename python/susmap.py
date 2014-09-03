#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
#
# Processes the susceptibility map from Thomas Stanly
#

import sys, os, inspect
import argparse
from osgeo import osr, gdal

# Site configuration
import config

verbose = 1
force 	= 1

def execute( cmd ):
	if verbose:
		print cmd
	os.system(cmd)
	
def generate_map( dx ):
	# make sure it exists
	region		= config.regions[dx]
	
	if verbose:
		print "Processing Susceptibility Map for Region:", dx, region['name']	
	
	color_file				= os.path.join("./cluts", 	"susmap_colors2.txt")
	basedir					= "susmap.2"
	
	input_file				= os.path.join(config.data_dir, basedir, "susmap_"+ dx + ".tif")
	input_file_warped		= os.path.join(config.data_dir, basedir, "susmap_"+ dx + "_warped.tif")
	rgb_output_file			= os.path.join(config.data_dir, basedir, "susmap_"+ dx + "_rgb.tif")
	output_file_shp			= os.path.join(config.data_dir, basedir, "susmap_"+ dx + ".shp")
	output_file_geojson		= os.path.join(config.data_dir, basedir, "susmap_"+ dx + ".geojson")
	output_file_topojson	= os.path.join(config.data_dir, basedir, "susmap_"+ dx + ".topojson")
	mbtiles_dir				= os.path.join(config.data_dir, basedir, "mbtiles_"+ dx)
	mbtiles_fname 			= os.path.join(config.data_dir, basedir, "susmap_"+ dx + ".mbtiles")
	
	# get raster size
	src_ds 			= gdal.Open( input_file )
	ncols 			= src_ds.RasterXSize
	nrows 			= src_ds.RasterYSize
	
	xres	 		= ncols * 10
	
	region			= config.regions[dx]
	tzoom			= region['tiles-zoom']

	# increase resolution by 100 and do cubic spline interpolation to smooth the rater
	if force or not os.path.exists(input_file_warped):		
		cmd = "gdalwarp -ts "+ str(xres) + " 0 -r cubicspline -multi -co 'TFW=YES' " + input_file + " " + input_file_warped
		execute(cmd)
	
	# colorize interpolated raster
	if force or not os.path.exists(rgb_output_file):		
		cmd = "gdaldem color-relief -alpha -of GTiff "+input_file_warped+" " + color_file + " " + rgb_output_file
		execute(cmd)

	# generate mbtiles
	if force or not os.path.exists(mbtiles_fname):		
		cmd = "./gdal2tiles.py -z "+ tzoom + " " + rgb_output_file  + " " + mbtiles_dir
		execute(cmd)

		cmd = "./mb-util " + mbtiles_dir  + " " + mbtiles_fname
		execute(cmd)

	# copy mbtiles to S3
	if force or not os.path.exists(mbtiles_fname):
		bucketName = region['bucket']
		cmd = "aws-copy.py --bucket "+bucketName+ " --file " + mbtiles_fname
		if verbose:
			cmd += " --verbose "
		execute(cmd)

		cmd = "rm -rf "+ mbtiles_dir
		execute(cmd)
				
	if 0:
		cmd = "gdal_contour -a risk " + rgb_output_file+ " "+ output_file_shp + " -i 1"
		if verbose:
			print cmd
		os.system(cmd)

		cmd = "ogr2ogr -f GeoJSON "+ output_file_geojson + " " + output_file_shp
		if verbose:
			print cmd
		os.system(cmd)
	
		cmd = "topojson -o "+ output_file_topojson + " " + output_file_geojson
		if verbose:
			print cmd
		os.system(cmd)
	
	
# =======================================================================
# Main
#
if __name__ == '__main__':
	#version_num = int(gdal.VersionInfo('VERSION_NUM'))
	#if version_num != 1920: # because of GetGeoTransform(can_return_null)
	#	print('ERROR: Python bindings of GDAL 1.9.2 required', version_num)
	#	sys.exit(1)

	generate_map('d03')
	generate_map('d02')
	print "Done."
