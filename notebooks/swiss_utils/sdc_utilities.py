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
import logging
import time

from IPython.display import clear_output
from datetime import datetime
import psutil
import pandas as pd
import numpy as np
import xarray as xr

from ipyleaflet import (
    Map,
    basemaps,
    basemap_to_tiles,
    LayersControl,
    Rectangle,
    GeoJSON,
    DrawControl
)

import matplotlib.pyplot as plt
from matplotlib import colors

from utils.dc_utilities import clear_attrs, write_geotiff_from_xr

def draw_map():
    """
    Description:
      Create an empty map to be used to draw a polygon or rectangle
    -----
    Input:
      None
    Output:
      m: empty map ti interact with
      dc: draw control
    Usage:
      Draw a polygon or a rectangle
    """

    # Location
    center = [47, 8]
    zoom = 7
    m = Map(center=center, zoom=zoom)

    # Layers
    # http://leaflet-extras.github.io/leaflet-providers/preview/
    esri = basemap_to_tiles(basemaps.Esri.WorldImagery)
    m.add_layer(esri)
    terrain = basemap_to_tiles(basemaps.Stamen.Terrain)
    m.add_layer(terrain)
    mapnik = basemap_to_tiles(basemaps.OpenStreetMap.Mapnik)
    m.add_layer(mapnik)

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

