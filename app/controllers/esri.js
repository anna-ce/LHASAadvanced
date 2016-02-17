module.exports = {
  
  	// List all
	index: function(req, res) {	
		var product		= req.params['id']
		var host 		= req.protocol + "://"+ req.get('Host')
		var latitude	= 33.87
		var longitude	= -90.77
		
		console.log("esri product", product)
		var prefix		= product.split(".")[0]
		
		console.log("esri index", prefix)
		
		if( (prefix == "precip_1d") || (prefix == "precip_3d") || (prefix == "precip_7d") || (prefix=="precip_3hrs") || (prefix=="precip_30mn")) {
			source 	= "gpm"
		} else if( prefix == 'landslide_nowcast') {
			source  	= "landslide_model"
			latitude	= 27
			longitude	= 83
		} else if( prefix == 'flood_nowcast') {
			source 		= "gfms"
			latitude	= 27
			longitude	= 83
		} else if( prefix == 'landslide_catalog') {
			source 		= "dk"
			latitude	= 27
			longitude	= 83
		} else {
			return res.send(404, "invalid product")
		}
		
		console.log(prefix, source, latitude, longitude)
		res.render("esri/index.ejs", {
			layout: 	false,
			host: 		host,
			product: 	prefix,
			source: 	source,
			latitude: 	latitude,
			longitude: 	longitude
		})			
	}
}