#!/bin/sh
#
# process every 30mn  (GPM/IMERG)
#

DIR="$( dirname $0 )"
cd $DIR

# For cron and friends
. ../envs.docker.sh

echo "Starting processing GPM 30mn: `date`, cwd:" $DIR
python gpm_early.py --regions 'global,r01,r02,r03,r04,r05,r06,r07,r08,r09,r10'

echo "Starting Global Landlside nowcast 30mn: `date`, cwd:" $DIR
python landslide_nowcast_global_30mn.py

echo "Done: `date`"