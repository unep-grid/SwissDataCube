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
import rasterio
import gdal

import numpy as np
import xarray as xr

from datetime import datetime
from numpy.lib.stride_tricks import as_strided

from utils.data_cube_utilities.dc_utilities import clear_attrs


def create_slc_clean_mask(slc, valid_cats = [4, 5, 6, 7, 11]):
    """
    Description:
      Create a clean mask from a list of valid categories,
    Input:
      slc (xarray) - slc from dc_preproc product (generated with sen2cor)
    Args:
      slc: xarray data array to extract clean categories from.
      valid_cats: array of ints representing what category should be considered valid.
      * category selected by default
      ###################################
      # slc categories:                 #
      #   0 - no data                   #
      #   1 - saturated or defective    #
      #   2 - dark area pixels          #
      #   3 - cloud_shadows             #
      #   4 * vegetation                #
      #   5 * not vegetated             #
      #   6 * water                     #
      #   7 * unclassified              #
      #   8 - cloud medium probability  #
      #   9 - cloud high probability    #
      #  10 - thin cirrus               #
      #  11 * snow                      #
      ###################################
    Output:
      clean_mask (boolean numpy array)
    """

    return xr.apply_ufunc(np.isin, slc, valid_cats).values


# Return unique values and count
def unik_count(vals):
    bc = vals.flatten()
    bc = np.bincount(bc)
    unik = np.nonzero(bc)[0]
    cnt = bc[unik] * 100
    return (unik, cnt)


# Return bit length
def bit_length(int_type):
    length = 0
    while (int_type):
        int_type >>= 1
        length += 1
    return(length)


def ls_qa_clean(dc_qa, valid_bits = [1, 2, 4]):
    """
    Description:
      create a clean mask of a Landsat Collection 1 dataset using pixel_qa band and a list of valid bits
    Input:
      dc_qa: pixel_qa band of a Landast Collection 1 xarray.DataArray
    Args:
      valid_bits: array of ints representing which bit should be considered as valid (default: clear, water, snow)
      #############################################
      # BITS : CATEGORIES                         #
      #    0 : Fill                               #
      #    1 : Clear                              #
      #    2 : Water                              #
      #    3 : Cloud shadow                       #
      #    4 : Snow                               #
      #    5 : Cloud                              #
      #   10 : Terrain occlusion (Landsat 8 only) #
      #############################################
    Output:
      clean_mask (boolean numpy array)
    """

    # Check submitted input
    if str(type(dc_qa)) != "<class 'xarray.core.dataarray.DataArray'>":
        sys.exit("SCRIPT INTERRUPTED: dc_qa should be an xarray.DataArray")
    if dc_qa.name != "pixel_qa":
        sys.exit("SCRIPT INTERRUPTED: dc_qa name  should be pixel_qa")

    # List and count all dc_qa unique values
    dc_qas, dc_cnt = unik_count(dc_qa.values)
    # Return bit encoding
    bit_len = bit_length(max(dc_qas))

    # First keep only low confidence cloud (and cirrus)
    ok_qas = []
    ko_qas = []

    if bit_len == 8: # Landsat 5 and 7
        for v in sorted(dc_qas):
            b = str(bin(v))[2:].zfill(bit_len)[::-1]
            if b[6] == '1' and b[7] == '0':
                ok_qas.append(v)
            else:
                ko_qas.append(v)

    if bit_len >= 10: # Landsat 8 (>= as sometimes pixel_qa become 11 bit !!!)
        for v in sorted(dc_qas):
            b = str(bin(v))[2:].zfill(bit_len)[::-1]
            if b[6] == '1' and b[7] == '0' and b[8] == '1' and b[9] == '0':
                ok_qas.append(v)
            else:
                ko_qas.append(v)

    # Second keep only valid_bits
    data_qas = []
    nodata_qas = []
    for v in sorted(ok_qas):
        b = str(bin(v))[2:].zfill(bit_len)[::-1]
        for c in valid_bits:
            if b[c] == '1':
                data_qas.append(v)
                break

    return xr.apply_ufunc(np.isin, dc_qa, data_qas, dask = 'allowed').values


def get_platform(dc, products):
    """
    Description:
      Create a list of platforms from a list of products
    Input:
      dc:       datacube.api.core.Datacube
                The Datacube instance to load data with.
      products: list of products
    Output:
      list of platforms
    Authors:
      Bruno Chatenoux (UNEP/GRID-Geneva, 4.3.2019)
    """
    list_of_products = dc.list_products()
    platforms = []
    for product in products:
        try:
            platforms.append(list_of_products[list_of_products['name'] == product].iloc[0]['platform'])
        except:
            sys.exit('Cannot find a platform for product \"%s\"' % (prod))
    return platforms


