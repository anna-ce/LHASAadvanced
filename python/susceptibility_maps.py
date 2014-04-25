#!/usr/bin/env python
#
# Created on 11/21/2013 Pat Cappelaere - Vightel Corporation
#
# Generates Susceptibility Maps for Landslides Application
#
import numpy, sys, os, inspect, urllib
import argparse

from osgeo import osr, gdal
from ftplib import FTP
from datetime import date, timedelta
from which import *

# Site configuration
import config

# Directory of Hydroshed tiles
dem_dir 	= "/Volumes/MacBay3/HAND/HydroSHEDS"

if not os.path.isdir(dem_dir):
	print "**ERR: HydroSHEDS Directory does not exist!!!", dem_dir
	sys.exit(-1)
	
# Hysdrosheds tiles are 5x5 deg @90m (3 arc-second resolution)
# named after lower left corner

force 		= 0
verbose 	= 0

def	build_dem_vrt(dx, region, dir):
	dem_vrt = os.path.join(dir, dx+"_dem.vrt")
	if not force and os.path.isfile(dem_vrt):
		if verbose:
			print dem_vrt+ " exists!"
		return
	
	cmd 	= "gdalbuildvrt " + dem_vrt
	files 	= " "
	
	for tile in region['hydroshed_tiles']:
		fileName = os.path.join(dem_dir, tile)
		if not os.path.exists( fileName):
			if verbose:
				print "File:", fileName, " does not exist"
		else:
			basename = tile.split("/")
			dem_bil  = basename[1]+"_dem_bil"
			files += fileName + "/"+ dem_bil + "/" + basename[1]+"_dem.bil "
	
	cmd += files
	if verbose:
		print cmd
	err = os.system(cmd)
	
# Create bbox subset @1km
def	build_tif_bbox(dx, region, dir):
	dem_vrt = os.path.join(dir, dx+"_dem.vrt")
	dem_tif = os.path.join(dir, dx+"_dem.tif")
	if not force and os.path.isfile(dem_tif):
		if verbose:
			print dem_tif+ " exists!"
		return
	
	pixSizeX 		= 0.008999
	pixSizeY 		= 0.008999
	
	bbox 			= region['bbox']
	ofStr 			= ' -of GTiff' 
	bbStr 			= ' -te %s %s %s %s '%(bbox[0], bbox[1], bbox[2], bbox[3]) 
	resStr 			= ' -tr %s %s '%(pixSizeX, pixSizeY)
	overwriteStr 	= ' -overwrite ' # Overwrite output if it exists
	additionalOptions = ' -co COMPRESS=LZW -dstalpha ' # Additional options
	#warpOptions 	= ofStr + bbStr + resStr + projectionStr + overwriteStr + additionalOptions
	warpOptions 	= ofStr + bbStr + resStr + overwriteStr + additionalOptions

	cmd = 'gdalwarp ' + warpOptions + dem_vrt + ' ' + dem_tif
	if verbose:
		print cmd
	err = os.system(cmd)
	if err != 0:
		print('ERROR: dem could not be generated:', err)
		sys.exit(-1)

def	build_tif_slope(dx, region, dir):
	dem_tif 	= os.path.join(dir, dx+"_dem.tif")
	dem_slope 	= os.path.join(dir, dx+"_dem_slope.tif")

	if force or not os.path.isfile(dem_slope):
		cmd = "gdaldem slope -s 111120 " + dem_tif + " " + dem_slope 
		if verbose:
			print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: slope file could not be generated:', err)
			sys.exit(-1)

