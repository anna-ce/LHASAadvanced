import sys, os, inspect
import argparse
from osgeo import osr, gdal

# =======================================================================
# Main
#
if __name__ == '__main__':
	
	parser = argparse.ArgumentParser(description='Process susceptibility maps')
	apg_input = parser.add_argument_group('Input')
	apg_input.add_argument("-f", "--file")
	apg_input.add_argument("-", "--lat")
	apg_input.add_argument("-r", "--lng")

	options 	= parser.parse_args()
	
	file 	= options.file
	lat		= options.lat
	lng		= options.lng
	
	print file, lat, lng
	
	drv 	= gdal.GetDriverByName('GTiff')
	src_ds 	= gdal.Open( file )

	band 	= src_ds.GetRasterBand(1)
	data 	= band.ReadAsArray(0, 0, src_ds.RasterXSize, src_ds.RasterYSize )
	
	print "size ", src_ds.RasterXSize,"x", src_ds.RasterYSize
	
	for r in range(src_ds.RasterYSize):
		print "r:", r, data[r]
		#for c in range( src_ds.RasterXSize ):
			#pos = r*src_ds.RasterXSize + c
		#	print data[r]
			
	