def load_multi_clean(dc, products, time, lon, lat, measurements, dropna = False, platforms = [], valid_cats = []):
    """
    Description:
      Create a clean dataset (multi-product or not) using cleaning "autor's recommended ways"
      - ls_qa_clean
      - create_slc_clean_mask
      Sorted by ascending time
      Works with Landsat or Sentinel 2 (but not mixed).
      Platforms arguments are not mandatory
      dropna option removes time without any data
    Input:
      dc:           datacube.api.core.Datacube
                    The Datacube instance to load data with.
    Args:
      platforms:    list of platforms (not mandatory)
      products:     list of products
      time:         pair (list) of minimum and maximum date
      lon:          pair (list) of minimum and maximum longitude
      lat:          pair (list) of minimum and maximum longitude
      measurements: list of measurements (must include pixel_qa or slc (not and !))
      dropna:       if True removes times without any data
      valid_cats:   array of ints representing what category should be considered valid
                    * meand category by default
      # SENTINEL 2 ################################
      #   0 - no data                             #
      #   1 - saturated or defective              #
      #   2 - dark area pixels                    #
      #   3 - cloud_shadows                       #
      #   4 * vegetation                          #
      #   5 * not vegetated                       #
      #   6 * water                               #
      #   7 * unclassified                        #
      #   8 - cloud medium probability            #
      #   9 - cloud high probability              #
      #  10 - thin cirrus                         #
      #  11 * snow                                #
      #############################################
      # LANDSAT 5, 7 and 8 ########################
      #    0 : Fill                               #
      #    1 * Clear                              #
      #    2 * Water                              #
      #    3 : Cloud shadow                       #
      #    4 * Snow                               #
      #    5 : Cloud                              #
      #   10 : Terrain occlusion (Landsat 8 only) #
      #############################################
    Output:
      cleaned dataset and clean_mask sorted by ascending time
    Authors:
      Bruno Chatenoux (UNEP/GRID-Geneva, 10.12.2019)
    """

    # Check submitted input
    # Convert product string into list
    if isinstance(products, str):
        products = products.split()
    # Get platforms if not provided
    if len(products) != len(platforms):
        platforms = get_platform(dc, products)
    # Check LANDSAT and SENTINEL products are not mixed using products prefix
    prfx = []
    for platform in platforms:
        prfx. append(platform.split('_')[0])
    if len(set(prfx)) > 1:
        sys.exit('Mixed platforms %s' % (set(prfx)))

    # Create raw dataset
    dataset_clean = None
    for product,platform in zip(products, platforms):
        dataset_tmp = dc.load(platform = platform, product = product,
                         time = time,
                         lon = lon,
                         lat = lat,
                         measurements = measurements)

        if len(dataset_tmp.variables) == 0: continue # skip the current iteration if empty

        # Clean dataset_tmp
        if prfx[0] == "LANDSAT":
            if len(valid_cats) == 0: valid_cats = [1, 2, 4]
            clean_mask_tmp = ls_qa_clean(dataset_tmp.pixel_qa, valid_cats)
        elif platforms[0] == "SENTINEL_2":
            if len(valid_cats) == 0: valid_cats = [4, 5, 6, 7, 11]
            clean_mask_tmp = create_slc_clean_mask(dataset_tmp.slc, valid_cats)
        dataset_clean_tmp = dataset_tmp.where(clean_mask_tmp)
        del dataset_tmp

        # Remove negative values
        dataset_clean_tmp = dataset_clean_tmp.where(dataset_clean_tmp >= 0)

        if dataset_clean is None:
            dataset_clean = dataset_clean_tmp.copy(deep=True)
        else:
            dataset_clean = xr.concat([dataset_clean, dataset_clean_tmp], dim = 'time')
        del dataset_clean_tmp


    if dropna:
        # remove time without any data
        dataset_clean = dataset_clean.dropna('time', how='all')

    if dataset_clean is not None:
        # Sort dataset by ascending time
        dataset_clean = dataset_clean.sortby('time')
        return (dataset_clean, ~np.isnan(dataset_clean[measurements[0]].values))
    else:
        return (0, 0)


