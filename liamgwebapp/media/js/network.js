function gen_thread(id, ntime) {
	var name = {name:"thread #" + id, tid:id};
	var data = []
	for (var time = 0; time < ntime; time++) {
		size =  Math.floor(Math.random() * 8);
		size = (size > 0)? size + 2: 0;
		enter = [];
		exit = [];
		if (time == 5 && id == 2) enter = [5];
		else if (time == 3 && id == 4) enter = [1,9];
		else if (time == 4 && id == 4) enter = [8]		
		else if (time == 5 && id == 8) exit = [2]				
		data.push({tid: id, time: time, size: size, enter: enter, exit: exit, payload: "Thread " + id + " at timestep " + time})
	}
	return [name, data];
}

function gen_threads(n) {
	var ret = [];
	for (var i = 0; i < n; i++) {
		ret.push(gen_thread(i, 10));
	}
	return ret;
}




function darker(color) {
	return d3.rgb(color).darker(0.5);
}

function circle_mousein(d,i) {	
	$(this).css({"fill" : d3.rgb(color(d.tid)).brighter(0.5).toString(),
		'stroke-width': 4,
		'stroke' : d3.rgb(color(d.tid)).darker().toString(),
		'cursor' : "pointer"});
	tooltipid = "tooltip_" + d.tid + "_" + i;
	tooltip = $("#"+tooltipid);
	mx = d3.event.pageX
	my = d3.event.pageY
	nc = $("#network_container")
	ncpos = nc.position()
	offset = Math.max(20, d.size + 10) ;

	mx = x(d.time) + ncpos.left - window.pageXOffset;
	my = y(d.tid) + ncpos.top - window.pageYOffset;
	upperx = mx + offset + tooltip.outerWidth()
	uppery = my + offset + tooltip.outerHeight()

	offsetx = (upperx > window.innerWidth)? -(offset + tooltip.outerWidth()) : offset;
	mx = mx + offsetx + window.pageXOffset;
	offsety = (uppery > window.innerHeight)? -(offset + tooltip.outerHeight()) : offset;
	my = my + offsety + window.pageYOffset
	tooltip.show().css({"left":mx,"top": my});

}

function circle_mouseout(d,i) {
	$(this).css({'fill' : color(d.tid),
		'stroke-width' : 0,
		'cursor' : "none"});
	tooltipid = "tooltip_" + d.tid + "_" + i;
	$("#" + tooltipid).hide()
}





function gen_line(d,i) {
	var pts = [{x: x(i-1), y: y(d.tid)}, {x: x(i), y: y(d.tid)}]
	var ret =  d3.svg.line()
	    .x(function(d) { return d.x; })
	    .y(function(d) { return d.y; })
	(pts) + "Z";
	return ret;
}

// track functions
function track_x1(d,i) {
	ret = (i == 0)? x(0) : x(i-1);
	size = (i == 0)? 0: data[d.tid][i-1].size;
	margin = (size == 0)? 0 : trackmargin;
	return ret + size + margin;
}
function track_x2(d,i) {return x(i) - d.size - ((d.size==0)? 0 : trackmargin);}
function track_y1(d,i) {return y(d.tid);}
function track_y2(d,i) {return y(d.tid);}






function arrow_offset(d) {
	return d.size + arrowmargin;
	r = d.size + arrowmargin;
	alpha = Math.pow((r*r)/2.0, 0.5);
	return alpha;
}

function create_arrowpath(d,i) {
	A = 10
	B = 4
	
	time = d.time;
	tid = d.tid;
	nextel = data[d.nexttid][time+1];
	arroffset1 = arrow_offset(d);
	mult1 = (d.nexttid < d.tid)? -1 : 1;
	x1 = x(time) + arroffset1// + arroffset1
	y1 = y(d.tid) + mult1 * arroffset1;
	y11 = y1 + mult1 * Math.min(7, ((y(1) + y(0)) / 2.2));
	
	
	arroffset2 = arrow_offset(nextel);
	mult2 = (d.nexttid < d.tid)? 1 : -1;
	x2 = x(time+1) - arroffset2 - (A-B/2);
	y2 = y(nextel.tid) + mult2 * (arroffset2 + (A-B/2));

	// create the path.  y then x
	path = [[x1,y1], [x1, y11], [(x2+x1)/2, y11], [(x2+x1)/2, y2], [x2,y2]]
	ret = path.map(function (pt) { return pt[0]  + " " + pt[1] })
	ret = "M " + ret.join(" L ") + " ";
	
	ret = "M " + x1 + " " + y1 + " C" + [[x1 + (x2-x1)/3, y1], [x1+2*(x2-x1)/3, y2], [x2,y2]].map(function(pt){return pt.join(" ")}).join(" ");
	
	return ret;
}
function create_arrowhead(d,i) {
	A = 10
	B = 4		
	time = d.time;
	tid = d.tid;
	nextel = data[d.nexttid][time+1];		
	offset = arrow_offset(nextel);
	mult = (d.nexttid < d.tid)? 1 : -1;
	xpos = x(time+1) - offset;
	ypos = y(nextel.tid) + mult * offset;		

	path = [[xpos - A, ypos + mult * (A-B)], [xpos - (A-B), ypos + mult * A], [xpos,ypos]]
	ret = path.map(function (pt) { return pt[0]  + " " + pt[1] })
	ret = "M " + ret.join(" L ") + " z";
	return ret;
	
}

function flatten_enter(el) {
	var ret = [];
	for (var key in el.enter) {
		nexttid = el.enter[key]
		copy = clone(el);
		copy.nexttid = nexttid;
		ret.push(copy)
	}
	return ret;
}
function flatten_exit(el) {
	var ret = [];
	for (var key in el.exit) {
		nexttid = el.exit[key]
		copy = clone(el);
		copy.nexttid = nexttid;
		ret.push(copy)
	}
	return ret;
}

function setup_enter_path(d) {
	filtered = d.filter(function(el) {return el.enter.length > 0;})
	return d3.merge(filtered.map(flatten_enter)) 
}
function setup_exit_path(d) {
	filtered = d.filter(function(el) {return el.exit.length > 0;})
	return d3.merge(filtered.map(flatten_exit)) 
}
