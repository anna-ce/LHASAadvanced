var util			= require('util'),
	async			= require('async'),
	eyes			= require('eyes'),
	moment			= require('moment'),
	path			= require('path'),
	mkdirp 			= require('mkdirp'),
	filesize 		= require('filesize'),
	Hawk			= require('hawk'),
	glob 			= require("glob")
	debug			= require('debug')('products'),
	exec 			= require('child_process').exec,
	mime			= require('mime-types'),
	osm_geojson		= require("osm-and-geojson/osm_geojson"),
	tokml			= require('tokml'),
	turf			= require('turf'),
	turf_bbox_clip	= require('./lib/turf-bbox-clip');

	fs				= require('fs'),
	topojson		= require('topojson'),
    topotype 		= require("topojson/lib/topojson/type"),

	zlib 			= require('zlib');
	
	var yaml		= JSON.parse(fs.readFileSync("./config/products.yaml", "utf-8"))
	
	function makePoly( bbox, options ) {
		var feature = turf.polygon([[
			[ bbox[0], bbox[1] ],
			[ bbox[0], bbox[3] ],
			[ bbox[2], bbox[3] ],
			[ bbox[2], bbox[1] ],
			[ bbox[0], bbox[1] ]
		]], options)
		
		return feature
	}
	
	module.exports = {
		index: function(req, res) {
			var user 		= req.session.user		
			res.render("products/v2/index", {
				products: yaml,
				user: user, 
				layout: false})
		},
		
		whichProduct: function(req,res) {
			var user 	= req.session.user
			var prod	= req.params["prod"]
			var span	= req.params["span"]
			var reg		= req.params["reg"]
			
			var region	= yaml.regions[reg]
			region.id	= reg
			
			var geojson = makePoly(region.bbox)
			
			var product	= yaml.products[prod]
			var id		= "gpm_24.20150604"
			
			console.log(region.id, id)
			res.render("products/v2/whichProduct", {
				prod: 		prod,
				span: 		span,
				region: 	region,
				product: 	product,
				id: 		id,
				user: 		user, 
				layout: false})
		},
		
		getProduct: function(req,res) {
			var user 	= req.session.user
			var prod	= req.params["prod"]
			var span	= req.params["span"]
			var reg		= req.params["reg"]
			var region	= yaml.regions[reg]
			var id		= req.params["id"]
			var fmt		= req.params["fmt"]
			
			var dirname		= path.join(app.root,"public")
			var fileName	= path.join(dirname, id+".topojson.gz")
			console.log("Reading in", fileName)
			
			console.log("decompress...")
			var gzip 		= zlib.createGunzip();
			var inp 		= fs.createReadStream(fileName);
			var data		= ''
			inp.pipe(gzip)
				.on('data', function(chunk) { data += chunk })
				.on('end', function() {
					
					console.log("convert topojson to geojson...")
					var topology = JSON.parse(data)

					var precision = Math.pow(10, 3), round = isNaN(precision)
				    ? function(x) { return x; }
				    : function(x) { return Math.round(x * precision) / precision; };

					// convert to geojson					
    				for (var key in topology.objects) {
    					var geojson = topojson.feature(topology, topology.objects[key]);
					    topotype({
					      Feature: function(feature) {
					        return this.defaults.Feature.call(this, feature);
					      },
					      point: function(point) {
					        point[0] = round(point[0]);
					        point[1] = round(point[1]);
					      }
					    }).object(geojson);
    				}

					console.log("intersects...", geojson.features.length)
					
					//var poly1 = makePoly(region.bbox, null)
					var features = [];
					for (var f in geojson.features ) {
						try {
							//var intersection = turf.intersect(poly1, geojson.features[f])
							var intersection = turf_bbox_clip(geojson.features[f], region.bbox)
							if( intersection && intersection.geometry.coordinates.length ) {
								intersection.properties = geojson.features[f].properties
								features.push(intersection)
							} else {
								//console.log("null intersect")
							}
						} catch(e) {
							//console.log("dies in", JSON.stringify(geojson.features[f]))
							console.log("dies in", f)
						}
					}
					console.log("done", features.length)
					geojson.features = features
					
				    // Convert GeoJSON to TopoJSON.
				    //var object = topojson.topology(geojson, {});
					
					res.send(geojson)
					// clip it to bbox
					// convert it back to topojson
					// compress it
					//send it
				})
		},
		regions: function(req, res) {
			var user 	= req.session.user
			var prod	= req.params["prod"]
			
			var product = yaml.products[prod]
			
			var features = [
			]
			
			for( var r in product.regions ) {
				var region 	= yaml.regions[product.regions[r]]
				var bbox	= region.bbox
				var name	= region.name
				
				var feature = turf.polygon([[
					[ bbox[0], bbox[1] ],
					[ bbox[0], bbox[3] ],
					[ bbox[2], bbox[3] ],
					[ bbox[2], bbox[1] ],
					[ bbox[0], bbox[1] ]
				]], { name: name, bucket: product.regions[r] })
				
				features.push(feature)
			}
			
			var geojson = turf.featurecollection(features);
			console.log(JSON.stringify(geojson))
			
			res.render("products/v2/regions", {
				config: yaml,
				prod: prod,
				product: yaml.products[prod],
				user: 	user, 
				geojson: geojson,
				layout: false})
		}
	}
	
	