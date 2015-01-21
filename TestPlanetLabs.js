var fs				= require('fs'),
	unirest			= require("unirest")
	;

var base_url	= "https://api.planet.com/v0/scenes/ortho/";
var key 		= process.env.PLANET_LABS_KEY;


function DownloadData( url, fname ) {
	console.log("Trying to download", url)
	var chunks = [];
	
	var req = unirest.get(url)
	.auth({
		user: key,
		password: '',
		sendImmediately: true
	})
	.encoding(null)
	.end( function(response) {
			
		//var buffer = Buffer(response.body)
		fs.writeFileSync(fname, response.body)
		fs.close				
		console.log("Saved as", fname)
	})
}

// test thumbnail
var thumbnail_url = base_url + "ydnYQ9/thumb"
DownloadData( thumbnail_url, "ydnYQ9.thn.png" )	

var full_url = base_url + "ydnYQ9/full"
DownloadData( full_url, "ydnYQ9.tif" )	
	