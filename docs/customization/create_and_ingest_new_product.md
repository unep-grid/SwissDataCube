# Create and ingest a new product (e.g. Landsat 7 SR from USGS)
* Order SR scenes from (https://espa.cr.usgs.gov)

![](../media/ordering_ESPA.png)

* Download scenes faster using Firefox plugin DownThemAll

* Adapt and place *ls7_C1_sr_scene.yaml* in */home/sdcuser/Datacube/agdc-v2/ingest/dataset_types*
* Adapt and place *ls7_C1_sr_ch.yaml* in */home/sdcuser/Datacube/agdc-v2/ingest/ingestion_configs*
* Adapt and place *usgs_ls_ard_C1_prepare.py* in *.../agdc-v2/ingest/prepare_scripts*
* Transfer downloaded *tar.gz* to */datacube/scenes*
* Unzip them to */datacube/original_data*
* Then via ssh:
```
cd ~/Datacube/agdc-v2
source ~/Datacube/datacube_env/bin/activate
datacube product add ingest/dataset_types/ls7_C1_sr_scene.yaml
python /home/sdcuser/Datacube/agdc-v2/ingest/prepare_scripts/usgs_ls_ard_C1_prepare.py /datacube/original_data/*
datacube dataset add /datacube/original_data/*/*.yaml --auto-match
datacube -v ingest -c /home/sdcuser/Datacube/agdc-v2/ingest/ingestion_configs/ls7_C1_sr_ch.yaml
deactivate
```
* Add your product in the datacube using the admin section

![](../media/admin_new_product.png)