# source: https://stackoverflow.com/questions/32846846/quick-way-to-upsample-numpy-array-by-nearest-neighbor-tiling
def tile_array(a, x0, x1, x2):
    t, r, c = a.shape                                    # number of rows/columns
    ts, rs, cs = a.strides                                # row/column strides
    x = as_strided(a, (t, x0, r, x1, c, x2), (ts, 0, rs, 0, cs, 0)) # view a as larger 4D array
    return x.reshape(t*x0, r*x1, c*x2)                      # create new 2D array


def updown_sample(ds_l, ds_s, resampl):
    """
    Description:
      Up or down sample a "large" resolution xarray.Dataset (so far Landsat products) and a "small" resolution
      xarray.Dataset (so far Sentinel 2 product) and combine them into a single xarray.Dataset.
      "large" resolution must be a multiple of "small" resolution and geographical extent must be adequate.
      Xarray.Dataset need to be cleaned as mask band will be removed from the output
      To enforce this requirement usage of load_lss2_clean function (without the resampl option) is
      highly recommended.

    Args:
      ds_l:         'large' resolution xarray.Dataset
      ds_s:         'small' resolution xarray.Dataset
      resampl:      'up' to upsample
                    'down_mean' to downsample using mean values
                    'down_median' to downsample using median values

    Output:
      Upsampled and combined dataset and clean_mask sorted by ascending time.
    Authors:
      Bruno Chatenoux (UNEP/GRID-Geneva, 11.12.2019)
    """

    # check resampl options
    resampl_opts = ['up', 'down_mean', 'down_median']
    assert (resampl in resampl_opts) or (resampl == ''), \
           '\nif used, resample option must be %s' % resampl_opts

    # check ds ratio
    ratiox = len(ds_s.longitude.values) / len(ds_l.longitude.values)
    ratioy = len(ds_s.latitude.values) / len(ds_l.latitude.values)
    assert (ratiox == 3), \
           '\nthe ratio of the number of columns should be 3 (Landsat/Sentinel 2 only so far) !'
    assert (ratioy == 3), \
           '\nthe ratio of the number of rows should be 3 (Landsat/Seentinel 2 only so far) !'

    # check ds resolutions
    resx_l = (ds_l.longitude.values.max() - ds_l.longitude.values.min()) / (len(ds_l.longitude.values) - 1)
    resy_l = (ds_l.latitude.values.max() - ds_l.latitude.values.min()) / (len(ds_l.latitude.values) - 1)
    resx_s = (ds_s.longitude.values.max() - ds_s.longitude.values.min()) / (len(ds_s.longitude.values) - 1)
    resy_s = (ds_s.latitude.values.max() - ds_s.latitude.values.min()) / (len(ds_s.latitude.values) - 1)
    # in reason of proper float storage issue, compare resolution with a 0.1% accuracy
    assert ((abs(resx_s - resx_l / ratiox) / resx_s * 100) < 0.1), \
           '\nthe column resolution is not a mutiple of %i !' % (ratiox)
    assert ((abs(resy_s - resy_l / ratioy) / resy_s * 100) < 0.1), \
           '\nthe row resolution is not a mutiple of %i !' % (ratioy)

    # check spacing of ds top left pixel center with a 0.1%
    assert ((abs(ds_l.longitude.values.min() - ds_s.longitude.values.min()) - resx_s) < resx_s * 0.001), \
           '\nthe longitudinal extent of both dataset do not overlay properly !' + \
           '\nuse load_lss2_clean function to fix this issue'
    assert ((abs(ds_l.latitude.values.min() - ds_s.latitude.values.min()) - resy_s) < resy_s * 0.001), \
           '\nthe latitudinal extent of both dataset do not overlay properly !' + \
           '\nuse load_lss2_clean function to fix this issue'

    # check vars (without mask band as they will no be combined)
    vars_l = [ele for ele in sorted(list(ds_l.data_vars)) if ele not in ['pixel_qa', 'slc']]
    vars_s = [ele for ele in sorted(list(ds_s.data_vars)) if ele not in ['pixel_qa', 'slc']]
    assert (vars_l == vars_s), \
           '\nmeasurements in dataset are not identical'

    # upsample "large" dataset (using temporary array)
    for index, var in enumerate(vars_l):
        if resampl == 'up':
            arr_l = tile_array(ds_l[var].values, 1, int(ratiox), int(ratioy))
            da_l = xr.DataArray(arr_l, dims=['time', 'latitude', 'longitude'])
            da_l = da_l.assign_coords(time = ds_l.time,
                                        latitude = ds_s.latitude,
                                        longitude = ds_s.longitude)
            # combine s and l
            da = xr.concat([ds_s[var], da_l], dim = 'time')
        elif resampl[:5] == 'down_':
            # source: https://stackoverflow.com/questions/42463172/how-to-perform-max-mean-pooling-on-a-2d-array-using-numpy/42463491#42463491
            # 4x faster than skimage way (who has an issue with median function in the case of large stdev !)
            t, lat, lon = ds_s[var].values.shape
            nlat = lat // ratiox
            nlon = lon // ratioy
            if resampl == 'down_median':
                arr_s = np.nanmedian(ds_s[var].values[:1*t, :int(nlat*ratioy), :int(nlon*ratiox)]. \
                        reshape(1, t, int(nlat), int(ratioy), int(nlon), int(ratiox)), axis=(0, 3, 5))
            elif resampl == 'down_mean':
                arr_s = np.nanmean(ds_s[var].values[:1*t, :int(nlat*ratioy), :int(nlon*ratiox)]. \
                        reshape(1, t, int(nlat), int(ratioy), int(nlon), int(ratiox)), axis=(0, 3, 5))
            da_s = xr.DataArray(arr_s, dims=['time', 'latitude', 'longitude'])
            da_s = da_s.assign_coords(time = ds_s.time,
                                      latitude = ds_l.latitude,
                                      longitude = ds_l.longitude)
            # combine l and s
            da = xr.concat([ds_l[var], da_s], dim = 'time')

        if index == 0:
            ds = da.to_dataset(name = var)
        else:
            ds = ds.merge(da.to_dataset(name = var))

    # Sort dataset by ascending time
    ds = ds.sortby('time')

    return ds


