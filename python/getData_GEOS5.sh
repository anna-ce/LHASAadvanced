# From Huan Wu
# UMD GFMS

# This script extracts prectot from ARCTAS GEOS5 HDF file 
# and save as binary. The output data saves the first line as the southest
# row of the data, and in little_endian. The output rain is in mm/h
# tavg2d - 2-dimensional hourly time averaged fields, time-stamped 
# at the center of the averaging period. For example, 03:30z output 
# would be a 3z-4z time average).


#t0="Jun 11 2013"   # starting time: 0Z 
#t1="Jul 31 2013"   # end time: 0Z

# File location config 
dpath=/data1/www/flood/forcing/GEOS-5/
opath=/data1/www/flood/forcing/GEOS-5/

#where is GrADS
grads=/data1/www/flood/grads-2.0.1.oga.1/Contents/grads

#================================================
rm /data1/www/flood/forcing/GEOS-5/*.bin

## H00 forecast; only at H00, GEOS-5 provides 5 day precip forecast
fc=00
ovar=prectot   # output var: total precip 

#the script will be trigered at 11:10 am every day
currDate=`date +"%Y%m%d"`
echo $currDate

#sec0=`date -u -d "$t0" +%s`
#sec1=`date -u -d "$t1" +%s`
#let days=(sec1-sec0)/86400

#  t1=`date -u -d "$t0 $day day"`  # for new "date" command
  cyr=`date -u -d "$currDate" +%Y` 
  cmn=`date -u -d "$currDate" +%m` 
  cdy=`date -u -d "$currDate" +%d` 

  # 00-24h forecast: first forecast, 1:30 hr (90 min) ahead, 3h (180min) apart
  # 8 steps forward 
  for lead in 1 2 3 4 5; do   # lead time (day) 
    ns=0
    let fm=(lead-1)*24*60+90 

  while [ $ns -lt 8 ]; do 
    # forecast date and time
    fyr=`date -u -d "$currDate $fm min" +%Y`
    fdate=`date -u -d "$currDate $fm min" +%Y%m%d`
    ftime=`date -u -d "$currDate $fm min" +%H%M`
    gtime=`date -u -d "$currDate $fm min" +%H:%MZ%d%b%Y`
    #fdir="$opath/D$lead/$fyr/$fdate"
    #if [ ! -d $fdir ]; then
    #  mkdir -p $fdir
    #fi
    gs=/tmp/${fdate}_${ftime}.gs
    dfile=GEOS.fp.fcst.tavg1_2d_flx_Nx.$cyr$cmn${cdy}_${fc}+${fdate}_${ftime}.V01.nc4
    #wget -O /$dpath/$dfile ftp://gmao_ops:@ftp.nccs.nasa.gov/fp/forecast/Y$cyr/M$cmn/D$cdy/H$fc/$dfile


#the rain data is converted from mm/s to mm/h by *3600 below
    echo extracting $dfile
    cat > $gs <<EOF
'sdfopen $dpath/$dfile'
'set fwrite -le -st -cl $dpath/${ovar}_H00_${fdate}_${ftime}.1gd4r'
'set gxout fwrite'
'set x 1 1152'
'set y 1 721'
'd $ovar*3600'
'disable fwrite'
'quit'
EOF

#$grads -blc "run $gs"
#rm $dpath/$dfile

# now reprojection
  gs=/tmp/${fdate}_${ftime}_0.25.gs
  echo converting $dpath/${fdate}_${ftime}

#in the original GEOS-5 data, the first line saves the southest row.
#so it doesnot need to set the yrev in the prectot.ctl to flip the data.

    cat > $gs <<EOF
'open $opath/prectot.ctl'
'set time $gtime'
'set gxout fwrite'
'set fwrite -le -st -cl $dpath/${ovar}_H00_${fdate}_${ftime}-0.25.1gd4r'
'd re($ovar, 1440, linear, -179.875, 0.25, 480, linear, -59.875, 0.25)'
'disable fwrite'
'quit'
EOF
#'set time $gtime'

#$grads -blc "run $gs"
#rm $dpath/${ovar}_H00_${fdate}_${ftime}.1gd4r


#mv $dpath/${ovar}_H00_${fdate}_${ftime}-0.25.1gd4r $dpath/${fdate}${ftime}_Prec.bin

#let fm=fm+180
# let ns=ns+1 
  done   # while 

 done   # for lead 

