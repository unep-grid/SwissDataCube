# Changing pre-collection mask options
Adapt the clean_mask values in *data_cube_ui/utils/cd_utilities.py*
```python
    #########################
    # cfmask values:        #
    #   0 - clear           #
    #   1 - water           #
    #   2 - cloud shadow    #
    #   3 - snow            #
    #   4 - cloud           #
    #   255 - fill          #
    #########################

    clean_mask = (cfmask == 0) | (cfmask == 1)
```
