#!/bin/sh
#
# Process Daily (GPM/IMERG)
#

DIR="$( dirname $0 )"
cd $DIR

# For cron and friends
. ../envs.docker.sh

echo "Starting processing GPM Daily: `date`, cwd:" $DIR
python gpm_daily.py --regions 'global,r01,r02,r03,r04,r05,r06,r07,r08,r09,r10'

echo "Starting processing daily Global Landslide NowCast based on GPM: `date` "
python landslide_nowcast_global.py

echo "Starting processing GFMS Daily: `date`"
python gfms_vectorizer.py

#echo "Starting processing GEOS-5 Daily: `date`"
#python geos5_daily.py

echo "Done: `date`"