# Copyright 2018 GRID-Geneva. All Rights Reserved.
#
# This code is licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# Import necessary stuff
import os
import shutil
import logging
import rasterio
import re
from PIL import Image, ImageDraw, ImageFont

from IPython.display import display, HTML
from datetime import datetime
from base64 import b64encode
from io import BytesIO
from os.path import basename
from math import ceil

import pandas as pd
import numpy as np
import xarray as xr
import geopandas as gpd
import osmnx as ox # !pip install osmnx (requires libspatialindex-dev (apt install ...))

from ipyleaflet import (
    Map,
    basemaps,
    basemap_to_tiles,
    ImageOverlay,
    LayersControl,
    Rectangle,
    DrawControl
)

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib import colors
from mpl_toolkits.axes_grid1 import make_axes_locatable
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
from skimage import exposure
from math import cos, sin, asin, sqrt, radians
from osgeo import ogr
from shapely.geometry import Polygon

from utils.data_cube_utilities.dc_display_map import _degree_to_zoom_level


def draw_map(lat_ext = None, lon_ext = None):
    """
    Description:
      Create an empty map with a blue rectangle of given <lat_ext>, <lon_ext> to be used to manually
      draw a polygon or rectangle
    -----
    Input:
      lat_ext: latitude extent
      lon_ext: longitude extent
    Output:
      m: empty map ti interact with
      dc: draw control
    Usage:
      Draw a polygon or a rectangle
    """
    # check options combination
    assert not((lat_ext is None) or (lon_ext is None)), \
           'lat_ext and lon_ext are required'
    assert lat_ext[0] < lat_ext[1], 'lat_ext values are in the wrong order'
    assert lon_ext[0] < lon_ext[1], 'lon_ext values are in the wrong order'

    # Location
    center = [np.mean(lat_ext), np.mean(lon_ext)]

    # source: https://sdc.unepgrid.ch:8080/edit/utils/data_cube_utilities/dc_display_map.py
    margin = -0.5
    zoom_bias = 0
    lat_zoom_level = _degree_to_zoom_level(margin = margin, *lat_ext ) + zoom_bias
    lon_zoom_level = _degree_to_zoom_level(margin = margin, *lon_ext) + zoom_bias
    zoom = min(lat_zoom_level, lon_zoom_level)

    m = Map(center=center, zoom=zoom, scroll_wheel_zoom = True)

    # Layers
    # http://leaflet-extras.github.io/leaflet-providers/preview/
    esri = basemap_to_tiles(basemaps.Esri.WorldImagery)
    m.add_layer(esri)
    terrain = basemap_to_tiles(basemaps.Stamen.Terrain)
    m.add_layer(terrain)
    mapnik = basemap_to_tiles(basemaps.OpenStreetMap.Mapnik)
    m.add_layer(mapnik)

    rectangle = Rectangle(bounds = ((lat_ext[0], lon_ext[0]),
                                   (lat_ext[1], lon_ext[1])),
                          color = 'red', weight = 2, fill = False)

    m.add_layer(rectangle)

    m.add_control(LayersControl())

    # Controls
    dc = DrawControl(rectangle={'shapeOptions': {'color': '#0000FF'}},
                     polygon={'shapeOptions': {'color': '#0000FF'}},
                     marker={},
                     polyline={},
                     circle={},
                     circlemarker={}
                    )

    m.add_control(dc)

    return m, dc


