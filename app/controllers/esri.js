module.exports = {
  
  	// List all
	index: function(req, res) {	
		var product	= req.params['id']
		var host 		= "http://"+req.headers.host
		var latitude	= 33.87
		var longitude	= -90.77
		
		if( product === "precip_1d") {
			source 	= "gpm"
		} else if( product === 'landslide_nowcast') {
			source  	= "landslide_model"
			latitude	= 27
			longitude	= 83
		} else if( product === 'flood_nowcast') {
			source 		= "gfms"
			latitude	= 27
			longitude	= 83
		} else {
			return res.send(404, "invalid product")
		}
		
		res.render("esri/index.ejs", {
			layout: 	false,
			host: 		host,
			product: 	product,
			source: 	source,
			latitude: 	latitude,
			longitude: 	longitude
		})			
	}
}