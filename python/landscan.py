#!/usr/bin/env python
#
# Created on 7/5/2013 Pat Cappelaere - Vightel Corporation
# 
# Requirements:
#	gdal...
#
# Requires 2011 LandScan EPSG:4326
# cd [ls]/LandScan-2011/ArcGIS/Population
# gdalwarp lspop2011 -t_srs EPSG:4326 -of GTIFF lspop2011_4326.tif
#

import os, inspect, sys
import argparse

from osgeo import gdal
from osgeo import osr
from osgeo import ogr

import config
import json

from browseimage import MakeBrowseImage, wms
from s3 import CopyToS3
#from level import CreateLevel

force 		= 0
verbose 	= 0

BASE_DIR 	= config.LS_DIR

def execute( cmd ):
	if verbose:
		print cmd
	os.system(cmd)
	
def CreateLevel(l, geojsonDir, fileName, src_ds, data, attr, _force, _verbose):
	global force, verbose
	force 				= _force
	verbose				= _verbose
	
	if verbose:
		print "CreateLevel", l, _force, _verbose
	
	projection  		= src_ds.GetProjection()
	geotransform		= src_ds.GetGeoTransform()
	#band				= src_ds.GetRasterBand(1)
		
	xorg				= geotransform[0]
	yorg  				= geotransform[3]
	xres				= geotransform[1]
	yres				= -geotransform[5]
	stretch				= 1	# xres/yres
	
	if verbose:
		print xres, yres, stretch
		
	xmax				= xorg + geotransform[1]* src_ds.RasterXSize
	ymax				= yorg + geotransform[5]* src_ds.RasterYSize


	if not force and os.path.exists(fileName):
		return
		
	driver 				= gdal.GetDriverByName( "GTiff" )

	dst_ds_dataset		= driver.Create( fileName, src_ds.RasterXSize, src_ds.RasterYSize, 1, gdal.GDT_Byte, [ 'COMPRESS=DEFLATE' ] )
	dst_ds_dataset.SetGeoTransform( geotransform )
	dst_ds_dataset.SetProjection( projection )
	o_band		 		= dst_ds_dataset.GetRasterBand(1)
	o_data				= o_band.ReadAsArray(0, 0, dst_ds_dataset.RasterXSize, dst_ds_dataset.RasterYSize )
	
	count 				= (data >= l).sum()	

	o_data[data>=l] 	= 255
	o_data[data<l]		= 0

	if verbose:
		print "*** Level", l, " count:", count

	if count > 0 :

		dst_ds_dataset.SetGeoTransform( geotransform )
			
		dst_ds_dataset.SetProjection( projection )
		
		o_band.WriteArray(o_data, 0, 0)
		
		ct = gdal.ColorTable()
		ct.SetColorEntry( 0, (255, 255, 255, 255) )
		ct.SetColorEntry( 255, (255, 0, 0, 255) )
		o_band.SetRasterColorTable(ct)
		
		dst_ds_dataset 	= None
		if verbose:
			print "Created", fileName

		cmd = "gdal_translate -q -of PNM " + fileName + " "+fileName+".pgm"
		execute(cmd)

		# -i  		invert before processing
		# -t 2  	suppress speckles of up to this many pixels. 
		# -a 1.5  	set the corner threshold parameter
		# -z black  specify how to resolve ambiguities in path decomposition. Must be one of black, white, right, left, minority, majority, or random. Default is minority
		# -x 		scaling factor
		# -L		left margin
		# -B		bottom margin

		if stretch != 1:
			cmd = str.format("potrace -i -z black -a 3 -t 10 -b geojson -o {0} {1} -x {2} -S {3} -L {4} -B {5} ", fileName+".geojson", fileName+".pgm", xres, stretch, xorg, ymax ); 
		else:
			cmd = str.format("potrace -i -z black -a 3 -t 10 -b geojson -o {0} {1} -x {2} -L {3} -B {4} ", fileName+".geojson", fileName+".pgm", xres, xorg, ymax ); 
			
		execute(cmd)

		#cmd = str.format("node set_geojson_property.js --file {0} --prop frost={1}", fileName+".geojson", frost)
		#execute(cmd)
	
		out = ""
		if not verbose:
			out = "> /dev/null 2>&1"
			
		cmd = str.format("topojson -o {0} --simplify-proportion 0.75 -p {3}={1} -- {3}={2} {4}", fileName+".topojson", l, fileName+".geojson", attr, out );
		execute(cmd)
	
		# convert it back to json
		cmd = "topojson-geojson --precision 4 -o %s %s" % ( geojsonDir, fileName+".topojson" )
		execute(cmd)
	
		# rename file
		output_file = "%s_level_%d.geojson" % (attr, l)
		json_file	= "%s.json" % attr
		cmd = "mv %s %s" % (os.path.join(geojsonDir,json_file), os.path.join(geojsonDir, output_file))
		execute(cmd)
			
