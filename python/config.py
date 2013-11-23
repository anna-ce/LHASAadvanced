from datetime import date

#
# Configuration Parameters
#

data_dir 	= "/Volumes/MacBay3/landslide/data"

today 		= date.today()
year		= today.year
month		= today.month
day			= today.day

#
# Hardcoded day for now so we can all agree
#

year 		= 2013
month		= 10
day			= 26
hour		= 6
today		= date(year, month, day)
jd			= today.timetuple().tm_yday
ym	 		= "%s%02d" % (year, month)

# BBOX of interest
#bbox		= [-94, 19, -76, 6]
#bbox[0] 	+= 360
#bbox[2] 	+= 360

# wrf bboxes lllon,lllat,urlon,urlat

d1 			= [-99.23,0.79,-56.76,31.40 ]
d2			= [-92.67, 6.17, -75.85, 19.08 ]		# Central America
d3			= [-74.94, 16.35, -64.98, 21.42 ]		# Haiti

regions		= {
	'global': {
		'global':		"World",
		'bbox': 		[-180, -50, 180, 50 ],
		'bucket':		"ojo-global",
        'tiles-zoom':   "2-6"
	
	},
	'd02': {
		'name':			"Central America",
		'bbox': 		[-92.67, 6.17, -75.85, 19.08 ],
		'bucket':		"ojo-d2",
		'modis_tiles':  [
			"100W020N",
			"090W020N",
			"090W010N"	
		],
		'hydroshed_tiles': [
			"CA/n15w095",
			"CA/n10w095",
			"CA/n15w090",
			"CA/n10w090",
			"CA/n05w090",
			"CA/n15w085",
			"CA/n10w085",
			"CA/n05w085",
			"CA/n15w080",
			"CA/n10w080",
			"CA/n05w080",
		],
		'tiles-zoom':	"5-14",
		'modis-win': 	"Win04"		# MCD45 Window (MODIS Burned Areas)
	},
	'd03': {
		'name':			"Hispaniola",
		'bbox': 		[-74.94, 16.35, -64.98, 21.42 ],
		'bucket':		"ojo-d3",
		'modis_tiles':  [
			"080W020N",
			"070W020N"
		],
		'hydroshed_tiles': [
			"CA/n20w075",
			"CA/n15w075",
			"CA/n15w070"
		],
		'tiles-zoom':    "5-14",
		'modis-win': 	"Win04"		# MCD45 Window (MODIS Burned Areas)
	},
}

# Landlside database csv
db_csv 		= "db2.csv"
db_xml 		= "db2.xml"
db_osm		= "db2.osm"
db_geojson	= "db2.geojson"