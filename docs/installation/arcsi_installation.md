# ARCSI installation
## Install anaconda
```
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
source ~/.bashrc
rm Miniconda3-latest-Linux-x86_64.sh
conda update conda --yes
```
## Install ARCSI
```
conda create --name osgeoenv python=3.5 --yes
source activate osgeoenvconda install -c conda-forge arcsi --yes
conda update -c conda-forge --allarcsi.py -h # To test installation
source deactivate
```
