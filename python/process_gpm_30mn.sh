#!/bin/sh
#
# process_gpm_30mn
#

DIR="$( dirname $0 )"
cd $DIR

echo "Starting processing GPM 30mn: `date`, cwd:" $DIR
gpm_global.py --timespan 30mn
echo "Done: `date`"