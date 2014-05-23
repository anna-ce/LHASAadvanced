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
ymd 		= config.ymd

def execute(cmd):
	if(verbose):
		print cmd
	os.system(cmd)
	
# Generate Curren
def build_tif(dx, region, dir):
	region 		= config.regions[dx]
	bbox		= region['bbox']
	tzoom   	= region['tiles-zoom']
	pixelsize   = region['pixelsize']
	thn_width   = region['thn_width']
	thn_height  = region['thn_height']
	bucketName 	= region['bucket']

	# get the 90th and 99th percentile rainfall limits
	limit_90 = os.path.join(config.data_dir,"rain_limits", "%s_90.tif" % (dx))
	if not os.path.exists(limit_90):
		print "**ERR: file not found", limit_90
		sys.exit(-1)

	# get the 90th and 99th percentile rainfall limits
	limit_99 = os.path.join(config.data_dir,"rain_limits", "%s_99.tif" % (dx))
	if not os.path.exists(limit_99):
		print "**ERR: file not found", limit_99
		sys.exit(-1)
	
	# Find the daily rainfall accumulation file for the area
	daily_rainfall 	= os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s_1km.tif" % (dx,ymd))
	if not os.path.exists(daily_rainfall):
		print "**ERR: file not found", daily_rainfall
		sys.exit(-1)
		
	# Find susceptibility map
	susmap 	= os.path.join(config.data_dir, "susmap", "susmap_%s.tif" %(dx))
	if not os.path.exists(susmap):
		print "**ERR: file not found", susmap
		sys.exit(-1)

	forecast_landslide_bin 		= os.path.join(config.data_dir, "landslide_risk", dx, ymd, "landslide_risk_%s_%s.tif" %(dx,ymd))
	forecast_landslide_bin_rgb 	= os.path.join(config.data_dir, "landslide_risk", dx, ymd, "landslide_risk_%s_%s_rgb.tif" %(dx,ymd))

	forecast_landslide_100m_bin 		= os.path.join(config.data_dir, "landslide_risk", dx, ymd, "landslide_risk_%s_%s_100m.tif" %(dx,ymd))
	forecast_landslide_100m_bin_rgb 	= os.path.join(config.data_dir, "landslide_risk", dx, ymd, "landslide_risk_%s_%s_100m_rgb.tif" %(dx,ymd))
	
	
	color_file					= "./cluts/landslide_colors.txt"
	#color_file					= "./cluts/susmap_colors2.txt"
	
	shp_file 					= os.path.join(config.data_dir,"landslide_risk", dx, ymd, "landslide_risk_%s_%s.shp" % (dx,ymd))

	watch_geojson_file 			= os.path.join(config.data_dir,"landslide_risk", dx, ymd, "landslide_watch_%s_%s.geojson" % (dx,ymd))
	warning_geojson_file 		= os.path.join(config.data_dir,"landslide_risk", dx, ymd, "landslide_warning_%s_%s.geojson" % (dx,ymd))
	
	topojson_file				= os.path.join(config.data_dir,"landslide_risk", dx, ymd, "landslide_risk_%s_%s.topojson" % (dx,ymd))
	topojson_gz_file			= os.path.join(config.data_dir,"landslide_risk", dx, ymd, "landslide_risk_%s_%s.topojson.gz" % (dx,ymd))
	thumbnail_file 				= os.path.join(config.data_dir,"landslide_risk", dx, ymd, "landslide_risk_%s_%s.thn.png" % (dx,ymd))
	static_file 				= os.path.join(config.data_dir,"landslide_risk", dx, "%s_static.tiff" % (dx))

	if force or not os.path.exists(forecast_landslide_bin):
		if verbose:
			"Processing forecast landslide model for %s..." % config.ym
			
		if verbose:
			print "Loading ", susmap

		smap_ds			= gdal.Open( susmap )
		smap_ncols 		= smap_ds.RasterXSize
		smap_nrows 		= smap_ds.RasterYSize
		smap_band 		= smap_ds.GetRasterBand(1)
		smap_data 		= smap_band.ReadAsArray(0, 0, smap_ncols, smap_nrows )
		projection   	= smap_ds.GetProjection()
		geotransform 	= smap_ds.GetGeoTransform()

		if verbose:
			print "Loaded ", susmap, smap_ncols, smap_nrows

			
		if verbose:
			print "Loading ", daily_rainfall

		rainfall_ds		= gdal.Open( daily_rainfall )
		rainfall_ncols 	= rainfall_ds.RasterXSize
		rainfall_nrows 	= rainfall_ds.RasterYSize
		rainfall_band 	= rainfall_ds.GetRasterBand(1)
		rainfall_data 	= rainfall_band.ReadAsArray(0, 0, rainfall_ncols, rainfall_nrows )
	
		if verbose:
			print "cols %d rows %d" %(rainfall_ncols, rainfall_nrows)

		if verbose:
			print "Loading ", limit_90
			
		limit_90_ds		= gdal.Open( limit_90 )
		limit_90_ncols 	= limit_90_ds.RasterXSize
		limit_90_nrows 	= limit_90_ds.RasterYSize
		limit_90_band 	= limit_90_ds.GetRasterBand(1)
		limit_90_data 	= limit_90_band.ReadAsArray(0, 0, limit_90_ncols, limit_90_nrows )

		if verbose:
			print "Loading ", limit_99
			
		limit_99_ds		= gdal.Open( limit_99 )
		limit_99_ncols 	= limit_99_ds.RasterXSize
		limit_99_nrows 	= limit_99_ds.RasterYSize
		limit_99_band 	= limit_99_ds.GetRasterBand(1)
		limit_99_data 	= limit_99_band.ReadAsArray(0, 0, limit_99_ncols, limit_99_nrows )

		# wipe out where there is no risk
		#rainfall_data[smap_data<2] = 0

		# Set the thresholds based in rainfall limits
		#rainfall_data[ numpy.where( rainfall_data <= limit_90_data)] 	= 0
		arr = numpy.zeros(shape=(rainfall_nrows,rainfall_ncols))
		
		
		#arr[smap_data<6] = -9999
		arr[ rainfall_data >= limit_90_data] 	= 4		# yello Warning
		arr[ rainfall_data >= limit_99_data] 	= 5		# Red Warning
		
		arr[smap_data<3] 	= 0
		# susmap nodata value = 127
		arr[smap_data==127] = 0
		
		#arr[numpy.where(smap_data>3) and numpy.where(smap_data<6) ] = 4
		
		#rainfall_data[ rainfall_data < limit_90_data] 	= 0		# Yellow Watch
		#rainfall_data[ rainfall_data >= limit_90_data] 	= 4		# Red Warning

		# Write the file
		driver 			= gdal.GetDriverByName("GTiff")
		cur_ds 			= driver.Create(forecast_landslide_bin, smap_ncols, smap_nrows, 1, gdal.GDT_Byte)
		outband 		= cur_ds.GetRasterBand(1)
		
		#outband.WriteArray(rainfall_data.astype(numpy.uint8), 0, 0)
		outband.WriteArray(arr.astype(numpy.uint8), 0, 0)

		cur_ds.SetGeoTransform( geotransform )
		cur_ds.SetGeoTransform( geotransform )

		smap_ds 		= None
		rainfall_ds 	= None
		cur_ds			= None
		limit_90_ds		= None
		limit_99_ds		= None

	# Now let's colorize it
	if force or not os.path.exists(forecast_landslide_bin_rgb):
		cmd = "gdaldem color-relief -alpha " +  forecast_landslide_bin + " " + color_file + " " + forecast_landslide_bin_rgb
		if verbose:
			print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: slope file could not be generated:', err)
			sys.exit(-1)
	
	# upsample it to smooth it
	if force or not os.path.exists(forecast_landslide_100m_bin):
		cmd = "gdalwarp -overwrite -q -tr %f %f -te %f %f %f %f -r cubicspline -co COMPRESS=LZW %s %s"%(pixelsize/10, pixelsize/10, bbox[0], bbox[1], bbox[2], bbox[3], forecast_landslide_bin, forecast_landslide_100m_bin)
		execute(cmd)
	
	# Now let's colorize it
	if force or not os.path.exists(forecast_landslide_100m_bin_rgb):
		cmd = "gdaldem color-relief -alpha " +  forecast_landslide_100m_bin + " " + color_file + " " + forecast_landslide_100m_bin_rgb
		if verbose:
			print cmd
			err = os.system(cmd)
			if err != 0:
				print('ERROR: slope file could not be generated:', err)
				sys.exit(-1)
	
	# Create Caution file
	if force or not os.path.exists(watch_geojson_file):
		if force:
			execute("rm -f "+watch_geojson_file)
		cmd = "gdal_contour -q -f GEOJSON -i 4 -a risk %s %s" % ( forecast_landslide_100m_bin, watch_geojson_file )
		execute(cmd)

	# Create Alert file
	if force or not os.path.exists(warning_geojson_file):
		if force:
			execute("rm -f "+warning_geojson_file)
		cmd = "gdal_contour -q -f GEOJSON -i 5 -a risk %s %s" % ( forecast_landslide_100m_bin, warning_geojson_file )
		execute(cmd)
	
	if force or not os.path.exists(topojson_file):
		watch = "landslide_watch_%s_%s" % (dx, ymd)
		warning	= "landslide_warning_%s_%s" % (dx, ymd)
		cmd = "topojson --simplify-proportion 0.5  --bbox -p risk -o %s -- %s=%s %s=%s" % (topojson_file, watch, watch_geojson_file, warning, warning_geojson_file ) 
		execute(cmd)
	
	if force or not os.path.exists(topojson_gz_file):
		if force:
			execute("rm -f "+topojson_file)
		cmd = "gzip %s" % (topojson_file)
		execute(cmd)

	tmp_file = thumbnail_file + ".tmp.tif"
	if force or not os.path.exists(thumbnail_file):
		cmd="gdalwarp -overwrite -q -multi -ts %d %d -r cubicspline -co COMPRESS=LZW %s %s" % (thn_width, thn_height, forecast_landslide_bin_rgb, tmp_file )
		execute(cmd)
		cmd = "composite -blend 80 %s %s %s" % ( tmp_file, static_file, thumbnail_file)
		execute(cmd)
		execute("rm "+tmp_file)

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
	
def generate_map( dx ):
	# make sure it exists
	region		= config.regions[dx]
	
	if verbose:
		print "Processing Forecast Landslide Map for Region:", dx, region['name']	
	
	# Destination Directory
	dir			= os.path.join(config.data_dir, "landslide_risk", dx, ymd)
	if not os.path.exists(dir):
		os.makedirs(dir)

	build_tif(dx, region, dir )

# =======================================================================
# Main
#
if __name__ == '__main__':
	
	parser 		= argparse.ArgumentParser(description='Generate Forecast Landslide Estimates')
	apg_input 	= parser.add_argument_group('Input')
	
	apg_input.add_argument("-f", "--force", action='store_true', help="Forces new products to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose

	generate_map('d03')
	#generate_map('d02')
	
	print "Done."
