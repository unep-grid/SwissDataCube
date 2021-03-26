# Swiss and Open datacube utilities

This repository provides the Swiss datacube and Open datacube missing utils files for the Baobab cluster at University of Geneva.

The utils files are the following notebook files:

* The provided Swiss datacube were pulled from the [bruno.chatenoux](https://git.unepgrid.ch/bruno.chatenoux/sdc_notebook) (UNEP) repository.

* The provided Open datacube utils were pulled from the [CEOS-SEO](https://github.com/ceos-seo/data_cube_utilities) repository.

* The provided Open datacube utils were pulled from the [opendatacube](https://github.com/opendatacube/datacube-notebooks) repository. Those utils are currently **unused** but are still there for testing purpose.

## Installation

The installation process is in two step: (i) install the provided utils files by copying them in an installation directory.
Then (ii) add the provided module file in your modules path.

### Step 1: install the utils files

Log in to baobab: `baobab2.hpc.unige.ch` (SSH).
Then clone the repository to any installation directory of your choice.
Take note of the installation path where the files have been pulled.

In your Baobab home directory:
```
$ mkdir py_libs
$ cd py_libs
$ git clone git@github.com:GRIDgva/SwissDataCube.git
```

Then you'll see in the `SwissDataCube/baobab` folder the utils files stored in two subfolders.

### Step 2: add the new module

In the pulled repository you'll see in the `modulefiles` folder a `dc_utils.own` module file.
The path of this file must be added to the `MODULEPATH` environment variable.

To do so edit your `.bashrc` file stored in your home folder and add the following line at the end of the file:
```
export MODULEPATH=${MODULEPATH}:${HOME}/py_libs/SDCUtils/SwissDataCube/baobab/py_src/
```
if you used the clone/install directory from the previous step.
Otherwise provide instead of `${HOME}/py_libs` the directory you used in step 1.

Then in the `modulefiles/dc_utils.own` stored in the cloned repository, modify the line:
```
prepend-path PYTHONPATH REPLACE_THIS_BY_YOUR_PATH
```
to one containing the path to `dc_utils`, i.e:
```
prepend-path PYTHONPATH /home/user/py_libs/SDCUtils/SwissDataCube/baobab/py_src/
```

Once this is done, log out and log back in to Baobab.
Or source your `.bashrc` file.

Once it's done, check the `MODULEPATH` contains your path:
```
$ echo $MODULEPATH
/etc/modulefiles:/usr/share/modulefiles:/opt/modulefiles/Linux:/usr/share/lmod/
lmod/modulefiles/Core:/opt/ebmodules/all/Core:/home/user/py_libs/SDCUtils/SwissDataCube/baobab/
modulefiles
```

## Usage of dc_utilties

Once the lmod module installed it needs to be loaded on Baobab and then imported in your Python code.

### Usage of the Lmod modules (Baobab)

Now you can simply load the module as any other module on Baobab:
```
$ module spider dc_utils

---------------------------------------------------
  dc_utils.own: dc_utils.own
----------------------------------------------------

    This module can be loaded directly: module load 
    dc_utils.own

    Help:
      Adds Open datacube and Swiss datacube utilities 
      to the Python environment

```
For example to have the full datacube libs, you can do:
```
module load GCC/8.2.0-2.31.1 
module load OpenMPI/3.1.3
module load SwissDatacube/0.0.1-Python-3.7.2
module load dc_utils.own
```

### Usage of the Python modules (in your scripts)

If you try to import the python module without loading the module on Baobab, you'll get an error like:
```python
>>> from utils.data_cube_utilities.dc_chunker import create_geographic_chunks, 
    combine_geographic_chunks
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ModuleNotFoundError: No module named 'utils'
```

But now that the module are loaded, and assuming `datacube` is imported, they can be imported like:
```python
>>> from swiss_utils.data_cube_utilities.sdc_utilities import load_multi_clean
```

for the UNEP utils. 
And then we can call its functions, like:
```python
>>> load_multi_clean(...)
```

The same can be done for the CEOS-SEO utils:
```python
>>> from utils.data_cube_utilities.dc_display_map import display_map, _degree_to_zoom_level
>>> from utils.data_cube_utilities.dc_chunker import create_geographic_chunks, 
    combine_geographic_chunks
>>> display_map(...)
>>> combine_geographic_chunks(...)
```
