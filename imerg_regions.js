// Convert imerg_regions to geojson
var fs = require('fs')

var inputFileName 	= 'imerg_regions.yaml'
var outputFileName 	= 'imerg_regions.geojson'

var imerg_regions = JSON.parse( fs.readFileSync(inputFileName))

var regions = {
	type: 'FeatureCollection',
	features: []
}

function ToPolygons(bbox) {
	var poly = [
		[bbox[0], bbox[1]],
		[bbox[2], bbox[1]],
		[bbox[2], bbox[3]],
		[bbox[0], bbox[3]],
		[bbox[0], bbox[1]]
	]
	return poly
}

for( var r in imerg_regions.regions) {
	var region = imerg_regions.regions[r]
	var feature = {
		type: 	'Feature',
		id: 	region.id,
		properties: {
			name: region.name,
		},
		geometry: {
			type: "Polygon",
			coordinates: [
				ToPolygons(region.bbox)
			]
		}
	}
	regions.features.push(feature)
}

fs.writeFileSync(outputFileName, JSON.stringify(regions,null,'\t'), 'utf-8')
console.log("Generated", outputFileName)