# Adapt scale to custom mosaic product
In the case the datacube contains products with large values range difference (for example USGS SR values are ~10x the values of GRID made SR).
* Modify lines 390 and 455 *data_cube_ui/apps/custom_mosaic_tool/tasks.py* into (the range need to be adapted)
```python
        scale = (0, 4096) if "C1" in task.platform else (0, 500),
```
* Then via ssh:
```
sudo /etc/init.d/data_cube_ui restart
sudo /etc/init.d/celerybeat restart
```
