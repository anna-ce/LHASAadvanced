var util 			= require('util'),
	fs				= require('fs'),
	async	 		= require('async'),
	path			= require('path'),
	moment			= require('moment'),
	unirest			= require('unirest'),
	xml2js 			= require('xml2js'),
	_				= require('underscore'),
	mime			= require('mime-types'),
	Hawk			= require('hawk'),
	childProcess 	= require('child_process'),
	debug			= require('debug')('pl');

var base_url		= "https://api.planet.com/v0/scenes/ortho/";
var key 			= process.env.PLANET_LABS_KEY;
var auth 			= "Basic " + new Buffer(key + ":").toString("base64");

var tmpdir			= app.get("tmp_dir")
var planetLabsDir	= tmpdir + "/tmp/planet-labs"
	
if( !fs.existsSync(planetLabsDir)) fs.mkdirSync(planetLabsDir)
	
// array of long,lat coordinates from GeoJSON
// return sw corner and ne corner in lat lon
function fromPolygon(arr) {
	var sw_lat=90, 	ne_lat=-90;
	var sw_lon=180, ne_lon=-180;
	
	for( var i in arr ) {
		var lonlat = arr[i]
		// lon
		if(lonlat[0] < sw_lon) sw_lon = lonlat[0]
		if(lonlat[0] > ne_lon) ne_lon = lonlat[0]
		//lat
		if(lonlat[1] < sw_lat) sw_lat = lonlat[1]
		if(lonlat[1] > ne_lat) ne_lat = lonlat[1]
	}
	return [[sw_lat,sw_lon],[ne_lat,ne_lon]]
}

function DownloadData( url, fname, cb ) {
	debug("Download", url)
	var req = unirest.get(url)
	.auth({
		user: key,
		password: '',
		sendImmediately: true
	})
	.encoding(null)
	.end( function(response) {
		//console.log(response.status)
		if( response.ok ) {
			fs.writeFileSync(fname, response.body)
			debug("Saved as", fname)
		} else {
			logger.error( response.code, JSON.stringify(response.error))
		}
		cb(response.ok)
	})
}

function sendFile( res, file ) {
	var ext 		= path.extname(file)
	var basename 	= path.basename(file)
	var dirname 	= path.dirname(file)
	
	var mime_type 	= mime.lookup(path.basename(file))
	//console.log( "sendFile", file, ext, mime_type)
	
	if( ext == ".topojson") {
		res.header("Content-Type", "application/json")
		res.header("Content-Encoding", "gzip")
		basename += ".gz"
		//console.log("sending .topojson application/json gzip", basename)
	} else {
		//console.log("sending ", mime_type, basename, dirname)
		res.header("Content-Type", mime_type, basename)
		res.header("Content-Disposition", 'attachment; filename="'+basename +'"')
		//console.log(ext, mime_type, "no encoding")
	}
	
	res.header("Access-Control-Allow-Origin", "*")
	res.sendfile(basename, {root: dirname})
}

