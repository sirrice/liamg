
function getTopSendersList(id, start, end){

	if (start === undefined || start == null) start = "2010-1-1";
	if (end === undefined || end == null) end = "2011-8-14";

 	$.getJSON("/emailanalysis/topsenders/json/",{start:start, end:end},function(data){
		var email, count;
		$("#" + id).empty();
		var table = $("<table></table>");
		table.attr("id", "table_" + i);
		$("#" + id).append(table);

		for (var i = 0; i < data.labels.length; i++) {
			email = data.labels[i];
			count = data.y[i];
			
			if (email.length > 23)
			 email = email.substr(0,10) + "..." + email.substr(email.length-10,10)
			
			
			var tr = $("<tr></tr>");
			var td1 = $("<td class='email'></td>").text(email);
			var td2 = $("<td class='count'></td>").text(count + " emails");
			var td3 = $("<td class='spark'></td>");
			var spark = $("<span></span>").attr("id", "spark_" + i);
			td3.append("<label>"+start+"</label>").append(spark).append("<label>"+end+"</label>");
			tr.append(td1).append(td2).append(td3);
			table.append(tr)
			loadSpark(email, spark, start, end);				
		}
		

	}); 
};

function loadSpark(email, el, start, end) {
			$.getJSON("/emailanalysis/getcount/json/", {start:start, end:end, granularity:"week", email:email}, function(data) {
				var options = {
					type : "line",
					width: 200,
					height: 25
				}
				el.sparkline(data.y, options);
			});		
}



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
	

	
	function displayValues(slider, values){
  		//slider.parents("form").find("input[name=min]").val($.datepicker.formatDate("yy-mm-dd", values.min));
	  	//slider.parents("form").find("input[name=max]").val($.datepicker.formatDate("yy-mm-dd", values.max));
	  
	}
	
	function makeDateSlider(selector, options, f){
		function updateValuesChanged(event, ui) {
			values = ui.values;
			start = $.datepicker.formatDate("yy-mm-dd", values.min)
			end = $.datepicker.formatDate("yy-mm-dd", values.max);
			if (!(f === undefined)) f(start, end)
		}		
		
		
		var slider = $(selector)
			.dateRangeSlider(options)
			.bind("valuesChanging", function(event, ui){updateValuesChanging(event, ui);})
			.bind("valuesChanged", function(event, ui){updateValuesChanged(event, ui);})
			.addClass("ui-rangeSlider-dev");
		displayValues(slider, slider.rangeSlider("values"));
	}