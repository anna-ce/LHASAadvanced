#!/usr/bin/env python
#
# Returns vals on boox edges
#
import os, sys
import osgeo.gdal as gdal
import numpy
import config

#inFile 	= sys.argv[1]
#outFile	= sys.argv[3]

#infile_name		= "d02/20140820_20140822/sm_d02_20140820_20140822_1km.tif"
infile_name		= "d02/20140820_20140822/sm_d02_20140820_20140822_1km.tif"
inFile 			= os.path.join(config.data_dir, "smos", infile_name)

outfile_name	= "d02/20140820_20140822/20140820_20140822.smp.tif.bbox.txt"
outFile 		= os.path.join(config.data_dir, "smos", outfile_name)

# Get information from image
dataset 		= gdal.Open(inFile, gdal.GA_ReadOnly )
projection 		= dataset.GetProjection()
geotransform 	= dataset.GetGeoTransform()

xSize 			= dataset.RasterXSize
ySize 			= dataset.RasterYSize

# Get bounding box
minX 			= geotransform[0]
maxY 			= geotransform[3]
pixSizeX 		= geotransform[1]
pixSizeY 		= geotransform[5]
maxX 			= minX + (xSize * pixSizeX)
minY 			= maxY + (ySize * pixSizeY)

ncols 			= dataset.RasterXSize
nrows 			= dataset.RasterYSize
band 			= dataset.GetRasterBand(1)
data 			= band.ReadAsArray(0, 0, ncols, nrows )

nodata = band.GetNoDataValue()
print "NDV", nodata
print "minX,maxY,pixSizeX,pixSize", minX, maxY, pixSizeX, pixSizeY


myArray			= numpy.array(data)

myArray 		= numpy.ma.masked_equal(myArray, nodata)
	
print ncols, nrows
print myArray.shape, myArray.size

maxLatArray		= myArray[0,:]
print maxLatArray.shape, maxLatArray.size
#print maxLatArray[0:200]

minLatArray		= myArray[nrows-1,:]
print minLatArray.shape, minLatArray.size
#print maxLatArray

minLongArray	= myArray[:,0]
print minLongArray.shape, minLongArray.size
#print minLongArray

maxLongArray	= myArray[:,ncols-1]
print maxLongArray.shape, maxLongArray.size
#print maxLongArray

msg = "["
msg += "{ \"type\": \"maxLatArray\",\n"
msg += " \"value\": " + str(maxY) + ',\n'
msg += " \"array\": [" + '\n'

for c in range(ncols):
	msg += "  [" + str(minX+c*pixSizeX) + ", " + str(maxLatArray[c])+"]"
	if c < (ncols-1):
		msg += ",\n"

msg += ']},\n'

msg += "{ \"type\": \"minLatArray\",\n"
msg += " \"value\": " + str(minY) + ',\n'
msg += " \"array\": [" + '\n'

for c in range(ncols):
	msg += "  [" + str(minX+c*pixSizeX) + ", " + str(minLatArray[c])+"]"
	if c < (ncols-1):
		msg += ",\n"

msg += ']},\n'

msg += "{ \"type\": \"minLongArray\",\n"
msg += " \"value\": " + str(minX) + ',\n'
msg += " \"array\": [" + '\n'

for r in range(nrows):
	msg += "  [" + str(maxY-r*pixSizeY) + ", " + str(minLongArray[r])+"]"
	if r < (nrows-1):
		msg += ",\n"

msg += ']},\n'

msg += "{ \"type\": \"maxLongArray\",\n"
msg += " \"value\": " + str(maxX) + ',\n'
msg += " \"array\": [" + '\n'

for r in range(nrows):
	msg += "  [" + str(maxY-r*pixSizeY) + ", " + str(maxLongArray[r])+"]"
	if r < (nrows-1):
		msg += ",\n"

msg += ']\n'
msg += "}]"

file = open(outFile, "w")
file.write(msg)
file.close()
