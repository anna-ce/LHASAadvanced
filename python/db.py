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
import codecs
from xml.sax.saxutils import escape

#import xml.etree.ElementTree as ET

# Site configuration
import config

# Start from Excel ouptut in XML
# db.py -i <input> -x -o db2.osm
# #osm2change.py db2.osm (-> db2.osc)
# #upload.py -m "Changeset Comment" -c yes db2.osc
# osm2pgsql --create -d dk -U postgres -S db.style db2.osm
#

def toOSM( row ):
	id			= row[1] 
	year 		= int(row[2])
	month		= int(row[3])
	day			= int(row[4])
	date 		= "%04d-%02d-%02d" % ( year,month,day )

	latitude	= float(row[6])
	longitude	= float(row[7])

	time					= row[5]
	if time.find("1899-12-31T")>=0:
		#print "time:", time
		time = time[11:len(time)-4]
		#print time
		#sys.exit(-1)
		
	country					= row[8]
	nearest_places			= row[9]
	hazard_type	 			= row[10] 
	landslide_type			= row[11]
	trigger					= row[12]
	storm_name				= row[13]
	fatalities				= row[14]
	injuries				= row[15]
	source_name				= row[16]
	source_link				= row[17]
	if source_link == "LS Info" or source_link == "LS info":
		source_link = ""
	else:
		source_link = escape(row[17])
		
	#if len(row[18])>2045:
		#print "truncating comments for record:", id, len(row[18])
		#print row[18]
		#print "<"	
		
	comments				= escape(row[18][0:2045])
	location_description 	= row[19]
	location_accuracy	 	= row[20]
	landslide_size		 	= row[21]
	
	# we need to check the length of the link and see if it exists
	#if len(link) >= 255:
	#	link= ""
	#	print '** Link > 255 for record id:'+id
		
	if source_link.find('//maps.google.com') > 0 :
		source_link= ""
		print '** Removed maps.google.com link for record id:'+id
		
	if( len(trigger) >= 255):
		trigger= trigger[0:254]
		print '** trigger > 255 for record id:'+id
				
	if( len(fatalities) >= 255):
		damages= fatalities[0:254]
		print '** fatalities > 255 for record id:'+id
		
	osm = '<node id=\"' + id +'\" version="1" uid="1" user="dalia_kirschbaum" changeset="1"'
	osm += ' lat="%.5f" lon="%.5f"' % (latitude, longitude) 
	osm += ' visible="true" timestamp="'+ date +'">\n'
	osm += '    <tag k="hazard_prone" v="yes" /> \n'
	osm += '    <tag k="hazard_type" v="landslide" />\n'
	osm += '    <tag k="dk:catalog_id" v="' + id + '" />\n'
	osm += '    <tag k="dk:landslide_type" v="'+landslide_type+'" />\n'
	osm += '    <tag k="dk:date" v="' + date + '" />\n'

	if time:
		osm += '    <tag k="dk:time" v="' + time + '" />\n'
	osm += '    <tag k="dk:country" v="' + country + '" />\n'
	osm += '    <tag k="dk:nearest_places" v="' + nearest_places + '" />\n'
	osm += '    <tag k="dk:trigger" v="' + trigger + '" />\n'

	if storm_name:
		osm += '    <tag k="dk:storm_name" v="' + storm_name + '" />\n'

	if fatalities:
		osm += '    <tag k="dk:fatalities" v="' + fatalities + '" />\n'

	if injuries:
		osm += '    <tag k="dk:injuries" v="' + injuries + '" />\n'
	
	if source_name:
		osm += '    <tag k="dk:source_name" v="' + source_name + '" />\n'
	
	if source_link:
		osm += '    <tag k="dk:source_link" v="' + source_link + '" />\n'

	if comments:
		osm += '    <tag k="dk:comments" v="' + comments + '" />\n'

	if location_description:
		osm += '    <tag k="dk:location_description" v="' + location_description + '" />\n'

	if location_accuracy:
		osm += '    <tag k="dk:location_description" v="' + location_accuracy + '" />\n'

	if landslide_size:
		osm += '    <tag k="dk:landslide_size" v="' + landslide_size + '" />\n'
	
	osm += '</node>\n'
	
	return osm
	
