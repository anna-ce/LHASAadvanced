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

# Site configuration
import config
dem_dir 	= "/Volumes/MacBay3/HAND/HydroSHEDS"
# Hysdrosheds tiles are 5x5 deg @90m (3 arc-second resolution)
# named after lower left corner

def	build_dem_vrt(dx, region, dir):
	dem_vrt = os.path.join(dir, dx+"_dem.vrt")
	if not force and os.path.isfile(dem_vrt):
		print dem_vrt+ " exists!"
		return
	
	cmd 	= "gdalbuildvrt " + dem_vrt
	files 	= " "
	
	for tile in region['hydroshed_tiles']:
		fileName = os.path.join(dem_dir, tile)
		if not os.path.exists( fileName):
			print "File:", fileName, " does not exist"
		else:
			basename = tile.split("/")
			dem_bil  = basename[1]+"_dem_bil"
			files += fileName + "/"+ dem_bil + "/" + basename[1]+"_dem.bil "
	
	cmd += files
	print cmd
	err = os.system(cmd)
	
# Create bbox subset @1km
def	build_tif_bbox(dx, region, dir):
	dem_vrt = os.path.join(dir, dx+"_dem.vrt")
	dem_tif = os.path.join(dir, dx+"_dem.tif")
	if not force and os.path.isfile(dem_tif):
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
		print "Loading ", dem_slope
		driver 			= gdal.GetDriverByName("GTiff")
		src_ds 			= gdal.Open( dem_slope )
		ncols 			= src_ds.RasterXSize
		nrows 			= src_ds.RasterYSize
		band 			= src_ds.GetRasterBand(1)
		print "get slope binary data...", ncols, nrows
		data 			= band.ReadAsArray(0, 0, ncols, nrows )
		
		print "get projection..."
		projection   	= src_ds.GetProjection()
		print "get transform..."
		geotransform 	= src_ds.GetGeoTransform()

		print "thresholding..."
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
		
		dst_ds 		= None
		src_ds 		= None

def build_contours(dx, region, dir):
	dem_slope_bin 	= os.path.join(dir, dx+"_dem_slope_bin.tif")
	dem_contour 	= os.path.join(dir, dx+"_dem_countours.tif")
	color_file		= "./susmap_colors.txt"
	
	if force or not os.path.isfile(dem_contour):
		cmd = "gdaldem color-relief -alpha " +  dem_slope_bin + " " + color_file + " " + dem_contour
		print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: geokson file could not be generated:', err)
			sys.exit(-1)
	
def	build_json_files(dx, region, dir):
	dem_slope_bin 	= os.path.join(dir, dx+"_dem_slope_bin.tif")
	dem_geojson 	= os.path.join(dir, dx+"_dem_slope_bin.geojson")
	dem_topojson 	= os.path.join(dir, dx+"_dem_slope_bin.topojson")

	if force or not os.path.isfile(dem_geojson):
		cmd ="gdal_contour -f geoJSON -a susceptibility -i 1 " +  dem_slope_bin + " " + dem_geojson
		print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: geokson file could not be generated:', err)
			sys.exit(-1)

	if force or not os.path.isfile(dem_topojson):
		cmd ="topojson --bbox --simplify 0.5 " +  dem_geojson + " -o " + dem_topojson
		print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: topojson file could not be generated:', err)
			sys.exit(-1)


def	build_color_relief(dx, region, dir):
	dem_tif 			= os.path.join(dir, dx+"_dem.tif")
	dem_color_relief 	= os.path.join(dir, dx+"_dem_color_relief.tif")
	color_file			= os.path.join(config.data_dir, "dem_slope_colors.txt")
	
	cmd = "gdaldem color-relief -alpha " +  dem_tif + " " + dem_color_relief + " " + dem_color_relief
	print cmd
	err = os.system(cmd)
	if err != 0:
		print('ERROR: slope file could not be generated:', err)
		sys.exit(-1)

def	build_hillshade(dx, region, dir):
	dem_tif 		= os.path.join(dir, dx+"_dem.tif")
	dem_hillshade 	= os.path.join(dir, dx+"_dem_hillshade.tif")
	cmd = "gdaldem hillshade -co compress=lzw " + dem_tif + " " + dem_hillshade
	print cmd
	err = os.system(cmd)
	if err != 0:
		print('ERROR: hillshade file could not be generated:', err)
		sys.exit(-1)

def generate_map( dx , force, verbose ):
	# make sure it exists
	region		= config.regions[dx]
	
	print "Processing Susceptibility Map for Region:", dx, region['name']	
	
	# Destination Directory
	dir			= os.path.join(config.data_dir, "susmap", dx)
	if not os.path.exists(dir):
		os.makedirs(dir)
	
	#build_dem_vrt(dx, region, dir)
	#build_tif_bbox(dx, region, dir)
	#build_tif_slope(dx, region, dir)
	#build_hillshade(dx, region, dir)
	#build_color_relief(dx, region, dir)
	build_slope_bin(dx, region, dir)
	build_contours(dx, region, dir)
	#build_json_files(dx, region, dir)
#
# Main
#
if __name__ == '__main__':
	version_num = int(gdal.VersionInfo('VERSION_NUM'))
	if version_num < 1800: # because of GetGeoTransform(can_return_null)
		print('ERROR: Python bindings of GDAL 1.8.0 or later required')
		sys.exit(1)

	parser 		= argparse.ArgumentParser(description='Generate Susceptibility Maps')
	apg_input 	= parser.add_argument_group('Input')
	
	apg_input.add_argument("-f", "--force", action='store_true', help="HydroSHEDS forces new water image to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose

	generate_map('d03', force, verbose)
	#generate_map('d02', force, verbose)
	print "Done."


