#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Requirements:
#
# Convert DB to geojson
#
import os, sys, inspect
import array
from datetime import date
import csv
import argparse
import urllib
from lxml import etree
#import xml.etree.ElementTree as ET

# Site configuration
import config

#	Start from Excel ouptut in XML
# db.py -x -o db2.osm
# osm2change.py db2.osm (-> db2.osc)
# upload.py -m "Changeset Comment" -c yes db2.osc
#

def toOSM( row ):
	id			= row[2] 
	date 		= "%04d-%02d-%02d" % ( int(row[4]), int(row[5]), int(row[6]))
	trigger		= row[8]
	latitude	= row[9]
	longitude	= row[10]
	radius		= row[11]
	loc_class 	= row[12]
	size_class  = row[13]
	fatalities	= row[14]
	damages		= row[15]
	road		= row[16]
	#evt_type	= row[16]
	link		= urllib.quote(row[17])
	#source		= row[24]
	#comments	= row[25]
	
	# we need to check the length of the link and see if it exists
	if len(link) >= 255:
		link= ""
		print '** Link > 255 for record id:'+id
		
	if link.find('//maps.google.com') > 0 :
		link= ""
		print '** Removed maps.google.com link for record id:'+id
		
	if( len(trigger) >= 255):
		trigger= trigger[0:254]
		print '** trigger > 255 for record id:'+id
		
	if( len(damages) >= 255):
		damages= damages[0:254]
		print '** damages > 255 for record id:'+id
		
	if( len(fatalities) >= 255):
		damages= fatalities[0:254]
		print '** fatalities > 255 for record id:'+id
		
	osm = '<node id=\"-' + id +'\" version="1"'
	osm += ' lat="'+ latitude + '" lon="'+ longitude +'" visible="true" timestamp="'+ date +'">\n'
	osm += '    <tag k="hazard_prone" v="yes" /> \n'
	osm += '    <tag k="hazard_type" v="landslide" />\n'

	osm += '    <tag k="dk:trigger" v="' + trigger + '" />\n'
	osm += '    <tag k="dk:radius" v="' + radius + '" />\n'
	osm += '    <tag k="dk:loc_class" v="' + loc_class + '" />\n'
	osm += '    <tag k="dk:size_class" v="' + size_class + '" />\n'
	osm += '    <tag k="dk:fatalities" v="' + fatalities + '" />\n'
	osm += '    <tag k="dk:damages" v="' + damages + '" />\n'
	#osm += '    <tag k="dk:evt_type" v="' + evt_type + '" />\n'
	osm += '    <tag k="dk:link" v="' + link + '" />\n'
	#osm += '    <tag k="dk:source" v="' + source + '">\n'
	#osm += '    <tag k="dk:comments" v="' + comments + '">\n'
	
	osm += '</node>\n'
	
	return osm
	
def to_geojson( row ):
	json 		= ""
	id			= row[2] 
	date 		= "%04d-%02d-%02d" % ( int(row[4]), int(row[5]), int(row[6]))
	latitude	= row[13]
	longitude	= row[12]

	trigger		= row[11]
	radius		= row[14]
	loc_class 	= row[15]
	size_class  = row[16]
	fatalities	= row[17]
	damages		= row[18]
	#evt_type	= row[20]
	link		= row[20]
	#source		= row[24]
	#comments	= row[25]
	
	json = '{ type: "Feature",\n'
	json +='  properties: {\n'
	json +='     kind: "node",\n'
	json +='     id: "'+id+'",\n'
	json +='     version: "1",\n'
	json +='     timestamp: "'+ date +'",\n'
	json +='     user: "'+user+'",\n'
	
	json +='     hazard_prone: "yes"\n'
	json +='     hazard_type: "landslide"\n'
	
	json +='     dk:trigger: "' + trigger +'"\n'
	json +='     dk:radius: "' + radius +'"\n'
	json +='     dk:loc_class: "' + loc_class +'"\n'
	json +='     dk:size_class: "' + size_class +'"\n'
	json +='     dk:fatalities: "' + fatalities +'"\n'
	json +='     dk:damages: "' + damages +'"\n'
	#json +='     dk:evt_type: "' + evt_type +'"\n'
	json +='     dk:link: "' + link +'"\n'
	#json +='     dk:source: "' + source +'"\n'
	#json +='     dk:comments: "' + comments +'"\n'
	json +='  },\n'
	json +=' geometry: {\n'
	json +='     type: "Point",\n'
	json +='     coordinates: [\n'
	json +='        "'+ longitude + '",\n'
	json +='        "' + latitude + '"\n'
	json +='     ]\n'
	json +=' },\n'
	json +='}\n'
	return json
	
#
# ======================================================================
#
if __name__ == '__main__':
	filename = os.path.join(config.data_dir, config.db_csv)
	
	parser = argparse.ArgumentParser(description='Generate OSM file from Excel')
	apg_input = parser.add_argument_group('Input')

	apg_input.add_argument("-x", "--xml", action='store_true', help="generate OSM from Excel XML file")

	apg_output = parser.add_argument_group('Output')
	apg_output.add_argument("-o", '--output', help='name for outputfile')

	options = parser.parse_args()
	
	xml 		= options.xml
	
	with open(filename, 'rU') as csvfile:
		evts = csv.reader(csvfile, delimiter=',', quotechar='|')
		#for row in evts:
		#	print ', '.join(row)
		header= evts.next()
		#print header
		
		if xml:
			filename = os.path.join(config.data_dir, config.db_xml)
			outfile = os.path.join( config.data_dir, config.db_osm)
			f = open(outfile,'w')
			f.write("<?xml version='1.0' encoding='UTF-8'?>")
			f.write("<osm version='0.6' generator='PGC'>")
			
			print "parse:", filename
			namespaces = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet', 'x': 'urn:schemas-microsoft-com:office:excel', 'html': 'http://www.w3.org/TR/REC-html40', 'o': 'urn:schemas-microsoft-com:office:office'}
			doc 	= etree.parse(filename)
			root	= doc.getroot()
			rows 	= root.xpath('.//Row', namespaces=namespaces)
			del rows[0]
			rindex   = 1 
			for row in rows:
				cells = row.xpath('.//Cell', namespaces=namespaces)
				arr = ["" for i in range(0,18)]
				i = 0
				for cell in cells:
					#print cell.attrib
					#print cell.attrib.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
					index = cell.attrib.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
					#print index
					if( index ):
						i = int(index)
					else:
						i = i+1
					data = cell.xpath('.//Data', namespaces=namespaces)
					#print i, data[0].text
					text = data[0].text
					arr[i] = text.replace( '"', '')
				#print rindex, arr
				osm_str = toOSM(arr)
				f.write( osm_str )
				
				rindex += 1
				
			f.write("</osm>")
			f.close()
			