def printandlog(msg, logname = 'default.log', started = False, reset = False):
    """
    Description:
      Function to print and write in a log file any info
    -----
    Input:
      message: Message to print and log
      started: Starting time to calculate processing time
      reset: Reset the existing log if True, or append to existing log if False (default)
      logname: Name of the logfile. It is strongly advised to defined it once in the configuration section
    Output:
      Print message in page and logname after date and time
    -----
    Usage:
      printandlog('Started computing', 'any_name.log', started = start_time, reset = True)
    """
    logging.basicConfig(filename=logname,
                        level=logging.INFO,
                        format='%(asctime)s | %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    if reset:
        open(logname, 'w').close()

    if started:
        msg = '%s (done in %s)' % (msg, datetime.now() - started)

    print('%s | %s' % (datetime.now(), msg))
    logging.info(msg)
    return


def str_ds(ds):
    """
    create a string from a given xarray.Dataset by combining geographical extent and resolution
    keeping 6 digits, removing '.', adding 3 leading 0 to longitude and 2 to latitude and using
    '-' as separator.

    Parameters
    ----------
    ds: xarray.Dataset
    """
    return '{:010.6f}-{:010.6f}-{:09.6f}-{:09.6f}-{:01.6f}' \
      .format(ds.longitude.min().values, ds.longitude.max().values,
              ds.latitude.min().values, ds.latitude.max().values,
              ds.longitude.resolution).replace('.','')


def get_ds_geoinfo(ds):
    """
    return a dictionnary containing the geographical information (number of columns and rows,
    x and y resolutions, real (including half pixel border) geographical extent)of a given
    xarray.Dataset.

    Parameters
    ----------
    ds: xarray.Dataset
    """
    geoinfo_dict = {}
    geoinfo_dict['cols'] = len(ds.longitude)
    geoinfo_dict['rows'] = len(ds.latitude)

    # 17x faster than list_products way and more accurate !
    geoinfo_dict['resx'] = (ds.longitude.values.max() - ds.longitude.values.min()) / geoinfo_dict['cols']
    geoinfo_dict['resy'] = (ds.latitude.values.max() - ds.latitude.values.min()) / geoinfo_dict['rows']

    geoinfo_dict['minx'] = ds.longitude.values.min() - geoinfo_dict['resx'] / 2
    geoinfo_dict['maxx'] = ds.longitude.values.max() + geoinfo_dict['resx'] / 2
    geoinfo_dict['miny'] = ds.latitude.values.min() - geoinfo_dict['resy'] / 2
    geoinfo_dict['maxy'] = ds.latitude.values.max() + geoinfo_dict['resy'] / 2

    return geoinfo_dict


def osm_to_shp(ds, wd = './', plot = False):
    """
    download OSM streets and buildings and convert them to separate shapefile.

    Parameters
    ----------
    ds: xarray.Dataset
    wd (optional, notebook directory by default): string
        working directory to save shapefile and tif
    plot (optional, False by default): Boolean
        plot streets and buildings
    """

    # create or empty working directory
    if wd != './':
        if os.path.exists(wd):
            shutil.rmtree(wd)
        os.makedirs(wd)

    # get ds geographical information
    geoinfo_dict = get_ds_geoinfo(ds)

    # generate AOI shapefile
    PolygonS = Polygon([[geoinfo_dict['minx'], geoinfo_dict['miny']],
                        [geoinfo_dict['minx'], geoinfo_dict['maxy']],
                        [geoinfo_dict['maxx'],geoinfo_dict['maxy']],
                        [geoinfo_dict['maxx'],geoinfo_dict['miny']]])
    gpd.GeoDataFrame(pd.DataFrame(['p1'], columns = ['geom']),
         crs = {'init':'epsg:4326'},
         geometry = [PolygonS]).to_file(wd + '/aoi_limited.shp')

    # Get OSM streets and buildings
    # streets
    try:
#         streets = ox.graph_from_bbox(max_lat, min_lat, max_lon, min_lon,
        streets = ox.graph_from_bbox(geoinfo_dict['maxy'], geoinfo_dict['miny'], geoinfo_dict['maxx'], geoinfo_dict['minx'],
                                   network_type='drive',
                                   retain_all=True, truncate_by_edge = True)
        assert streets.size() > 0, 'No road within the AOI !'
        # "TypeError: unhashable type: 'dict'" when using 'ox.graph_from_polygon'
        nodes, edges = ox.graph_to_gdfs(streets)
        ox.save_graph_shapefile(streets, folder = wd, filename='streets')
    except:
        print('No streets within the AOI !')
    # building
    try:
        buildings = ox.footprints.footprints_from_polygon(PolygonS,
                                                          footprint_type='building',
                                                          retain_invalid = False)
        ox.save_load.save_gdf_shapefile(buildings, folder = wd, filename='buildings')
    except:
        print('No buildings within the AOI !')

#     # Save as shapefile
#     ox.save_graph_shapefile(streets, folder = wd, filename='streets')
#     ox.save_load.save_gdf_shapefile(buildings, folder = wd, filename='buildings')
    # optionaly plot
    if plot:
        fig, ax = plt.subplots(figsize=(12,8))
        if edges:
            edges.plot(ax=ax, linewidth=1, edgecolor='black')
        if buildings:
            buildings.plot(ax=ax, facecolor='gray')

    return 0


def buffer_shp(shp, ref_ds, size_px):
    """
    export a buffered shapefile (buffer size based on the average xy resolution of a given dataset.

    Parameters
    ----------
    shp: string
        path to shapefile to buffer
    ref_ds: xarray.dataset
        reference dataset
    size_px: float
        buffer size based on <ref_ds> pixel size (e.g. 1 * S2 ds = 10 m)
    """
    assert (os.path.exists(shp)), \
           'Path to shapefile (<shp>) is not valid !'
    assert (all(item in list(ref_ds.dims) for item in ['latitude','longitude'])), \
           '<ref_ds> does not contains latitude and/or longitude !'
    assert (len(ref_ds.longitude) * len(ref_ds.latitude) > 0), \
           '<ref_ds> is empty !'
    assert (size_px * 1.0 > 0), \
           '<size_px> should be a positive number !'

    # estimate buffer size in dd
    geoinfo_dict = get_ds_geoinfo(ref_ds)
    size_dd = size_px * (geoinfo_dict['resx'] + geoinfo_dict['resy']) / 2

    # Open shapefile
    inDataSource = ogr.Open(shp, 0)
    inLayer = inDataSource.GetLayer()

    # Create the output shapefile
    outDriver = ogr.GetDriverByName("ESRI Shapefile")
    outDataSource = outDriver.CreateDataSource('buffer.shp') # not working with full path
    outLayer = outDataSource.CreateLayer('buffer',
                                         inLayer.GetSpatialRef(), geom_type=ogr.wkbPolygon)

    # Get the output Layer's Feature Definition
    outLayerDefn = outLayer.GetLayerDefn()

    # Create the feature and set values
    featureDefn = outLayer.GetLayerDefn()
    for feat in inLayer:
        geomet= feat.GetGeometryRef()
        feature = feat.Clone()
        feature.SetGeometry(geomet.Buffer(size_dd))
        outLayer.CreateFeature(feature)
        del geomet
    # Close DataSource
    inDataSource.Destroy()
    outDataSource.Destroy()

    # move the shapefile in working directory
    for ext in ['dbf', 'shp', 'shx', 'prj']:
        filename = 'buffer.' + ext
        shutil.move(filename, os.path.dirname(shp) + '/' + filename)

    return 0


def check_overlay(ds, dst):
    """
    check proper overlay of a given dataset with a given rasterio.io.DatasetReader.

    Parameters
    ----------
    ds: xarray.Dataset
    dst: rasterio.io.DatasetReader
    """
    geoinfo = get_ds_geoinfo(ds)
    bounds = dst.bounds
    assert (geoinfo['minx'] - bounds.left == 0), \
        'min_lon differ between dataset and geotiff !'
    assert (geoinfo['maxx'] - bounds.right == 0), \
        'max_lon differ between dataset and geotiff !'
    assert (geoinfo['miny'] - bounds.bottom == 0), \
        'min_lat differ between dataset and geotiff !'
    assert (geoinfo['maxy'] - bounds.top == 0), \
        'max_lat differ between dataset and geotiff !'
    assert (geoinfo['cols'] - dst.width == 0), \
        'number of columns differ between dataset and geotiff !'
    assert (geoinfo['rows'] - dst.height == 0), \
        'number of rows differ between dataset and geotiff !'


def tif_to_da(tif_path, ds):
    """
    convert given geotiff into a xarray.DataArray fitting a given xarray.Dataset.

    Parameters
    ----------
    tif: string
        path to geotiff to convert
    ds: xarray.Dataset
    """
    with rasterio.open(tif_path, driver='GTiff') as dst:
        data_np_arr = dst.read()
        check_overlay(ds, dst)
        dst.close()
    da = xr.DataArray(data_np_arr, dims=['time', 'latitude', 'longitude'])
    da = da.assign_coords(time = range(data_np_arr.shape[0]),
                          latitude=ds.latitude,
                          longitude=ds.longitude)
    da = da.drop('time').squeeze()
    return da.where(da != 0)


def shp_to_da(shp, ds, val = 1, alltouch = False):
    """
    convert given shapefile into a xarray.DataArray fitting a given xarray.Dataset.

    Parameters
    ----------
    shp: string
        path to shapefile to convert
    ds: xarray.Dataset
    val (optional, 1 by default): positive integer
        value to burn (must be positive integer)
    alltouch (optional, False by default): Boolean
        ALL_TOUCHED option so that all pixels touched will be rasterized
    """
    gdal_rast_path = '/usr/bin/gdal_rasterize'
    assert (os.path.exists(gdal_rast_path)),\
           'path <gdal_rast> path is not valid !'
    assert (os.path.exists(shp)), \
           'Path to shapefile (<shp>) is not valid !'
    assert (all(item in list(ds.dims) for item in ['latitude','longitude'])), \
           '<ds> does not contains latitude and/or longitude !'
    assert (len(ds.longitude) * len(ds.latitude) > 0), \
           '<ds> is empty !'
    assert ((isinstance(val, int)) and (val >= 0)), \
           '<val> must be positive integer !'

    # get ds resolution
    geoinfo_dict = get_ds_geoinfo(ds)

    # rasterize shapefile fitting ds
    tif_path = os.path.splitext(shp)[0] + '.tif'
    display(HTML("""<a href={} target="_blank" >{}</a> created""".format(tif_path, tif_path)))
    cmd = ("{} -burn {} -a_nodata 0 -te {:.20f} {:.20f} {:.20f} {:.20f} -ts {} {} \
           -co COMPRESS=DEFLATE {} {}".
           format(gdal_rast_path, val,
                  geoinfo_dict['minx'], geoinfo_dict['miny'],
                  geoinfo_dict['maxx'], geoinfo_dict['maxy'],
                  geoinfo_dict['cols'], geoinfo_dict['rows'],
                  shp, tif_path))
    if alltouch:
        cmd = cmd + ' -at'
    os.system(cmd)
    return tif_to_da(tif_path, ds)


def osm_to_da(ds, wd = './', size_px = 0, all_touch = False):
    """
    Download OSM streets and buildings and convert them into a xarray.DataArray fitting a given
    xarray.Dataset (optionally a buffer can be applied on streets layer).

    Parameters
    ----------
    ds: xarray.Dataset
    wd (optional, notebook directory by default): string
        working directory to save shapefile and tif
    size_px (optional, 0 by default): float
        buffer size based on <ds> pixel size (e.g. 1 * S2 ds = 10 m)
    alltouch (optional, False by default): Boolean
        ALL_TOUCHED option so that all pixels touched will be rasterized
    """
    osm_to_shp(ds, wd)
    streets_name = '/streets/edges/edges.shp'
    if size_px != 0:
        buffer_shp(wd + streets_name, ds, size_px)
        streets_name = '/streets/edges/buffer.shp'
    streets = shp_to_da(wd + streets_name, ds, alltouch = all_touch)
    buildings = shp_to_da(wd + '/buildings/buildings.shp', ds, alltouch = all_touch)
    return buildings.combine_first(streets)


def stbu_to_da(st_tif, bu_tif, ds):
    """
    convert streets and building geotiff processed with osm_to_da function into a xarray.DataArray.

    Parameters
    ----------
    st_tif & bu_tif: string
        path to streets and buildings geotiff to convert
    ds: xarray.Dataset
        dataset used to generate the geotiffs
    """
    assert (os.path.exists(st_tif)),\
           'path <st_tif> path is not valid !'
    assert (os.path.exists(bu_tif)),\
           'path <bu_tif> path is not valid !'

    buildings = tif_to_da(bu_tif, ds)
    streets = tif_to_da(st_tif, ds)
    return buildings.combine_first(streets)


def da_linreg_params(y, dim = 'time'):
    """
    Description:
      Calculation of linear regression slope on a given xarray.DataArray.
      nan "bullet proof", faster than vectorized ufunc approach.
    Input:
      y:            xarray.DataArray
      dim:          x dimension (time per fault)
    Output:
      slope and intercept
    Authors:
      Bruno Chatenoux (UNEP/GRID-Geneva, 11.6.2019)
    """
    x = y.where(np.isnan(y), y[dim]) # attribute time to pixel with values

    mean_x = x.mean(dim=dim)
    mean_y = y.mean(dim=dim)
    mean_xx = (x * x).mean(dim=dim)
    mean_xy = (x * y).mean(dim=dim)

    s = ((mean_x * mean_y) - mean_xy) / ((mean_x * mean_x) - mean_xx)

    i = mean_y - mean_x * s

    return s, i


def da_to_png64(da, cm):
    # source: https://github.com/jupyter-widgets/ipyleaflet/blob/master/examples/Numpy.ipynb
    # but without reprojection:
    # - see to have an issue with bounds still in WGS84 and array reprojected
    # - reprojection create more problems than solve them

    arr = da.values
    arr_norm = arr - np.nanmin(arr)
    arr_norm = arr_norm / np.nanmax(arr_norm)
    arr_norm = np.where(np.isfinite(arr), arr_norm, 0)
    arr_im = Image.fromarray(np.uint8(cm(arr_norm)*255))
#     arr_im = PIL.Image.fromarray(np.uint8(cm(arr_norm)*255))
    arr_mask = np.where(np.isfinite(arr), 255, 0)
    mask = Image.fromarray(np.uint8(arr_mask), mode='L')
    im = Image.new('RGBA', arr_norm.shape[::-1], color=None)
#     mask = PIL.Image.fromarray(np.uint8(arr_mask), mode='L')
#     im = PIL.Image.new('RGBA', arr_norm.shape[::-1], color=None)
    im.paste(arr_im, mask=mask)
    f = BytesIO()
    im.save(f, 'png')
    data = b64encode(f.getvalue())
    data = data.decode('ascii')
    imgurl = 'data:image/png;base64,' + data
    return imgurl


def display_da(da, cm):
    """
    Description:
      Display a colored xarray.DataArray on a map and allow the user to select a point
    -----
    Input:
      da: xarray.DataArray
      cm: matplotlib colormap
    Output:
      m: map to interact with
      dc: draw control
    Usage:
      View, interact and point a location to be used later on
    """

    # Check inputs
    assert 'dataarray.DataArray' in str(type(da)), "da must be an xarray.DataArray"

    # convert DataArray to png64
    imgurl = da_to_png64(da, cm)


    # Display
    latitude = (da.latitude.values.min(), da.latitude.values.max())
    longitude = (da.longitude.values.min(), da.longitude.values.max())

    margin = -0.5
    zoom_bias = 0
    lat_zoom_level = _degree_to_zoom_level(margin = margin, *latitude ) + zoom_bias
    lon_zoom_level = _degree_to_zoom_level(margin = margin, *longitude) + zoom_bias
    zoom = min(lat_zoom_level, lon_zoom_level) - 1
    center = [np.mean(latitude), np.mean(longitude)]
    m = Map(center=center, zoom=zoom)

    # http://leaflet-extras.github.io/leaflet-providers/preview/
    esri = basemap_to_tiles(basemaps.Esri.WorldImagery)
    m.add_layer(esri)

    io = ImageOverlay(name = 'DataArray', url=imgurl, bounds=[(latitude[0],longitude[0]),(latitude[1], longitude[1])])
    m.add_layer(io)

    dc = DrawControl(circlemarker={'color': 'yellow'},
                    polygon={}, polyline={})
    m.add_control(dc)

    m.add_control(LayersControl())

    return m, dc, io


def fig_aspects(sizes, max_size = 20):
    pxx = sizes['longitude']
    pxy = sizes['latitude']
    orient = 'horizontal'
    posit = 'bottom'
    width = max_size
    height = pxy * (max_size / pxx)
    if pxx * 1.01 < pxy:
        orient = 'vertical'
        posit = 'right'
        height = max_size
        width = pxx * (max_size / pxy)
    return (height, width, orient, posit)


def xtrms_format(vals):
    min_val = min(vals)
    max_val = max(vals)
    diff_val = max_val - min_val
    digits = 3

    return ['{:.{prec}f}'.format(round(min_val, digits), prec = digits),
            '{:.{prec}f}'.format(round(max_val, digits), prec = digits)]


def dd2km(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    source: https://gis.stackexchange.com/questions/61924/python-gdal-degrees-to-meters-without-reprojecting
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km


def create_scalebar(data, ax, scalebar_color):
    """
    Description:
      Compute and create an horizontal scalebar in kilometer or meter to be added to the map.
    -----
    Input:
      data: xarray to be mapped
      ax: matplotlib.axes to work on
      scalebar_color (OPTIONAL): scalebar color (e.g.'orangered')
                                 https://matplotlib.org/examples/color/named_colors.html)
    Output:
      Scalebar to be added
    """
    # Convert lenght at average latitude from decimal degree into kilometer
    ave_lat = ((min(data.latitude) + max(data.latitude)) / 2).values
    lon_km = dd2km(ave_lat, min(data.longitude).values, ave_lat, max(data.longitude).values)
    # Calculate the scalebar caracteristics (rounded value of 1/4 of lengths)
    lon_px = len(data.longitude)
    bar_len = lon_km * 0.25 # 25% of the map width
    if bar_len >= 1:
        units = 'kilometer'
        bar_len = round(bar_len)
        bar_px = round(lon_px * bar_len / lon_km)
    else:
        units = 'meter'
        bar_len = round(bar_len * 10) * 100
        bar_px = round(lon_px * bar_len / 1000 / lon_km)
    # add the scalebar
    fontprops = fm.FontProperties(size=18)
    scalebar = AnchoredSizeBar(ax.transData,
                               bar_px, '%i %s' % (bar_len, units), 'lower right',
                               pad=0.1,
                               color=scalebar_color,
                               frameon=False,
                               size_vertical=1,
                               label_top=True,
                               fontproperties=fontprops)
    return(scalebar)


def oneband_fig(data, leg, title, scalebar_color= None, fig_name=None, v_min=None, v_max=None, max_size=16):
    """
    Description:
      Create a one band (one time) figure
    -----
    Input:
      data: one time xarray.DataArray.
      leg: colormap to be applied (either standard (https://matplotlib.org/examples/color/colormaps_reference.html)
           or custom)
      title: prefix of the figure title
      scalebar_color (OPTIONAL): scalebar color (https://matplotlib.org/examples/color/named_colors.html)
      v_min (OPTIONAL, default minimum value): minimum value to display.
      v_max (OPTIONAL, default maximum value): maximum value to display.
      fig_name (OPTIONAL): file name (including extension) to save the figure (show only if not added to input).
      max_size (OPTIONAL, default 16): maximum size of the figure (either horizontal or vertical).
    Output:
      figure.
    """
    # check options combination
    assert not((v_min is not None) ^ (v_max is not None)), \
           'v_min option requires v_max option, and inverserly'
    if v_min is not None:
        assert v_min < v_max, 'v_min value must be lower than v_max'

    height, width, orient, posit = fig_aspects(data.sizes, max_size)

    plt.close('all')
    fig, ax = plt.subplots()
    fig.set_size_inches(width, height)

    if not v_min and not v_max:
        im = ax.imshow(data, interpolation='nearest', cmap=leg)
    else:
        im = ax.imshow(data, interpolation='nearest', cmap=leg, vmin = v_min, vmax = v_max)

    # add a scalebar if required
    if scalebar_color:
        ax.add_artist(create_scalebar(data, ax, scalebar_color))

    # ticks moved 1 pixel inside to guarantee they are displayed
    plt.yticks([data.shape[0] - 1, 1], xtrms_format(data.latitude.values))
    plt.xticks([1, data.shape[1] - 1], xtrms_format(data.longitude.values))

    plt.title(title, weight='bold', fontsize=16)

    divider = make_axes_locatable(plt.gca())
    cax = divider.append_axes(posit, "2%", pad="5%")
    cbar = fig.colorbar(im, orientation=orient, cax=cax)

    fig.tight_layout()
    if fig_name:
        plt.savefig(fig_name, dpi=150)
        display(HTML("""<a href="{}" target="_blank" >View and download {}</a>""".format(fig_name, basename(fig_name))))
    else:
        plt.show()
    plt.close()


def composite_fig(data, bands, title, scalebar_color=None, fig_name=None, max_size=16, hist_str=None, \
                  v_min = None, v_max = None):
    """
    Description:
      Create a three band (one time) composite figure
    -----
    Input:
      data: one time xarray.Dataset containing the three bands mentionned in bands.
      bands: bands to be used in the composite (RGB order).
      title: prefix of the figure title.
      scalebar_color (OPTIONAL): scalebar color (https://matplotlib.org/examples/color/named_colors.html)
      fig_name (OPTIONAL): file name (including extension) to save the figure (show only if not added to input).
      max_size (OPTIONAL, default 16): maximum size of the figure (either horizontal or vertical).
      hist_str: (OPTIONAL): histogram stretch type (['contr','eq','ad_eq']). Cannot be used with v_min, v_max options.
      v_min (OPTIONAL, default minimum value): minimum value to display. Cannot be used with hist_str option.
      v_max (OPTIONAL, default maximum value): maximum value to display. Cannot be used with hist_str option.
    Output:
      figure.
    """

    # check options combination
    assert not((hist_str is not None) and (v_min is not None or v_max is not None)) , \
           'hist_str option cannot be used with v_min, vmax options'
    assert not((v_min is not None) ^ (v_max is not None)), \
           'v_min option requires v_max option, and inverserly'
    if v_min is not None:
        assert v_min < v_max, 'v_min value must be lower than v_max'

    # Create a copy to unlink from original dataset
    rgb = data.copy(deep = True)

    height, width, orient, posit = fig_aspects(rgb.sizes, max_size)

    rgb = np.stack([rgb[bands[0]],
                    rgb[bands[1]],
                    rgb[bands[2]]])

    # perform stretch on each band
    for b in range(3):
        # https://scikit-image.org/docs/dev/auto_examples/color_exposure/plot_equalize.html
        # Contrast stretching
        if hist_str == 'contr':
            p2, p98 = np.nanpercentile(rgb[b], (2, 98))
            rgb[b] = exposure.rescale_intensity(rgb[b], in_range=(p2, p98))
        # Equalization
        if hist_str == 'eq':
            rgb[b] = exposure.equalize_hist(rgb[b])
        # Adaptive Equalization
        if hist_str == 'ad_eq':
            rgb[b] = exposure.equalize_adapthist(rgb[b], clip_limit=0.03)

    rgb = np.stack(rgb, axis = -1)

    # normalize between 0 and 1
    if v_min is None:
        rgb = (rgb - np.nanmin(rgb)) / (np.nanmax(rgb) - np.nanmin(rgb))
    else:
        rgb = (rgb - v_min) / (v_max - v_min)

    # Start plotting the figure
    plt.close('all')
    fig, ax = plt.subplots()
    fig.set_size_inches(width, height)
    im = ax.imshow(rgb, vmin = 0, vmax = 1)

    # add a scalebar if required
    if scalebar_color:
        ax.add_artist(create_scalebar(data, ax, scalebar_color))

    # ticks moved 1 pixel inside to guarantee they are displayed
    plt.yticks([rgb.shape[0] - 1, 1], xtrms_format(data.latitude.values))
    plt.xticks([1, rgb.shape[1] - 1], xtrms_format(data.longitude.values))

    plt.title(title, weight='bold', fontsize=16)

    fig.tight_layout()
    if fig_name:
        plt.savefig(fig_name, dpi=150)
        display(HTML("""<a href="{}" target="_blank" >View and download {}</a>""".format(fig_name, basename(fig_name))))
    else:
        plt.show()
    plt.close()
    

def natural_sort(l): 
    convert = lambda text: int(text) if text.isdigit() else text.lower() 
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
    return sorted(l, key = alphanum_key)

# source: https://code.activestate.com/recipes/578267-use-pil-to-make-a-contact-sheet-montage-of-images/
def make_contact_sheet(fnames, ncols = 0 ,nrows = 0 , photow = 0, photoh = 0, by = 'row',
                       title = None, font = 'LiberationSans-Bold.ttf', size = 14,
                       fig_name = None):
    """
    Description:
      Make a contact sheet from a group of images filenames.
    -----
    Input:
      fnames (OPTIONAL): a list of names of the image files
      ncols, nrows (OPTIONAL): number of columns OR rows in the contact sheet
      photow, photoh (OPTIONAL): width OR eight of the photo thumbs in pixels
      by (OPTIONAL): images displayed by row (default) or columns
      title (OPTIONAL): optional title
      font (OPTIONAL): title font (default LiberationSans bold)
      size (OPTIONAL): title font size (default 14)
      fig_name (OPTIONAL): file name (including extension) to save the figure (show only if not added to input).      
    Output:
      figure.
    """
    
    assert ncols * nrows == 0 and ncols + nrows > 0, '! You need to specify <ncols> OR <nrows>'
    assert photow * photoh == 0 and photow + photoh > 0, '! You need to specify <photow> OR <photoh>'
    assert by in ('row, col'), "! <by> can only be 'row' or 'col' !"
    
    if ncols > 0:
        nrows = ceil(len(fnames)/ncols)
    else:
        ncols = ceil(len(fnames)/nrowss)
        
    # get first photo size
    pxw, pxh = Image.open(fnames[0]).size
    if photow > 0:
        photoh = ceil(photow * pxh / pxw)
    else:
        photow = ceil(photoh * pxw / pxx)
    
    # Calculate the size of the output image, based on the
    #  photo thumb sizes, margins, and padding
    marl, marr, mart, marb = 5,5,5,5 # hardcoded margins
    padding = 1                      # hardcoded padding
    
    if title:
        try:
            font = ImageFont.truetype(font, size=size)
        except:
            print('! {} font is not availble, run !fc-list to find one !'.format(font))
            sys.exit
        mart += size
    
    marw = marl+marr
    marh = mart+ marb
    padw = (ncols-1)*padding
    padh = (nrows-1)*padding
    isize = (ncols*photow+marw+padw,nrows*photoh+marh+padh)
    
    # Create the new image. The background doesn't have to be white
    white = (255,255,255)
    inew = Image.new('RGB',isize,white)
    
    # reshape <fnames> if required
    if by == 'col':
        # append nans to get a proper fnames length
        ns = [np.nan] * (ncols * nrows - len(fnames))
        fnames += ns
        fnames = np.reshape(fnames, (ncols, nrows)).T.flatten()

    count = 0
    # Insert each thumb:
    for irow in range(nrows):
        for icol in range(ncols):
            left = marl + icol*(photow+padding)
            right = left + photow
            upper = mart + irow*(photoh+padding)
            lower = upper + photoh
            bbox = (left,upper,right,lower)
            try:
                # Read in an image and resize appropriately
                img = Image.open(fnames[count]).resize((photow,photoh))
            except:
                break
            inew.paste(img,bbox)
            count += 1
    
    if title:
        d = ImageDraw.Draw(inew)
        w, h = d.textsize(title)
        d.text(((isize[0] - w)/2, 5), title, fill='black', font = font)
    
    if fig_name:
        inew.save(fig_name)
        display(HTML("""<a href="{}" target="_blank" >View and download {}</a>""".format(fig_name, basename(fig_name))))
    else:
        return inew
