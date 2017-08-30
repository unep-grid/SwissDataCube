# Changing collection 1 mask options

Identify the bit values using the appropriate *yaml* in *agdc-v2/ingest/dataset_types*

```yaml
    - name: 'pixel_qa'
      aliases: [pixel_qa]
      dtype: uint16
      nodata: 1
      units: 'bit_index'
      flags_definition:
        pixel_qa:
          bits: [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
          description: Level 2 Pixel Quality Band
          values:
            1: Fill
            2: Clear
            4: Water
            8: Cloud shadow
            16: Snow
            32: Cloud
            64: Cloud Confidence Low Bit
            128: Cloud Confidence High Bit
            256: Unused
            512: Unused
            1024: Unused
            2048: Unused
            4096: Unused
            8192: Unused
            16384: Unused
            32786: Unused
```

Then adapt the *create_cfmask_clean_mask* function in the appropriate task.py (in our case *data_cube_ui/apps/custom_mosaic_tool/tasl.py*):
```python
clear_mask = create_cfmask_clean_mask(data.cf_mask) if 'cf_mask' in data else create_bit_mask(data.pixel_qa,
                                                                                                            [1, 2, 4])
```
Be careful as you can have several fucntion called several time in a single python script.

Another radical option is to bypass the *valid_bits* list in the script *data_cube_ui/utils/dc_utilities*:
```python
def create_bit_mask(data_array, valid_bits, no_data=-9999):
    valid_bits = [1, 2, 4]
```
