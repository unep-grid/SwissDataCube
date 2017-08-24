# Create and ingest a new product (e.g. Landsat 7 SR from USGS)
* Order SR scenes from (https://espa.cr.usgs.gov)

![](../media/ordering_ESPA.png)

* Download scenes faster using Firefox plugin DownThemAll

* Adapt and place *ls7_collections_sr_scene.yaml* in */home/sdcuser/Datacube/agdc-v2/ingest/dataset_types*
* Adapt and place *ls7_collections_sr_ch.yaml* in */home/sdcuser/Datacube/agdc-v2/ingest/ingestion_configs*
* Copy the file *usgs_ls_ard_prepare.py* from *.../agdc-v2/ingest/prepare_scripts/landsat_collection* to *.../agdc-v2/ingest/prepare_scripts*

