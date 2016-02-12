#!/bin/bash
#
# process_gpm_3hrs
#

DIR="$( dirname $0 )"
cd $DIR


echo "Starting processing GPM 3hrs: `date`, cwd:" $DIR
gpm_global.py --timespan 3hrs -v
echo "Done: `date`"
