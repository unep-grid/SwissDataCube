# SwissDataCube - Viewer
This is the repository for the SwissDataCUbe - Viewer.
The aim is to develop an application to visualize, query, and download time-series data produced by the SwissDataCube.
It is based on bootleaf (https://github.com/bmcbride/bootleaf) providing a simple, responsive template for building web mapping applications with [Bootstrap](http://getbootstrap.com/), [Leaflet](http://leafletjs.com/), and [typeahead.js](http://twitter.github.io/typeahead.js/).

Data are published using GeoServer (http://www.geoserver.org) to provide an interoperable access to data using OGC WMS & WCS standards.

The viewer allows:
  - Visualizing and Downloading single raster product layers
  - Visualizing and Downloading time-series raster product layers
  - Generating graph for a given pixel of a time-series raster product layer
  - Access products in your own client with WMS & WCS standards
  - In the (short) future, visualize dedicated storymaps
