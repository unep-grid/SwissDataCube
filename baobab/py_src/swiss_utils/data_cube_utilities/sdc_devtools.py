# Copyright 2019 GRID-Geneva. All Rights Reserved.
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

import os
import glob

import numpy as np
import xarray as xr

from IPython.display import HTML

# source: https://gist.github.com/seberg/3866040
def rolling_window(array, window=(0,), asteps=None, wsteps=None, axes=None, toend=True):
    """
    Create a view of `array` which for every point gives the n-dimensional
    neighbourhood of size window. New dimensions are added at the end of
    `array` or after the corresponding original dimension.
    
    Parameters
    ----------
    array : array_like
        Array to which the rolling window is applied.
    window : int or tuple
        Either a single integer to create a window of only the last axis or a
        tuple to create it for the last len(window) axes. 0 can be used as a
        to ignore a dimension in the window.
    asteps : tuple
        Aligned at the last axis, new steps for the original array, ie. for
        creation of non-overlapping windows. (Equivalent to slicing result)
    wsteps : int or tuple (same size as window)
        steps for the added window dimensions. These can be 0 to repeat values
        along the axis.
    axes: int or tuple
        If given, must have the same size as window. In this case window is
        interpreted as the size in the dimension given by axes. IE. a window
        of (2, 1) is equivalent to window=2 and axis=-2.       
    toend : bool
        If False, the new dimensions are right after the corresponding original
        dimension, instead of at the end of the array. Adding the new axes at the
        end makes it easier to get the neighborhood, however toend=False will give
        a more intuitive result if you view the whole array.
    
    Returns
    -------
    A view on `array` which is smaller to fit the windows and has windows added
    dimensions (0s not counting), ie. every point of `array` is an array of size
    window.
    """
    
    array = np.asarray(array)
    orig_shape = np.asarray(array.shape)
    window = np.atleast_1d(window).astype(int) # maybe crude to cast to int...
    
    if axes is not None:
        axes = np.atleast_1d(axes)
        w = np.zeros(array.ndim, dtype=int)
        for axis, size in zip(axes, window):
            w[axis] = size
        window = w
    
    # Check if window is legal:
    if window.ndim > 1:
        raise ValueError("`window` must be one-dimensional.")
    if np.any(window < 0):
        raise ValueError("All elements of `window` must be larger then 1.")
    if len(array.shape) < len(window):
        raise ValueError("`window` length must be less or equal `array` dimension.") 

    _asteps = np.ones_like(orig_shape)
    if asteps is not None:
        asteps = np.atleast_1d(asteps)
        if asteps.ndim != 1:
            raise ValueError("`asteps` must be either a scalar or one dimensional.")
        if len(asteps) > array.ndim:
            raise ValueError("`asteps` cannot be longer then the `array` dimension.")
        # does not enforce alignment, so that steps can be same as window too.
        _asteps[-len(asteps):] = asteps
        
        if np.any(asteps < 1):
             raise ValueError("All elements of `asteps` must be larger then 1.")
    asteps = _asteps
    
    _wsteps = np.ones_like(window)
    if wsteps is not None:
        wsteps = np.atleast_1d(wsteps)
        if wsteps.shape != window.shape:
            raise ValueError("`wsteps` must have the same shape as `window`.")
        if np.any(wsteps < 0):
             raise ValueError("All elements of `wsteps` must be larger then 0.")

        _wsteps[:] = wsteps
        _wsteps[window == 0] = 1 # make sure that steps are 1 for non-existing dims.
    wsteps = _wsteps

    # Check that the window would not be larger then the original:
    if np.any(orig_shape[-len(window):] < window * wsteps):
        raise ValueError("`window` * `wsteps` larger then `array` in at least one dimension.")

    new_shape = orig_shape # just renaming...
    
    # For calculating the new shape 0s must act like 1s:
    _window = window.copy()
    _window[_window==0] = 1
    
    new_shape[-len(window):] += wsteps - _window * wsteps
    new_shape = (new_shape + asteps - 1) // asteps
    # make sure the new_shape is at least 1 in any "old" dimension (ie. steps
    # is (too) large, but we do not care.
    new_shape[new_shape < 1] = 1
    shape = new_shape
    
    strides = np.asarray(array.strides)
    strides *= asteps
    new_strides = array.strides[-len(window):] * wsteps
    
    # The full new shape and strides:
    if toend:
        new_shape = np.concatenate((shape, window))
        new_strides = np.concatenate((strides, new_strides))
    else:
        _ = np.zeros_like(shape)
        _[-len(window):] = window
        _window = _.copy()
        _[-len(window):] = new_strides
        _new_strides = _
        
        new_shape = np.zeros(len(shape)*2, dtype=int)
        new_strides = np.zeros(len(shape)*2, dtype=int)
        
        new_shape[::2] = shape
        new_strides[::2] = strides
        new_shape[1::2] = _window
        new_strides[1::2] = _new_strides
    
    new_strides = new_strides[new_shape != 0]
    new_shape = new_shape[new_shape != 0]
    
    return np.lib.stride_tricks.as_strided(array, shape=new_shape, strides=new_strides)