module.exports = {
	process: function(req, res) {
		var id 		= req.params.id
		var cmd 	= app.root + "/python/pl_floodmap.py --scene "+id
		var user	= req.session.user
			
		console.log("process pl", cmd)	
			
		var child 	= childProcess.exec(cmd, function (error, stdout, stderr) {
			if (error) {
		  	   console.log(error.stack);
		  	   console.log('Error code: '+error.code);
		  	   console.log('Signal received: '+error.signal);
		   	}
			console.log('Child Process STDOUT: '+stdout);
			console.log('Child Process STDERR: '+stderr);
		});

		child.on('exit', function (code) {
			console.log('Child process exited with exit code '+code);
		}); 
		
		res.render('products/planetlabs_floodmap_processing', {
			user: 				user,
			id: id
		})
	},
	
	map: function(req,res) {
		var id 			= req.params.id
		var url			= base_url + id
		var user		= req.session.user
		var host		= req.headers['host']
		var query		= req.query.q
			 
		var mbtiles		= null;	//path.join(planetLabsDir, id+"_full.mbtiles")
		var thn 		= null
		var topojson 	= null;
		
		if (query == 'rgb_composite') {
			thn			= "http://"+host+"/products/planetlabs/"+ id + "/thn"
		} else {
			topojson	= "http://"+host+"/products/planetlabs/"+ id + "/surface_water.topojson"			
		}
			
		debug("Map", id)
		
		var req = unirest.get(url)
		.auth({
			user: key,
			password: '',
			sendImmediately: true
		})
		.encoding(null)
		.end( function(response) {
		    if (response.ok) {
		        var data = response.body;
				console.log(data)				
			}
			
			data.properties.source = {
				"@label": "source",
				"@value": "Planet-Labs Dove"
			}
				
			data.properties.source.resolution = {
				"@label": "resolution",
				"@value": "3m"
			}
			
			var target=[data.properties.sat.lat, data.properties.sat.lng]
			var bounds=fromPolygon(data.geometry.coordinates[0])
				 
			//console.log(data)
			res.render('products/map_mbtiles', {
				user: 				user,
				mapbox_accessToken: process.env["MAPBOX_PUBLIC_TOKEN"],
				map_id: 			app.config.regions.Global.map_id,
				worldmapid: 		app.config.worldmapid,	
				target:  			target,
				bounds: 			bounds,
				id: 				id,
				query: 				query,
				data: 				data,
				mbtiles: 			mbtiles,
				thn: 				thn,
				topojson: 			topojson
			})
		})
	},
	
	thn: function(req,res) {
		var id 			= req.params.id
		var url			= base_url + id+"/thumb"
		var sceneDir	= path.join(planetLabsDir, id)
		if( ! fs.existsSync(sceneDir)) fs.mkdirSync(sceneDir)
		
			var fname		= path.join(sceneDir, id+"_thn.png")
		if( ! fs.existsSync(fname)) {
			debug("thn download", id, fname)
			url += "?size=lg"
			DownloadData( url, fname, function(err) {
				if( fs.existsSync(fname)) {
					sendFile( res, fname )
				} else {
					res.send("Error downloading thn for", id)
				}				
			})
		} else {
			debug("thn exists", id, fname)
			sendFile( res, fname )		
		}
	},
	
	full: function(req,res) {
		var id 			= req.params.id
		var url			= base_url + id + "/full"
		var sceneDir	= path.join(planetLabsDir, id)
		
		console.log("full", sceneDir)
			
		if( ! fs.existsSync(sceneDir)) fs.mkdirSync(sceneDir)

		var fname		= path.join(sceneDir, id+"_full.tif")
		if( ! fs.existsSync(fname)) {
			DownloadData( url, fname, function(err) {
				if( fs.existsSync(fname)) {
					sendFile( res, fname )
				} else {
					res.send("Error downloading full image for", id)
				}		
			})
		} else {
			sendFile( res, fname )			
		}
	},
	topojson: function(req,res) {
		var id 			= req.params.id
		var sceneDir	= path.join(planetLabsDir, id)
		var fname		= path.join(sceneDir, "surface_water.topojson")
		sendFile( res, fname )
		
	},
	topojsongz: function(req,res) {
		var id 			= req.params.id
		var sceneDir	= path.join(planetLabsDir, id)
		var fname		= path.join(sceneDir, "surface_water.topojson.gz")
		sendFile( res, fname )
	},
	index: function(req, res) {
		var id 			= req.params.id
		var url			= base_url + id
		var fbAppId 	= app.config.fbAppId;
		var region		= app.config.regions.d04;
		var query		= req.query.q
		var host		= req.headers['host']
			
		console.log(query)
		var req = unirest.get(url)
		.auth({
			user: key,
			password: '',
			sendImmediately: true
		})
		.encoding(null)
		.end( function(response) {
		    if (response.ok) {
				console.log(response.body)
		        var data = response.body;
			}
			
			debug("planetlabs", id)
			var data_url;
			if( query == 'rgb_composite') {
				data_url = "http://"+host+"/products/planetlabs/"+id+"/full"
			} else {
				data_url = "http://"+host+"/products/planetlabs/"+id+"/surface_water.topojson.gz"
			}
				
			res.render("products/planetlabs", {
				layout: 		false,
				fbAppId: 		fbAppId,
				url: 			url,
				date: 			moment().format("YYY-MM-DD"),
				region: 		region,
				id: 			id,
				query: 			query,
				data: 			data,
				data_url: 		data_url,
				image: 			"/products/planetlabs/"+id+"/thn",
				description: 	"PlanetLabs Scene "+id
			
			})		
		})
	}
}