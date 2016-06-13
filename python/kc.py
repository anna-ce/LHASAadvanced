#!/usr/bin/env python

import os, sys, inspect, io
import array
from datetime import date
import csv
import json


features = []

def feature(row):
	index = row['index']
	properties = {
		'id': 			index, 
		'name': 		row['name'],
		'students': 	row['students'],
		'classrooms': 	row['classrooms'],
		'teachers': 	row['teachers']
	}
	
	latlng 		= row['latlng'].split(",")
	
	if len(latlng)>1:
		latitude 	= float(latlng[0]) 
		longitude 	= float(latlng[1])
		coordinates = [longitude, latitude]
	
		feature = {"type": "Feature", "geometry": { "type": "Point", "coordinates": coordinates}, "properties": properties}
		features.append(feature)
	
filename 			= "../KC.csv"
geojson_filename	= "../KC.json"

f					= open(filename, 'rU')
reader 				= csv.DictReader( f, fieldnames = ( 'index','name','latlng','students','classrooms','teachers' ) )
	
	#evts = csv.reader(csvfile, delimiter=',', quotechar='|')
	# skip first row
	
count = 0
for row in reader:
	if count > 0:
		feature(row)
	count += 1
	
geojson = {"type": "FeatureCollection", "features": features}
	#print "features found:", len(features)

print "JSON", json.dumps(geojson, ensure_ascii=False)

with io.open(geojson_filename, 'w', encoding='utf-8') as f:
	f.write(unicode(json.dumps(geojson, ensure_ascii=False)))

#print features