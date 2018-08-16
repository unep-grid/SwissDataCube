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
var gsHost = appConfig.gsHost;
var ch_borders = L.tileLayer.wms(gsHost, {
	layers: 'sdc:ch_border',
	format: 'image/png',
	transparent: 'true',
	attribution: "<a href='https://data.geo.admin.ch' target='_blank'>geo.admin.ch</a> data"
});
var canton_borders = L.tileLayer.wms(gsHost, {
	layers: 'sdc:canton_borders',
	format: 'image/png',
	transparent: 'true',
	attribution: "<a href='https://data.geo.admin.ch' target='_blank'>geo.admin.ch</a> data"
});
var ch_mask = L.tileLayer.wms(gsHost, {
	layers: 'sdc:ch_mask',
	format: 'image/png',
	transparent: 'true',
	opacity: 0.5,
});

/* Products WMS service - SDC GeoServer */
//Single Tile layer
var ch_mosaic_2016 = L.tileLayer.wms(gsHost, {
	layers: 'sdc:L8_CHmosaic_2016',
	//layers: 'sdc:LS8mosaicCH2018wgs84',
	format: 'image/png',
	transparent: 'true',
	pointerCursor: true,
	attribution: "<a href='http://www.swissdatacube.ch' target='_blank'>Swiss Data Cube</a> data"
});
ch_mosaic_2016.setZIndex(3); //to ensure that data is loaded over base maps but behind borders data

//Time-series raster
var snow_CH = L.tileLayer.wms(gsHost, {
	layers: 'sdc:snow',
	format: 'image/png',
	transparent: 'true',
	attribution: "<a href='http://www.swissdatacube.ch' target='_blank'>Swiss Data Cube</a> data"
});
var tdWmsLayer = L.timeDimension.layer.wms(snow_CH);
var timeDimension = new L.TimeDimension({
	timeInterval: "2009-10-01/2009-12-01",
	period: "P1M"
});
var timeDimensionControlOptions = {
	timeDimension: timeDimension,
	position:      'bottomright',
	speedSlider: false,
	timeSliderDragUpdate: false
};
var timeDimensionControl = new L.Control.TimeDimension(timeDimensionControlOptions);
tdWmsLayer.setZIndex(4); //to ensure that data is loaded over base maps but behind borders data

//Map object
var mapZoom = appConfig.mapZoom; 
var mapMinZoom = appConfig.mapMinZoom;
var mapMaxZoom = appConfig.mapMaxZoom;
var mapCenter = appConfig.mapCenter;

map = L.map("map", {
  zoom: mapZoom,
  minZoom: mapMinZoom,
  maxZoom: mapMaxZoom,	
  center: mapCenter,
  layers: [toto,ch_mask, ch_borders],
  maxBounds: [
	  //south - west; min lat - min long
	  [45.6755, 5.7349],
	  //north - east; max lat - max long
	  [47.9163, 10.6677]
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

//MousePosition
var mousePosition = L.control.mousePosition({
	numDigits: 3
}).addTo(map);

//ScaleBar
var scaleBar = L.control.scale({
	position: "bottomleft",
	imperial: false //remove miles
}).addTo(map);

//Print module
var printModule = L.easyPrint({
	title: 'Print',
	position: 'topleft',
	tileLayer: allMapLayers,
	sizeModes: ['Current','A4Portrait', 'A4Landscape'],
	filename: 'SwissDataCube_print',
	exportOnly: true,
	hideControlContainer: true
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

//Base Layers for background
var baseLayers = {
  "Base Map": toto,
  "Aerial Imagery": usgsImagery
};

//other layers to overlay
var groupedOverlays = {
  "Borders": {
    "Country": ch_borders,
	"Cantons": canton_borders,
	"Mask": ch_mask 
  }
};

//use for managing the URL hash
var allMapLayers = {
	"OSM": toto,
  	"Satellite": usgsImagery,
    "Country": ch_borders,
	"Cantons": canton_borders,
	"Mask": ch_mask,
	"Mosaic": ch_mosaic_2016,
}
var urlParam = L.hash(map, allMapLayers);

//Layer control
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