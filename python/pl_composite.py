#!/usr/bin/env python
#
# Created on 07/11/2014 Pat Cappelaere - Vightel Corporation
#

import os, inspect, sys
import argparse
import numpy
import config
import json

from osgeo import gdal_array, gdal

DATA_DIR		= "/Users/patricecappelaere/Development/ojo/ojo-bot/tmp"
PL_DIR			= DATA_DIR + "/planet-labs"
BASE_URL		= "https://api.planet.com/v0/scenes/ortho/"

band_luts		= []

def execute( cmd ):
	if verbose:
		print cmd
	os.system(cmd)
	
# python pl_composite.py --scene 8g3oO2
if __name__ == '__main__':
	parser 		= argparse.ArgumentParser(description='Generate Planet-Labs RGB Composite')
	apg_input 	= parser.add_argument_group('Input')
	
	apg_input.add_argument("-f", "--force", 	action='store_true', help="Forces new product to be generated")
	apg_input.add_argument("-v", "--verbose", 	action='store_true', help="Verbose on/off")
	apg_input.add_argument("-s", "--scene", 	required=1, help="PlanetLabs Scene")
	
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose
	scene		= options.scene

	json_data	= open('lut-color-curve.json')
	lut 		= json.load(json_data)
	
	for key in ['red', 'green', 'blue', 'master']:
		key_lut = numpy.array(lut[key][0:4095:16])/16
		band_luts.append(key_lut.tolist())
	
	fileName		= os.path.join(PL_DIR, scene, scene+"_full_4326.tif")
	outputfileName	= os.path.join(PL_DIR, scene, scene+"_full_4326_rgb.tif")
	
	img = gdal_array.LoadFile(fileName)
	
	for band_index in range(3):
		img[band_index] = numpy.take(band_luts[band_index], img[band_index],mode='clip')
		img[band_index] = numpy.take(band_luts[3], img[band_index])

	gdal_array.SaveArray(img, outputfileName, prototype = gdal.Open(fileName))
	