#!/bin/sh
#
# process every 3hr  (GPM/IMERG)
#

DIR="$( dirname $0 )"
cd $DIR

# For cron and friends
. ../envs.docker.sh

#echo "Starting processing Global Landslide Nowcast 3hr product: `date`, cwd:" $DIR
#python landslide_nowcast_global_3hr.py

echo "Done: `date`"