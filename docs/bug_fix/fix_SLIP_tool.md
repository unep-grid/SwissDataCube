# Fix SLIP tool
Using https://earthexplorer.usgs.gov/ > Data Sets > Digital Elevation > ASTER GLOBAL DEM.

Download tiles and unzip them on the server in */original_data/* folder.
```
cd ~/Datacube/agdc-v2
source ~/Datacube/datacube_env/bin/activate
datacube product add ingest/dataset_types/aster_gdem/aster_gdem_product_definition.yaml # DO IT ONLY THE 1ST TIME
datacube product list # just to check
python ./ingest/prepare_scripts/aster_gdem/aster_gdem2_prepare_bc.py -p /datacube/original_data/ASTGTM2_N42E042/ # modified by BC: ASTGTM2_N??W???_ -> ASTGTM2_???????_
datacube dataset add /datacube/original_data/*/*.yaml --auto-match
datacube -v ingest -c ./ingest/ingestion_configs/aster_gdem_wgs84_georgia.yaml --executor multiproc 3
deactivate
```
