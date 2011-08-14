

function split( val ) {
	return val.split( /,\s*/ );
}
function extractLast( term ) {
	return split( term ).pop();
}

function get_emails(id) {
	return split($( "#" + id ).val());
}

function make_autocomplete(id, data) {
	$( "#" + id )
		// don't navigate away from the field on tab when selecting an item
		.bind( "keydown", function( event ) {
			if ( event.keyCode === $.ui.keyCode.TAB &&
					$( this ).data( "autocomplete" ).menu.active ) {
				event.preventDefault();
			}
		})
		.autocomplete({
			minLength: 0,
			maxLength: 30,
			source: function( request, response ) {
				// delegate back to autocomplete, but extract the last term
				response( $.ui.autocomplete.filter(
					data, extractLast( request.term ) ) );
			},
			focus: function() {
				// prevent value inserted on focus
				return false;
			},
			select: function( event, ui ) {
				var terms = split( this.value );
				// remove the current input
				terms.pop();
				// add the selected item
				terms.push( ui.item.value );
				// add placeholder to get the comma-and-space at the end
				terms.push( "" );
				this.value = terms.join( ", " );
				return false;
			}
		});
}












	function updateValuesChanging(event, ui){
		displayValues(ui.label, ui.values)
	}
	
	function updateValuesChanged(event, ui) {
		values = ui.values;
		start = $.datepicker.formatDate("yy-mm-dd", values.min)
		end = $.datepicker.formatDate("yy-mm-dd", values.max);
		byHour(start, end)
	}
	
	function displayValues(slider, values){
  		//slider.parents("form").find("input[name=min]").val($.datepicker.formatDate("yy-mm-dd", values.min));
	  	//slider.parents("form").find("input[name=max]").val($.datepicker.formatDate("yy-mm-dd", values.max));
	  
	}
	
	function makeDateSlider(selector, options){
		var slider = $(selector)
			.dateRangeSlider(options)
			.bind("valuesChanging", function(event, ui){updateValuesChanging(event, ui);})
			.bind("valuesChanged", function(event, ui){updateValuesChanged(event, ui);})
			.addClass("ui-rangeSlider-dev");
		displayValues(slider, slider.rangeSlider("values"));
	}