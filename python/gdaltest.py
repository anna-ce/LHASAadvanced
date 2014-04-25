#!/usr/bin/env python
#
# Created on 11/21/2013 Pat Cappelaere - Vightel Corporation
#
# Generates Susceptibility Maps for Landslides Application
#
import numpy, sys, os
import argparse

from osgeo import osr, gdal
import config

dx = 'd03'
force = 0
dir			= os.path.join(config.data_dir, "susmap", dx)

version_num = int(gdal.VersionInfo('VERSION_NUM'))
print "GDAL Version:", version_num

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