#
# Pat Cappelaere pat@cappelaere.com
#
#	Example to process some data products from WRF (MARN, San Salvador)
#
import numpy, os, sys, inspect
from osgeo import osr, gdal
from datetime import date
from dateutil.parser import parse

import warnings
from gzip import GzipFile
import pygrib
import pyproj
import argparse
import json

from osgeo.gdalconst import GA_Update
from s3 import CopyToS3
from level import CreateLevel
from browseimage import MakeBrowseImage, wms

# Site configuration
import config

force		= 1
verbose		= 1

def execute(cmd):
	if(verbose):
		print cmd
	os.system(cmd)


def process_file(filename, product, variable, wrf_mode, dt, region, hours, s3_bucket, s3_folder):
	if verbose:
		print "processing: "+filename+ " product:", product, " variable:"+variable
	
	zoom 			= region['thn_zoom']
	fpathname 		= os.path.dirname(filename)
	fdir			= os.path.join( fpathname, dt, product)
	
	if not os.path.exists(fdir):
		os.makedirs(fdir)

	if force:
		cmd = "rm -rf "+fdir+"/*"
		execute(cmd)

	geojsonDir	= os.path.join(fdir,"geojson")
	if not os.path.exists(geojsonDir):            
		os.makedirs(geojsonDir)

	levelsDir	= os.path.join(fdir,"levels")
	if not os.path.exists(levelsDir):            
		os.makedirs(levelsDir)

	levels				= [ 377, 		233, 		144, 		89, 		55, 		34, 		21, 		13, 		8, 			5,			3]
	colors 				= ["#4D004A",	"#810F7C",	"#084081",	"#0868ac",	"#2b8cbe",	"#4eb3d3",	"#7bccc4",	"#a8ddb5",	"#ccebc5",	"#e0f3db", "#f7fcf0"]
	
	output_file			= os.path.join( fdir, "%s.%s_MERC.tif" % (product,dt))
	flipped_file		= os.path.join( fdir, "%s.%s_MERC_flipped.tif" % (product,dt))
	supersamp_file		= os.path.join( fdir, "%s.%s_MERC_flipped_100.tif" % (product,dt))
	
	reproj_file			= os.path.join( fdir, "%s.%s.tif" % (product,dt))
	reproj_rgb_file		= os.path.join( fdir, "%s.%s_rgb.tif" % (product,dt))
	color_file 			= os.path.join("cluts", "wrf_colors.txt")

	merge_filename 		= os.path.join(geojsonDir, "%s.%s.geojson" % (product,dt))
	topojson_filename 	= os.path.join(geojsonDir, "..", "%s.%s.topojson" % (product,dt))
	browse_filename 	= os.path.join(geojsonDir, "..", "%s.%s_browse.tif" % (product,dt))
	subset_filename 	= os.path.join(geojsonDir, "..", "%s.%s_small_browse.tif" % (product,dt))
	subset_aux_filename = os.path.join(geojsonDir, "..", "%s.%s_small_browse.tif.aux" % (product,dt))
	osm_bg_image		= os.path.join(fdir, "..", "osm_bg.png")
	sw_osm_image		= os.path.join(geojsonDir, "..", "%s.%s_thn.jpg" % (product,dt))

	if force or not os.path.exists(output_file):
		grbs 		= pygrib.open(filename)
		grbvars	 	= grbs.select(name=variable)
		count		= 0
		total		= []
	
		for grbvar in grbvars:
			grbstr 	    = "%s" % grbvar	
			arr 	    = grbstr.split(':')
			# 1090:Total Precipitation:kg m**-2 (instant):mercator:surface:level 0:fcst time 1 hrs:from 201604241200
			id 		    = arr[0]
			name		= arr[1]
			rate		= arr[2]
			fcst		= arr[6]
			dt			= arr[7].replace('from ', '')
		
			if( rate.find('accum') > 0):
				count += 1
			
				print id, name, rate, fcst, dt
				if count == 1:
					total = grbvar['values']
				else:
					total += grbvar['values']
				#lats, lons 	= p.latlons()
			
				if count > hours:
					break
		grbs.close()
	

		# Get critical info from GRIB file
		ds 				= gdal.Open( filename )
		ncols 			= ds.RasterXSize
		nrows 			= ds.RasterYSize
		geotransform	= ds.GetGeoTransform()
		projection  	= ds.GetProjection()
	
		# Create gtif
		driver 			= gdal.GetDriverByName("GTiff")
		dst_ds 			= driver.Create(output_file, ncols, nrows, 1, gdal.GDT_Float32 )
		band 			= dst_ds.GetRasterBand(1)
	
		band.WriteArray(total, 0, 0)
		dst_ds.SetGeoTransform( geotransform )
		dst_ds.SetProjection( projection )
	
		dst_ds			= None
		ds				= None
	
	# Flip it since it is bottom up
	if force or not os.path.exists(flipped_file):			
		cmd = "flip_raster.py -o %s %s" % ( flipped_file, output_file )
		execute(cmd)
	
	# Reproject to EPSG:4326
	if force or not os.path.exists(reproj_file):			
		cmd = "gdalwarp -q -t_srs EPSG:4326 " + flipped_file + " " + reproj_file
		execute(cmd)
	
	ds 				= gdal.Open( reproj_file )
	geotransform	= ds.GetGeoTransform()
	pixelsize		= geotransform[1]
	ds				= None
	
	# Supersample and interpolate to make it output smoother
	if force or not os.path.exists(supersamp_file):			
		cmd = "gdalwarp -q -multi -tr %f %f -r cubicspline %s %s" % (pixelsize/10,pixelsize/10,reproj_file,supersamp_file)
		execute(cmd)
	
	# Color it using colormap
	if verbose and not os.path.exists(reproj_rgb_file):			
		cmd = "gdaldem color-relief -q -alpha "+supersamp_file+" " + color_file + " " + reproj_rgb_file
		execute(cmd)

	ds 					= gdal.Open( supersamp_file )
	band				= ds.GetRasterBand(1)
	data				= band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize )
	
	geotransform 		= ds.GetGeoTransform()
	xorg				= geotransform[0]
	yorg  				= geotransform[3]
	pres				= geotransform[1]
	xmax				= xorg + geotransform[1]* ds.RasterXSize
	ymax				= yorg - geotransform[1]* ds.RasterYSize

	if force or not os.path.exists(topojson_filename+".gz"):
		for l in levels:
			fileName 		= os.path.join(levelsDir, dt+"_level_%d.tif"%l)
			CreateLevel(l, geojsonDir, fileName, ds, data, "precip", force, verbose)
	
		jsonDict = dict(type='FeatureCollection', features=[])
	
		for l in reversed(levels):
			fileName 		= os.path.join(geojsonDir, "precip_level_%d.geojson"%l)
			if os.path.exists(fileName):
				if verbose:
					print "merge", fileName
				with open(fileName) as data_file:    
					data = json.load(data_file)
		
				if 'features' in data:
					for f in data['features']:
						jsonDict['features'].append(f)
	

		with open(merge_filename, 'w') as outfile:
		    json.dump(jsonDict, outfile)	

		if verbose:
			output = " "
		else:
			output = " > /dev/null 2>&1"		

		# Convert to topojson
		cmd 	= "topojson -p -o "+ topojson_filename + " " + merge_filename + output
		execute(cmd)

		if verbose:
			cmd 	= "gzip --keep -f "+ topojson_filename
		else:
			cmd 	= "gzip -f "+ topojson_filename
		execute(cmd)

	if not os.path.exists(osm_bg_image):
		ullat = yorg
		ullon = xorg
		lrlat = ymax
		lrlon = xmax
		wms(ullat, ullon, lrlat, lrlon, osm_bg_image)
	
	if force or not os.path.exists(sw_osm_image):
		scale		= 2
		MakeBrowseImage(ds, browse_filename, supersamp_file, osm_bg_image, sw_osm_image, levels, colors, force, verbose, zoom, scale)
		
	ds = None
	
	file_list = [ sw_osm_image, topojson_filename+".gz", reproj_file ]
	
	CopyToS3( s3_bucket, s3_folder, file_list, force, verbose )
		
	if not verbose: # Cleanup
		cmd = "rm -rf %s %s %s %s %s %s %s %s" % (flipped_file, output_file, supersamp_file, browse_filename, subset_filename, subset_aux_filename, geojsonDir, levelsDir)
		execute(cmd)
	

# python wrf.py -f -v
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

	region		= config.regions['d02']	
	today		= parse("2016-04-24")
	year		= today.year
	month		= today.month
	day			= today.day
	doy			= today.strftime('%j')

	variable	= "Total Precipitation"
	
	# To differentiate from then 5km product
	wrf_mode	= 'wrf_30km'
	
	product		= 'fct_precip_1d'

	s3_bucket 	= region['bucket']	
	s3_folder	= os.path.join(wrf_mode, str(year), doy)

	#filename 	= "/app/user/data2/wrf/201604241200_arw_wrfout_d01.grb2"	
	filename 	= "/Users/patricecappelaere/landslide/data/wrf_marn/20160424/201604241200_arw_wrfout_d01.grb2"	

	arr	 		= os.path.basename(filename).split('_')
	
	# File timestamp to identify product
	dt			= arr[0]
	
	if product == 'fct_precip_1d':
		hours = 24
	if product == 'fct_precip_2d':
		hours = 48
	if product == 'fct_precip_3d':
		hours = 72
	
	#print(filename, product, variable, wrf_mode, dt, region, hours, s3_bucket, s3_folder)
	process_file(filename, product, variable, wrf_mode, dt, region, hours, s3_bucket, s3_folder)