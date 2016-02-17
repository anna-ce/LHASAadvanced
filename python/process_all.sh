#!/bin/sh

#
# process_all
#

DIR="$( dirname $0 )"
cd $DIR

echo "Starting processing: `date`, cwd:", $DIR
python process_all.py
echo "process_all.sh Done: `date`"
