# ===============
# PGC NOTES
#
#
# need gdal with python bindings
brew install libpng libtiff
brew install gdal --with-python

# build jasper-1.900.1 and install in /usr/local/lib

# build pytrmm
> cd pytrmm-0.1.0
> python setup.py install

# compile and make grib_api
> cd grib_api-1.11.0
> ./configure --with-jasper=/usr/local/lib --prefix=/Users/patrice/Development/landslide/python/grib_api_dir

# build/install pyproj-1.9.3
> cd pyproj-1.9.3
> python setup.py build
> python setup.py install

# build pygrib
> cd pygrib-1.9.6
# modify setup.cfg to specify grib_api_dir and libjasper
> python setup.py build
> sudo python setup.py install

# add environment variables
setenv GRIBAPI_DIR      /Users/patrice/Development/landslide/python/grib_api_dir
setenv GRIBAPI_LIBDIR   $GRIBAPI_DIR/lib
setenv GRIB_DEFINITION_PATH	$GRIBAPI_DIR/share/grib_api/definitions


test:
cd /public/data
> python
>>> import pygrib
>>> grbs = pygrib.open('gdas1.t06z.sfluxgrbf09.grib2')


## Database loading:

Realtime database:
	osmosis is delivered as part of ojo... some mods were necessary to support heroku loading..
	there is a /package/script folder that contains sql files.  We are using the snapshot format
	
	sudo su - postgres
	createdb dk2
	createlang plpgsql osm
	createuser <username>

	connect to db with pgsql or equivalent:
	-- Enable PostGIS (includes raster)
	CREATE EXTENSION postgis;
	-- Enable Topology
	CREATE EXTENSION postgis_topology;
	-- fuzzy matching needed for Tiger
	CREATE EXTENSION fuzzystrmatch;
	-- Enable US Tiger Geocoder
	CREATE EXTENSION postgis_tiger_geocoder;
 	CREATE EXTENSION hstore;

	cd  ojo/osmosis/package/script
	psql -d dk2 -f pgsnapshot_schema_0.6.sql
	psql -d dk2 -f pgsnapshot_schema_0.6_action.sql
	psql -d dk2 -f pgsnapshot_schema_0.6_bbox.sql
	psql -d dk2 -f pgsnapshot_schema_0.6_linestring.sql
	
	# Load with osmosis
	# problem is 
	osmosis --read-xml db2.osm --write-pgsql database=dk2 validateSchemaVersion=false
	
	# dump local database
	pg_dump -Fc --no-acl --no-owner -h localhost  dk > dk.dump
	# upload to S3 ojo-databases and make public.  Link: https://s3.amazonaws.com/ojo-databases/dk.dump
	# reload to proper database and DO NOT SCREW IT UP
	cd ojo-streamer
	heroku pgbackups:restore DATABASE 'https://s3.amazonaws.com/ojo-databases/dk.dump'
	
	
Production database: