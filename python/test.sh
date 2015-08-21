## H00 forecast; only at H00, GEOS-5 provides 5 day precip forecast
fc=00
ovar=prectot   # output var: total precip 

#the script will be trigered at 11:10 am every day
currDate=`date +"%Y%m%d"`
echo $currDate

#cyr=`date -u "$currDate" +%Y` 
#cmn=`date -u  "$currDate" +%m` 
#cdy=`date -u  "$currDate" +%d` 

#echo $cyr $cmn $cdy
# 00-24h forecast: first forecast, 1:30 hr (90 min) ahead, 3h (180min) apart
# 8 steps forward 
for lead in 1 2 3 4 5; do   # lead time (day) 
  ns=0
  let fm=(lead-1)*24*60+90 

#  echo $fm $ns
  while [ $ns -lt 8 ]; do 
  echo $fm $ns
    # forecast date and time
#    fyr=`date "$currDate $fm " +%Y`
    #fdate=`date -u -d dst "$currDate $fm " +%Y%m%d`
    #ftime=`date -u -d dst "$currDate $fm " +%H%M`
    #gtime=`date -u -d dst "$currDate $fm " +%H:%MZ%d%b%Y`
    #gs=/tmp/${fdate}_${ftime}.gs
    #dfile=GEOS.fp.fcst.tavg1_2d_flx_Nx.$cyr$cmn${cdy}_${fc}+${fdate}_${ftime}.V01.nc4
    #echo $dfile
#    echo $fyr
    
    let fm=fm+180
    let ns=ns+1 
  done
done