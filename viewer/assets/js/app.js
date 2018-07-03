var map;

$(window).resize(function() {
  sizeLayerControl();
});

$("#about-btn").click(function() {
  $("#aboutModal").modal("show");
  $(".navbar-collapse.in").collapse("hide");
  return false;
});

$("#legend-btn").click(function() {
  $("#legendModal").modal("show");
  $(".navbar-collapse.in").collapse("hide");
  return false;
});

$("#login-btn").click(function() {
  $("#loginModal").modal("show");
  $(".navbar-collapse.in").collapse("hide");
  return false;
});

$("#help-btn").click(function() {
  $("#helpModal").modal("show");
  $(".navbar-collapse.in").collapse("hide");
  return false;
});

$("#webservices-btn").click(function() {
  $("#webservicesModal").modal("show");
  $(".navbar-collapse.in").collapse("hide");
  return false;
});

$("#storymaps-btn").click(function() {
  $("#storymapsModal").modal("show");
  $(".navbar-collapse.in").collapse("hide");
  return false;
});

$("#list-btn").click(function() {
  animateSidebar();
  return false;
});

$("#nav-btn").click(function() {
  $(".navbar-collapse").collapse("toggle");
  return false;
});

$("#sidebar-toggle-btn").click(function() {
  animateSidebar();
  return false;
});

$("#sidebar-hide-btn").click(function() {
  animateSidebar();
  return false;
});

function animateSidebar() {
  $("#sidebar").animate({
    width: "toggle"
  }, 350, function() {
    map.invalidateSize();
  });
}

function sizeLayerControl() {
  $(".leaflet-control-layers").css("max-height", $("#map").height() - 50);
}

/* Basemap Layers */
var toto = L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw', {
	maxZoom: 19,
	id: 'mapbox.streets',
	attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="http://mapbox.com">Mapbox</a>'
});
toto.setZIndex(1);
var usgsImagery = L.layerGroup([L.tileLayer("http://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}", {
  maxZoom: 15,
}), L.tileLayer.wms("http://raster.nationalmap.gov/arcgis/services/Orthoimagery/USGS_EROS_Ortho_SCALE/ImageServer/WMSServer?", {
  minZoom: 16,
  maxZoom: 19,
  layers: "0",
  format: 'image/jpeg',
  transparent: true,
  attribution: "Aerial Imagery courtesy USGS"
})]);
usgsImagery.setZIndex(2);

/* Overlay Layers */
var ch_borders = L.tileLayer.wms('https://geoserver.swissdatacube.org/geoserver/ows?', {
	layers: 'sdc:ch_border',
	format: 'image/png',
	transparent: 'true',
});
var canton_borders = L.tileLayer.wms('https://geoserver.swissdatacube.org/geoserver/ows?', {
	layers: 'sdc:canton_borders',
	format: 'image/png',
	transparent: 'true'
});
var ch_mask = L.tileLayer.wms('https://geoserver.swissdatacube.org/geoserver/ows?', {
	layers: 'sdc:ch_mask',
	format: 'image/png',
	transparent: 'true',
	opacity: 0.5
});

/* Products WMS service - SDC GeoServer */
var ch_mosaic_2016 = L.tileLayer.wms('https://geoserver.swissdatacube.org/geoserver/ows?', {
	layers: 'sdc:L8_CHmosaic_2016',
	format: 'image/png',
	transparent: 'true',
	attribution: "Swiss Data Cube"
});
ch_mosaic_2016.setZIndex(3); //to ensure that data is loaded over base maps but behind borders data

map = L.map("map", {
  zoom: 8,
  minZoom: 7,
  maxZoom: 15,	
  center: [46.78, 8.22],
  layers: [toto,ch_mask, ch_borders],
  maxBounds: [
  	//south west
	  [45.8294, 5.9670],
    //north east 
	  [47.8066, 10.4882]
  ],	
  zoomControl: true,
  attributionControl: true,
  defaultExtentControl: true,
  fullscreenControl: true,	
  fullscreenControlOptions: {
	  title:"Enter fullscreen mode",
	  titleCancel:"Exit fullscreen mode",
	  position: "topleft"
  },
});

map.bounds = [],
// detect fullscreen toggling
map.on('enterFullscreen', function(){
	if(window.console) window.console.log('enterFullscreen');
});
map.on('exitFullscreen', function(){
	if(window.console) window.console.log('exitFullscreen');
});

var mousePosition = L.control.mousePosition({
	numDigits: 3
}).addTo(map);

var scaleBar = L.control.scale({
	position: "bottomleft",
	imperial: false //remove miles
}).addTo(map);

/* GPS enabled geolocation control set to follow the user's location */
var locateControl = L.control.locate({
  position: "topleft",
  drawCircle: true,
  follow: true,
  setView: true,
  keepCurrentZoomLevel: true,
  markerStyle: {
    weight: 1,
    opacity: 0.8,
    fillOpacity: 0.8
  },
  circleStyle: {
    weight: 1,
    clickable: false
  },
  icon: "fa fa-location-arrow",
  metric: false,
  strings: {
    title: "My location",
    popup: "You are within {distance} {unit} from this point",
    outsideMapBoundsMsg: "You seem located outside the boundaries of the map"
  },
  locateOptions: {
    maxZoom: 18,
    watch: true,
    enableHighAccuracy: true,
    maximumAge: 10000,
    timeout: 10000
  }
}).addTo(map);

/* Larger screens get expanded layer control and visible sidebar */
if (document.body.clientWidth <= 767) {
  var isCollapsed = true;
} else {
  var isCollapsed = false;
}

var baseLayers = {
  //"Street Map": cartoLight,
  "Base Map": toto,
  "Aerial Imagery": usgsImagery
};

var groupedOverlays = {
  "Borders": {
    "Country": ch_borders,
	"Cantons": canton_borders,
	"Mask": ch_mask 
  }
};

var layerControl = L.control.groupedLayers(baseLayers, groupedOverlays, {
  collapsed: isCollapsed
}).addTo(map);

/* Highlight search box text on click */
$("#searchbox").click(function () {
  $(this).select();
});

/* Prevent hitting enter from refreshing the page */
$("#searchbox").keypress(function (e) {
  if (e.which == 13) {
    e.preventDefault();
  }
});

$("#featureModal").on("hidden.bs.modal", function (e) {
  $(document).on("mouseout", ".feature-row", clearHighlight);
});

// Leaflet patch to make layer control scrollable on touch browsers
var container = $(".leaflet-control-layers")[0];
if (!L.Browser.touch) {
  L.DomEvent
  .disableClickPropagation(container)
  .disableScrollPropagation(container);
} else {
  L.DomEvent.disableClickPropagation(container);
}
