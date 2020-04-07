# coding=utf-8
"""
Prepare a Sentinel 2 L2A scene prepared with dc_preproc scripts for datacube indexing and ingestion.

This script uses the MTD_MSIL1C.xml or S2A_USER_MTD_L2A_DS*.xml files.

Created by Bruno Chatenoux (GRID-Geneva, the 22.11.2017)

To be run from datacube_env
"""
import click
import logging
from pathlib import Path
import re
import os
from dateutil import parser
import uuid
import rasterio.warp
from osgeo import osr
import yaml

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

def prep_dataset(fields, path):
    images_list = []
    for file in os.listdir(str(path)):
        if file == "MTD.xml":
            metafile = os.path.join(str(path),file)
        if file.startswith("L2A_")  and file.endswith(".tif") :
            images_list.append(os.path.join(str(path),file))
    
    with open(metafile) as searchfile:
        for line in searchfile:
            if "DATASTRIP_SENSING_START" in line:
                aos = parser.parse(re.findall(r'\>(.*)\<', line)[0])
            if "DATASTRIP_SENSING_STOP" in line:
                los = parser.parse(re.findall(r'\>(.*)\<', line)[0])
            if "PROCESSING_CENTER" in line:
                name = re.findall(r'\>(.*)\<', line)[0]
            if "UTC_DATE_TIME" in line:
                creation_dt = parser.parse(re.findall(r'\>(.*)\<', line)[0])

    center_dt = aos + (los-aos)/2

    images = {im_path.stem.replace('L2A_',''): {
        'path': str(im_path.relative_to(path))   
    } for im_path in path.glob('*.tif')}

    projdict = get_projection(path/next(iter(images.values()))['path'])

    doc = {
        'id': str(uuid.uuid4()),
        'processing_level': fields["level"],
        'product_type': fields["type"],
        'creation_dt':  str(creation_dt.strftime('%Y-%m-%d %H:%M:%S')),
        'platform': {'code': 'SENTINEL_2'},
        'instrument': {'name': fields["instrument"]},
        'acquisition': {
            'groundstation': {
                'name': name.replace('_', ''),
                'aos': str(aos.strftime('%Y-%m-%d %H:%M:%S')),
                'los': str(los.strftime('%Y-%m-%d %H:%M:%S'))
            }
        },
        'extent': {
            'from_dt': str(aos.strftime('%Y-%m-%d %H:%M:%S')),
            'to_dt': str(los.strftime('%Y-%m-%d %H:%M:%S')),
            'center_dt': str(center_dt.strftime('%Y-%m-%d %H:%M:%S'))
        },
        'format': {'name': 'GeoTiff'},
        'grid_spatial': {
            'projection': projdict   
        },
        'image': {
            'tile': fields["tile"],
            'bands': images
        },
       
        'lineage': {'source_datasets': {}}
    }
    
    populate_coord(doc)
    return doc

def prepare_datasets(nbar_path):
    # S2A_MSIL1C_20160717T104026_N0204_R008_T32TLS_20160718T060439
    fields = re.match((r"(?P<sensor>S2A|S2B)_MSIL1C_"
                       r"(?P<productyear>[0-9]{4})"
                       r"(?P<productmonth>[0-9]{2})"
                       r"(?P<productday>[0-9]{2})T"
                       r"(?P<producthour>[0-9]{2})"
                       r"(?P<productminute>[0-9]{2})"
                       r"(?P<productsecond>[0-9]{2})_N"
                       r"(?P<baselinenumber>[0-9]{4})_R"
                       r"(?P<relativeorbit>[0-9]{3})_T"
                       r"(?P<tile>[A-Z0-9]{5})_"), nbar_path.stem).groupdict()

    fields.update({'level': 'L2A',
        'type': 'dc_preproc',
        'instrument': 'MSI',
        'creation_dt': '%s-%s-%s 00:00:00' % (fields['productyear'], fields['productmonth'], fields['productday'])})

    nbar = prep_dataset(fields, nbar_path)
    return (nbar, nbar_path)

@click.command(help="Prepare a Sentinel 2 L2A scene prepared with dc_preproc scripts for datacube indexing and ingestion.")
@click.argument('datasets', type=click.Path(exists=True, readable=True, writable=True), nargs=-1)
def main(datasets):
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.ERROR)
    print("Entering program")
    for dataset in datasets:
        path = Path(dataset)
        print("Processing", path)
        logging.info("Processing %s", path)
        documents = prepare_datasets(path)
        print("completed preparing dataset, about to write output")
        dataset, folder = documents
        yaml_path = str(folder.joinpath('agdc-metadata.yaml'))
        logging.info("Writing %s", yaml_path)
        with open(yaml_path, 'w') as stream:
            yaml.dump(dataset, stream)

if __name__ == "__main__":
    main()
