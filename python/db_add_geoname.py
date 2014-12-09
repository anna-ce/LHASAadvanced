#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Requirements:
#
# Add geonames to db when missing
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
import psycopg2
import ppygis
from psycopg2.extensions import adapt
import json, ast
import time
#import xml.etree.ElementTree as ET

# Site configuration
import config

if __name__ == '__main__':

	dbhost 		= os.environ['DBHOST']
	dbname 		= os.environ['DBNAME']
	dbport 		= os.environ['DBPORT']
	user 		= os.environ['DBOWNER']
	password 	= os.environ['PGPASS']

	assert (dbhost),	"Set DBHOST"
	assert (dbname),	"Set DBNAME"
	assert (dbport),	"Set DBPORT"
	assert (user),		"Set DBOWNER"
	assert (password),	"Set PGPASS"

	print dbhost, dbname, dbport, user
	
	str= "host=%s dbname=%s port=%s user=%s password=%s"% (dbhost,dbname,dbport,user,password)
	print "connect to", str

	connection 	= psycopg2.connect(str)
	cursor 		= connection.cursor()
	records		= []
	
	cmd = "SELECT id, ST_X(way) AS lon, ST_Y(way) as lat, cat_src from planet_osm_point"	
	cursor.execute(cmd)
	for record in cursor:
		if record[3] == None:
			rid	= record[0]
			lng	= record[1]
			lat = record[2]
			
			r = { 'id': rid, 'lat': lat, 'lng': lng }
			records.append(r)
			
	count = 0
	for r in records:
		rid 	= r['id']
		lat 	= r['lat']
		lng 	= r['lng']
		 
		url 	= "http://api.geonames.org/findNearbyPlaceNameJSON?lat=%f&lng=%f&radius=300&style=FULL&cities=cities1000&maxRows=1&username=cappelaere"%(lat,lng)
		print rid, url
		
		result  		= urllib.urlopen(url).read()
		
		geoname 		= ast.literal_eval(result)
		geonames		= geoname['geonames'][0]
		
		countryName 	= geonames[u'countryName']
		adminName1 		= geonames[u'adminName1']
		adminName2 		= geonames[u'adminName2']
		adminName3 		= geonames[u'adminName3']
		near		 	= geonames[u'toponymName']
		distance 		= geonames[u'distance']
		population 		= geonames[u'population']
		tz				= geonames[u'timezone']
		countrycode 	= geonames[u'countryCode']
		continentcode 	= geonames[u'continentCode']
		
		
		print countryName, adminName1, adminName2,adminName3,near,distance,population,tz,countrycode,continentcode
		cat_src 		= 'glc'
		
		cmd = "UPDATE planet_osm_point SET (countryname, adminname1, adminname2, adminname3, near, distance, population, cat_src, cat_id, tz, countrycode, continentcode ) = (%s, %s, %s, %s, %s, %s, %s, %s, %d, %s, %s, %s ) WHERE id= %d;" % \
(adapt(countryName), adapt(adminName1), adapt(adminName2), adapt(adminName3), adapt(near), distance, population, adapt(cat_src), rid, adapt(json.dumps(tz)), adapt(countrycode), adapt(continentcode), rid)
		print cmd
		cursor.execute(cmd)
		time.sleep(2)
		count += 1
		#if count == 2:
		#	break

	connection.commit()
	cursor.close()
	connection.close()				
	sys.exit(0)