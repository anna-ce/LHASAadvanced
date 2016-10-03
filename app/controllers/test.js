var util 		= require('util');
var fs	 		= require('fs');
var path		= require('path');
var eyes		= require('eyes');
var async		= require('async');
var request		= require('request');
var debug		= require('debug')('tests');
var	geopix		= require('geopix');
var zlib 		= require('zlib');
var moment		= require('moment');

function getClientAddress(request){ 
	//console.log("connection.remoteAddress", connection.remoteAddress)
	//console.log(request.headers)
	console.log(request.connection.remoteAddress)
	
    with(request)
        return (headers['x-forwarded-for'] || '').split(',')[0] 
            || request.connection.remoteAddress
}

// horrible to work around throttling of github
function sleep(milliseconds) {
  var start = new Date().getTime();
  for (var i = 0; i < 1e7; i++) {
    if ((new Date().getTime() - start) > milliseconds){
      break;
    }
  }
}

function getGeopixValue(fileName, lat, lng) {
	console.log("getGeopixValue", fileName, lat, lng)
	//try {
		var tif				= geopix.GEOTIFFFile(fileName)
		return tif.LatLng(lat, lng)
		//} catch(e) {
		//logger.error("getGeopixValue Exception", e)
		//return(-1)
	//}
}

module.exports = {
	gpm: function(req, res) {
		res.render("test/gpm.ejs", { layout: false })	
	},

	gpm2: function(req, res) {
		var id 	= req.params['id'];
		var ip 	= getClientAddress(req)
		var url = 'http://freegeoip.net/json/' + ip
		request.get( url, function (error, response, body) {
			if(!error && response.statusCode == 200 ) {
				var data = JSON.parse(body)
				//console.log(data)
				res.render("test/gpm2.ejs", { 
					layout: false,
					token: process.env.MAPBOX_PUBLIC_TOKEN,
					latitude: data.latitude,
					longitude: data.longitude
				 })	
			}
		})
	},
	gfms: function(req, res ) {
		res.render("test/gfms.ejs", { 
			layout: false,
			token: process.env.MAPBOX_PUBLIC_TOKEN,
			latitude: 30,
			longitude: 70
		 })	
	},
	gpm3: function(req, res) {
		res.render("test/gpm3.ejs", { layout: false })	
	},
	
	feed: function(req, res) {
		var feed = {'type': 'FeatureCollection', 'features': [
			{ 	'type': 'Feature',
				'properties': {
					'msgType': 'Alert', 'link': '/test/r07?show=Floodcast', 'effective': '2016/05/15', 'title': 'Flood Floodcast Alert issued 2016/05/15', 'areaDesc': 'Region of Gorno-Badakhshan, Tajikistan; ', 'published': '2016/05/15', 'event': 'Flood Floodcast Alert', 'summary': 'Flood Floodcast Alert'
				}
			}, 
			{ 	'type': 'Feature',
				'properties': {		
					'msgType': 'Warning', 'link': '/test/r07?show=Floodcast', 'effective': '2016/05/15', 'title': 'Flood Floodcast Warning issued 2016/05/15', 'areaDesc': 'District of Badulla, Sri Lanka; District of M\u0101tale, Sri Lanka; District of P\u014f\u1e37\u014fnnaruva, Sri Lanka; Region of Gorno-Badakhshan, Tajikistan; Province of Sichuan, China; Autonomous Region of Xizang, China; Autonomous Region of Xinjiang, China; Province of Chardzhou, Turkmenistan; Province of Jawzjan, Afghanistan; ', 'published': '2016/05/15', 'event': 'Flood Floodcast Warning', 'summary': 'Flood Floodcast Warning'
				}
			},
			{ 	'type': 'Feature',
				'properties': {		
					'msgType': 'Alert', 'link': '/test/r07?show=Landslide', 'effective': '2016/05/15', 'title': 'Landslide Floodcast Alert issued 2016/05/15', 'areaDesc': 'Province of Baghlan, Afghanistan; Province of Laghman, Afghanistan; Province of Samangan, Afghanistan; Province of Nangarhar, Afghanistan; Province of Nuristan, Afghanistan; Province of Takhar, Afghanistan; Province of Sari Pul, Afghanistan; Province of Kapisa, Afghanistan; Province of Kabul, Afghanistan; Province of Badakhshan, Afghanistan; Province of Kunar, Afghanistan; Province of Bamyan, Afghanistan; Province of Parwan, Afghanistan; Region of Osh, Kyrgyzstan; Region of Batken, Kyrgyzstan; Administrative Zone of Janakpur, Nepal; District of Bagmati, Nepal; Administrative Zone of Sagarmatha, Nepal; Administrative Zone of Dhawalagiri, Nepal; Administrative Zone of Mechi, Nepal; Administrative Zone of Karnali, Nepal; District of Seti, Nepal; Administrative Zone of Rapti, Nepal; District of Bheri, Nepal; District of Bhojpur, Nepal; District of Gandaki, Nepal; Administrative Zone of Mahakali, Nepal; District of Chhukha, Bhutan; District of Daga, Bhutan; District of Paro, Bhutan; District of Samchi, Bhutan; District of Geylegphug, Bhutan; District of Samdrup Jongkhar, Bhutan; District of Ha, Bhutan; Division of Tanintharyi, Myanmar; Division of Sagaing, Myanmar; State of Shan, Myanmar; Division of Mandalay, Myanmar; State of Kachin, Myanmar; Province of N.W.F.P., Pakistan; Territory of F.A.T.A., Pakistan; Centrally Administered Area of Azad Kashmir, Pakistan; Centrally Administered Area of Northern Areas, Pakistan; Admin-1 minor island of None, Indonesia; State of Tripura, India; State of Nagaland, India; State of Jammu and Kashmir, India; State of Karnataka, India; State of Chhattisgarh, India; State of Uttaranchal, India; State of Meghalaya, India; Union Territory of Lakshadweep, India; State of Mizoram, India; State of Assam, India; State of Kerala, India; State of Andhra Pradesh, India; State of Manipur, India; State of Arunachal Pradesh, India; State of Orissa, India; State of Sikkim, India; None of Daman and Diu, India; Region of Jizzakh, Uzbekistan; Region of Sirdaryo, Uzbekistan; Region of Ferghana, Uzbekistan; Region of Surkhandarya, Uzbekistan; State of Perlis, Malaysia; Province of Sichuan, China; Autonomous Region of Xizang, China; Autonomous Region of Xinjiang, China; Province of Qinghai, China; Province of Yunnan, China; Province of Kanchanaburi, Thailand; Province of Chiang Rai, Thailand; Province of Nakhon Sawan, Thailand; Region of Tadzhikistan Territories, Tajikistan; Region of Gorno-Badakhshan, Tajikistan; Region of Khatlon, Tajikistan; Region of Leninabad, Tajikistan; Division of Sylhet, Bangladesh; ', 'published': '2016/05/15', 'type': 'Feature', 'event': 'Landslide Floodcast Alert', 'summary': 'Landslide Floodcast Alert'
				}
			},
			{ 	'type': 'Feature',
				'properties': {	
					'msgType': 'Warning', 'link': '/test/r07?show=Landslide', 'effective': '2016/05/15', 'title': 'Landslide Floodcast Warning issued 2016/05/15', 'areaDesc': 'Province of Baghlan, Afghanistan; Province of Laghman, Afghanistan; Province of Samangan, Afghanistan; Province of Nangarhar, Afghanistan; Province of Nuristan, Afghanistan; Province of Takhar, Afghanistan; Province of Sari Pul, Afghanistan; Province of Balkh, Afghanistan; Province of Logar, Afghanistan; Province of Kapisa, Afghanistan; Province of Kabul, Afghanistan; Province of Badakhshan, Afghanistan; Province of Kunar, Afghanistan; Province of Wardak, Afghanistan; Province of Bamyan, Afghanistan; Province of Parwan, Afghanistan; Region of Osh, Kyrgyzstan; Region of Batken, Kyrgyzstan; Administrative Zone of Janakpur, Nepal; District of Bagmati, Nepal; Administrative Zone of Sagarmatha, Nepal; District of Gandaki, Nepal; Administrative Zone of Mechi, Nepal; Administrative Zone of Karnali, Nepal; District of Seti, Nepal; Administrative Zone of Rapti, Nepal; District of Bheri, Nepal; District of Bhojpur, Nepal; Administrative Zone of Dhawalagiri, Nepal; Administrative Zone of Mahakali, Nepal; Division of Tanintharyi, Myanmar; Division of Sagaing, Myanmar; State of Shan, Myanmar; Division of Mandalay, Myanmar; State of Kachin, Myanmar; District of Chhukha, Bhutan; District of Daga, Bhutan; District of Gasa, Bhutan; District of Samchi, Bhutan; District of Wangdi Phodrang, Bhutan; District of Geylegphug, Bhutan; District of Samdrup Jongkhar, Bhutan; District of Paro, Bhutan; District of Tongsa, Bhutan; District of Ha, Bhutan; District of Mongar, Bhutan; Province of N.W.F.P., Pakistan; Centrally Administered Area of Northern Areas, Pakistan; Province of Punjab, Pakistan; Centrally Administered Area of Azad Kashmir, Pakistan; Territory of F.A.T.A., Pakistan; Province of Sind, Pakistan; Admin-1 minor island of None, Indonesia; State of Tripura, India; State of Nagaland, India; State of Jammu and Kashmir, India; State of Karnataka, India; State of Chhattisgarh, India; State of Uttaranchal, India; State of Meghalaya, India; State of Goa, India; State of West Bengal, India; State of Mizoram, India; State of Assam, India; State of Jharkhand, India; State of Kerala, India; State of Andhra Pradesh, India; State of Manipur, India; Union Territory of Lakshadweep, India; State of Arunachal Pradesh, India; State of Orissa, India; State of Sikkim, India; None of Daman and Diu, India; Region of Sirdaryo, Uzbekistan; Region of Ferghana, Uzbekistan; Region of Jizzakh, Uzbekistan; Region of Kashkadarya, Uzbekistan; Region of Samarkand, Uzbekistan; Region of Surkhandarya, Uzbekistan; State of Perlis, Malaysia; Atoll of Raa, Maldives; Atoll of Haa Alifu, Maldives; Atoll of Alifu Alifu, Maldives; Atoll of Lhaviyani, Maldives; Atoll of Shaviyani, Maldives; Atoll of Alifu Dhaalu, Maldives; Atoll of Baa, Maldives; Atoll of Noonu, Maldives; Atoll of Kaafu, Maldives; Atoll of Faafu, Maldives; Atoll of Haa Dhaalu, Maldives; Autonomous Region of Xinjiang, China; Province of Qinghai, China; Province of Yunnan, China; Province of Sichuan, China; Autonomous Region of Xizang, China; Province of Gansu, China; District of K\xe6galla, Sri Lanka; District of Gampaha, Sri Lanka; District of Kuru\u1e47\xe6gala, Sri Lanka; District of Nuvara \u0114liya, Sri Lanka; District of P\u014f\u1e37\u014fnnaruva, Sri Lanka; District of M\u0101tara, Sri Lanka; District of Anur\u0101dhapura, Sri Lanka; District of M\u014f\u1e47ar\u0101gala, Sri Lanka; District of K\u014f\u1e37amba, Sri Lanka; District of Ka\u1e37utara, Sri Lanka; District of G\u0101lla, Sri Lanka; District of Ma\u1e0dakalapuva, Sri Lanka; District of Hambant\u014f\u1e6da, Sri Lanka; District of Ratnapura, Sri Lanka; District of Amp\u0101ra, Sri Lanka; District of M\u0101tale, Sri Lanka; District of Badulla, Sri Lanka; District of Mahanuvara, Sri Lanka; District of Triku\u1e47\u0101malaya, Sri Lanka; Province of Uthai Thani, Thailand; Province of Ratchaburi, Thailand; Province of Chiang Rai, Thailand; Province of Suphan Buri, Thailand; Province of Nakhon Sawan, Thailand; Province of Kanchanaburi, Thailand; Province of Phayao, Thailand; Province of Tak, Thailand; Region of Tadzhikistan Territories, Tajikistan; Region of Gorno-Badakhshan, Tajikistan; Region of Khatlon, Tajikistan; Independent City of Dushanbe, Tajikistan; Region of Leninabad, Tajikistan; Division of Sylhet, Bangladesh; ', 'published': '2016/05/15', 'event': 'Landslide Floodcast Warning', 'summary': 'Landslide Floodcast Warning'
				}
			}
		]}
		res.send(feed)
	},
	
	r07: function(req, res) {
		var dt 		= req.query['date'];
		var show	= req.query['show']
		
		if( dt == undefined) {
			dt = "2016-05-15"
		}
		
		if( show == undefined ) {
			show = 'Floodcast'
		}
		
		res.render("test/r07.ejs", {
			date: dt,
			show: show,
			layout: false,
			latitude: 14,
			longitude: 80.7,
			token: process.env.MAPBOX_PUBLIC_TOKEN,
		 })			
	},
	notifications: function(req, res) {
		res.render("test/notifications.ejs", { 
			layout: false
		 })			
	},
	mapboxgl: function(req, res) {
		var host = req.protocol + "://" + req.get('host')
		
		res.render("test/mapboxgl.ejs", { 
			token: process.env.MAPBOX_PUBLIC_TOKEN,
			host: host,
			latitude: 10,
			longitude: -80.7,
			layout: false
		 })	
	},
	r07_download: function(req, res) {
		console.log("download", req.body)
		var which 	= req.body['which']
		var format 	= req.body['format']

		//var dt = req.params['date']
		var dt 				= "2016-05-15"
		var mday 			= moment(dt)
		var formattedDate 	= mday.format("YYYYMMDD")
		var ext				= ".topojson.gz"
		
		switch(format) {
		case 'geojson':
			ext = ".geojson"
			break
		case 'shape':
			ext = ".shp.zip"
			break
		case 'kml':
			ext = ".kml"
		}
		var url;
		
		switch (which) {
			case 'flood':
				var basename = formattedDate + "_levels"+ext
				if( ext == 'topojson') {
					url = "/products/s3/r07/gfms/" + mday.format("YYYY")+ "/"+ mday.format("DDDD") + "/" + basename
				} else {
					url = "/products/gfms/export/r07/" + mday.format("YYYY")+ "/"+ mday.format("DDDD") + "/" + basename
				}
				
				console.log(url)
				res.redirect(url)
				break
			case 'landslide':
				var basename = "global_landslide_nowcast_" + formattedDate + ext
				if( ext == 'topojson') {
					url = "/products/s3/r07/global_landslide_nowcast/" + mday.format("YYYY")+ "/"+ mday.format("DDDD") + "/" + basename
				} else {
					url = "/products/global_landslide_nowcast/export/r07/" + mday.format("YYYY")+ "/"+ mday.format("DDDD") + "/" + basename
				}
				console.log(url)
				res.redirect(url)
				break			
			case 'precipitation':
				var basename = "gpm_1d." + formattedDate + ext
				if( ext == 'topojson') {
					url = "/products/s3/r07/gpm_1d/" + mday.format("YYYY")+ "/"+ mday.format("DDDD") + "/" + basename
				} else {
					url = "/products/gpm_1d/export/r07/" + mday.format("YYYY")+ "/"+ mday.format("DDDD") + "/" + basename
				}	
				console.log(url)
				res.redirect(url)
				break
			default:
				res.redirect("/test/ro7")
						
		}
	},
	topojson: function(req,res) {
		var id 			= req.params['id'];
		var dirname		= path.join(app.root,"public")
		var fileName	= path.join(dirname, id+".topojson.gz")
		
		var gzip 		= zlib.createGzip();
		var inp 		= fs.createReadStream(fileName);
		var tj			= ''
		inp.pipe(gzip)
			.on('data', function(chunk) { tj += chunk })
			.on('end', function() {
				console.log(tj)
				// convert to geojson
				// clip it to bbox
				// convert it back to topojson
				// compress it
				//send it
			})
	},
	precip: function(req,res) {
		var id			= req.params['id'];
		var lat 		= parseFloat(req.query['lat']);
		var lng			= parseFloat(req.query['lng']);
		
		console.log("precip", id)
		
		var tmp_dir 	= app.get("tmp_dir")
				
		var dt			= id.replace("gpm_1d.", "")
		var date 		= moment(dt, "YYYYMMDD")
		var year		= date.years().toString()
		var month		= date.month() + 1
		if( month < 10 ) {
			month = "0"+ month
		} else {
			month = month.toString()
		}
		var day			= date.date().toString()
		if (day < 10 ) day = "0"+day
				
		var jday		= date.dayOfYear()
		if( jday < 10) {
			jday = "00"+jday
		} else if( jday < 100 ) {
			jday = "0"+jday
		} else {
			jday = jday.toString()
		}
		
		console.log(year, month, day, jday)
		var fileName	= path.join(tmp_dir, "ojo-global", "gpm", year, jday, id+".tif")
		
		var json 	= {
			'id': 		id,
			'lat': 		lat,
			'lng': 		lng,
			'precip': 	"??"
		}

		console.log(fileName, lat, lng)
		try {
			if( !fs.existsSync(fileName)) {
				var options = {
					Bucket: "ojo-global", 
					Key:  "gpm/"+year+"/"+jday+"/"+id+".tif"
				};
				app.s3.headObject(options, function(err, data) {
					if (err) {
						console.log("headObject", otpions, "error", err, err.stack); // an error occurred
						return res.sendStatus(500)
					} else {
						console.log("Object seems to be there...creating", fileName)
						var file = fs.createWriteStream(fileName);
						app.s3.getObject(options)
						.createReadStream()
						.pipe(file)
			
						file.on('close', function() {
							console.log("got file from S3", fileName)
							var result 	= getGeopixValue(fileName, lat, lng)
							json.precip = result / 10
							res.send(json)
						});
					}    
				});
			} else {
				console.log("File exists... getting geopix...")
				var result 	= getGeopixValue(fileName, lat, lng)
				json.precip = result / 10
				
				res.send(json)
			}
		} catch(e) {
			console.log("Error", er)
			res.send(json)			
		}
		
	},

	index2: function(req, res) {       
		var id 	= req.params['id'];
		var ip 	= getClientAddress(req)
		var url = 'http://freegeoip.net/json/' + ip
		request.get( url, function (error, response, body) {
			if(!error && response.statusCode == 200 ) {
				var data = JSON.parse(body)
				console.log(data)
			}
		})
		
		res.render("test/index.ejs", {layout: false})
	},
	image: function(req, res) {
		res.sendfile("./public/img/trmm_24_d03_20140421.thn.png")
	},
	index: function(req, res) {
		var userid = 2

		function getAuthorInfo( cb ) {
			sleep(1000)
			console.log("getAuthorInfo", userid)
			cb(null)
		}
		function updateModifiedRecords( cb ) {
			async.eachSeries([1,2,3,5,8], function(el, next) {
				console.log("Modifying", userid, el)
				sleep(1000)
			
				next(null)
			}, function(err) {
				console.log("updateModifiedRecords done")
				cb(null)
			})
		}
		function createChangeSet( cb ) {
			console.log("creating Changeset...")
			sleep(1000)
			console.log("created!")
			cb(null)
		}
				
		async.series([
			getAuthorInfo,
			updateModifiedRecords,
			createChangeSet
		], function(err, results) {
				if( err ) {
					console.log("** Err async series", err)
				} else {
					console.log("changeset saved")
				}
				res.send("Done")
			})
	}
};