def to_geojson( row ):
	json 		= ""
	id			= row[1] 
	
	date 		= "%04d-%02d-%02d" % ( int(row[2]), int(row[3]), int(row[4]))
	latitude	= row[6].toFixed(5)
	longitude	= row[7].toFixed(5)

	country					= row[8]
	nearest_places			= row[9]
	hazard_type	 			= row[10] 
	landslide_type			= row[11]
	trigger					= row[12]
	storm_name				= row[13]
	fatalities				= row[14]
	injuries				= row[15]
	source_name				= row[16]
	source_link				= row[17]
	comments				= row[18]
	location_description 	= row[19]
	location_accuracy	 	= row[20]
	landslide_size		 	= row[21]
	
	
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
# Example: db.py -i db-2013.xml -xml -o db3.osm 
#
# Then we need to load it

 
if __name__ == '__main__':
	filename = os.path.join(config.data_dir, config.db_csv)
	
	parser = argparse.ArgumentParser(description='Generate OSM file from Excel')
	apg_input = parser.add_argument_group('Input')

	apg_input.add_argument("-x", "--xml", action='store_true', help="generate OSM from Excel XML file")
	apg_input.add_argument("-i", "--input", help="Inputfile file")

	apg_output = parser.add_argument_group('Output')
	apg_output.add_argument("-o", '--output', help='name for outputfile')

	options = parser.parse_args()
	
	xml 	= options.xml
	_infile		= options.input
	_outfile	= options.output
	
	#with open(filename, 'rU') as csvfile:
		#evts = csv.reader(csvfile, delimiter=',', quotechar='|')
		#for row in evts:
		#	print ', '.join(row)
		#header= evts.next()
		#print header
		
	if xml:
		# db = config.db_xml
		# db = "db2-2.xml"
		
		# Notes: 
		#  Need to remove xmlns default workspace in file
		#  Need to remove unused worksheets and retain the data one
		#
		filename	= os.path.join(config.data_dir, _infile)
		outfile		= os.path.join( config.data_dir, _outfile)
		
		#f = open(outfile,'w')
		f = codecs.open(outfile, mode="w", encoding="utf-8")
		f.write("<?xml version='1.0' encoding='UTF-8'?>")
		f.write("<osm version='0.6' generator='PGC'>")
		
		print "parse:", filename
		namespaces = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet', 'x': 'urn:schemas-microsoft-com:office:excel', 'html': 'http://www.w3.org/TR/REC-html40', 'o': 'urn:schemas-microsoft-com:office:office'}
		parser 	= etree.XMLParser(encoding="utf-8")
		doc 	= etree.parse(filename, parser=parser)
		root	= doc.getroot()
		rows 	= root.xpath('.//Row', namespaces=namespaces)
		
		del rows[0]
		rindex   = 1 
		for row in rows:
			cells = row.xpath('.//Cell', namespaces=namespaces)
			arr = ["" for i in range(0,22)]
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
				
				href = cell.attrib.get('{urn:schemas-microsoft-com:office:spreadsheet}HRef')
				if href and i>16:
					arr[i] = href
				else:
					data = cell.xpath('.//Data', namespaces=namespaces)
					if data:
						data_type = data[0].attrib.get('{urn:schemas-microsoft-com:office:spreadsheet}Type')
						
						if data_type == 'Number':
							text 	= data[0].text.encode('utf-8')
							arr[i] 	= text
						elif data_type == 'String':
							if data[0].text:
								string = data[0].text.encode('utf-8','ignore')

								arr[i] 	= string
								arr[i] 	= arr[i].replace( '"', 'inches')
								arr[i] 	= arr[i].replace( '&', 'and')
								arr[i] 	= arr[i].replace( '<CR>', '\n')
								arr[i] 	= arr[i].replace( '<br />', '\n')
								
						elif data_type == 'DateTime':
							text 	= data[0].text.encode('utf-8')
							arr[i] 	= text							
						else:
							print "Invalid type", data_type, data[0].text
							arr[i] = "****" #data[0].text.encode('utf-8')
							sys.exit(-1)
							
						#print i, data_type, arr[i]
						
				if i >= len(arr):
					break
						
			if( arr[1] ):
				#print rindex, arr
				osm_str = toOSM(arr)
				#print osm_str
				f.write( osm_str.decode('utf-8', 'ignore') )
			
			#if rindex == 187:
			#	sys.exit(-1)
			
			rindex += 1
			
		f.write("</osm>")
		f.close()
			
