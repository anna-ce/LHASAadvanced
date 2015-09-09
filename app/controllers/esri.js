module.exports = {
  
  	// List all
	index: function(req, res) {	
		var id = req.params['id']	
		res.render("esri/"+id+".ejs", {
			layout: false
		})			
	}
}