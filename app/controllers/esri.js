module.exports = {
  
  	// List all
	index: function(req, res) {	
		var product		= req.params['id']
		var host 		= req.protocol + "://"+ req.get('Host')
		var latitude	= 33.87
		var longitude	= -90.77
		
		console.log("esri product", product)
		
		if( (product === "precip_1d") || (product === "precip_3d") || (product == "precip_7d") || (product=="precip_3hrs") || (product="precip_30mn")){
			source 	= "gpm"
		} else if( product === 'landslide_nowcast') {
			source  	= "landslide_model"
			latitude	= 27
			longitude	= 83
		} else if( product === 'flood_nowcast') {
			source 		= "gfms"
			latitude	= 27
			longitude	= 83
		} else if( product === 'landslide_catalog') {
			source 		= "dk"
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