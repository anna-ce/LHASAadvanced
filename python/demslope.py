#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Requirements:
#	gdal, numpy pytrmm...
#
# Access and Process DEM
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
from scipy import stats

# Site configuration
import config

dem_dir 	= "/Volumes/MacBay3/HAND/HydroSHEDS"
d3_dem_vrt 	= "/Volumes/MacBay3/HAND/hand/d3_dem_4326.vrt"

d3_tiles = [
"CA/n15w070",
"CA/n15w075",
"CA/n15w080",
"CA/n20w075",
"CA/n20w080"
]

def process_dem_d03_file(force):
	#filename			= "dem_d3"
	#filename			= "n15w075_dem_3857"
	#filename			= "dem_3857"
	filename			= "dem_d3_4326"
	dem 				= os.path.join(config.data_dir,filename+".tif")
	dem_slope 			= os.path.join(config.data_dir,filename+"_slope.tif")
	dem_slope_bin		= os.path.join(config.data_dir,filename+"_slope_bin.tif")
	dem_slope_bin_rgb	= os.path.join(config.data_dir,filename+"_slope_bin_rgb.tif")
	dem_shp				= os.path.join(config.data_dir,filename+"_slope.shp")
	dem_geojson			= os.path.join(config.data_dir,filename+"_slope.geojson")
	dem_topojson		= os.path.join(config.data_dir,filename+"_slope.topojson")
	
	slopeshade		 	= os.path.join(config.data_dir,filename+"_slopeshade.tif")
	hillshade		 	= os.path.join(config.data_dir,filename+"_hillshade.tif")
	
	slope_txt_file 		= os.path.join(config.data_dir, "color_slope.txt")
	bin_slope_txt_file 	= os.path.join(config.data_dir, "dem_slope_colors.txt")

	d3 					= config.d3
	#pixSizeX 			= 0.000833333333333
	#pixSizeY 			= 0.000833333333333
	pixSizeX 			= 0.008999
	pixSizeY 			= 0.008999
	
	if force or not os.path.isfile(dem):
		# Create gdalwarp command
		ofStr 			= ' -of GTiff' 
		bbStr 			= ' -te %s %s %s %s '%(d3[0], d3[1], d3[2], d3[3]) 
		resStr 			= ' -tr %s %s '%(pixSizeX, pixSizeY)
		overwriteStr 	= ' -overwrite ' # Overwrite output if it exists
		additionalOptions = ' -co COMPRESS=LZW -dstalpha ' # Additional options
		#warpOptions 	= ofStr + bbStr + resStr + projectionStr + overwriteStr + additionalOptions
		warpOptions 	= ofStr + bbStr + resStr + overwriteStr + additionalOptions

		cmd = 'gdalwarp ' + warpOptions + d3_dem_vrt + ' ' + dem
		print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: dem could not be generated:', err)
			sys.exit(-1)
	
	# WARNING: we are in 4326 to use scale
	#if force or not os.path.isfile(hillshade):
	#	cmd = "gdaldem hillshade -co compress=lzw -s 111120 " + dem + " " + hillshade 
	#	print cmd
	#	err = os.system(cmd)
	#	if err != 0:
	#		print('ERROR: slope file could not be generated:', err)
	#		sys.exit(-1)

	# WARNING: we are in 4326 so we need to use scale
	if force or not os.path.isfile(dem_slope):
		cmd = "gdaldem slope -s 111120 " + dem + " " + dem_slope 
		print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: slope file could not be generated:', err)
			sys.exit(-1)
	
	if force or not os.path.isfile(dem_slope_bin):
		driver 			= gdal.GetDriverByName("GTiff")
		src_ds 			= gdal.Open( dem_slope )
		ncols 			= src_ds.RasterXSize
		nrows 			= src_ds.RasterYSize
		band 			= src_ds.GetRasterBand(1)
		data 			= band.ReadAsArray(0, 0, ncols, nrows )
		
		projection   	= src_ds.GetProjection()
		geotransform 	= src_ds.GetGeoTransform()

		print "thresholding..."
		lessthan1 		= numpy.where( data<1 )
	
		data[ numpy.where( data<15 )] = 1
		data[ lessthan1 ] = 0		
		data[ numpy.where( data>30 )] = 5
		data[ numpy.where( data>25 )] = 4
		data[ numpy.where( data>20 )] = 3
		data[ numpy.where( data>15 )] = 2
		
		print "done"
		
		dst_ds 		= driver.Create(dem_slope_bin, ncols, nrows, 1, gdal.GDT_Byte)
		outband 	= dst_ds.GetRasterBand(1)
		outband.WriteArray(data.astype(numpy.uint8), 0, 0)
		
		dst_ds.SetGeoTransform( geotransform )
		dst_ds.SetGeoTransform( geotransform )
		
		dst_ds 		= None
		src_ds 		= None
		data	 	= None
	
	if force or not os.path.isfile(dem_slope_bin_rgb):
		cmd ="gdaldem color-relief -alpha " +  dem_slope_bin + " " + bin_slope_txt_file + " " + dem_slope_bin_rgb
		print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: dem_slope_bin_rgb file could not be generated:', err)
			sys.exit(-1)
			
 	if force or not os.path.isfile(slopeshade):
		cmd ="gdaldem color-relief -alpha " +  dem_slope + " " + slope_txt_file + " " + slopeshade
		print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: slopeshade file could not be generated:', err)
			sys.exit(-1)

	if force or not os.path.isfile(dem_shp):
		cmd ="gdal_contour -a susceptibility -i 1 " +  dem_slope_bin + " " + dem_shp
		print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: geokson file could not be generated:', err)
			sys.exit(-1)


	if force or not os.path.isfile(dem_geojson):
		cmd ="gdal_contour -f geoJSON -a susceptibility -i 1 " +  dem_slope_bin + " " + dem_geojson
		print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: geokson file could not be generated:', err)
			sys.exit(-1)

	if force or not os.path.isfile(dem_topojson):
		cmd ="topojson " +  dem_geojson + " -o " + dem_topojson
		print cmd
		err = os.system(cmd)
		if err != 0:
			print('ERROR: topojson file could not be generated:', err)
			sys.exit(-1)

def build_d3_dem_vrt(force):
	if not force and os.path.isfile(d3_dem_vrt):
		print d3_dem_vrt+ " exists!"
		return
 	
	cmd 	= "gdalbuildvrt " + d3_dem_vrt
	files 	= " "
	for name in d3_tiles:
		ar 	= name.split('/')
		zone = ar[0]
		tile = ar[1]
		dem_file = os.path.join(dem_dir, zone, tile, tile+"_dem_bil", tile+"_dem.bil" )

		files += dem_file + " "

	cmd += files
	print cmd
	err = os.system(cmd)
#
# Main
#
if __name__ == '__main__':
	version_num = int(gdal.VersionInfo('VERSION_NUM'))
	if version_num < 1800: # because of GetGeoTransform(can_return_null)
		print('ERROR: Python bindings of GDAL 1.8.0 or later required')
		sys.exit(1)

	parser 		= argparse.ArgumentParser(description='Generate HAND')
	apg_input 	= parser.add_argument_group('Input')
	apg_input.add_argument("-f", "--force", action='store_true', help="HydroSHEDS forces new water image to be generated")
	options 	= parser.parse_args()

	force		= options.force

	build_d3_dem_vrt(force)

	#process_dem_d01_file()
	#process_dem_d02_file()
	process_dem_d03_file(force)
