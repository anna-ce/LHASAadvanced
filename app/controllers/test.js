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
				console.log(data)
				res.render("test/gpm2.ejs", { 
					layout: false,
					token: process.env.MAPBOX_PUBLIC_TOKEN,
					latitude: data.latitude,
					longitude: data.longitude
				 })	
			}
		})
	},
	
	gpm3: function(req, res) {
		res.render("test/gpm3.ejs", { layout: false })	
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
			var result 	= getGeopixValue(fileName, lat, lng)
			json.precip = result / 10
				
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