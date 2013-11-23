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
