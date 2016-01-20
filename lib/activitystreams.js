// Activity Streams
// Pat Cappelaere
// Inspired by jasnell/activitystrea.ms v2 1.4?
var mime_type = require("mime-types")

function Action(name, type) {
	this['@type'] 			= type
	this['displayName']		= name
	this['using']			= []
}

Action.prototype.addHttpGet = function (name, url, size) {
	var mediaType = mime_type.lookup(url)
	var a = {
		"@type": 		"as:HttpRequest",
		"method": 		"GET",
		"medaType": 	mediaType,
		"url": 			url,
		"displayName": 	name,
	}

	if(size) a.size = size
		
	this.using.push(a)
	return this
}

// define entry object
function Entry(id, type, name) {
	this['@id'] 		= id
	this['@type']		= type
	this['displayName']	= name
}

Entry.prototype.stringify = function() {
	return JSON.stringify(this,null,"\t")
}

function Image(url) {
	var mediaType	= mime_type.lookup(url)
	this.url 		= url
	this.mediaType 	= mediaType
	this.rel		= "browse"
}

Entry.prototype.addProperty = function(tag,name,value) {
	if (this.properties == undefined) { this.properties = {}}
	this.properties[tag] = {
		"@label": name,
		"@value": value
	}
	return this
}

Entry.prototype.addImage = function(url, type) {
	var img = new Image(url, type)
	if (this.image == undefined) { this.image = []}
	this.image.push(img)
	return this
}

Entry.prototype.addAction = function(a) {
	
	if (this.action == undefined) { this.action = []}
	this.action.push(a)
	return this
}

Entry.prototype.geometry_bbox = function(bbox) {
	this.geometry = {
		"type": "Polygon",
		"coordinates": [[
			[bbox[0], bbox[1]],
			[bbox[0], bbox[3]],
			[bbox[2], bbox[3]],
			[bbox[2], bbox[1]],
			[bbox[0], bbox[1]]
		]]
	}
	return this
}

module.exports = {
	entry: function(id, type) {
		return new Entry(id, type)
	},
	action: function(name, type) {
		return new Action(name, type)
	}
}