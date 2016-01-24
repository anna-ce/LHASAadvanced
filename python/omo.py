import sys, os, inspect, math
import datetime
from datetime import date
from dateutil.parser import parse
import cubehelix

from osgeo import gdal
import numpy

# Site configuration
import config
import argparse

# http://www.temis.nl/docs/OMI_NO2_HE5_2.0_2011.pdf
# https://github.com/jradavenport/cubehelix
# http://bl.ocks.org/mbostock/11415064
# http://www.ifweassume.com/2014/04/cubehelix-colormap-for-python.html

maxval		= 144
fibvalues 	= [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]

# matplotlib.colors.LinearSegmentedColormap
#cx 			= cubehelix.cmap(start=0., rot=-0.5, nlev=maxval+1)
#cmap_vals	= cx._segmentdata

#for index in range(0,maxval+1):
#	print index, int(cmap_vals['red'][index][1]*255), int(cmap_vals['green'][index][1]*255), int(cmap_vals['blue'][index][1]*255), 255

verbose 	= 1
force 		= 0

def execute( cmd ):
	if verbose:
		print cmd
	os.system(cmd)

# ======================================================================
#	python geos5.py --date 2015-08-10 -v
#
if __name__ == '__main__':

	parser 		= argparse.ArgumentParser(description='GEOS-5 Processing')
	apg_input 	= parser.add_argument_group('Input')
	apg_input.add_argument("-f", "--force", action='store_true', help="forces new product to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	apg_input.add_argument("-d", "--date", 	help="Date")

	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose
	
	todaystr	= date.today().strftime("%Y-%m-%d")
	dt			= options.date or todaystr
	
	today		= parse(dt)
	tomorrow	= today + datetime.timedelta(hours=24)
	
	year		= today.year
	month		= today.month
	day			= today.day
	doy			= today.strftime('%j')
	
	ymd 		= "%d%02d%02d" % (year, month, day)

	mydir 		= os.path.join(config.DATA_DIR, "omi", str(year), doy)
	filename	= os.path.join(mydir, "%04d_%02d_%02d_NO2TropCS30.hdf5" % (year, month, day))

	dstfilename	= filename.replace(".hdf5", ".tif")
	rgbfilename	= filename.replace(".hdf5", "_rgb.tif")
	color_file	= "./cluts/omi_cubehelix_org_144.txt"
	
	ds 			= gdal.Open(filename)
	
	band		= ds.GetRasterBand(1)
	data		= band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize )
	
	data		/= 1e+15
	
	data.astype(int)
		
	driver 				= gdal.GetDriverByName( "GTiff" )
	dst_ds_dataset		= driver.Create( dstfilename, ds.RasterXSize, ds.RasterYSize, 1, gdal.GDT_Float32, [ 'COMPRESS=DEFLATE' ] )
	dst_band		 	= dst_ds_dataset.GetRasterBand(1)
	o_data				= dst_band.ReadAsArray(0, 0, dst_ds_dataset.RasterXSize, dst_ds_dataset.RasterYSize )
	dst_band.SetNoDataValue(-32768)
	
	dst_band.WriteArray(data, 0, 0)

	ds 					= None
	dst_ds_dataset		= None
	
	cmd = "gdaldem color-relief -q -alpha -nearest_color_entry -of GTiff %s %s %s" % ( dstfilename, color_file, rgbfilename)
	execute(cmd)

	
	
	