def load_lss2_clean(dc, products, time, lon, lat, measurements,
                   resampl = '', dropna = False, platforms = [], valid_cats = [[],[]]):
    """
    Description:
      Create a clean dataset mixing Landsat and Sentinel 2 products (respectively with prefixs 'ls' and 's2')
      and using cleaning "autor's recommended ways":
      - ls_qa_clean
      - create_slc_clean_mask
      Sorted by ascending time
      If resample option is activated ('up' or 'down_mean', 'down_median') up/downsampling is performed and
      products output combined into a single 'lss2' prefix
      dropna option removes time without any data
      This function works as load_multi_clean function, but with a mix of Landsat and Sentinel 2 products
      the resampl option was added (to optionally combine products output), and platforms options not used

    Input:
      dc:           datacube.api.core.Datacube
                    The Datacube instance to load data with.
    Args:
      products:     list of products
      time:         pair (list) of minimum and maximum date
      lon:          pair (list) of minimum and maximum longitude
      lat:          pair (list) of minimum and maximum longitude
      measurements: list of measurements (without mask band, landsat and Sentinel 2 products prefix shouls be
                    'ls or 's2)
      resampl:      (OPTIONAL) Up/Downsample ('up', 'down_mean', 'down_median' ) products and combine their
                    output
      dropna:       (OPTIONAL) if True removes times without any data
      platforms:    (OPTIONAL) list of platforms (not used but kept to better mimic load_multi_clean function)
      valid_cats:   (OPTIONAL) list of list of ints representing what category should be considered valid
                    first Landsat categories, then Sentinel 2 categories
                    * meand category by default
      # SENTINEL 2 ################################
      #   0 - no data                             #
      #   1 - saturated or defective              #
      #   2 - dark area pixels                    #
      #   3 - cloud_shadows                       #
      #   4 * vegetation                          #
      #   5 * not vegetated                       #
      #   6 * water                               #
      #   7 * unclassified                        #
      #   8 - cloud medium probability            #
      #   9 - cloud high probability              #
      #  10 - thin cirrus                         #
      #  11 * snow                                #
      #############################################
      # LANDSAT 5, 7 and 8 ########################
      #    0 : Fill                               #
      #    1 * Clear                              #
      #    2 * Water                              #
      #    3 : Cloud shadow                       #
      #    4 * Snow                               #
      #    5 : Cloud                              #
      #   10 : Terrain occlusion (Landsat 8 only) #
      #############################################
    Output:
      cleaned dataset and clean_mask sorted by ascending time stored in dictionnaries,
      if no up/downsampling is performed dictionnaries contains the two Landsat and Sentinel 2 output products
    Authors:
      Bruno Chatenoux (UNEP/GRID-Geneva, 11.12.2019)
    """

    # dictionnary sensor - mask band (Higher resolution first !)
    dict_sensmask = {'ls':'pixel_qa',
                     's2': 'slc'}

    resampl_opts = ['up', 'down_mean', 'down_median']

    sensors = []
    for product in products:
        if product[:2] not in sensors:
            sensors.append(product[:2])

    # check sensors
    assert (sorted(set(sensors)) == sorted(set(dict_sensmask.keys()))), \
           '\nA mix of Landsat and Sentinel 2 products is required !\nYou should use load_multi_clean function'

    assert (len(valid_cats) == 2), \
           '\nvalid_cats argument must be a list of list (read the doc for more details)'

    assert (resampl in resampl_opts) or (resampl == ''), \
           '\nif used, resample option must be %s' % resampl_opts

    dict_dsc = {}
    dict_cm = {}

    # Process first Landsat and then Sentinel 2 (based on dict_sensmask order)
    for index, sensor in enumerate(dict_sensmask.keys()):
        # Remove mask bands if any
        measurements = [ele for ele in measurements if ele not in dict_sensmask.values()]
        # append propermask band to measurements
        measurements.append(dict_sensmask[sensor])

        # fix Sentinel 2 geographical extent based on Landsat dataset
        if index == 1:
            resx = (dsc.longitude.values.max() - dsc.longitude.values.min()) / len(dsc.longitude.values)
            resy = (dsc.latitude.values.max() - dsc.latitude.values.min()) / len(dsc.latitude.values)
            lon = (dsc.longitude.values.min() - resx / 3, dsc.longitude.values.max() + resx / 3)
            lat = (dsc.latitude.values.min() - resy / 3, dsc.latitude.values.max() + resy / 3)

        dsc, cm = load_multi_clean(dc = dc,
                                  products = [prod for prod in products if prod[:2] == sensor] ,
                                  time = time,
                                  lon = lon,
                                  lat = lat,
                                  measurements = measurements,
                                  dropna = dropna,
                                  valid_cats = valid_cats[index])
        dict_dsc[sensor] = dsc
        dict_cm[sensor] = cm

    if resampl in resampl_opts :
        dsc = updown_sample(dict_dsc['ls'], dict_dsc['s2'], resampl)
        dict_dsc = {}
        dict_cm = {}
        dict_dsc['lss2'] = dsc
        dict_cm['lss2'] = ~np.isnan(dsc[measurements[0]].values)

    return dict_dsc, dict_cm


