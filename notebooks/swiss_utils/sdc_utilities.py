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
import pandas as pd
import numpy as np

import matplotlib.pyplot as plt
from matplotlib import colors

from utils.dc_utilities import clear_attrs, write_geotiff_from_xr


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
        dt_export(data, measurements, '%s.nc' % (prfx), ncortif)
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