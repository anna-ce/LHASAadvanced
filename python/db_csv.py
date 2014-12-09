#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Requirements:
#
# Convert DB to geojson
#

from urlparse import urlparse
import os, sys, inspect
import array
from datetime import date
import csv
import codecs
import argparse
import urllib
from lxml import etree
import codecs
from xml.sax.saxutils import escape
import psycopg2
import ppygis
from psycopg2.extensions import adapt

#import xml.etree.ElementTree as ET

# Site configuration
import config

def updateDB(row, cursor):
	recid = int(row[0])
	#cmd = cursor.mogrify("UPDATE planet_osm_point SET comments=%s where id=%s;", (psycopg2.extensions.QuotedString(row[1]), row[0]))
	#cmd = cursor.mogrify("UPDATE planet_osm_point SET comments=%s where id=%s;", (unicode(row[1], 'latin-1').encode('utf-8'), row[0]) )

	cmd = cursor.mogrify("UPDATE planet_osm_point SET comments=%s where id=%s;", (row[1], row[0]) )
	print cmd	
	cursor.execute(cmd)
#
# ===================================
#
# Example: db_csv.py -i db_id_comments.csv 
#

class UnicodeReader(object):
    def __init__(self, f, dialect=None, encoding='utf-8', errors='strict',
                 **kwds):
        format_params = ['delimiter', 'doublequote', 'escapechar', 'lineterminator', 'quotechar', 'quoting', 'skipinitialspace']
        if dialect is None:
            if not any([kwd_name in format_params for kwd_name in kwds.keys()]):
                dialect = csv.excel
        self.reader = csv.reader(f, dialect, **kwds)
        self.encoding = encoding
        self.encoding_errors = errors

    def next(self):
        row = self.reader.next()
        encoding = self.encoding
        encoding_errors = self.encoding_errors
        float_ = float
        unicode_ = unicode
        return [(value if isinstance(value, float_) else
                 unicode_(value, encoding, encoding_errors)) for value in row]

    def __iter__(self):
        return self

    @property
    def dialect(self):
        return self.reader.dialect

    @property
    def line_num(self):
        return self.reader.line_num
		
		
if __name__ == '__main__':
	filename = os.path.join(config.data_dir, config.db_csv)
	
	parser 		= argparse.ArgumentParser(description='Update comments from CSV')
	apg_input 	= parser.add_argument_group('Input')
	
	apg_input.add_argument("-i", "--input", help="Input file name")

	options = parser.parse_args()
	
	_infile		= options.input

	filename	= os.path.join(config.data_dir, "glc", _infile)

	#urllib.parse.uses_netloc.append("postgres")
	
	DATABASE_URL = os.environ["DATABASE_URL"]
	assert( DATABASE_URL)
	
	url = urlparse(DATABASE_URL)
	
	print "DATABASE_URL value:" +str(os.environ["DATABASE_URL"])
	print "scheme: " + str(url.scheme)
	#print "netloc: " + str(url.netloc)
	print "  host: " + str(url.hostname)
	print "  port: " + str(url.port)
	print "  database: " + str(url.path[1:])
	print "  user: " + str(url.username)
	print "passwd: " + str(url.password)
	
	#psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
	connection 	= psycopg2.connect(database=url.path[1:],user=url.username,password=url.password,host=url.hostname,port=url.port)
	cursor 		= connection.cursor()
	#connection.set_client_encoding('LATIN1')
	count = 0
	with open(filename, 'rU') as csvfile:
		#evts = csv.reader(csvfile, dialect=csv.excel, delimiter=',', quotechar='\"')
		evts = UnicodeReader(csvfile, encoding='macroman')
		for row in evts:
			count += 1
			#print count, row[0], unicode(row[1], 'latin-1').decode('utf-16')
			print count, row[0], row[1]
			updateDB(row, cursor)
			
		#header= evts.next()
		#print header
		

	connection.commit()
	cursor.close()
	connection.close()
					
	sys.exit(0)
		