def _get_transform_from_xr(dataset):
    """Create a geotransform from an xarray dataset.
    """

    cols = len(dataset.longitude)
    rows = len(dataset.latitude)
    pixelWidth = abs(dataset.longitude[-1] - dataset.longitude[0]) / (cols - 1)
    pixelHeight = abs(dataset.latitude[-1] - dataset.latitude[0]) / (rows - 1)

    from rasterio.transform import from_bounds
    geotransform = from_bounds(dataset.longitude[0] - pixelWidth / 2, dataset.latitude[-1] - pixelHeight / 2,
                               dataset.longitude[-1] + pixelWidth / 2, dataset.latitude[0] + pixelHeight / 2,
                               cols, rows)
    return geotransform


def write_geotiff_from_xr(tif_path, dataset, bands, no_data=-9999, crs="EPSG:4326", compr=""):
    """
    Write a geotiff from an xarray dataset
    Modified for SDC:
    - fixed pixel shift bug
    - original band name added to band numbers
    - compression option added

    Args:
        tif_path: path for the tif to be written to.
        dataset: xarray dataset
        bands: list of strings representing the bands in the order they should be written
        no_data: nodata value for the dataset
        crs: requested crs
        compr: compression option (None by default), could be e.g. 'DEFLATE' or 'LZW'

    """
    assert isinstance(bands, list), "Bands must a list of strings"
    assert len(bands) > 0 and isinstance(bands[0], str), "You must supply at least one band."

    # Create the geotiff
    with rasterio.open(
            tif_path,
            'w',
            driver='GTiff',
            height=dataset.dims['latitude'],
            width=dataset.dims['longitude'],
            count=len(bands),
            dtype=dataset[bands[0]].dtype,
            crs=crs,
            transform=_get_transform_from_xr(dataset),
            nodata=no_data,
            compress=compr) as dst:
        for index, band in enumerate(bands):
            dst.write(dataset[band].values, index + 1)
        dst.close()

    # set band names
    ds = gdal.Open(tif_path, gdal.GA_Update)
    for index, band in enumerate(bands):
        rb = ds.GetRasterBand(index + 1)
        rb.SetDescription(band)
    del ds
    