def ds_focus(ds, dough_width, stat):
    """
    Select within an `array` the window (size given by `dough_width`) with sum of min, max values
    (defined by `stat`argument).
    
    Parameters
    ----------
    ds : xarray.Dataset
        Xarray.Dataset to to be focused on.
    dough_width : int
        doughnut width (window size will be 2 * dough_size + 1).
    stat : string ('min', 'max')
        stat type to apply for window selection.
    
    Returns
    -------
    An extract of ds containing the min or max sum of data count.
    """
    # check ds
    assert ('Dataset' in str(type(ds))), \
           '\n<ds> must be an xarray.Dataset !'
    
    # check dough_width
    assert ((isinstance(dough_width, int)) & (dough_width > 0)), \
           '\n<dough_width> must be a positive integer !'
    assert (min(len(ds.latitude), len(ds.longitude)) > dough_width * 2 + 1), \
           '\n<dough_width> should make a window smaller than the dataset !'
    
    # check start arguments
    stat_args = ['min', 'max']
    assert (stat in stat_args), \
           '\n<stat> argument must be one element of the list %s !' % stat_args
    
    # data count through time for the first band
    arr = ds[list(ds.var())[0]].count(dim=['time']).values
    
    # apply a "rolling window" sum filter on the count
    sums = rolling_window(arr, (dough_width * 2 + 1, dough_width * 2 + 1)).sum((2,3))
    
    # get the coords of the first pixel with targimum sum value
    sums_da = xr.DataArray(sums, dims = ['latitude', 'longitude'])
    sums_da = sums_da.assign_coords(latitude = ds.latitude[dough_width:len(ds.latitude) - dough_width],
                                    longitude = ds.longitude[dough_width:len(ds.longitude) - dough_width])
    if stat == 'min':
        targ_sum = sums_da.where(sums_da == sums_da.values.min(), drop=True)
    elif stat == 'max':
        targ_sum = sums_da.where(sums_da == sums_da.values.max(), drop=True)          
    targ_sum = targ_sum.to_dataframe(name = 'count').dropna().reset_index()[:1]
    
    # get new AOI
    ctr_lat_index = np.where(ds.latitude.values == float(targ_sum['latitude']))[0]
    ctr_lon_index = np.where(ds.longitude.values == float(targ_sum['longitude']))[0]
    # index seems inverted for latitude !!!
    targ_min_lat = ds.latitude.values[ctr_lat_index + dough_width][0]
    targ_max_lat = ds.latitude.values[ctr_lat_index - dough_width][0]
    targ_min_lon = ds.longitude.values[ctr_lon_index - dough_width][0]
    targ_max_lon = ds.longitude.values[ctr_lon_index + dough_width][0]

    # subset dataset (and mask)
    targ_ds = ds.sel(latitude = (ds.latitude >= targ_min_lat) &
                                (ds.latitude <= targ_max_lat),
                    longitude = (ds.longitude >= targ_min_lon) &
                                (ds.longitude <= targ_max_lon))
    
    return targ_ds


# In-script function
# DO NOT RUN THIS CELL IF YOU WANT TO USE THE IMPORTED FUNCTION (LAST LINE OF CELL ABOVE)
# To make sure to not run inadvertently this cell convert it to Raw NBConvert

import os
import glob

from IPython.display import HTML

def find_ipynb(search_string, search_dir = './', search_pattern=''):
    """
    Description:
      Search (and link to) all .ipynb files containing a given <search_string>, optionally a <search_pattern> can be applied.
      e.g. find_ipynb(search_string = 'ndvi =')
             will list all scripts containing the string 'ndvi =' in the current directory
           find_ipynb(search_string = 'ndvi =', search_dir = '../../', search_pattern = 'BC_')
             will list all scripts containing 'BC_' in their name and containing the string 'ndvi ='
             in starting in 2nd level parent directory
    -----
    Input:
      search_string: string to search for example
      search_dir (OPTIONAL): search path (current folder by default)
      search_pattern (OPTIONAL): string to filter result
    Output:
      List of scripts with a direct link (do not forget to 'Close and halt' the script after reading), and the first line containing the <search_string>)
    """
    for root, dirs, files in os.walk(search_dir):
        for file in files:
            if (file.endswith('.ipynb')) and \
            not(file.endswith('-checkpoint.ipynb')) and \
            (search_pattern in file):
                fname = os.path.join(root,file)
                with open(fname) as f:
                    for line in f:
                        if search_string in line:
                            display(HTML('<a href="%s" target="_blank">%s</a><br /> %s' % (fname, fname, line.replace("\"","").strip())))
                            break
