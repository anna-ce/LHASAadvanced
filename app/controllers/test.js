var util 		= require('util');
var fs	 		= require('fs');
var path		= require('path');
var eyes		= require('eyes');
var async		= require('async');
var request		= require('request');
var debug		= require('debug')('tests');
var	geopix		= require('geopix');
var zlib 		= require('zlib');

function getClientAddress(request){ 
    with(request)
        return (headers['x-forwarded-for'] || '').split(',')[0] 
            || connection.remoteAddress
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
		res.render("test/gpm2.ejs", { layout: false })	
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
		var dirname		= path.join(app.root,"public")
		var fileName	= path.join(dirname, id+".tif")
		var json 	= {
				'id': 	id,
				'lat': 	lat,
				'lng': 	lng,
				'precip': "??"
		}

		try {
			
			console.log(fileName, lat, lng)
			if( fs.existsSync(fileName)) {
				var result 	= getGeopixValue(fileName, lat, lng)
				json.precip = result / 10
				
				console.log(json)
			} else {
				logger.error("File does not exist", fileName)
			}
			
			res.send(json)
		} catch(e) {
			console.log("error", e)
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