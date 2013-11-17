var map = null; 
var currentWpIndex = 0;

var polyLine;
var tmpPolyLine;
var markers = [];
var vmarkers = []; 
var g = google.maps;
var planPath;

var initMap = function(mapHolder) {
    markers = [];
    vmarkers = [];
    var mapOptions = {
	zoom: 11,
	center: new g.LatLng(58.19, 15.6),
	mapTypeId: g.MapTypeId.HYBRID,
	draggableCursor: 'auto',
	draggingCursor: 'move',
	disableDoubleClickZoom: true
    };
    map = new g.Map(document.getElementById(mapHolder), mapOptions);
    g.event.addListener(map, "click", mapLeftClick);
    mapHolder = null;
    mapOptions = null;
};
 
var initPolyline = function() {
    var arrowHead = {
	path: g.SymbolPath.FORWARD_CLOSED_ARROW
    };

    var polyOptions = {
	icons: [{
		    icon: arrowHead,
		    offset: '100%'
	    }],
	strokeColor: "#3355FF",
	strokeOpacity: 0.8,
	strokeWeight: 2
    };
    var tmpPolyOptions = {
	strokeColor: "#3355FF",
	strokeOpacity: 0.4,
	strokeWeight: 6
    };

    polyLine = new g.Polyline(polyOptions);
    polyLine.setMap(map);
    tmpPolyLine = new g.Polyline(tmpPolyOptions);
    tmpPolyLine.setMap(map);
};
 
var mapLeftClick = function(event) {
    if (event.latLng) {
	var marker = createMarker(event.latLng);
	markers.push(marker);
	markers[markers.length - 1].setMap(map);
	if (markers.length != 1) {
	    var vmarker = createVMarker(event.latLng);
	    vmarkers.push(vmarker);
	    vmarker = null;
	}
	var path = polyLine.getPath();
	path.push(event.latLng);
	marker = null;
    }
    event = null;
};
 
var createMarker = function(point) {

    var imageNormal = {
	path: g.SymbolPath.CIRCLE,
	scale: 5,
    };
    var imageHover = {
	path: g.SymbolPath.CIRCLE,
	scale: 7,
	strokeColor: '#FF0000',
    };

    var marker = new g.Marker({
	    position: point,
	    map: map,
	    draggable: true,
	    icon: imageNormal
	    
	});
        g.event.addListener(marker, "mouseover", function() {
    	    marker.setIcon(imageHover);
    	});
       g.event.addListener(marker, "mouseout", function() {
    	    marker.setIcon(imageNormal);
    	});
    g.event.addListener(marker, "drag", function() {
	    for (var m = 0; m < markers.length; m++) {
		if (markers[m] == marker) {
		    polyLine.getPath().setAt(m, marker.getPosition());
		    moveVMarker(m);
		    break;
		}
	    }
	    m = null;
	});
    g.event.addListener(marker, "click", function() {
	    for (var m = 0; m < markers.length; m++) {
		if (markers[m] == marker) {
		    marker.setMap(null);
		    markers.splice(m, 1);
		    polyLine.getPath().removeAt(m);
		    removeVMarkers(m);
		    break;
		}
	    }
	    m = null;
	});
    return marker;
};
 
