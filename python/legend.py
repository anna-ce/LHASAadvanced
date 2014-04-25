#!/usr/bin/env python

# Creates a legend out of a color file
#
# Requires PIL
#

import os, sys, inspect
import argparse

import Image, ImageDraw, ImageFont
import textwrap
import numpy as np
import tempfile
from array import array

class LEGEND:
	def __init__( self, colorFileName, outputFileName, title ):
		self.colorFileName 	= colorFileName
		self.outputFileName	= outputFileName
		self.title			= title
		self.min			=  999999
		self.max			= -999999
		
	def parseColorFile(self):
		self.data 	= np.genfromtxt(colorFileName, dtype=None)
		#print self.data
		self.count  = 0
		# find min and max of non transparent items
		for line in self.data:
			#print line[0]
			if line[4] != 0:
				if line[0] < self.min:
					self.min = line[0]
				if line[0] > self.max:
					self.max = line[0]
				self.count += 1
		print "find count %d min %d max %d" %(self.count, self.min, self.max)
				
	def generateColormap(self):
		rng 	= self.max - self.min
		step	= rng/255.0
		
		# generate image
		size 	= 85, 290 
		im 		= Image.new('RGB', size, "white")
		pix		= im.load()
		
		value 	= self.max
		
		xoffset = 15
		yoffset = 5
		
		for iy in np.arange(255):
			for ix in np.arange(25):
				#print iy, int(value)
				im.putpixel( (ix+xoffset,iy+yoffset), int(value))
			value -= step
			
		tf 		= tempfile.NamedTemporaryFile()
		tmpName = tf.name + ".tif"
		
		print "writing", tmpName
		im.save(tmpName)
		
		cmd = "gdaldem color-relief "+ tmpName + " " + self.colorFileName + " " + self.outputFileName
		print cmd
		os.system(cmd) 
		
		os.remove(tmpName)
				
	def addNumbers(self):
		im				= Image.open(self.outputFileName)
		draw			= ImageDraw.Draw(im)
		text			= "" 
		rng 			= self.max - self.min
		step			= rng/255.0
		X				= 50
		Y				= 245
		#font_file   	= "./pilfonts/helvB08.pil"
		font_file   	= "./pilfonts/timR10.pil"
		font 			= ImageFont.load(font_file)
		fontsize		= 10
		#font			= 'arial'
		#font = ImageFont.truetype("media/text/fonts/" + font + ".ttf", fontsize, encoding="unic")
		
		print "rng %f step %f count %d"%(rng,step, self.count)
		
		# total height 	= 255
		# num labels 	= self.count
		dy = 255.0/self.count
		print "dy %f", dy
		for line in self.data:
			if line[4] != 0:
				value 	= line[0]
				height 	= value * step
				text	= "%4d" % value
				#print "y: %f %s" % (Y,text)
				draw.text((X, Y), text, (0,0,0), font=font)
				Y -= dy
		
		print "add title:", self.title
		draw.text((5,265),self.title, font=font, fill=(0,0,0,255))
		
		im.save(self.outputFileName)
		 
				
#
# Main
# Usage: legend.py --file colors.txt --output color.png
#
if __name__ == '__main__':
	print "Do elevation legend..."
	parser 		= argparse.ArgumentParser(description='Generate Legend')
	apg_input 	= parser.add_argument_group('Input')	
	apg_input.add_argument("-f", "--file", nargs=1, help="color file used by gdadem")
	apg_input.add_argument("-o", "--output", nargs=1, help="color legend")
	apg_input.add_argument("-t", "--title", nargs=1, help="color title")
	
	options 	= parser.parse_args()
		
	if options.file:
		colorFileName 	= options.file[0]
	else:
		colorFileName 	= './colors.txt'
		
	if options.output:
		outputFileName 	= options.output[0]
	else:
		outputFileName	= './legend.png'
		
	if options.title:
		title = options.title[0]
	else:
		title = "Precipitation"
		
	app = LEGEND(colorFileName, outputFileName, title )
	app.parseColorFile()
	app.generateColormap()
	app.addNumbers()