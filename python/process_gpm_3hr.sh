#!/bin/sh
#
# process_gpm_3hr
#

DIR="$( dirname $0 )"
cd $DIR

echo "Starting processing GPM 3hr products: `date`, cwd:" $DIR
python landslide_nowcast_global_3hr.py
echo "Done: `date`"