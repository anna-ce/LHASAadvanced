#!/usr/bin/env python
#
# Created on 11/21/2013 Pat Cappelaere - Vightel Corporation
#
# Generates Current Landslide Estimate
#

import numpy, sys, os, inspect, urllib
import argparse

from osgeo import osr, gdal
from ftplib import FTP
from datetime import date, timedelta
from which import *

# Site configuration
import config

force 		= 0
verbose 	= 0

# Generate Curren
def build_tif(dx, region, dir):
	# Find the daily rainfall accumulation file for the area
	current_daily_rainfall 	= os.path.join(config.data_dir,"trmm", dx, "trmm_24_%s_%s_subset_4326.tif" % (dx,config.ymd))
	if not os.path.exists(current_daily_rainfall):
		print "**ERR: file not found", current_daily_rainfall
		
	# Find susceptibility map
	dem_slope_bin 	= os.path.join(config.data_dir, "susmap", dx, dx+"_dem_slope_bin.tif")
	if not os.path.exists(dem_slope_bin):
		print "**ERR: file not found", dem_slope_bin

	current_landslide_bin 		= os.path.join(config.data_dir, "landslide_estimate", dx, dx+"_current_landslide_%s.tif" %(config.ymd))
	current_landslide_bin_rgb 	= os.path.join(config.data_dir, "landslide_estimate", dx, dx+"_current_landslide_%s_rgb.tif" %(config.ymd))
	color_file					= "./cluts/landslide_colors.txt"
	
	mbtiles_dir					= os.path.join(config.data_dir,"mbtiles", "landslide_estimate_%s_%s" % (dx, config.ymd))
	mbtiles_fname 				= mbtiles_dir +".mbtiles"
	
	if force or not os.path.exists(current_landslide_bin):
		if verbose:
			"Processing current landslide model for %s..." % config.ymd
			
		if verbose:
			print "Loading ", dem_slope_bin
			
		smap_ds			= gdal.Open( dem_slope_bin )
		smap_ncols 		= smap_ds.RasterXSize
		smap_nrows 		= smap_ds.RasterYSize
		smap_band 		= smap_ds.GetRasterBand(1)
		smap_data 		= smap_band.ReadAsArray(0, 0, smap_ncols, smap_nrows )
		projection   	= smap_ds.GetProjection()
		geotransform 	= smap_ds.GetGeoTransform()
		
		if verbose:
			print "smap cols: %d rows %d"%(smap_ncols, smap_nrows)
			
		if verbose:
			print "Loading ", current_daily_rainfall
			
		rainfall_ds		= gdal.Open( current_daily_rainfall )
		rainfall_ncols 	= rainfall_ds.RasterXSize
		rainfall_nrows 	= rainfall_ds.RasterYSize
		rainfall_band 	= rainfall_ds.GetRasterBand(1)
		rainfall_data 	= rainfall_band.ReadAsArray(0, 0, rainfall_ncols, rainfall_nrows )

		if verbose:
			print "rainfall cols: %d rows %d"%(rainfall_ncols, rainfall_nrows)
		
		# wipe out where there is no risk
		rainfall_data[ numpy.where( smap_data < 1)] = 0

		# Set the thresholds based in rainfall limits
		rainfall_data[ numpy.where( rainfall_data > config.rainfall_red_limit)] 	= 4
		rainfall_data[ numpy.where( rainfall_data > config.rainfall_orange_limit)] 	= 3
		rainfall_data[ numpy.where( rainfall_data > config.rainfall_yellow_limit)] 	= 2
	
		# Write the file
		driver 			= gdal.GetDriverByName("GTiff")
		cur_ds 			= driver.Create(current_landslide_bin, smap_ncols, smap_nrows, 1, gdal.GDT_Byte)
		outband 		= cur_ds.GetRasterBand(1)
		outband.WriteArray(rainfall_data.astype(numpy.uint8), 0, 0)
	
		cur_ds.SetGeoTransform( geotransform )
		cur_ds.SetGeoTransform( geotransform )
	
		smap_ds 		= None
		rainfall_ds 	= None
		cur_ds			= None

	# Now let's colorize it
	if force or not os.path.exists(current_landslide_bin_rgb):
		cmd = "gdaldem color-relief -alpha " +  current_landslide_bin + " " + color_file + " " + current_landslide_bin_rgb
		if verbose:
			print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: slope file could not be generated:', err)
			sys.exit(-1)
	
	# Generate mbtiles
	if force or not os.path.exists(mbtiles_fname):	

		if force:
			os.system("rm "+mbtiles_fname)
			os.system("rm -rf "+mbtiles_dir)

		#zoom 		= "-z "+tzoom
		zoom 		= ""		
		processes 	= "--processes 10"
		srs 		= "--s_srs=EPSG:4326"	# I am not sure we need this
		 
		cmd = "./gdal2tiles.py %s %s %s %s %s" % (processes, srs, zoom, current_landslide_bin_rgb, mbtiles_dir)
		if verbose:
			print cmd
		os.system(cmd)

		# generate metadata.json
		metafile = os.path.join(mbtiles_dir, "metadata.json")
		json = "{\n"
		json += "  \"name\": \"Landslide Estimate - "+ config.ymd + "\",\n"
		json += "  \"description\": \"Landslide GSFC\",\n"
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
	
def generate_map( dx ):
	# make sure it exists
	region		= config.regions[dx]
	
	if verbose:
		print "Processing Susceptibility Map for Region:", dx, region['name']	
	
	# Destination Directory
	dir			= os.path.join(config.data_dir, "landslide_estimate", dx)
	if not os.path.exists(dir):
		os.makedirs(dir)

	build_tif(dx, region, dir )

# =======================================================================
# Main
#
if __name__ == '__main__':
	version_num = int(gdal.VersionInfo('VERSION_NUM'))
	if version_num != 1920: # because of GetGeoTransform(can_return_null)
		print('ERROR: Python bindings of GDAL 1.9.2 required')
		sys.exit(1)

	confirm_availability_of("bzip2")
	confirm_availability_of("potrace")
	confirm_availability_of("topojson")

	parser 		= argparse.ArgumentParser(description='Generate Current Landslide Estimates')
	apg_input 	= parser.add_argument_group('Input')
	
	apg_input.add_argument("-f", "--force", action='store_true', help="Forces new products to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose

	generate_map('d03')
	generate_map('d02')
	
	print "Done."
