# Fix fractional cover tool
Rename 'localuser' to 'sdcuser' in  *data_cube_ui/utils/dc_fractional_coverage_classifier.py*
```python
end_members = np.loadtxt(
        '/home/sdcuser/Datacube/data_cube_ui/utils/endmembers_landsat.csv', delimiter=',')
```
If the change is not effective, type:
> sudo /etc/init.d/data_cube_ui restart\n
> sudo /etc/init.d/celerybeat restart
