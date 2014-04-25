#!/usr/bin/env python

from osgeo import gdal, gdalconst

dir = "/Users/patricecappelaere/landslide/data/trmm/d03/"

# Source
src_filename 	= dir + 'trmm_24_d03_20140418_subset_4326.tif'
src 			= gdal.Open(src_filename, gdalconst.GA_ReadOnly)
src_proj 		= src.GetProjection()
src_geotrans 	= src.GetGeoTransform()
wide 			= src.RasterXSize
high 			= src.RasterYSize

print src_geotrans

scale 			= 10
#src_geotrans[1]	= src_geotrans[1]/scale
#src_geotrans[5]	= src_geotrans[5]/scale

# Output / destination
dst_filename = dir + 'trmm_24_d03_20140418_subset_4326_reproj.tif'
dst = gdal.GetDriverByName('GTiff').Create(dst_filename, wide*scale, high*scale, 1, gdalconst.GDT_Float32)
dst.SetGeoTransform( [src_geotrans[0],src_geotrans[1]/scale, src_geotrans[2], src_geotrans[3],src_geotrans[4],src_geotrans[5]/scale] )
dst.SetProjection( src_proj)

# Do the work
gdal.ReprojectImage(src, dst, None, None, gdalconst.GRA_Lanczos)

del dst # Flush
del src # Flush