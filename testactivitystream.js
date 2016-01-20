var as = require("./lib/activitystreams.js")

var entry = as.entry("precip_movie_20160112_20160115_7h64s7b", "geoss:precip_movie", "precip_movie")
				.addImage("movie.jpg")
				.geometry_bbox([ -43, -21.6332733, -41, -19.6332733 ])
				.addProperty("source", "source", "NASA GSFC GPM")				
				.addProperty("url", "url", "http://pmm.nasa.gov/")				
				.addProperty("sensor", "sensor", "GPM")
				.addProperty("date", "date", "2016/01/12 - 2016/01/15")				
				.addProperty("resolution", "resolution", "1000m")

var browse = as.action("ojo:browse", "browse")
				.addHttpGet("movie", "movie.mp4")

entry.addAction(browse)
							
console.log( entry.stringify() )