def new_get_query_metadata(dc, product, quick = False):
    """
    Gets a descriptor based on a request.

    Args:
        dc: The Datacube instance to load data with.
        product (string): The name of the product associated with the desired dataset.
        quick (boolean): Attempt to quickly get metadata from a small dataset, and process
                         the full dataset if not possible. tile_count will not be evaluated
                         with this option.

    Returns:
        scene_metadata (dict): Dictionary containing a variety of data that can later be
                               accessed.
    """
    todo = True
    if quick:
        limit = 10
        ds = dc.load(product, measurements = [], limit = limit)
        if len(ds.time) == limit:
            todo = False
            tile_count = 'not calculated with quick option'
    if todo:
        ds = dc.load(product, measurements = [])
        tile_count = ds.time.size
    try:
        ds = ds.rename({'longitude': 'x', 'latitude': 'y'})
    except: 
        pass
    resx = (max(ds.x.values) - min(ds.x.values)) / (len(ds.x) -1)
    resy = (max(ds.y.values) - min(ds.y.values)) / (len(ds.y) -1)
    minx = min(ds.x.values) - resx / 2
    miny = min(ds.y.values) - resy / 2
    maxx = max(ds.x.values) + resx / 2
    maxy = max(ds.y.values) + resy / 2
    
    return {'lat_extents': (miny, maxy),
            'lon_extents': (minx, maxx),
            'time_extents': (ds.time[0].values.astype('M8[ms]').tolist(),
                             ds.time[-1].values.astype('M8[ms]').tolist()),
            'tile_count': tile_count,
            'pixel_count': len(ds.x) * len(ds.y)}
    
def summarize_products_extents(dc, products):
    """
    Returns the maximum extent (in space and time) of a given list of products.
    Args:
        dc: The Datacube instance to load data with
        products (list): List of products to get metadata from.

    Returns:
        scene_metadata (dict): Dictionary of min and max extents.
    """
    miny, maxy = 1E27, -1E27
    minx, maxx = 1E27, -1E27
    start_date, end_date = datetime.strptime('2050-12-31', '%Y-%m-%d'), datetime.strptime('1970-01-01', '%Y-%m-%d')
    for product in products:
        mt = new_get_query_metadata(dc, product)
        miny = mt['lat_extents'][0] if mt['lat_extents'][0] < miny else miny
        maxy = mt['lat_extents'][1] if mt['lat_extents'][1] > maxy else maxy
        minx = mt['lon_extents'][0] if mt['lon_extents'][0] < minx else minx
        maxx = mt['lon_extents'][1] if mt['lon_extents'][1] > maxx else maxx
        start_date = mt['time_extents'][0] if mt['time_extents'][0] < start_date else start_date
        end_date = mt['time_extents'][1] if mt['time_extents'][1] > end_date else end_date
    
    return {'lat_extents': (miny, maxy),
            'lon_extents': (minx, maxx),
            'time_extents': (start_date, end_date)}


def get_products_attributes(dc, qry, cols = ['name', 'crs', 'resolution']):
    """
    Description:
      Get products attributes using a query (WITHOUT "", e.g. products['name'].str.startswith('SPOT'))
    Input:
      dc:           datacube.api.core.Datacube
                    The Datacube instance to load data with.
    Args:
      qry:          query string, e.g.:
                    "products['name'].str.startswith('SPOT')"
                    "products['name'].str.match('^SPOT.*$')" should give the same result as startswith example
                    "products['name'].str.match('^SPOT.*_PAN_scene$')"
                    
      cols:         (OPTIONAL) list of column names to get (you can view the column available by running 'dc.list_products().columns')
    Output:
      pandas.Dataframe
    Authors:
      Bruno Chatenoux (UNEP/GRID-Geneva, 5.11.2020)
    """
    products = dc.list_products()
    prod_df = products[eval(qry)][cols].reset_index().drop(['id'], axis=1)
    prod_df['measurements'] = prod_df.apply(lambda row: sorted(map(lambda x: x['name'],
                                                                   filter(lambda x: x['product'] == row['name'],
                                                                          dc.list_measurements(with_pandas=False)))), axis=1)
    return(prod_df)

def time_list(ds):
    time_list = []
    for i in range(len(ds.time)):
        time_list.append(i)
    return time_list
