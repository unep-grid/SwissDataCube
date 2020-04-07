# coding=utf-8
"""
Ingest data from the command-line.
"""
from __future__ import absolute_import, division

from __future__ import print_function
import logging
import uuid
from xml.etree import ElementTree
import re
from pathlib import Path
import yaml
from dateutil import parser
from datetime import datetime, timedelta
import rasterio.warp
import click
from osgeo import osr
import os


def band_name(path):
    if '_VH_' in str(path):
        layername = 'vh_gamma0'
    if '_VV_' in str(path):
        layername = 'vv_gamma0'

    return layername


def get_projection(path):
    with rasterio.open(str(path)) as img:
        left, bottom, right, top = img.bounds

        return {
            'spatial_reference': str(str(getattr(img, 'crs_wkt', None) or img.crs.wkt)),
            'geo_ref_points': {
                'ul': {'x': left, 'y': top},
                'ur': {'x': right, 'y': top},
                'll': {'x': left, 'y': bottom},
                'lr': {'x': right, 'y': bottom},
            }
        }


def get_coords(geo_ref_points, spatial_ref):
    spatial_ref = osr.SpatialReference(spatial_ref)
    t = osr.CoordinateTransformation(spatial_ref, spatial_ref.CloneGeogCS())

    def transform(p):
        lon, lat, z = t.TransformPoint(p['x'], p['y'])
        return {'lon': lon, 'lat': lat}

    return {key: transform(p) for key, p in geo_ref_points.items()}


def populate_coord(doc):
    proj = doc['grid_spatial']['projection']

    doc['extent']['coord'] = get_coords(proj['geo_ref_points'], proj['spatial_reference'])


def prep_dataset(fields, path):
    aos = datetime.strptime(path.stem[14:26], '%Y%m%d%H%M')
    los = datetime.strptime(path.stem[29:41], '%Y%m%d%H%M')
    cos = aos + (los - aos) / 2
    start_time = aos
    end_time = los
    fields['creation_dt'] = aos
    fields['satellite'] = 'SENTINEL_1'

    images = {band_name(im_path): {
        'path': str(im_path.relative_to(path))
    } for im_path in path.glob('*.tif')}

    doc = {
        'id': str(uuid.uuid4()),
        'processing_level': "L3 backscatter composite",
        'product_type': "gamma0",
        'creation_dt': aos,
        'platform': {'code': 'SENTINEL_1_L3C'},
        'instrument': {'name': 'SAR'},
        'acquisition': {'groundstation': {'code': 'XXX', 'aos': str(aos), 'los': str(los)}
                        },
        'extent': {
            'from_dt': str(start_time),
            'to_dt': str(end_time),
            'center_dt': str(cos)
        },
        'format': {'name': 'GeoTiff'},
        'grid_spatial': {
            'projection': get_projection(path / next(iter(images.values()))['path'])
        },
        'image': {
            'bands': images
        },
        'lineage': {'source_datasets': {}}
    }
    populate_coord(doc)
    return doc


def prepare_datasets(s1_path):
    fields = {'level': 'gamma0', 'type': 'intensity'}
    s1 = prep_dataset(fields, s1_path)
    return (s1, s1_path)


@click.command(help="Prepare SENTINEL 1 L3 backscatter composite processed by UZH Geography Dept. for ingestion into the Data Cube.")
@click.argument('datasets',
                type=click.Path(exists=True, readable=True, writable=True),
                nargs=-1)
def main(datasets):
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)

    for dataset in datasets:
        path = Path(dataset)

        logging.info("Processing %s", path)
        documents = prepare_datasets(path)

        dataset, folder = documents
        yaml_path = str(folder.joinpath('l3comp-metadata.yaml'))
        logging.info("Writing %s", yaml_path)
        with open(yaml_path, 'w') as stream:
            yaml.dump(dataset, stream)


if __name__ == "__main__":
    main()
