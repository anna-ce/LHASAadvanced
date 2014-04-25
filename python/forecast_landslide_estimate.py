#!/usr/bin/env python
#
# Created on 11/21/2013 Pat Cappelaere - Vightel Corporation
#
# Generates 24hr Forecast Landslide Estimate
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
	forecast_rainfall 	= os.path.join(config.data_dir,"wrf", dx, "wrf_precip_out_%s_%s_4326_1km.tif" % (dx,config.ym))
	if not os.path.exists(forecast_rainfall):
		print "**ERR: file not found", forecast_rainfall
		
	# Find susceptibility map
	dem_slope_bin 	= os.path.join(config.data_dir, "susmap", dx, dx+"_dem_slope_bin.tif")
	if not os.path.exists(dem_slope_bin):
		print "**ERR: file not found", dem_slope_bin

	forecast_landslide_bin 		= os.path.join(config.data_dir, "landslide_forecast", dx, dx+"_forecast_landslide_%s.tif" %(config.ym))
	forecast_landslide_bin_rgb 	= os.path.join(config.data_dir, "landslide_forecast", dx, dx+"_forecast_landslide_%s_rgb.tif" %(config.ym))
	color_file					= "./landslide_colors.txt"
	
	if force or not os.path.exists(forecast_landslide_bin):
		if verbose:
			"Processing forecast landslide model for %s..." % config.ym
			
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
			print "cols %d rows %d" %(smap_ncols, smap_nrows)
			
		if verbose:
			print "Loading ", forecast_rainfall
			
		rainfall_ds		= gdal.Open( forecast_rainfall )
		rainfall_ncols 	= rainfall_ds.RasterXSize
		rainfall_nrows 	= rainfall_ds.RasterYSize
		rainfall_band 	= rainfall_ds.GetRasterBand(1)
		rainfall_data 	= rainfall_band.ReadAsArray(0, 0, rainfall_ncols, rainfall_nrows )
	
		if verbose:
			print "cols %d rows %d" %(rainfall_ncols, rainfall_nrows)
		
		# wipe out where there is no risk
		rainfall_data[ numpy.where( smap_data < 1)] = 0

		# Set the thresholds based in rainfall limits
		rainfall_data[ numpy.where( rainfall_data > config.rainfall_red_limit)] 	= 4
		rainfall_data[ numpy.where( rainfall_data > config.rainfall_orange_limit)] 	= 3
		rainfall_data[ numpy.where( rainfall_data > config.rainfall_yellow_limit)] 	= 2
	
		# Write the file
		driver 			= gdal.GetDriverByName("GTiff")
		cur_ds 			= driver.Create(forecast_landslide_bin, smap_ncols, smap_nrows, 1, gdal.GDT_Byte)
		outband 		= cur_ds.GetRasterBand(1)
		outband.WriteArray(rainfall_data.astype(numpy.uint8), 0, 0)
	
		cur_ds.SetGeoTransform( geotransform )
		cur_ds.SetGeoTransform( geotransform )
	
		smap_ds 		= None
		rainfall_ds 	= None
		cur_ds			= None

	# Now let's colorize it
	if force or not os.path.exists(forecast_landslide_bin_rgb):
		cmd = "gdaldem color-relief -alpha " +  forecast_landslide_bin + " " + color_file + " " + forecast_landslide_bin_rgb
		if verbose:
			print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: slope file could not be generated:', err)
			sys.exit(-1)
	
	
	
def generate_map( dx ):
	# make sure it exists
	region		= config.regions[dx]
	
	if verbose:
		print "Processing Forecast Landslide Map for Region:", dx, region['name']	
	
	# Destination Directory
	dir			= os.path.join(config.data_dir, "landslide_forecast", dx)
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

	parser 		= argparse.ArgumentParser(description='Generate Forecast Landslide Estimates')
	apg_input 	= parser.add_argument_group('Input')
	
	apg_input.add_argument("-f", "--force", action='store_true', help="Forces new products to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose

	generate_map('d03')
	generate_map('d02')
	
	print "Done."