# Generate a binary file based on slope
def	build_slope_bin(dx, region, dir):
	dem_slope		= os.path.join(dir, dx+"_dem_slope.tif")
	dem_slope_bin 	= os.path.join(dir, dx+"_dem_slope_bin.tif")
	
	if force or not os.path.isfile(dem_slope_bin):
		driver 			= gdal.GetDriverByName("GTiff")
		src_ds 			= gdal.Open( dem_slope )
		ncols 			= src_ds.RasterXSize
		nrows 			= src_ds.RasterYSize
		band 			= src_ds.GetRasterBand(1)
		
		if verbose:
			print "get slope binary data...", ncols, nrows
			
		data 			= band.ReadAsArray(0, 0, ncols, nrows )
		projection   	= src_ds.GetProjection()
		geotransform 	= src_ds.GetGeoTransform()

		lessthan1 		= numpy.where( data<1 )
	
		data[ numpy.where( data<15 )] = 1
		data[ lessthan1 ] = 0		
		data[ numpy.where( data>30 )] = 5
		data[ numpy.where( data>25 )] = 4
		data[ numpy.where( data>20 )] = 3
		data[ numpy.where( data>15 )] = 2
		
		#data[ numpy.where( data<15 )] = 0
		#data[ numpy.where( data>=15 )] = 1
		
		print "done"
		
		dst_ds 		= driver.Create(dem_slope_bin, ncols, nrows, 1, gdal.GDT_Byte)
		outband 	= dst_ds.GetRasterBand(1)
		outband.WriteArray(data.astype(numpy.uint8), 0, 0)
		
		dst_ds.SetGeoTransform( geotransform )
		dst_ds.SetGeoTransform( geotransform )
		
		#dst_ds 		= None
		#src_ds 		= None

def build_contours(dx, region, dir):
	dem_slope_bin 	= os.path.join(dir, dx+"_dem_slope_bin.tif")
	map_rgb		 	= os.path.join(dir, dx+"_dem_slope_bin_rgb.tif")
	map_pgm		 	= os.path.join(dir, dx+"_dem_slope_bin.pgm")
	map_png		 	= os.path.join(dir, dx+"_dem_slope_bin.png")
	map_tif		 	= os.path.join(dir, dx+"_dem_slope_bin_tif.tif")
	map_bmp		 	= os.path.join(dir, dx+"_dem_slope_bin.bmp")
	map_geojson		= os.path.join(dir, dx+"_map.geojson")
	map_topojson 	= os.path.join(dir, dx+"_map.topojson")
	map_json 		= os.path.join(dir, dx+"_map.json")
	map_osm			= os.path.join(dir, dx+"_map.osm")
	map_bz2			= os.path.join(dir, dx+"_map.osm.bz2")
	map_properties	= os.path.join(dir, dx+"_map.properties.txt")
	
	color_file		= "./susmap_colors.txt"
	
	indataset 	= gdal.Open( dem_slope_bin )
	geomatrix 	= indataset.GetGeoTransform()
	rasterXSize = indataset.RasterXSize
	rasterYSize = indataset.RasterYSize

	xorg		= geomatrix[0]
	yorg  		= geomatrix[3]
	pres		= geomatrix[1]
	xmax		= xorg + geomatrix[1]* rasterXSize
	ymax		= yorg - geomatrix[1]* rasterYSize
	
	print "geojson bbox:", xorg, yorg, xmax, ymax, pres
	
	# turn slope bin into a tif
	if force or not os.path.exists(map_rgb):
		cmd = "gdaldem color-relief -alpha " +  dem_slope_bin + " " + color_file + " " + map_rgb
		if verbose:
			print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: slope file could not be generated:', err)
			sys.exit(-1)

	# convert to bmp for potrace input
	if force or not os.path.exists(map_bmp):
		# subset it, convert red band (band 1) and output to .pgm using PNM driver
		cmd = "gdal_translate -b 1 -of BMP -ot Byte %s %s" % (map_rgb, map_bmp)
		os.system(cmd)
		if verbose:
			print( cmd )
		os.system("rm -f "+map_bmp+".aux.xml")
		
	# Convert to geosjon
	if force or not os.path.isfile(map_geojson):
		cmd = str.format("potrace -z black -a 1.5 -O 0.5 -t 10 -i -b geojson -o {0} {1} -x {2} -L {3} -B {4} ", map_geojson, map_bmp, pres, xorg, ymax ); 
		if verbose:
			print(cmd)
		os.system(cmd)
	
	# Convert to topojson to simplify the polygons by 90%
	if force or not os.path.isfile(map_topojson):
		cmd = "topojson --bbox --simplify-proportion 0.9 " +  map_geojson + " -o " + map_topojson
		if verbose:
			print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: topojson file could not be generated:', err)
			sys.exit(-1)
	
	# Then we need to convert it back to geojson
	if force or not os.path.isfile(map_json):
		cmd = str.format("geojson --precision 5 -o {0} {1}", dir, map_topojson)
		if verbose:
			print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: simplified geojson file could not be generated:', err)
			sys.exit(-1)
	
	# Create properties file
	properties = "{  \"boundary\": \"landslide_susceptibility_map\",\n\t\"risk_level\": 1 }"
	pfile = open(map_properties, "w+")
	pfile.write(properties)
	pfile.close()
	
	# Convert to OSM
	if force or not os.path.isfile(map_osm):
		cmd = str.format("../geojson2osm.js --properties {0} -o {1} {2}", map_properties, map_osm, map_json)
		if verbose:
			print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: osm file could not be generated:', err)
			sys.exit(-1)

	# Compress to bz2
	if force or not os.path.isfile(map_bz2):
		cmd = str.format("rm {0}", map_bz2)
		os.system(cmd)
		
		cmd = str.format("bzip2 {0}", map_osm)
		if verbose:
			print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: bz2 osm file could not be generated:', err)
			sys.exit(-1)

	# Then we need to import it into the production database
	# osmosis --read-xml file="map.osm" --write-apidb populateCurrentTables=yes host="localhost" database="landslide-dev" user="postgres" password="openstreetmap" validateSchemaVersion=no
	
	# Create a changeset and import to realtime database
	
	
	indataset = None
	

