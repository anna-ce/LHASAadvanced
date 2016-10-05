(function (undefined) {

var play = false
	
map.on('load', function () {
	AddMapLayers()
});

var toggleableLayerIds 	= [ 'precipitation', 'flood_nowcast',  'global_landslide_nowcast' ];
var labels 				= [ 'precipitation', 'flood',  'landslides' ];
var visibility 			= [ 'none', 'visible',  'none' ];

function get_GPM_url(){
	var formattedDate 	= dt.format("YYYYMMDD")
	var basename 		= "gpm_1d." + formattedDate + ".mvt"
	var url 			= host + "/products/gpm_1d/vt/Global/"+ dt.format("YYYY")+"/" + dt.format("DDDD")+"/{z}/{x}/{y}/" + basename
	return url
}

function get_GFMS_url(){
	var formattedDate 	= dt.format("YYYYMMDD")
	var basename 		= "flood_14km."+formattedDate + ".mvt"		
	var url 			= host + "/products/gfms/vt/Global/"+ dt.format("YYYY")+"/"+ dt.format("DDDD")+"/{z}/{x}/{y}/"+ basename
	return url
}
	
function getLandslideFileName(){
	var formattedDate 	= dt.format("YYYYMMDD")
	var basename 		= "global_landslide_nowcast_" + formattedDate + ".mvt"		
	var url 			= host + "/products/global_landslide_nowcast/vt/Global/" + dt.format("YYYY")+ "/"+ dt.format("DDDD") + "/{z}/{x}/{y}/"+basename
	return url
}

function RemoveMapLayers() {
	//console.log("RemoveMapLayers")
	for (var i = 0; i < toggleableLayerIds.length; i++) {
	    var id = toggleableLayerIds[i];
		map.removeLayer(id)
		map.removeSource(id)
	}
}

function AddMapLayers() {
	//console.log("AddMapLayers:", dt.format("YYYY-MM-DD"))
	
    map.addSource('precipitation', {
        type: 'vector',
		tiles: [ get_GPM_url() ]
    });
	
    map.addLayer({
        "id": "precipitation",
        "type": "fill",
        "source": "precipitation",
        "source-layer": "precipitation",
		"layout": {
			'visibility': visibility[0]
		},
        "paint": {
			"fill-color": {
				"property": "precip",
				"stops": [
					[1,  "#c0c0c0"],
					[2,  "#018414"],
					[3,  "#018c4e"],
					[5,  "#02b331"],
					[10,  "#57d005"],
					[20, "#b5e700"],
					[40, "#f9f602"],
					[70, "#fbc500"],
					[120, "#FF9400"],
					[200, "#FE0000"],
					[350, "#C80000"],
					[600, "#8F0000"],
				]
			},
			"fill-opacity": 0.2
        }
    });
		
    map.addSource('flood_nowcast', {
        type: 'vector',
		tiles: [ get_GFMS_url() ]
    });
	
    map.addLayer({
        "id": "flood_nowcast",
        "type": "fill",
        "source": "flood_nowcast",
        "source-layer": "flood_nowcast",
		"layout": {
			'visibility': visibility[1]
		},
        "paint": {
			"fill-color": {
				"property": "flood",
				"stops": [
					[1,   "#00FF00"],
					[10,  "#00BFFF"],
					[20,  "#0000FF"],
					[50,  "#FFD700"],
					[100, "#FFA500"],
					[200, "#FF0000"]
				]
			},
			"fill-opacity": 0.5
        }
    });
	
	
    map.addSource('global_landslide_nowcast', {
        type: 'vector',
		tiles: [
			getLandslideFileName()
		]
    });
	
    map.addLayer({
        "id": "global_landslide_nowcast",
        "type": "fill",
        "source": "global_landslide_nowcast",
        "source-layer": "global_landslide_nowcast",
		"layout": {
			'visibility': visibility[2]
		},
        "paint": {
			"fill-color": {
				"property": "nowcast",
				"stops": [
					[1,  "#ffcc00"],
					[2,  "#ff0000"]
				]
			},
			"fill-opacity": 0.5
        }
    });
	
	UpdateButtons();
}

function UpdateLayers() {
	RemoveMapLayers()
	AddMapLayers()
}

var maxDays = 8;
var playTimeout;

AddOne = function() {
	var delta = parseInt($('#slider').val())+1
	if(delta <= maxDays) {		
		$('#slider').val(delta)
		$('#slider').trigger('change')
	}
}

SubtractOne = function() {
	var delta = parseInt($('#slider').val()) - 1
	if(delta >= 0) {
		$('#slider').val(delta)
		$('#slider').trigger('change')
	}
}

function PlayOne() {
	var delta = parseInt($('#slider').val()) + 1
	if(delta >= maxDays) {
		$('#slider').val(0)
		$('#slider').trigger('change')
	}
	AddOne()
}

Play = function() {
	if( play == false ) {
		play = true
		$('#play').removeClass('fa fa-play').addClass('fa fa-pause')
		playTimeout = window.setInterval(PlayOne, 3000)
	} else {
		play = false
		$('#play').removeClass('fa fa-pause').addClass('fa fa-play')
		window.clearTimeout(playTimeout)
	}
	
	AddOne()
}

$("#slider").on("change", function(){
	var delta 	= maxDays -1 - parseInt(this.value)
	dt			= startTime.clone()
	dt 			= dt.subtract('days', delta) 
	fdt		 	= dt.format("YYYY-MM-DD")
	$('#DateLabel').html(fdt)	
	$('#date').html(fdt)
	UpdateLayers()
});

function UpdateButtons() {
    $('#menu').html("");
	
	for (var i = 0; i < toggleableLayerIds.length; i++) {
	    var id = toggleableLayerIds[i];

	    var link = document.createElement('a');
	    link.href = '#';
		link.textContent = labels[i];	//id;
	
		if( visibility[i] == 'visible') {
			link.className = 'active';
			//map.setLayoutProperty(layerName, 'visibility', 'visible');
		} else {
	        //map.setLayoutProperty(id, 'visibility', 'none');
		}
	
	    link.onclick = function (e) {
	        var clickedLayer 	= this.textContent;
			var id 				= labels.indexOf(clickedLayer)
			var layerName 		= toggleableLayerIds[id]
		
	        e.preventDefault();
	        e.stopPropagation();

	        var vis = map.getLayoutProperty(layerName, 'visibility');

	        if (vis === 'visible') {
	            map.setLayoutProperty(layerName, 'visibility', 'none');
				visibility[id] = 'none'
	            this.className = '';
	        } else {
	            this.className = 'active';
	            map.setLayoutProperty(layerName, 'visibility', 'visible');
				visibility[id] = 'visible'
	        }
			//console.log("visibility", layerName, clickedLayer, id, visibility[id])
	    };

	    //var layers = document.getElementById('menu');
	    $('#menu').append(link);
	}
}
}).call(this);
