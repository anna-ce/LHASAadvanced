var util 		= require('util');
var fs	 		= require('fs');
var path		= require('path');
var eyes		= require('eyes');
var https		= require('https');
var debug		= require('debug')('s3');
var request		= require('request');
var zlib 		= require('zlib');
var tar			= require('tar');
var debug		= require('debug')('s3');

//
// Get cached file and return json
//
function get_cached_data( filename, callback ) {
	var data = fs.readFile( filename, function(err, data) {
		var json = JSON.parse(data)
		callback( err, json )
	})
}

module.exports = {

	index: function(req, res) {       
		var bucket 			= req.params['bucket'];
		var id 				= req.params['id'];
		var ifNoneMatch 	= req.headers['if-none-match']
		var lastModified 	= req.headers['last-modified']
	
		var fileName		= path.join(app.root,'tmp',bucket,id.replace(".tgz", ""))
		
		if( fs.existsSync( fileName )) {
			// return it
			console.log("Found file in cache...", fileName)
			get_cached_data(fileName, function(err, json ) {
				res.send(json)				
			})
			return;
		}
		
		console.log("File ", fileName, " does not exists... fetching it from s3...")
		
		var options = {Bucket: bucket, Key: id};
		if( ifNoneMatch ) 	options["IfNoneMatch"] 		= ifNoneMatch
		if( lastModified ) 	options["IfModifiedSince"] 	= lastModified
		
		app.s3.getObject( options, function(err, data) {
			if( !err ) {
				var out 		= fs.createWriteStream(fileName)	
				
				var buff 		= new Buffer(data.Body, "binary")
				var Readable 	= require('stream').Readable;
				var rs 			= new Readable;
				rs.push( buff )
				rs.push(null)
				
				rs.pipe(zlib.createGunzip())
					.pipe(tar.Parse())
					.pipe(out)
				
				get_cached_data(fileName, function(err, json ) {
					if( !err ) {
						res.send(json)				
					}
				})
			} else {
				logger.error( "S3 getObject bucket %s key %s Err", bucket, id, err )
				res.send(err.statusCode)
			}
		})
	}
};