def	build_color_relief(dx, region, dir):
	dem_tif 			= os.path.join(dir, dx+"_dem.tif")
	dem_color_relief 	= os.path.join(dir, dx+"_dem_color_relief.tif")
	color_file			= os.path.join(".", "dem_color_relief.txt")
	
	cmd = "gdaldem color-relief -alpha " +  dem_tif + " " + color_file + " " + dem_color_relief
	if verbose:
		print cmd
	err = os.system(cmd)
	if err != 0:
		print('ERROR: slope file could not be generated:', err)
		sys.exit(-1)

def	build_hillshade(dx, region, dir):
	dem_tif 		= os.path.join(dir, dx+"_dem.tif")
	dem_hillshade 	= os.path.join(dir, dx+"_dem_hillshade.tif")
	
	cmd = "gdaldem hillshade -co compress=lzw " + dem_tif + " " + dem_hillshade
	if verbose:
		print cmd
	err = os.system(cmd)
	if err != 0:
		print('ERROR: hillshade file could not be generated:', err)
		sys.exit(-1)

def generate_map( dx ):
	# make sure it exists
	region		= config.regions[dx]
	
	if verbose:
		print "Processing Susceptibility Map for Region:", dx, region['name']	
	
	# Destination Directory
	dir			= os.path.join(config.data_dir, "susmap", dx)
	if not os.path.exists(dir):
		os.makedirs(dir)
	
	build_dem_vrt(dx, region, dir)
	build_tif_bbox(dx, region, dir)
	build_tif_slope(dx, region, dir)
	build_hillshade(dx, region, dir)
	build_color_relief(dx, region, dir)
	build_slope_bin(dx, region, dir)
	build_contours(dx, region, dir)
	
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

	parser 		= argparse.ArgumentParser(description='Generate Susceptibility Maps')
	apg_input 	= parser.add_argument_group('Input')
	
	apg_input.add_argument("-f", "--force", action='store_true', help="new products to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose

	generate_map('d03')
	generate_map('d02')
	print "Done."