def process(mydir, lsFile, regionName, region, s3_bucket, s3_folder):
	scene			= regionName
	subsetFileName	= os.path.join(mydir, "ls.2011_subset.tif")
	
	if force or not os.path.exists(subsetFileName):
		bbox 			= region['bbox']
		print region['name'], region['bbox']
		
		warpOptions 	= "-q -overwrite -co COMPRESS=DEFLATE -r cubic -t_srs EPSG:4326 -te %s %s %s %s " % (bbox[0], bbox[1], bbox[2], bbox[3])
		#warpOptions		+= " -ts 2400 2400 "	# for India
		warpCmd 		= 'gdalwarp ' + warpOptions + lsFile + ' ' + subsetFileName
		execute( warpCmd )
		if verbose:
			print "LS Subset", subsetFileName

	if verbose:
		print "Processing", subsetFileName
		
	geojsonDir	= os.path.join(mydir,"geojson")
	if not os.path.exists(geojsonDir):            
		os.makedirs(geojsonDir)

	levelsDir	= os.path.join(mydir,"levels")
	if not os.path.exists(levelsDir):            
		os.makedirs(levelsDir)
	
	merge_filename 		= os.path.join(geojsonDir, "%s_levels.geojson" % scene)
	
	topojson_filename 	= os.path.join(geojsonDir, "..", "ls.2011.topojson" )
	browse_filename 	= os.path.join(geojsonDir, "..", "ls.2011_browse.tif" )
	subset_filename 	= os.path.join(geojsonDir, "..", "ls.2011_small_browse.tif" )
	osm_bg_image		= os.path.join(geojsonDir, "..", "osm_bg.png")
	sw_osm_image		= os.path.join(geojsonDir, "..", "ls.2011_thn.jpg" )

	#levels 				= [ 5500, 3400, 2100, 1300, 800, 500, 300, 200, 100 ]
	levels 				= [ 8900, 5500, 3400, 2100, 1300, 800, 500 ]
	
	# From http://colorbrewer2.org/	
	#hexColors 			= [	"#f7f4f9", "#e7e1ef", "#d4b9da", "#c994c7", "#df65b0", "#e7298a", "#ce1256", "#980043", "#67001f"]
	hexColors 			= ["#feebe2", "#fcc5c0", "#fa9fb5", "#f768a1", "#dd3497", "#ae017e", "#7a0177"]
	
	ds 					= gdal.Open( subsetFileName )
	band				= ds.GetRasterBand(1)
	data				= band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize )
	
	if force or not os.path.exists(topojson_filename+".gz"):
		for l in levels:
			fileName 		= os.path.join(levelsDir, scene+"_level_%d.tif"%l)
			CreateLevel(l, geojsonDir, fileName, ds, data, "population", force,verbose)
	
		jsonDict = dict(type='FeatureCollection', features=[])
	
		for l in reversed(levels):
			fileName 		= os.path.join(geojsonDir, "population_level_%d.geojson"%l)
			if os.path.exists(fileName):
				print "merge", fileName
				with open(fileName) as data_file:    
					data = json.load(data_file)
		
				if 'features' in data:
					for f in data['features']:
						jsonDict['features'].append(f)
	

		with open(merge_filename, 'w') as outfile:
		    json.dump(jsonDict, outfile)	

		# Convert to topojson
		cmd 	= "topojson -p -o "+ topojson_filename + " " + merge_filename
		execute(cmd)

		cmd 	= "gzip --keep "+ topojson_filename
		execute(cmd)

	if not os.path.exists(osm_bg_image):
		geotransform		= ds.GetGeoTransform()
		xorg				= geotransform[0]
		yorg  				= geotransform[3]

		xmax				= xorg + geotransform[1]* ds.RasterXSize
		ymax				= yorg + geotransform[5]* ds.RasterYSize
		ullat				= yorg
		ullon 				= xorg
		lrlat 				= ymax
		lrlon 				= xmax
		
		print "wms", ullat, ullon, lrlat, lrlon
		wms(ullat, ullon, lrlat, lrlon, osm_bg_image)
		
	if force or not os.path.exists(sw_osm_image):
		zoom = region['thn_zoom']
		MakeBrowseImage(ds, browse_filename, subset_filename, osm_bg_image, sw_osm_image,levels, hexColors, force, verbose, zoom)
		
	ds = None
	
	file_list = [ sw_osm_image, topojson_filename, topojson_filename+".gz", subsetFileName ]
	
	CopyToS3( s3_bucket, s3_folder, file_list, force, verbose )
	
#
# python landscan.py --region d04 -v -f
#
if __name__ == '__main__':
	version_num = int(gdal.VersionInfo('VERSION_NUM'))
	if version_num < 1800: # because of GetGeoTransform(can_return_null)
		print('ERROR: Python bindings of GDAL 1.8.0 or later required')
		sys.exit(1)

	parser 		= argparse.ArgumentParser(description='Generate Population Density')
	apg_input 	= parser.add_argument_group('Input')
	apg_input.add_argument("-f", "--force", action='store_true', help="forces new product to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose on/off")
	apg_input.add_argument("-r", "--region", help="region name")

	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose
	regionName	= options.region
	
	# Landscan directory
	lsFile		= "/Volumes/MacBay3/GeoData/ls/LandScan-2011/ArcGIS/Population/lspop2011_4326.tif"
	region		= config.regions[regionName]
	year		= 2011
	
	s3_folder	= os.path.join("ls", str(year))
	s3_bucket	= region['bucket']

	if not os.path.exists(lsFile):
		print "Landscan file does not exist", lsFile
		sys.exit(-1)
		
	ls_dir	= os.path.join(BASE_DIR,str(year), regionName)
	if not os.path.exists(ls_dir):
	    os.makedirs(ls_dir)

	process(ls_dir, lsFile, regionName, region, s3_bucket, s3_folder)