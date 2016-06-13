#!/bin/sh
#
# process_gpm_30mn to generate 30mn, 3-hr and 1-d every 30mn for all regions
#

DIR="$( dirname $0 )"
cd $DIR

echo "Starting processing GPM 30mn: `date`, cwd:" $DIR
python gpm_early.py --regions 'global,r01,r02,r03,r04,r05,r06,r07,r08,r09,r10'

python landslide_nowcast_global_30mn.py
echo "Done: `date`"