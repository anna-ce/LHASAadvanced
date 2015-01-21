from datetime import date

#
# Configuration Parameters
#

#data_dir 	= "/Volumes/MacBay3/landslide/data"
data_dir 	= "/Users/patricecappelaere/landslide/data"

today 		= date.today()
year		= today.year
month		= today.month
day			= today.day

#
# Hardcoded day for now so we can all agree
#

#year		= 2014
#month		= 06
#day		= 03

ym	 		= "%d%02d" % (year, month)
ymd 		= "%d%02d%02d" % (year, month, day)

# BBOX of interest
#bbox		= [-94, 19, -76, 6]
#bbox[0] 	+= 360
#bbox[2] 	+= 360

# Rainfall limits in mm/day fo rthe landslide model
rainfall_red_limit 		= 75
rainfall_orange_limit	= 50
rainfall_yellow_limit	= 35

# wrf bboxes lllon,lllat,urlon,urlat
# D02 1872x1438
#Upper Left  ( -92.6931093,  19.0872388) ( 92d41'35.19"W, 19d 5'14.06"N)
#Lower Left  ( -92.6931093,   6.1466768) ( 92d41'35.19"W,  6d 8'48.04"N)
#Upper Right ( -75.8469813,  19.0872388) ( 75d50'49.13"W, 19d 5'14.06"N)
#Lower Right ( -75.8469813,   6.1466768) ( 75d50'49.13"W,  6d 8'48.04"N)
#Center      ( -84.2700453,  12.6169578) ( 84d16'12.16"W, 12d37' 1.05"N)

# D03 1109x567
#Upper Left  ( -74.9570600,  21.4358479) ( 74d57'25.42"W, 21d26' 9.05"N)
#Lower Left  ( -74.9570600,  16.3334149) ( 74d57'25.42"W, 16d20' 0.29"N)
#Upper Right ( -64.9771690,  21.4358479) ( 64d58'37.81"W, 21d26' 9.05"N)
#Lower Right ( -64.9771690,  16.3334149) ( 64d58'37.81"W, 16d20' 0.29"N)
#Center      ( -69.9671145,  18.8846314) ( 69d58' 1.61"W, 18d53' 4.67"N)

regions		= {
	'global': {
		'global':		"World",
		'bbox': 		[-180, -50, 180, 50 ],
		'bucket':		"ojo-global",
        'tiles-zoom':   "2-6"
	
	},
	'd02': {
		'name':			"Central America",
		'bbox': 		[-92.6833333,   6.1666667, -75.8500000,  19.0833333],
		'centerlat':	12.625,
		'centerlon':	-84.26666665,
		'pixelsize':	0.008333333333330,
		'columns': 		2020,
		'rows': 		1550,
		'thn_width':	389,
		'thn_height':	298,
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
		'tiles-zoom':	"6-14",
		'modis-win': 	"Win04"		# MCD45 Window (MODIS Burned Areas)
	},
	'd03': {
		'name':			"Hispaniola",
		'bbox': 		[-74.9416667, 16.3500000, -64.9750000,  21.4250000],
		'centerlat':	18.8875,
		'centerlon':	-69.95833335,
		'pixelsize':	0.008333333333330,
		'columns': 		1196,
		'rows': 		609,
		'thn_width':	400,
		'thn_height':	204,
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
		'tiles-zoom':    "6-14",
		'modis-win': 	"Win04"		# MCD45 Window (MODIS Burned Areas)
	},
}

# Landslide database csv
db_csv 		= "db2.csv"
db_xml 		= "db2.xml"
db_osm		= "db2.osm"
db_geojson	= "db2.geojson"