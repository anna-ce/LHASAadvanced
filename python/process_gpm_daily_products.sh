#!/bin/sh
#
# process_gpm_30mn
#

DIR="$( dirname $0 )"
cd $DIR

echo "Starting processing GPM Daily: `date`, cwd:" $DIR
gpm_global.py --timespan 1day

echo "Starting processing GFMS Daily: `date`"
gfms_vectorizer.py

echo "Starting processing Global Landslide NowCast based on GPM: `date` "
#
# TBD
#
echo "Done: `date`"