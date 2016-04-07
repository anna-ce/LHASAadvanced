#!/bin/sh

#
# process_all
#

DIR="$( dirname $0 )"
cd $DIR

# This is to alleviate a problem with Lingon on the Mac and autoscheduling of daily processing script
. ~/.bashrc

echo "Starting processing: `date`, cwd:", $DIR
python process_all.py > errpgc.txt
echo "process_all.sh Done: `date`"
