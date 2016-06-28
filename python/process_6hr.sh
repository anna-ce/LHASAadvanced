#!/bin/sh
#
# process 6-hr products  (GPM/IMERG)
#

DIR="$( dirname $0 )"
cd $DIR

# For cron and friends
. ../envs.docker.sh

#echo "Starting processing GEOS-5 6hr: `date`, cwd:" $DIR
#python geos5_6hr.py

# Process Landslide Forecast every 6 hrs

# echo "Starting processing Global Landslide Forecast 6hr: `date`, cwd:" $DIR
# python landslide_forecast_global_6hr.py

echo "Done: `date`"