def printandlog(msg, logname = 'default.log', reset = False):
    """
    Description:
      Function to print and write in a log file any info
    -----
    Input:
      message: Message to print and log
      reset: Reset the existing log if True, or append to existing log if False (default)
      logname: Name of the logfile. It is strongly advised to defined it once in the configuration section
    Output:
      Print message in page and logname after date and time
    -----
    Usage:
      printandlog('Started computing', 'any_name.log', reset = True)
    """
    logging.basicConfig(filename=logname,
                        level=logging.INFO,
                        format='%(asctime)s | %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    if reset:
        open(logname, 'w').close()
    print('%s | %s' % (datetime.now(), msg))
    logging.info(msg)
    return

def slc_to_cfmask(slc_da):
    """
    Description:
      Aggregate a slc (Sentinel 2 mask standard) xarray.DataArray into cfmask (Landsat mask standard used by default by
      ODC) xarray.DataArray, ready to be added into an xarray.Dataset as "cf_mask" variable.
    -----
    Input:
      slc_da: slc xarray.DataArray extracted from a xarray.Dataset
    Output:
      cfmask xarray.DataArray
    -----
    Usage:
      dataset_in['cf_mask'] = slc_to_cfmask(dataset_in.slc)
    """

    import sys

    # Reclassify unsing a lookup table and indexing properties
    # lookups = [(0,255), (1,255), (2,0), (3,2), (4,0), (5,0), (6,1), (7,255), (8,4), (9,4), (10,4), (11,3)]  # Conservative 7 -> 255 (unclassified -> fill)
    lookups = [(0,255), (1,255), (2,0), (3,2), (4,0), (5,0), (6,1), (7,0), (8,4), (9,4), (10,4), (11,3)]    # 7 ->  0 (unclassified -> clear)

    idx, val = np.asarray(lookups).T
    lookup_array = np.zeros(idx.max() + 1)
    lookup_array[idx] = val

    cfmask = lookup_array[slc_da.values].astype(np.uint8)

    # Add cfmask ndarray tinto the xarray.Dataset
    cfmask = xr.DataArray(cfmask,
                          coords={'latitude': slc_da['latitude'].values,
                                  'longitude': slc_da['longitude'].values,
                                  'time': slc_da['time'].values},
                          dims=['time', 'latitude', 'longitude'])
    return cfmask

def monit_sys(proc_time = 10):
    """
    Description:
      Monitor and average CPU and RAM activity during a given time
    -----
    Input:
      proc_time: monitoring time (in seconds, 10 by default)
    Output:
      on screen
    """

    blocks_nb = 20 # length of the percentage bar
    cpu_log = []
    mem_log = []

    for i in range(proc_time, 0, -1):
        # get used CPU percentage values
        cpu_pc = psutil.cpu_percent()
        cpu_blocks = int(cpu_pc / 100 * blocks_nb)
        cpu_log.append(cpu_pc)

        # get used RAM percentage
        mem_pc = psutil.virtual_memory().percent
        mem_blocks = int(mem_pc / 100 * blocks_nb)
        mem_log.append(mem_pc)

        # Print out instant values
        clear_output(wait = True) # refresh display
        print('Monitoring: wait %i seconds' % (i))
        print('CPU\t[%s%s]' % ('#' * cpu_blocks, '-' * (blocks_nb - cpu_blocks)))
        print('MEM\t[%s%s]' % ('#' * mem_blocks, '-' * (blocks_nb - mem_blocks)))

        time.sleep(1)

    # Calulate average
    cpu_avg = sum(cpu_log) / len(cpu_log)
    mem_avg = sum(mem_log) / len(mem_log)

    # Print out averaged values
    clear_output(wait = True)
    print('%i seconds average:' % (proc_time))
    print('CPU\t %5.1f%%' % (cpu_avg))
    print('MEM\t %5.1f%%' % (mem_avg))


def dt_export(dt, meas, fname, ext):
    clear_attrs(dt)
    if ext == "nc":
        dt.to_netcdf('%s.nc' % (fname))
    elif ext == "tif":
        write_geotiff_from_xr('%s.tif' % (fname), dt, meas, nodata=-9999)


def easy_export(data, prfx, ncortif):
    """
    Description:
      Export any xarray Dataset or DataArray as either .nc ot .tif
    -----
    Input:
      data: xarray.Dataset or xarray.DataArray to be exported
      prfx: prefix to be used to name the exported file(s)
      ncortif: either nc(netcdf) or tif (geotiff)
    Output:
      .nc or .tif file(s) sliced by date (prfx_YYYYMMDDhhmmss.nc or .tif)
    """

    if ncortif not in ["nc", "tif"]:
        return "!!! Export format need to be either 'nc' (netcdf) or 'tif' (geotiff) !!!"

    if "DataArray" in str(type(data)):
        data = data.to_dataset(name=prfx)

    measurements = list(data.data_vars)

    if 'time' not in data.dims:
        dt_export(data, measurements, '%s' % (prfx), ncortif)
    else:
        for index in range(len(data.time)):
            datime = int(pd.to_datetime(
                str(data.isel(time=index).time.values)).strftime('%Y%m%d%H%M%S'))
            data_slice = data.isel(time=index).drop('time')
            dt_export(data_slice, measurements, '%s_%i' %
                      (prfx, datime), ncortif)
    return "xarray exported succesfully"


def easy_map(data, leg, title, bar_title):
    # To be adapted
    max_pixels = 2000
    max_size = 10
    # Estimate aspect
    pxx = data.sizes['longitude']
    pxy = data.sizes['latitude']
    ratio = int(max(pxy, pxx) / max_pixels)

    orient = 'horizontal'
    cb_pad = 0.03
    if pxx < pxy:
        orient = 'vertical'
        cb_pad = 0.01

    fig, ax = plt.subplots(figsize=(max_size, max_size))

    if ratio > 1:
        to = data[::ratio, ::ratio]
        cax = ax.imshow(to, interpolation='nearest', cmap=leg)
        plt.xticks([0, to.shape[1]], [round(float(np.min(to.longitude)), 1), round(
            float(np.max(to.longitude)), 1)])
        plt.yticks([to.shape[0], 0], [
                   round(float(np.min(to.latitude)), 1), round(float(np.max(to.latitude)), 1)])
    else:
        cax = ax.imshow(data, interpolation='nearest', cmap=leg)
        plt.xticks([0, data.shape[1]], [round(float(np.min(data.longitude)), 1), round(
            float(np.max(data.longitude)), 1)])
        plt.yticks([data.shape[0], 0], [round(
            float(np.min(data.latitude)), 1), round(float(np.max(data.latitude)), 1)])

    cbar = fig.colorbar(cax, orientation=orient, aspect=100, pad=cb_pad)
    cbar.set_label(label='%s - %s' % (title, bar_title), weight='bold')
    plt.xlabel('Longitude', labelpad=-10)
    plt.ylabel('Latitude', labelpad=-25)

    plt.draw()

def easy_map(data, leg, bar_title, max_size = 10):
    """
    Description:
      Create a map of an xarray DataArray.
    -----
    Input:
      data: xarray.DataArray to be mapped
      leg: colormap to be applied (either standard (https://matplotlib.org/examples/color/colormaps_reference.html) or custom)
      bar_title: Title of the colorbar
      max_size: maximum size of the figure (either horizontal or vertical), 10 by default
    Output:
      map
    """

    # To be adapted
    max_pixels = 2000

    # Estimate aspect
    pxx = data.sizes['longitude']
    pxy = data.sizes['latitude']
    ratio = int(max(pxy, pxx) / max_pixels)

    orient = 'horizontal'
    cb_pad = 0.03
    if pxx < pxy:
        orient = 'vertical'
        cb_pad = 0.01

    fig, ax = plt.subplots(figsize=(max_size, max_size))

    if ratio > 1:
        to = data[::ratio, ::ratio]
        cax = ax.imshow(to, interpolation='nearest', cmap=leg)
        plt.xticks([0, to.shape[1]], [round(float(np.min(to.longitude)), 1), round(
            float(np.max(to.longitude)), 1)])
        plt.yticks([to.shape[0], 0], [
                   round(float(np.min(to.latitude)), 1), round(float(np.max(to.latitude)), 1)])
    else:
        cax = ax.imshow(data, interpolation='nearest', cmap=leg)
        plt.xticks([0, data.shape[1]], [round(float(np.min(data.longitude)), 1), round(
            float(np.max(data.longitude)), 1)])
        plt.yticks([data.shape[0], 0], [round(
            float(np.min(data.latitude)), 1), round(float(np.max(data.latitude)), 1)])

    cbar = fig.colorbar(cax, orientation=orient, aspect=100, pad=cb_pad)
    cbar.set_label(label=bar_title, weight='bold')
    plt.xlabel('Longitude', labelpad=-10)
    plt.ylabel('Latitude', labelpad=-25)

    plt.draw()