var createVMarker = function(point) {
    var prevpoint = markers[markers.length-2].getPosition();
    var imageNormal = {
	path: g.SymbolPath.CIRCLE,
	scale: 3
    };
    var imageHover = {
	path: g.SymbolPath.CIRCLE,
	scale: 4,
	strokeColor: '#FF0000',
    };

    var marker = new g.Marker({
	    position: new g.LatLng(
				   point.lat() - (0.5 * (point.lat() - prevpoint.lat())),
				   point.lng() - (0.5 * (point.lng() - prevpoint.lng()))
				   ),
	    map: map,
	    draggable: true,
	    icon: imageNormal
	});
    g.event.addListener(marker, "mouseover", function() {
    	    marker.setIcon(imageHover);
    	});
    g.event.addListener(marker, "mouseout", function() {
    	    marker.setIcon(imageNormal);
    	});
    g.event.addListener(marker, "dragstart", function() {
	    for (var m = 0; m < vmarkers.length; m++) {
		if (vmarkers[m] == marker) {
		    var tmpPath = tmpPolyLine.getPath();
		    tmpPath.push(markers[m].getPosition());
		    tmpPath.push(vmarkers[m].getPosition());
		    tmpPath.push(markers[m+1].getPosition());
		    break;
		}
	    }
	    m = null;
	});
    g.event.addListener(marker, "drag", function() {
	    for (var m = 0; m < vmarkers.length; m++) {
		if (vmarkers[m] == marker) {
		    tmpPolyLine.getPath().setAt(1, marker.getPosition());
		    break;
		}
	    }
	    m = null;
	});
    g.event.addListener(marker, "dragend", function() {
	    for (var m = 0; m < vmarkers.length; m++) {
		if (vmarkers[m] == marker) {
		    var newpos = marker.getPosition();
		    var startMarkerPos = markers[m].getPosition();
		    var firstVPos = new g.LatLng(
						 newpos.lat() - (0.5 * (newpos.lat() - startMarkerPos.lat())),
						 newpos.lng() - (0.5 * (newpos.lng() - startMarkerPos.lng()))
						 );
		    var endMarkerPos = markers[m+1].getPosition();
		    var secondVPos = new g.LatLng(
						  newpos.lat() - (0.5 * (newpos.lat() - endMarkerPos.lat())),
						  newpos.lng() - (0.5 * (newpos.lng() - endMarkerPos.lng()))
						  );
		    var newVMarker = createVMarker(secondVPos);
		    newVMarker.setPosition(secondVPos);//apply the correct position to the vmarker
		    var newMarker = createMarker(newpos);
		    markers.splice(m+1, 0, newMarker);
		    polyLine.getPath().insertAt(m+1, newpos);
		    marker.setPosition(firstVPos);
		    vmarkers.splice(m+1, 0, newVMarker);
		    tmpPolyLine.getPath().removeAt(2);
		    tmpPolyLine.getPath().removeAt(1);
		    tmpPolyLine.getPath().removeAt(0);
		    newpos = null;
		    startMarkerPos = null;
		    firstVPos = null;
		    endMarkerPos = null;
		    secondVPos = null;
		    newVMarker = null;
		    newMarker = null;
		    break;
		}
	    }
	});
    return marker;
};
 
var moveVMarker = function(index) {
    var newpos = markers[index].getPosition();
    if (index != 0) {
	var prevpos = markers[index-1].getPosition();
	vmarkers[index-1].setPosition(new g.LatLng(
						   newpos.lat() - (0.5 * (newpos.lat() - prevpos.lat())),
						   newpos.lng() - (0.5 * (newpos.lng() - prevpos.lng()))
						   ));
	prevpos = null;
    }
    if (index != markers.length - 1) {
	var nextpos = markers[index+1].getPosition();
	vmarkers[index].setPosition(new g.LatLng(
						 newpos.lat() - (0.5 * (newpos.lat() - nextpos.lat())),
						 newpos.lng() - (0.5 * (newpos.lng() - nextpos.lng()))
						 ));
	nextpos = null;
    }
    newpos = null;
    index = null;
};
 
var removeVMarkers = function(index) {
    if (markers.length > 0) {//clicked marker has already been deleted
	if (index != markers.length) {
	    vmarkers[index].setMap(null);
	    vmarkers.splice(index, 1);
	} else {
	    vmarkers[index-1].setMap(null);
	    vmarkers.splice(index-1, 1);
	}
    }
    if (index != 0 && index != markers.length) {
	var prevpos = markers[index-1].getPosition();
	var newpos = markers[index].getPosition();
	vmarkers[index-1].setPosition(new g.LatLng(				  
						   newpos.lat() - (0.5 * (newpos.lat() - prevpos.lat())),
						   newpos.lng() - (0.5 * (newpos.lng() - prevpos.lng()))
										  ));
	prevpos = null;
	newpos = null;
    }
    index = null;
};


g.event.addDomListener(window, 'load', initialize);

function initialize() {
    initMap('map-canvas');
    initPolyline();
    initPlanPath();
};

  
function initPlanPath() {
    if (waypoints.length == 0) {
	planPath = null;
    }
    else {
	var arrowHead = {
	    path: g.SymbolPath.FORWARD_CLOSED_ARROW
	};

	planPath =  new g.Polyline({
		path: waypoints,
		geodesic: true,
		strokeColor: '#FF0000',
		
		strokeOpacity: 1.0,
		strokeWeight: 1
	    });
	planPath.setMap(map);
    }
}

function toggleWaypoints() {
    if (planPath == null) {
	alert("No waypoints defined");
    }
    var is_checked = document.getElementById("showPath").checked;
    if (is_checked) {
	planPath.setMap(map);
    }
    else {
	planPath.setMap(null);
    }
}
